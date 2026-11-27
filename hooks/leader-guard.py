"""Leader guard for the ai-dev-team plugin (PreToolUse).

During a dev-team run the main session is the leader: it plans, briefs and talks to the user, while agents
change the project's files. This hook denies a leader tool call that would change a project file (or a file in another git repository) outside
`.ai-dev-team/` and `.claude/`, or stage a whole folder, or `cd` outside a subshell. Agent calls (the input carries `agent_id`) may edit
files, but commands that discard or move other people's work on the shared tree, kill processes by name or
detach a process from the harness are denied for everyone, a leader spawn of a team agent without an explicit `model` is denied, as are shell writes into the team files that still
expand a backtick. Agents may not write project files through inline node / python scripts or run `sed -i` over
several files (COST-8). A monitor agent may not write project files (MON-1). A leader note line in the board or decisions whose
leading time is ahead of the clock is denied (note times come from `date`). Agents may not add a third browser script to a task's `qa-artifacts/` folder within 90 minutes. Repositories without a team workspace and leader
sessions that never loaded the dev-team skill (a Skill call or a typed `/ai-dev-team:dev-team`, not the skill listing)
are left alone. Any error lets the call through.

Hotfix (UserPromptSubmit): a user prompt naming a hotfix writes a per-session marker; while it stands the leader may change
project files directly and the Stop watchdog check is skipped. Only the user's prompt sets it (no tool call may touch the
marker); `hotfix off` / `hotfix done` / `end hotfix`, a typed `/ai-dev-team:dev-team`, or 6 hours without a hotfix prompt end it.

Turned off for one machine by the user with `leader_guard: off` in `.ai-dev-team/local.md`.
"""
import calendar
import json
import mmap
import os
import re
import shlex
import sys
import tempfile
import time

ALLOWED_DIRS = ('.ai-dev-team', '.claude')
BASH_WRITES = re.compile(
    r"\bsed\s+(-[a-zA-Z]*\s+)*-i|\bperl\s+(-[a-zA-Z]*\s+)*-[a-zA-Z]*i|\bgit\s+(checkout\s+--|restore\s+(?!--staged)|stash\b|apply\b)"
)
PY_HEREDOC = re.compile(r"\bpython3?\s+(-[A-Za-z]+\s+)*-\s*<<")
PY_WRITES = re.compile(r"\.write\(|open\([^)]*['\"][wa]\+?['\"]")
PY_RETYPE = re.compile(r"\.replace\(|\bre\.sub\(")
RETYPE_REASON = (
    "ai-dev-team guard (COST-8): a `python3 -` heredoc that re-types old and new text into files is not allowed. "
    "Use the Edit tool (all changes to one file in one pass), `perl -pi -e` for one substitution across many files, "
    "or `git apply` with a unified diff; a python script only for real logic, saved as a file under $TEAM_WS.")
SHARED_TREE = re.compile(
    r"\bgit\s+(checkout\s+(--|-p\b|\S+\s+--|[^-\s]\S*[./])|restore\s+(?!--staged)|stash\b|clean\b|reset\s+--(hard|keep|merge)\b)"
    r"|\bgit\s+(rebase|pull|merge)\b[^;&|\n]*--autostash"
    r"|\bpkill\b|\bkillall\b|\bnohup\b"
    r"|(^|[^&|>])&\s*($|;|\n|\))"
    r"|\bsetsid\b|\bdisown\b"
)
WAIT_LOOP = re.compile(r"\b(while|until|for)\b[^;\n]*[;\n]?\s*do\b(?:(?!\bdone\b).)*?\bsleep\b", re.S)
WAIT_REASON = (
    "ai-dev-team guard (BASE-14, COST-3): a loop with `sleep` that waits on another process or a file is not allowed "
    "(a `pgrep -f` loop can match its own command line and never end). Run the command itself through "
    "$TEAM_BIN/run-heavy.sh (it applies a timeout) in the foreground, or with run_in_background and end your turn: "
    "you are resumed when it finishes. The leader waits with one ScheduleWakeup or Monitor checkpoint.")
AGENT_GIT = re.compile(r"\bgit\s+(switch|checkout\b|branch\s+-[dD]|commit|add|rm\b|mv\b|reset\b|restore\b)")
SHARED_REASON = (
    "ai-dev-team guard: this command can discard or hide other people's work on the shared tree or bypass the "
    "harness (BASE-11, BASE-14, BASE-15, BASE-24). Copy a file to $TEAM_WS/ and back instead of checkout/restore/"
    "stash (a branch switch is `git switch`); stop only your own background task with TaskStop <id>; run long commands with run_in_background "
    "(through run-heavy.sh), never nohup or a trailing &. Only the leader commits, at commit time."
)
TEAM_WRITE = re.compile(r"(>>?|\btee\b)[^;&|\n]*(\.ai-dev-team|TEAM_WS|TEAM_STATE)|\.ai-dev-team[^;&|\n]*&&[^;|\n]*(>>?|\btee\b)")
QUOTED_HEREDOC = re.compile(r"<<-?\s*(['\"])(\w+)\1.*?\n\2[ \t]*(\n|$)", re.S)
SINGLE_QUOTED = re.compile(r"'[^']*'")
SUBST_REASON = (
    "ai-dev-team guard: this command writes into the team files while the shell still expands a backtick in it, "
    "so `...` runs as a command and its output (a whole git diff, for example) lands in the board. "
    "Write board, notes and decisions with the Edit tool, or a heredoc with a quoted delimiter (<<'EOF'); "
    "put a time from `date` in a variable first: t=$(date +%H:%M); then use \"$t\" outside the quoted text.")
SCRIPT_TARGET = re.compile(r"(?:>|\btee\s+(?:-a\s+)?)\s*([^\s;&|<>]+\.(?:mjs|cjs|js|ts|py))\b")
BROWSER_SCRIPT = re.compile(r"playwright|chromium\.launch|webkit\.launch")
SCRIPT_REASON = (
    "ai-dev-team guard (COST-13, qa-verification browser-testing P.1): this task folder already has browser scripts "
    "written in the last 90 minutes. Extend one of them to take a list of flows or states (one browser launch, one "
    "result line per flow) and run it with arguments, instead of writing a new script and launching a browser per check.")
STAGE_ALL = re.compile(r"\bgit\s+add\s+(-A\b|--all\b|\.(\s|$)|-u\b)")
STAGE_LIST = re.compile(r"\bgit\s+add\b[^;&|\n]*--pathspec-from-file|\bxargs\b[^|;&\n]*\bgit\s+add\b")
GIT_GLOBAL = re.compile(r"\bgit((?:\s+(?:-C\s+\S+|-c\s+\S+|--git-dir(?:=|\s+)\S+|--work-tree(?:=|\s+)\S+|--no-pager|-P|--literal-pathspecs))+)(?=\s)")


def strip_git_globals(command):
    """`git -C dir add …` must match the same rules as `git add …`; returns the command and the last -C dir."""
    cdir = None
    for match in GIT_GLOBAL.finditer(command):
        found = re.findall(r"-C\s+(\S+)", match.group(1))
        if found:
            cdir = found[-1].strip("'\"")
    return GIT_GLOBAL.sub("git", command), cdir


STAGE_STATUS = re.compile(r"\bgit\s+(status|diff\s+--name-only|ls-files)\b.*(\bgit\s+add\s+[^\n]*--pathspec-from-file|\|\s*(xargs\s+)?git\s+add\b)", re.S)
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEAM_BIN = os.path.join(PLUGIN_ROOT, 'skills', 'project-profiling', 'references')
REASON = (
    "ai-dev-team leader guard: during a dev-team run the leader does not change project files "
    "(dev-team SKILL, first paragraph). Make it a board task for a developer, or a one-line text fix with Edit "
    "on a .md file. Files under .ai-dev-team/ and .claude/ stay writable. Only the user turns this off "
    "(`leader_guard: off` in .ai-dev-team/local.md), or allows direct edits for this session by asking for a "
    "hotfix (a prompt with the word `hotfix`; `hotfix off` ends it) - tell the user, never write the marker yourself. "
    f"Installed plugin: TEAM_BIN={TEAM_BIN} - use it in every brief; if the board notes hold another TEAM_BIN, "
    "load /ai-dev-team:dev-team again (Phase 0 step 4) instead of searching the disk."
)


def find_root(start):
    path = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(path, '.ai-dev-team', 'workspace', '02_tasks.md')):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return None
        path = parent


ABS_PATH = re.compile(r"(?<![\w.])(/[^\s'\"`;&|()<>]+)")


def find_run_root(data):
    """The run's root from the session directory, else from the paths the call names.

    A session whose start directory was renamed or moved keeps the old path as its directory,
    so the paths in the call are the only link to the workspace."""
    root = find_root(data.get('cwd'))
    if root:
        return root
    tool_input = data.get('tool_input') or {}
    candidates = [tool_input.get('file_path') or '']
    candidates += ABS_PATH.findall(tool_input.get('command') or '')
    for path in candidates:
        if path.startswith('/'):
            start = path
            while start and not os.path.isdir(start):
                start = os.path.dirname(start)
            root = find_root(start) if start else None
            if root:
                return root
    return None


def guard_off(root):
    try:
        with open(os.path.join(root, '.ai-dev-team', 'local.md'), encoding='utf-8') as fh:
            return re.search(r'^leader_guard:\s*off\b', fh.read(), re.M) is not None
    except OSError:
        return False


LOAD_HINT = re.compile(
    rb'"skill":\s*"(?:ai-dev-team:)?dev-team"|<command-name>/(?:ai-dev-team:)?dev-team</command-name>')
LOAD_SKILLS = ('ai-dev-team:dev-team', 'dev-team')
LOAD_COMMAND = re.compile(
    r'^\s*(?:<command-message>[^<]*</command-message>\s*)?<command-name>/(?:ai-dev-team:)?dev-team</command-name>')


def _session(data):
    return re.sub(r'[^A-Za-z0-9_-]', '', str(data.get('session_id', '')))


def is_skill_load(entry):
    """A transcript entry that really loads the dev-team skill: the leader's Skill call, or the user typing the command.

    The skill listing, deny texts, tool results and quoted briefs that merely name the skill do not count."""
    content = (entry.get('message') or {}).get('content')
    if entry.get('type') == 'assistant':
        return any(isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('name') == 'Skill'
                   and (b.get('input') or {}).get('skill') in LOAD_SKILLS for b in content or [])
    if entry.get('type') != 'user' or entry.get('isMeta'):
        return False
    if isinstance(content, str):
        return bool(LOAD_COMMAND.match(content))
    return any(isinstance(b, dict) and b.get('type') == 'text' and LOAD_COMMAND.match(b.get('text') or '')
               for b in content or [])


def transcript_loads_skill(path):
    """True when the transcript holds a real dev-team skill load (see is_skill_load)."""
    try:
        with open(path, 'rb') as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            for match in LOAD_HINT.finditer(mm):
                start = mm.rfind(b'\n', 0, match.start()) + 1
                end = mm.find(b'\n', match.end())
                try:
                    entry = json.loads(mm[start:end if end != -1 else len(mm)])
                except ValueError:
                    continue
                if isinstance(entry, dict) and is_skill_load(entry):
                    return True
    except (OSError, ValueError):
        return False
    return False


def leading_run(data):
    """True when this session loaded the dev-team skill; a positive is cached per session.

    The cache name carries a version: files written by the older rule (any mention of the skill) are ignored."""
    session = _session(data)
    cache = os.path.join(tempfile.gettempdir(), f'ai-dev-team-leader-v2-{session}')
    if session and os.path.exists(cache):
        return True
    found = transcript_loads_skill(data.get('transcript_path') or '')
    if found and session:
        open(cache, 'w').close()
    return found


HOTFIX_PREFIX = 'ai-dev-team-hotfix-'
HOTFIX_TTL = 6 * 3600
HOTFIX_ON = re.compile(r'\bhot[- ]?fix(es|ing)?\b', re.I)
HOTFIX_OFF = re.compile(
    r"\bhot[- ]?fix\s+(off|done|over|ended|end)\b|\b(end|stop|finish|no|not|without|don't)\s+(the\s+|a\s+)?hot[- ]?fix\b",
    re.I)
DEV_TEAM_PROMPT = re.compile(r'(^|\s)/(ai-dev-team:)?dev-team\b')
HOTFIX_NOTE_ON = (
    "ai-dev-team: the user asked for a hotfix. Until the user says `hotfix off` (or types /ai-dev-team:dev-team), the "
    "leader guard lets this session change project files directly, with no board task, agents or watchdog required. "
    "Normal care still applies: keep the change small, run the related tests and verify the fix; when a run is open, "
    "add one line to decisions.md naming the hotfix and its files.")
HOTFIX_NOTE_OFF = "ai-dev-team: hotfix ended; the leader guard applies again for this session."
MARKER_REASON = (
    "ai-dev-team guard: the hotfix marker is set only by the user's own prompt (the word `hotfix`); no tool call may "
    "create, change or remove it. Ask the user if a direct edit is needed.")


def hotfix_marker(data):
    session = _session(data)
    return os.path.join(tempfile.gettempdir(), HOTFIX_PREFIX + session) if session else None


def hotfix_active(data, now=None):
    """True while the user's hotfix marker for this session stands and is younger than HOTFIX_TTL."""
    marker = hotfix_marker(data)
    try:
        return bool(marker) and (now or time.time()) - os.path.getmtime(marker) < HOTFIX_TTL
    except OSError:
        return False


def prompt_check(data):
    """UserPromptSubmit: a prompt naming a hotfix sets (or refreshes) the session's marker; ending words or a typed
    dev-team command clear it. Returns 'on', 'off' or None."""
    marker = hotfix_marker(data)
    prompt = str(data.get('prompt') or '')
    if not marker:
        return None
    if HOTFIX_OFF.search(prompt) or DEV_TEAM_PROMPT.search(prompt):
        if os.path.exists(marker):
            os.remove(marker)
            return 'off'
        return None
    if HOTFIX_ON.search(prompt):
        with open(marker, 'w') as fh:
            fh.write(str(int(time.time())))
        return 'on'
    return None


def marker_touched(data):
    """A tool call that names the hotfix marker: only the user's prompt may set or clear it."""
    tool_input = data.get('tool_input') or {}
    text = ' '.join(str(tool_input.get(k) or '') for k in ('command', 'file_path', 'notebook_path'))
    return HOTFIX_PREFIX in text


def inside(path, root):
    path = os.path.abspath(path)
    return path == root or path.startswith(root + os.sep)


def git_toplevel(path):
    """The working tree that holds `path` (a `.git` directory or worktree file above it), else None."""
    start = os.path.dirname(path)
    while not os.path.isdir(start):
        parent = os.path.dirname(start)
        if parent == start:
            return None
        start = parent
    while True:
        if os.path.exists(os.path.join(start, '.git')):
            return start
        parent = os.path.dirname(start)
        if parent == start:
            return None
        start = parent


def edit_denied(data, root):
    tool_input = data.get('tool_input') or {}
    target = tool_input.get('file_path') or tool_input.get('notebook_path')
    if not target:
        return False
    target = os.path.abspath(os.path.join(data.get('cwd') or root, target))
    if not inside(target, root):
        # A run's tasks may change a sibling repository; its files are agent work too.
        root = git_toplevel(target)
        if not root or inside(target, os.path.expanduser('~/.claude')):
            return False
    rel = os.path.relpath(target, root)
    if rel.split(os.sep, 1)[0] in ALLOWED_DIRS:
        return False
    if data.get('tool_name') == 'Edit' and target.endswith('.md'):
        size = len(tool_input.get('old_string', '')) + len(tool_input.get('new_string', ''))
        if size <= 400:
            return False
    return True


DATA_HEREDOC = re.compile(r"<<-?[ \t]*(['\"])(\w+)\1([^\n]*)\n(.*?)^[ \t]*\2[ \t]*$", re.S | re.M)
DATA_SINKS = ('cat', 'tee')
DATA_COMMANDS = DATA_SINKS + ('grep', 'egrep', 'fgrep', 'rg', 'echo', 'printf')
RUNS_TEXT = re.compile(
    r"\|\s*(?:sudo\s+)?(?:\S*/)?(?:(?:ba|z|da|k)?sh|python3?|perl|node|ruby|xargs|ssh|eval|source)\b"
    r"|(?:^|[;&|(\n]|\$\()\s*(?:eval|source|\.)\s")


def _command_word(text):
    """First word of the last simple command in `text`, skipping `VAR=value` prefixes."""
    words = re.split(r"[;&|(`\n]|\$\(", text)[-1].split()
    while words and re.match(r"\w+=", words[0]):
        words.pop(0)
    return os.path.basename(words[0]) if words else ''


def _quoted_args(command, strip):
    """`command` with single-quoted arguments of DATA_COMMANDS emptied (all of them when strip is None)."""
    out, scan, i, n = [], [], 0, len(command)
    while i < n:
        ch = command[i]
        if ch == '\\':
            out.append(command[i:i + 2])
            scan.append('xx')
            i += 2
        elif ch == '"':
            j = i + 1
            while j < n and command[j] != '"':
                j += 2 if command[j] == '\\' else 1
            out.append(command[i:j + 1])
            scan.append('""')
            i = j + 1
        elif ch == "'":
            end = command.find("'", i + 1)
            if end < 0:
                out.append(command[i:])
                break
            data = strip is None or _command_word(''.join(scan)) in DATA_COMMANDS
            out.append("''" if data else command[i:end + 1])
            scan.append("''")
            i = end + 1
        else:
            out.append(ch)
            scan.append(ch)
            i += 1
    return ''.join(out)


def strip_data(command):
    """Drop text a command only stores or searches and never runs, so the shared-tree patterns do not match words
    inside it: the body of a quoted heredoc fed to `cat` / `tee`, and single-quoted arguments of cat, tee, grep,
    rg, echo and printf. Nothing is dropped when that text is piped into a shell or interpreter, or eval'd."""
    def heredoc(match):
        line_start = command.rfind('\n', 0, match.start()) + 1
        head = command[line_start:match.start()]
        if _command_word(head) not in DATA_SINKS or RUNS_TEXT.search(head + match.group(3)):
            return match.group(0)
        return "<<'%s'%s\n%s" % (match.group(2), match.group(3), match.group(2))

    command = DATA_HEREDOC.sub(heredoc, command)
    if RUNS_TEXT.search(_quoted_args(command, None)):
        return command
    return _quoted_args(command, True)


def shared_tree_denied(data, agent):
    command, _ = strip_git_globals((data.get('tool_input') or {}).get('command') or '')
    command = strip_data(command)
    if SHARED_TREE.search(command):
        return True
    return bool(agent and AGENT_GIT.search(command))


def stage_denied(data, root):
    """Leader `git add` of everything or of a folder: only a task's own files are staged (BASE-7)."""
    command, cdir = strip_git_globals((data.get('tool_input') or {}).get('command') or '')
    if STAGE_ALL.search(command) or STAGE_STATUS.search(command) or STAGE_LIST.search(command):
        return True
    base = os.path.join(data.get('cwd') or root, cdir) if cdir else (data.get('cwd') or root)
    for match in re.finditer(r"\bgit\s+add\s+([^;&|\n]+)", command):
        for arg in match.group(1).split():
            if arg.startswith('-') or arg.startswith('$('):
                continue
            path = os.path.join(base, arg)
            rel = os.path.relpath(os.path.abspath(path), root)
            if os.path.isdir(path) and (rel.startswith('..') or rel.split(os.sep, 1)[0] not in ALLOWED_DIRS):
                return True
    return False


LEADER_CD = re.compile(r'(?:^|&&|\|\||;|\n)\s*cd(?:\s|$)')
CD_REASON = (
    "ai-dev-team leader guard: the leader never `cd`s — its shell keeps the directory between calls and the "
    "user's `!` commands run in it. Use absolute paths, `git -C <dir>`, a tool's own directory flag, or a "
    "subshell `( cd <dir> && … )`.")


def cd_denied(data):
    """A leader `cd` outside a subshell changes the directory the user's commands run in."""
    command = (data.get('tool_input') or {}).get('command') or ''
    if command.lstrip().startswith('('):
        return False
    return bool(LEADER_CD.search(command))


def bash_denied(data):
    command = (data.get('tool_input') or {}).get('command') or ''
    if '.ai-dev-team' in command:
        return False
    if BASH_WRITES.search(command):
        return True
    return bool(PY_HEREDOC.search(command) and PY_WRITES.search(command))


def retype_denied(data):
    """Agent edits that re-type text through a python heredoc (COST-8)."""
    command = (data.get('tool_input') or {}).get('command') or ''
    return bool(PY_HEREDOC.search(command) and PY_WRITES.search(command) and PY_RETYPE.search(command))


NODE_EVAL = re.compile(r"\bnode\s+(-[A-Za-z-]+\s+)*(-e\b|--eval\b|-p\b|--print\b|-\s*<<|<<)")
NODE_WRITES = re.compile(r"\b(writeFileSync|writeFile|appendFileSync|appendFile)\s*\(")
PY_INLINE = re.compile(r"\bpython3?\s+(-[A-Za-z]+\s+)*(-\s*<<|-c\b)")
PY_OPEN_WRITE = re.compile(
    r"(?<![\w.])open\(\s*(?P<path>[^,()]+(?:\([^()]*\))?[^,()]*?)\s*,\s*(?:mode\s*=\s*)?[rbf]?['\"](?P<mode>[rwaxbt+]+)['\"]")
PY_RECEIVER = r"((?:pathlib\.)?Path\([^()]*\)|[A-Za-z_][\w.]*)"
PY_METHOD_WRITE = re.compile(PY_RECEIVER + r"\.(?:write_text|write_bytes)\(")
PY_METHOD_OPEN = re.compile(PY_RECEIVER + r"\.open\(\s*(?:mode\s*=\s*)?['\"](?P<mode>[rwaxbt+]+)['\"]")
PY_ANY_METHOD_WRITE = re.compile(r"\.(write_text|write_bytes)\(")
SCRATCH_PATH = re.compile(r"\.ai-dev-team/|\.ai-dev-team['\"]|TEAM_WS|TEAM_STATE|['\"/]tmp/|^['\"]?/tmp/")
SED_FANOUT = re.compile(
    r"\bxargs\b[^|;&\n]*\bsed\s[^|;&\n]*(-[A-Za-z]*i|--in-place)"
    r"|-exec(dir)?\s+sed\s[^;\n]*(-[A-Za-z]*i|--in-place)"
    r"|\bfor\s+\w+\s+in\b[^\n]*?;?\s*do\b[^\n]*?\bsed\s[^|;&\n]*(-[A-Za-z]*i|--in-place)", re.S)
WRITE_REASON = (
    "ai-dev-team guard (COST-8): an inline node or python script that writes project files, or `sed -i` over several "
    "files, is not allowed. Use the Edit tool (all changes to one file in one pass), `perl -pi -e` for one substitution "
    "across many files, or `git apply` with a unified diff; `sed -i` on one file stays allowed; a script only for real "
    "logic, saved as a file under $TEAM_WS. Inline scripts may write only under .ai-dev-team/, $TEAM_WS, $TEAM_STATE "
    "or /tmp/.")


def _resolve(expr, script):
    """The text of a written path: the expression, plus the right side of a simple `name = ...` assignment."""
    expr = expr.strip()
    if re.fullmatch(r"[A-Za-z_]\w*", expr):
        match = re.search(r"(?m)(?:^|[;\s])" + re.escape(expr) + r"\s*=\s*([^\n;]+)", script)
        return match.group(1) if match else ''
    return expr


def py_write_denied(command):
    """A python heredoc or `python3 -c` that writes a file outside the team and scratch folders."""
    if not PY_INLINE.search(command):
        return False
    targets = []
    for match in PY_OPEN_WRITE.finditer(command):
        if set(match.group('mode')) & set('wax+'):
            targets.append(match.group('path'))
    for match in PY_METHOD_OPEN.finditer(command):
        if set(match.group('mode')) & set('wax+'):
            targets.append(match.group(1))
    receivers = [m.group(1) for m in PY_METHOD_WRITE.finditer(command)]
    if len(receivers) < len(PY_ANY_METHOD_WRITE.findall(command)):
        return True  # a write_text / write_bytes whose path cannot be read
    targets += receivers
    return any(not SCRATCH_PATH.search(_resolve(t, command)) for t in targets)


def _sed_files(tokens):
    """Files named by one `sed` call (tokens after `sed`), or None when it is not in-place."""
    in_place, script_given, rest, i = False, False, [], 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == '--':
            rest += tokens[i + 1:]
            break
        if tok.startswith('--'):
            if tok.startswith('--in-place'):
                in_place = True
            elif tok in ('--expression', '--file'):
                script_given, i = True, i + 1
            elif tok.startswith(('--expression=', '--file=')):
                script_given = True
        elif tok.startswith('-') and len(tok) > 1:
            flags = tok[1:]
            pos_i = flags.find('i')
            if pos_i != -1:
                in_place = True
                flags = flags[:pos_i]  # GNU sed: the rest of the cluster is the backup suffix
            if 'e' in flags or 'f' in flags:
                script_given = True
                if flags.endswith(('e', 'f')):
                    i += 1
        else:
            rest.append(tok)
        i += 1
    if not in_place:
        return None
    return rest if script_given else rest[1:]


def sed_fanout_denied(command):
    """`sed -i` over two or more files, a glob, a command substitution, xargs, find -exec or a loop."""
    if SED_FANOUT.search(command):
        return True
    for line in command.split('\n'):
        if not re.search(r"\bsed\b", line):
            continue
        line = re.sub(r"\$\([^()]*\)|`[^`]*`", ' __SUBST__ ', line)
        try:
            lexer = shlex.shlex(line, posix=True, punctuation_chars=';&|()<>')
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            continue
        segment = []
        for tok in tokens + [';']:
            if tok and set(tok) <= set(';&|()<>'):
                if segment and segment[-1].isdigit() and set(tok) & set('<>'):
                    segment.pop()  # the file descriptor of a redirect such as 2>/dev/null
                if segment and os.path.basename(segment[0]) == 'sed':
                    files = _sed_files(segment[1:])
                    if files is not None and (len(files) >= 2 or any(
                            '__SUBST__' in f or re.search(r"[*?\[]", f) for f in files)):
                        return True
                segment = []
            else:
                segment.append(tok)
    return False


def inline_write_denied(data):
    """Agent edits through inline node / python scripts or a fanned-out `sed -i` (COST-8)."""
    command = (data.get('tool_input') or {}).get('command') or ''
    if NODE_EVAL.search(command) and NODE_WRITES.search(command):
        return True
    return py_write_denied(command) or sed_fanout_denied(command)


def substitution_denied(data):
    """A shell write into the team files that still expands a backtick (board pasted with command output)."""
    command = (data.get('tool_input') or {}).get('command') or ''
    if '`' not in command or not TEAM_WRITE.search(command):
        return False
    live = SINGLE_QUOTED.sub('', QUOTED_HEREDOC.sub('', command))
    return '`' in live


def extra_script_denied(data):
    """An agent writing yet another browser script into a task's qa-artifacts folder."""
    tool_input = data.get('tool_input') or {}
    cwd = data.get('cwd') or os.getcwd()
    if data.get('tool_name') == 'Write':
        target, body = tool_input.get('file_path') or '', tool_input.get('content') or ''
    else:
        command = tool_input.get('command') or ''
        match = SCRIPT_TARGET.search(command)
        if not match:
            return False
        target, body = match.group(1), command
        lead = re.match(r"\s*cd\s+([^\s;&|]+)\s*(&&|;)", command)
        if lead:
            cwd = os.path.join(cwd, os.path.expanduser(lead.group(1)))
    if not target.endswith(('.mjs', '.cjs', '.js', '.ts', '.py')) or not BROWSER_SCRIPT.search(body):
        return False
    target = os.path.abspath(os.path.join(cwd, os.path.expanduser(target)))
    folder = os.path.dirname(target)
    if 'qa-artifacts' not in folder.split(os.sep) or os.path.exists(target):
        return False
    recent = 0
    now = time.time()
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not name.endswith(('.mjs', '.cjs', '.js', '.ts', '.py')) or now - os.path.getmtime(path) > 5400:
            continue
        with open(path, encoding='utf-8', errors='ignore') as fh:
            if BROWSER_SCRIPT.search(fh.read(20000)):
                recent += 1
    return recent >= 2


MONITOR_REASON = (
    "ai-dev-team guard (MON-1): the monitor never changes the watched project. Report the finding to the leader as a "
    "`run-fix`; plugin changes go only into the worktree from `$TEAM_BIN/monitor-integrate.sh start`.")


def monitor_write_denied(data, root):
    """A monitor agent writing a project file outside the team folder."""
    if not str(data.get('agent_type') or '').endswith('monitor'):
        return False
    target = (data.get('tool_input') or {}).get('file_path') or (data.get('tool_input') or {}).get('notebook_path')
    if not target:
        return False
    target = os.path.abspath(os.path.join(data.get('cwd') or root, target))
    return inside(target, root) and os.path.relpath(target, root).split(os.sep, 1)[0] != '.ai-dev-team'


NOTE_FILES = ('02_tasks.md', 'decisions.md')
NOTE_TIME = re.compile(r"(?:^|\n|\\n|[/^|'\x22])[ \t]*-[ \t]+([01]\d|2[0-3]):([0-5]\d)\b")
NOTE_WRITE = re.compile(r">>?|\btee\b|\b(?:perl|sed)\b[^\n]*\s-[A-Za-z]*i")
NOTE_SLACK = 2  # minutes a literal note time may run ahead of the clock
TIME_REASON = (
    "ai-dev-team leader guard (dev-team SKILL, Progress to the user): a board note or decision line starts with a "
    "time later than the clock now ({now}). Note times come from `date +%H:%M` run at that moment, never estimated: "
    "write `- $(date +%H:%M) …` in an unquoted heredoc or echo, or run `date +%H:%M` first and use what it prints.")


def future_note_time(data, now=None):
    """A leader write to the board or decisions that adds a note line whose leading `HH:MM` is ahead of the clock.

    Only times not already at the start of a line in the target file count, so moving or correcting an existing
    line passes; earlier times (a verdict or user message recorded late) always pass. Returns the clock or None."""
    tool_input = data.get('tool_input') or {}
    if data.get('tool_name') == 'Bash':
        text = tool_input.get('command') or ''
        names = [n for n in NOTE_FILES if n in text]
        if not names or not NOTE_WRITE.search(text):
            return None
        targets = [p for p in ABS_PATH.findall(text) if os.path.basename(p) in names]
    else:
        target = tool_input.get('file_path') or ''
        if os.path.basename(target) not in NOTE_FILES:
            return None
        text = tool_input.get('new_string') or tool_input.get('content') or ''
        old = tool_input.get('old_string') or ''
        text = '\n'.join(line for line in text.split('\n') if line not in old)
        targets = [target]
    existing = ''
    for path in targets:
        try:
            with open(path, encoding='utf-8', errors='ignore') as fh:
                existing += fh.read()
        except OSError:
            pass
    clock = time.localtime(now)
    minute = clock.tm_hour * 60 + clock.tm_min
    for hour, mins in NOTE_TIME.findall(text):
        ahead = (int(hour) * 60 + int(mins) - minute) % 1440
        if NOTE_SLACK < ahead < 720 and not re.search(r"(?m)^[ \t]*-[ \t]+%s:%s\b" % (hour, mins), existing):
            return time.strftime('%H:%M', clock)
    return None


MODEL_REASON = (
    "ai-dev-team leader guard: every spawn of a team agent passes `model` explicitly, taken from the Model per role "
    "table (dev-team SKILL); an omitted model inherits the session's model instead of the task's.")


def spawn_denied(data):
    """A leader Agent call for an ai-dev-team agent without an explicit model."""
    tool_input = data.get('tool_input') or {}
    kind = str(tool_input.get('subagent_type') or '')
    return kind.startswith('ai-dev-team:') and not tool_input.get('model')


CHECKPOINT_REASON = (
    "ai-dev-team leader guard (dev-team SKILL, Unattended runs 6 Watchdog): agents of this session are still "
    "running and no checkpoint is armed, so nothing wakes you if one hangs. Before ending the turn arm one "
    "checkpoint: ScheduleWakeup (delaySeconds ~300, prompt `watchdog checkpoint: check running agents, post the "
    "board line`) or a Monitor. At each checkpoint an agent with no new output for ~20 minutes, or a test or "
    "build older than its timeout, is stuck — stop it and brief a fresh agent from its notes.")


def _ts(value):
    try:
        return calendar.timegm(time.strptime(value[:19], "%Y-%m-%dT%H:%M:%S"))
    except (TypeError, ValueError):
        return None


def running_agents(transcript):
    """Background agents of this session whose run has not finished (from the subagents' meta files)."""
    folder = os.path.join(transcript[:-len('.jsonl')], 'subagents')
    names = []
    now = time.time()
    for name in os.listdir(folder) if os.path.isdir(folder) else []:
        if not name.endswith('.meta.json'):
            continue
        path = os.path.join(folder, name)
        log = path[:-len('.meta.json')] + '.jsonl'
        if now - os.path.getmtime(log if os.path.exists(log) else path) > 86400:
            continue
        with open(path, encoding='utf-8') as fh:
            meta = json.load(fh)
        if meta.get('requestShape') == 'background' and not meta.get('finished') and not meta.get('stoppedByUser'):
            names.append(meta.get('description') or name)
    return names


def checkpoint_armed(transcript):
    """True when a ScheduleWakeup, Monitor or cron armed by this session has not fired or expired yet."""
    now = time.time()
    armed = False
    with open(transcript, encoding='utf-8', errors='ignore') as fh:
        for line in fh:
            if '"tool_use"' not in line or not re.search(r'"(ScheduleWakeup|Monitor|CronCreate|CronDelete)"', line):
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            # Request copies (`api-request-blob`) repeat earlier tool calls without a timestamp.
            if entry.get('type') != 'assistant':
                continue
            started = _ts(entry.get('timestamp'))
            for block in (entry.get('message') or {}).get('content') or []:
                if not isinstance(block, dict) or block.get('type') != 'tool_use':
                    continue
                name, args = block.get('name'), block.get('input') or {}
                if name == 'ScheduleWakeup':
                    armed = bool(not args.get('stop') and started and started + float(args.get('delaySeconds') or 0) + 60 > now)
                elif name == 'Monitor':
                    armed = bool(started and started + float(args.get('timeout_ms') or 1800000) / 1000 > now)
                elif name == 'CronCreate':
                    armed = True
                elif name == 'CronDelete':
                    armed = False
    return armed


def stop_check(data):
    """Stop hook: the leader may not end a turn with agents running and no checkpoint armed."""
    transcript = data.get('transcript_path') or ''
    if data.get('stop_hook_active') or not transcript.endswith('.jsonl') or not leading_run(data):
        return
    root = find_root(data.get('cwd'))
    if not root or guard_off(root) or hotfix_active(data):
        return
    agents = running_agents(transcript)
    if agents and not checkpoint_armed(transcript):
        print(json.dumps({'decision': 'block', 'reason': CHECKPOINT_REASON + ' Running: ' + ', '.join(agents[:6]) + '.'}))


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}))


def main():
    data = json.load(sys.stdin)
    if data.get('hook_event_name') == 'Stop':
        stop_check(data)
        return
    if data.get('hook_event_name') == 'UserPromptSubmit':
        state = prompt_check(data)
        if state and find_root(data.get('cwd')):
            print(json.dumps({'hookSpecificOutput': {
                'hookEventName': 'UserPromptSubmit',
                'additionalContext': HOTFIX_NOTE_ON if state == 'on' else HOTFIX_NOTE_OFF}}))
        return
    root = find_run_root(data)
    if not root or guard_off(root):
        return
    agent = bool(data.get('agent_id'))
    tool = data.get('tool_name')
    if marker_touched(data):
        deny(MARKER_REASON)
        return
    if tool == 'Bash' and shared_tree_denied(data, agent):
        deny(SHARED_REASON)
        return
    if tool == 'Bash' and WAIT_LOOP.search((data.get('tool_input') or {}).get('command') or ''):
        deny(WAIT_REASON)
        return
    if tool == 'Bash' and substitution_denied(data):
        deny(SUBST_REASON)
        return
    if agent and tool == 'Bash' and retype_denied(data):
        deny(RETYPE_REASON)
        return
    if agent and tool == 'Bash' and inline_write_denied(data):
        deny(WRITE_REASON)
        return
    if agent and tool in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit') and monitor_write_denied(data, root):
        deny(MONITOR_REASON)
        return
    if agent and tool in ('Bash', 'Write') and extra_script_denied(data):
        deny(SCRIPT_REASON)
        return
    if agent or not leading_run(data):
        return
    if tool == 'Agent':
        if spawn_denied(data):
            deny(MODEL_REASON)
        return
    if tool == 'Bash' and cd_denied(data):
        deny(CD_REASON)
        return
    if tool in ('Bash', 'Edit', 'Write'):
        clock = future_note_time(data)
        if clock:
            deny(TIME_REASON.format(now=clock))
            return
    if tool == 'Bash' and stage_denied(data, root):
        deny("ai-dev-team leader guard: stage only the task's own files by name (BASE-7), never `git add -A`, "
             "`git add .`, `-u`, a whole folder, the whole `git status` list, a `--pathspec-from-file` list or `xargs git add` "
             "(also through `git -C <dir>` or a list built in an earlier call); other tasks' unreviewed changes would "
             "ride along. Stage named files, or `git add -- $($TEAM_BIN/rule-checks.sh task-diff <id> --name-only)`. "
             "Reaching a denied effect another way counts as resending the denied call (BASE-34).")
        return
    if hotfix_active(data):
        return  # the user asked for a hotfix: direct project edits are allowed
    denied = bash_denied(data) if tool == 'Bash' else edit_denied(data, root)
    if denied:
        deny(REASON)


if __name__ == '__main__':
    try:
        main()
    except Exception:  # never block on a guard failure
        pass
