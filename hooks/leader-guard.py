"""Leader guard for the ai-dev-team plugin (PreToolUse).

During a dev-team run the main session is the leader: it plans, briefs and talks to the user, while agents
change the project's files. This hook denies a leader tool call that would change a project file outside
`.ai-dev-team/` and `.claude/`, or stage a whole folder, or `cd` outside a subshell. Agent calls (the input carries `agent_id`) may edit
files, but commands that discard or move other people's work on the shared tree, kill processes by name or
detach a process from the harness are denied for everyone, a leader spawn of a team agent without an explicit `model` is denied, as are shell writes into the team files that still
expand a backtick. Agents may not write project files through inline node / python scripts or run `sed -i` over
several files (COST-8). Agents may not add a third browser script to a task's `qa-artifacts/` folder within 90 minutes. Repositories without a team workspace and leader
sessions that never loaded the dev-team skill are left alone. Any error lets the call through.

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
    "(`leader_guard: off` in .ai-dev-team/local.md). "
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


def leading_run(data):
    """True when this session loaded the dev-team skill; cached per session."""
    session = re.sub(r'[^A-Za-z0-9_-]', '', str(data.get('session_id', '')))
    cache = os.path.join(tempfile.gettempdir(), f'ai-dev-team-leader-{session}')
    if session and os.path.exists(cache):
        return True
    path = data.get('transcript_path') or ''
    try:
        with open(path, 'rb') as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            found = mm.find(b'ai-dev-team:dev-team') != -1
    except (OSError, ValueError):
        return False
    if found and session:
        open(cache, 'w').close()
    return found


def inside(path, root):
    path = os.path.abspath(path)
    return path == root or path.startswith(root + os.sep)


def edit_denied(data, root):
    tool_input = data.get('tool_input') or {}
    target = tool_input.get('file_path') or tool_input.get('notebook_path')
    if not target:
        return False
    target = os.path.abspath(os.path.join(data.get('cwd') or root, target))
    if not inside(target, root):
        return False
    rel = os.path.relpath(target, root)
    if rel.split(os.sep, 1)[0] in ALLOWED_DIRS:
        return False
    if data.get('tool_name') == 'Edit' and target.endswith('.md'):
        size = len(tool_input.get('old_string', '')) + len(tool_input.get('new_string', ''))
        if size <= 400:
            return False
    return True


def shared_tree_denied(data, agent):
    command, _ = strip_git_globals((data.get('tool_input') or {}).get('command') or '')
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
    if not root or guard_off(root):
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
    root = find_run_root(data)
    if not root or guard_off(root):
        return
    agent = bool(data.get('agent_id'))
    tool = data.get('tool_name')
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
    if tool == 'Bash' and stage_denied(data, root):
        deny("ai-dev-team leader guard: stage only the task's own files by name (BASE-7), never `git add -A`, "
             "`git add .`, `-u`, a whole folder, the whole `git status` list, a `--pathspec-from-file` list or `xargs git add` "
             "(also through `git -C <dir>` or a list built in an earlier call); other tasks' unreviewed changes would "
             "ride along. Stage named files, or `git add -- $($TEAM_BIN/rule-checks.sh task-diff <id> --name-only)`. "
             "Reaching a denied effect another way counts as resending the denied call (BASE-34).")
        return
    denied = bash_denied(data) if tool == 'Bash' else edit_denied(data, root)
    if denied:
        deny(REASON)


if __name__ == '__main__':
    try:
        main()
    except Exception:  # never block on a guard failure
        pass
