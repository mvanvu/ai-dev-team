"""Leader guard for the ai-dev-team plugin (PreToolUse).

During a dev-team run the main session is the leader: it plans, briefs and talks to the user, while agents
change the project's files. This hook denies a leader tool call that would change a project file outside
`.ai-dev-team/` and `.claude/`, or stage a whole folder. Agent calls (the input carries `agent_id`) may edit
files, but commands that discard or move other people's work on the shared tree, kill processes by name or
detach a process from the harness are denied for everyone, a leader spawn of a team agent without an explicit `model` is denied, as are shell writes into the team files that still
expand a backtick. Agents may not add a third browser script to a task's `qa-artifacts/` folder within 90 minutes. Repositories without a team workspace and leader
sessions that never loaded the dev-team skill are left alone. Any error lets the call through.

Turned off for one machine by the user with `leader_guard: off` in `.ai-dev-team/local.md`.
"""
import json
import mmap
import os
import re
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
    r"|(^|[^&|>])&\s*($|;|\n)"
)
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
    command = (data.get('tool_input') or {}).get('command') or ''
    if SHARED_TREE.search(command):
        return True
    return bool(agent and AGENT_GIT.search(command))


def stage_denied(data, root):
    """Leader `git add` of everything or of a folder: only a task's own files are staged (BASE-7)."""
    command = (data.get('tool_input') or {}).get('command') or ''
    if STAGE_ALL.search(command) or STAGE_STATUS.search(command):
        return True
    for match in re.finditer(r"\bgit\s+add\s+([^;&|\n]+)", command):
        for arg in match.group(1).split():
            if arg.startswith('-'):
                continue
            path = os.path.join(data.get('cwd') or root, arg)
            if os.path.isdir(path) and os.path.relpath(os.path.abspath(path), root).split(os.sep, 1)[0] not in ALLOWED_DIRS:
                return True
    return False


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


def deny(reason):
    print(json.dumps({'hookSpecificOutput': {
        'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason}}))


def main():
    data = json.load(sys.stdin)
    root = find_root(data.get('cwd'))
    if not root or guard_off(root):
        return
    agent = bool(data.get('agent_id'))
    tool = data.get('tool_name')
    if tool == 'Bash' and shared_tree_denied(data, agent):
        deny(SHARED_REASON)
        return
    if tool == 'Bash' and substitution_denied(data):
        deny(SUBST_REASON)
        return
    if agent and tool == 'Bash' and retype_denied(data):
        deny(RETYPE_REASON)
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
    if tool == 'Bash' and stage_denied(data, root):
        deny("ai-dev-team leader guard: stage only the task's own files by name (BASE-7), never `git add -A`, "
             "`git add .`, `-u`, a whole folder or the whole `git status` list; other tasks' unreviewed changes would "
             "ride along. List the task's files with `$TEAM_BIN/rule-checks.sh task-diff <id> --name-only` (or a worktree "
             "task's branch diff) and stage that list.")
        return
    denied = bash_denied(data) if tool == 'Bash' else edit_denied(data, root)
    if denied:
        deny(REASON)


if __name__ == '__main__':
    try:
        main()
    except Exception:  # never block on a guard failure
        pass
