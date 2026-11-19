"""Leader guard for the ai-dev-team plugin (PreToolUse).

During a dev-team run the main session is the leader: it plans, briefs and talks to the user, while agents
change the project's files. This hook denies a leader tool call that would change a project file outside
`.ai-dev-team/` and `.claude/`, or stage a whole folder. Agent calls (the input carries `agent_id`) may edit
files, but commands that discard or move other people's work on the shared tree, kill processes by name or
detach a process from the harness are denied for everyone. Repositories without a team workspace and leader
sessions that never loaded the dev-team skill are left alone. Any error lets the call through.

Turned off for one machine by the user with `leader_guard: off` in `.ai-dev-team/local.md`.
"""
import json
import mmap
import os
import re
import sys
import tempfile

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
STAGE_ALL = re.compile(r"\bgit\s+add\s+(-A\b|--all\b|\.(\s|$)|-u\b)")
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
    if STAGE_ALL.search(command):
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
    if agent and tool == 'Bash' and retype_denied(data):
        deny(RETYPE_REASON)
        return
    if agent or not leading_run(data):
        return
    if tool == 'Bash' and stage_denied(data, root):
        deny("ai-dev-team leader guard: stage only the task's own files by name (BASE-7), never `git add -A`, "
             "`git add .`, `-u` or a whole folder; other tasks' unreviewed changes would ride along.")
        return
    denied = bash_denied(data) if tool == 'Bash' else edit_denied(data, root)
    if denied:
        deny(REASON)


if __name__ == '__main__':
    try:
        main()
    except Exception:  # never block on a guard failure
        pass
