"""Leader guard for the ai-dev-team plugin (PreToolUse).

During a dev-team run the main session is the leader: it plans, briefs and talks to the user, while agents
change the project's files. This hook denies a leader tool call that would change a project file outside
`.ai-dev-team/` and `.claude/`. Agent calls (the input carries `agent_id`), sessions that never loaded the
dev-team skill and repositories without a team workspace are left alone. Any error lets the call through.

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
    r"\bsed\s+(-[a-zA-Z]*\s+)*-i|\bperl\s+(-[a-zA-Z]*\s+)*-[a-zA-Z]*i|\bgit\s+(checkout\s+--|restore\b|stash\b|apply\b)"
)
PY_HEREDOC = re.compile(r"\bpython3?\s+(-[A-Za-z]+\s+)*-\s*<<")
PY_WRITES = re.compile(r"\.write\(|open\([^)]*['\"][wa]\+?['\"]")
REASON = (
    "ai-dev-team leader guard: during a dev-team run the leader does not change project files "
    "(dev-team SKILL, first paragraph). Make it a board task for a developer, or a one-line text fix with Edit "
    "on a .md file. Files under .ai-dev-team/ and .claude/ stay writable. Only the user turns this off "
    "(`leader_guard: off` in .ai-dev-team/local.md)."
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


def bash_denied(data):
    command = (data.get('tool_input') or {}).get('command') or ''
    if '.ai-dev-team' in command:
        return False
    if BASH_WRITES.search(command):
        return True
    return bool(PY_HEREDOC.search(command) and PY_WRITES.search(command))


def main():
    data = json.load(sys.stdin)
    if data.get('agent_id'):
        return
    root = find_root(data.get('cwd'))
    if not root or guard_off(root) or not leading_run(data):
        return
    tool = data.get('tool_name')
    denied = bash_denied(data) if tool == 'Bash' else edit_denied(data, root)
    if denied:
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': REASON}}))


if __name__ == '__main__':
    try:
        main()
    except Exception:  # never block on a guard failure
        pass
