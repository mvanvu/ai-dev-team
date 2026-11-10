#!/usr/bin/env python3
"""Consistency check for the ai-dev-team plugin repo.

Verifies that cross-references between agents, skills and reference files still resolve:
  1. `references/<file>` and `<file>.md` mentions point to existing files
  2. `<file>.md` §N mentions point to an existing "## N." heading
  3. `ai-dev-team:<name>` mentions name an existing skill or agent
  4. every rule pack in rule-packs.md has existing must-read files and numbered checks
  5. rule IDs (COMPACT-3, ...) used anywhere exist in their pack
  6. the plugin version has a change log row; frontmatter names match file names

Usage: python3 scripts/check-plugin.py   (exit 0 clean, 1 problems)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
REGISTRY = SKILLS / "dev-team" / "references" / "rule-packs.md"
problems = []


def problem(path, message):
    problems.append(f"{path.relative_to(ROOT)}: {message}")


docs = sorted(list((ROOT / "agents").glob("*.md")) + list(SKILLS.rglob("*.md")))
all_docs = docs + [ROOT / "README.md", ROOT / "CLAUDE.md"]
reference_files = {}
for path in SKILLS.rglob("references/*"):
    reference_files.setdefault(path.name, []).append(path)
skill_names = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
agent_names = {p.stem for p in (ROOT / "agents").glob("*.md")}


def headings(path):
    """Section labels of a file: '7' for '## 7. Checks', '4a' for '## 4a. ...'."""
    return set(re.findall(r"^## (\d+[a-z]?)\.", path.read_text(), flags=re.M))


def numbered_items(path, section):
    """Count of top-level numbered items in a '## <section>' block (or '## Checks ...')."""
    text = path.read_text()
    if section == "checks":
        match = re.search(r"^## Checks[^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    else:
        match = re.search(rf"^## {re.escape(section)}\.[^\n]*\n(.*?)(?=^## |\Z)", text, flags=re.M | re.S)
    return len(re.findall(r"^\d+\. ", match.group(1), flags=re.M)) if match else 0


def resolve_reference(name, source):
    """Find a referenced file: next to the source skill first, then anywhere under skills/."""
    for base in (source.parent, source.parent / "references", source.parent.parent / "references"):
        if (base / name).is_file():
            return base / name
    candidates = reference_files.get(name, [])
    return candidates[0] if candidates else None


# 1 + 2: file and section references
for path in all_docs:
    text = path.read_text()
    for name in set(re.findall(r"references/([\w.-]+\.(?:md|sh|mjs|js))", text)):
        if name not in reference_files:
            problem(path, f"references/{name} does not exist")
    for name, section in set(re.findall(r"`?([\w-]+\.md)`? §(\d+[a-z]?)", text)):
        target = resolve_reference(name, path)
        if target is None:
            problem(path, f"{name} §{section}: file not found")
        elif section not in headings(target):
            problem(path, f"{name} §{section}: no '## {section}.' heading in {target.relative_to(ROOT)}")

# 3: namespaced skill / agent names
for path in all_docs:
    for name in set(re.findall(r"ai-dev-team:([a-z][a-z0-9-]+)", path.read_text())):
        if name not in skill_names and name not in agent_names:
            problem(path, f"ai-dev-team:{name} is neither a skill nor an agent")

# 4: rule packs
packs = {}
registry_text = REGISTRY.read_text()
for row in re.findall(r"^\| `([A-Z]+)` \|(.*)\|$", registry_text, flags=re.M):
    pack, rest = row
    cells = [c.strip() for c in rest.split("|")]
    must_read, checks = cells[1], cells[2]
    for rel in re.findall(r"`([\w./-]+\.md)`", must_read):
        if not (SKILLS / rel).is_file():
            problem(REGISTRY, f"pack {pack}: must-read {rel} does not exist")
    files = [SKILLS / rel for rel in re.findall(r"`([\w./-]+\.md)`", must_read) if (SKILLS / rel).is_file()]
    count = 0
    if "this file" in checks or "this file" in must_read:
        section = re.search(r"§(\d+)", checks).group(1)
        count = numbered_items(REGISTRY, section)
    elif pack == "ABUSE":
        count = 9 if {str(n) for n in range(2, 10)} <= headings(files[-1]) else 0
    else:
        section_match = re.search(r"§(\d+[a-z]?)", checks)
        named = re.search(r"`([\w-]+\.md)`", checks)
        target = resolve_reference(named.group(1), REGISTRY) if named else files[-1]
        count = numbered_items(target, section_match.group(1) if section_match else "checks")
    if count == 0:
        problem(REGISTRY, f"pack {pack}: no numbered checks found ({checks})")
    packs[pack] = count

# 5: rule IDs
for path in all_docs:
    for pack, number in set(re.findall(r"\b([A-Z]{3,8})-(\d+)\b", path.read_text())):
        if pack in packs and not 1 <= int(number) <= packs[pack]:
            problem(path, f"rule {pack}-{number} does not exist (pack has {packs[pack]} checks)")

# 6: version and frontmatter
version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
if f"| {version}:" not in (ROOT / "CLAUDE.md").read_text():
    problem(ROOT / "CLAUDE.md", f"no change log row for version {version}")
for path in list((ROOT / "agents").glob("*.md")) + list(SKILLS.glob("*/SKILL.md")):
    match = re.search(r"^name: (.+)$", path.read_text(), flags=re.M)
    expected = path.stem if path.parent.name == "agents" else path.parent.name
    if not match or match.group(1).strip() != expected:
        problem(path, f"frontmatter name should be '{expected}'")

if problems:
    print("\n".join(problems))
    print(f"\n{len(problems)} problem(s)")
    sys.exit(1)
print(f"ok: {len(docs)} files, {len(packs)} rule packs ({', '.join(f'{k}:{v}' for k, v in packs.items())})")
