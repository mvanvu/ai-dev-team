#!/usr/bin/env python3
"""Print what a dev-team run did since the last scan, for the ai-dev-team monitor agent.

Reads the leader session's transcript and its subagents' transcripts from the byte offset the previous
scan stopped at (a cursor file per session), and prints one compact line per user message, leader /
agent text and tool call, plus a `## Flags` section of patterns the plugin's rules forbid. The cursor
is advanced only after a successful print, so a failed scan is repeated in full next time.

Usage: monitor-scan.py <repo root> [--transcript <leader .jsonl>] [--max-chars N] [--width N] [--peek]
  <repo root>     the project whose `.ai-dev-team/` holds the run
  --transcript    the leader's transcript; default: the newest top-level transcript of this repo in
                  ${CLAUDE_CONFIG_DIR:-~/.claude}/projects/<slug>/ that loaded the dev-team skill
  --max-chars     output cap (default 60000); the oldest lines are dropped first and the cursor still advances
  --width         characters kept per line (default 300)
  --peek          print without advancing the cursor
Cursor: ~/.local/state/ai-dev-team/monitor/<session>.json
Exit: 0 printed (possibly "nothing new"), 2 no transcript found.
"""
import glob
import json
import os
import re
import sys

STATE = os.path.expanduser('~/.local/state/ai-dev-team/monitor')
FLAGS = [
    ('spawn without model', re.compile(r'TOOL Agent\[ai-dev-team:[a-z]+ model=None\]')),
    ('sleep wait loop', re.compile(r'TOOL Bash: .*\b(while|until|for)\b.*\bdo\b.*\bsleep\b')),
    ('pgrep / pkill', re.compile(r'TOOL Bash: .*\b(pgrep|pkill|killall)\b')),
    ('shared-tree discard', re.compile(r'TOOL Bash: .*\bgit\s+(stash|clean|restore\s+(?!--staged)|reset\s+--hard|checkout\s+--)')),
    ('python heredoc edit', re.compile(r'TOOL Bash: .*python3?\s+-\s*<<.*(\.replace\(|re\.sub\()')),
    ('stage all', re.compile(r'TOOL Bash: .*\bgit\s+add\s+(-A|--all|\.(\s|$)|-u)')),
    ('guard denial', re.compile(r'<- ERR .*(leader guard|ai-dev-team guard)')),
    ('permission denied', re.compile(r'<- ERR .*(permission|denied by the user|rejected)', re.I)),
    ('test or build failure', re.compile(r'<- .*\b(FAILED|failures?: [1-9]|exit code [1-9])')),
]


def slug(path):
    return re.sub(r'[^A-Za-z0-9]', '-', os.path.abspath(path))


def find_transcript(root):
    base = os.path.join(os.environ.get('CLAUDE_CONFIG_DIR') or os.path.expanduser('~/.claude'), 'projects', slug(root))
    for path in sorted(glob.glob(os.path.join(base, '*.jsonl')), key=os.path.getmtime, reverse=True):
        with open(path, 'rb') as fh:
            if b'ai-dev-team:dev-team' in fh.read():
                return path
    return None


def text_of(content):
    if isinstance(content, str):
        return content
    return ' '.join(b.get('text', '') for b in content or [] if isinstance(b, dict))


def entries(path, offset, label, width):
    """Lines for the transcript's new entries; returns (lines, new offset)."""
    lines = []
    with open(path, 'rb') as fh:
        fh.seek(offset)
        data = fh.read()
    end = data.rfind(b'\n') + 1
    for raw in data[:end].splitlines():
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        kind, ts = e.get('type'), (e.get('timestamp') or '')[11:19]
        content = (e.get('message') or {}).get('content')
        if kind == 'user':
            if isinstance(content, str):
                lines.append(f'{ts} {label} USER: {content}')
                continue
            for b in content or []:
                if b.get('type') == 'text':
                    lines.append(f'{ts} {label} USER: {b["text"]}')
                elif b.get('type') == 'tool_result':
                    err = 'ERR ' if b.get('is_error') else ''
                    lines.append(f'{ts} {label}   <- {err}{text_of(b.get("content"))[:width // 2]}')
        elif kind == 'assistant' and isinstance(content, list):
            for b in content:
                if b.get('type') == 'text':
                    lines.append(f'{ts} {label} SAYS: {b["text"]}')
                elif b.get('type') == 'tool_use':
                    i = b.get('input') or {}
                    name = b['name']
                    if name == 'Agent':
                        name = f'Agent[{i.get("subagent_type")} model={i.get("model")}]'
                    body = i.get('command') or i.get('description') or i.get('file_path') or i.get('message') or json.dumps(i)
                    lines.append(f'{ts} {label} TOOL {name}: {body}')
    return [l.replace('\n', ' ⏎ ')[:width] for l in lines], offset + end


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith('-'):
        print(__doc__)
        return 2
    root, opts = args[0], args[1:]
    get = lambda flag, default: opts[opts.index(flag) + 1] if flag in opts else default
    transcript = get('--transcript', None) or find_transcript(root)
    max_chars, width, peek = int(get('--max-chars', 60000)), int(get('--width', 300)), '--peek' in opts
    if not transcript or not os.path.isfile(transcript):
        print(f'monitor-scan: no leader transcript found for {root}')
        return 2
    session = os.path.basename(transcript)[:-len('.jsonl')]
    os.makedirs(STATE, exist_ok=True)
    cursor_path = os.path.join(STATE, f'{session}.json')
    try:
        with open(cursor_path) as fh:
            cursor = json.load(fh)
    except (OSError, ValueError):
        cursor = {}
    files = [(transcript, 'leader')]
    sub = os.path.join(transcript[:-len('.jsonl')], 'subagents')
    for path in sorted(glob.glob(os.path.join(sub, '*.jsonl'))):
        meta, label = path[:-len('.jsonl')] + '.meta.json', os.path.basename(path)[6:15]
        try:
            with open(meta) as fh:
                m = json.load(fh)
            label = f'{label}({(m.get("description") or "")[:40]})'
        except (OSError, ValueError):
            pass
        files.append((path, label))
    out, new_cursor = [], dict(cursor)
    for path, label in files:
        lines, offset = entries(path, cursor.get(path, 0), label, width)
        out += lines
        new_cursor[path] = offset
    out.sort(key=lambda l: l[:8])
    flags = [f'- {name}: {l[:200]}' for l in out for name, rx in FLAGS if rx.search(l)]
    body = '\n'.join(out)
    if len(body) > max_chars:
        body = '[older lines dropped]\n' + body[-max_chars:]
    print(f'# monitor-scan {session} — {len(out)} new lines from {len(files)} transcripts')
    print(body or 'nothing new')
    print('## Flags')
    print('\n'.join(flags[:60]) or 'none')
    if not peek:
        with open(cursor_path, 'w') as fh:
            json.dump(new_cursor, fh)
    return 0


if __name__ == '__main__':
    sys.exit(main())
