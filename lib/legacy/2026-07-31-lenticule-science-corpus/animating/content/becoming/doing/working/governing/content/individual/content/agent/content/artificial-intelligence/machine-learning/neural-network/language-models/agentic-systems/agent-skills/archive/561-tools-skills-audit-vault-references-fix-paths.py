#!/usr/bin/env python3
"""Find and fix broken md-link paths where the target file exists elsewhere in the vault."""

import re
import os
import subprocess
from pathlib import Path
from collections import Counter

vault = Path('content')

# Run audit to get fresh broken refs
result = subprocess.run(
    ['python', 'scripts/audit-vault-references.py'],
    capture_output=True, text=True
)

# Parse broken md-links
broken = []
for line in result.stdout.splitlines():
    line = line.rstrip()
    if not line or line.startswith('Source') or line.startswith('---'):
        continue
    if line.startswith('Total') or line.startswith('Top ') or line.startswith('  '):
        continue
    # Skip 404.md boilerplate
    if '404.md' in line:
        continue

    parts = re.split(r'\s{2,}', line.strip())
    if len(parts) >= 4:
        source, lineno, reftype, target = parts[0], parts[1], parts[2], parts[3]
        if reftype == 'md-link':
            broken.append((source, int(lineno), target))

print(f'Total broken md-links: {len(broken)}')

# Skip list for ambiguous stems
SKIP_STEMS = {
    'path', 'set', 'process', 'target', 'source', 'value', 'type',
    'model', 'term', 'concept', 'relation', 'example', 'index',
    'SKILL', 'closure', 'direction'
}

# For each, check if target filename exists somewhere in vault
fixable = []
ambiguous = []
missing = []

for source, lineno, target in broken:
    fname = target.split('/')[-1]
    if not fname.endswith('.md'):
        missing.append((source, lineno, target, 'not .md'))
        continue
    # Skip LaTeX-looking targets
    if len(fname) < 4 or ':' in fname:
        missing.append((source, lineno, target, 'latex'))
        continue
    stem = fname[:-3]

    if stem in SKIP_STEMS:
        missing.append((source, lineno, target, f'skipped stem: {stem}'))
        continue

    # Find all matches in vault
    matches = list(vault.rglob(stem + '.md'))
    # Filter out slop, triage, private, meta
    matches = [m for m in matches if not any(
        p in str(m) for p in ['slop/', 'triage/', 'private/', 'meta/', 'old-notes/']
    )]

    if len(matches) == 0:
        missing.append((source, lineno, target, 'no match'))
        continue

    if len(matches) > 1:
        # Try to disambiguate: if the target path contains hints, use them
        best = None
        target_parts = target.replace('\\', '/').split('/')
        for m in matches:
            m_parts = str(m.relative_to(vault)).replace('\\', '/').split('/')
            # Count how many path components match
            overlap = len(set(target_parts) & set(m_parts))
            if best is None or overlap > best[1]:
                best = (m, overlap)

        if best and best[1] >= 2:
            matches = [best[0]]
        else:
            ambiguous.append((source, lineno, target, [str(m.relative_to(vault)) for m in matches]))
            continue

    match = matches[0]
    source_file = vault / (source + '.md')
    if not source_file.exists():
        # Try without .md (in case source already includes .md)
        source_file = vault / source
    source_dir = source_file.parent

    correct_rel = os.path.relpath(match, source_dir)
    correct_rel = correct_rel.replace(os.sep, '/')

    if target != correct_rel:
        fixable.append((source, lineno, target, correct_rel, str(match.relative_to(vault))))

print(f'Fixable (unambiguous): {len(fixable)}')
print(f'Ambiguous (multiple matches): {len(ambiguous)}')
print(f'Missing (no match): {len(missing)}')

# Show fixable
print('\n=== FIXABLE ===')
for s, l, old, new, found in fixable:
    print(f'  {s}:{l}  {old} -> {new}')

# Show ambiguous
print('\n=== AMBIGUOUS ===')
for s, l, t, matches in ambiguous:
    print(f'  {s}:{l}  {t}')
    for m in matches:
        print(f'    candidate: {m}')

# Show missing
print('\n=== MISSING ===')
miss_reasons = Counter()
for s, l, t, reason in missing:
    miss_reasons[reason] += 1
    if reason == 'no match':
        print(f'  {s}:{l}  {t}')
print(f'\nMissing reasons: {dict(miss_reasons)}')

# Apply fixes
if fixable:
    print(f'\n=== APPLYING {len(fixable)} FIXES ===')
    files_modified = set()
    for source, lineno, old_target, new_target, _ in fixable:
        source_file = vault / (source + '.md')
        if not source_file.exists():
            source_file = vault / source
        if not source_file.exists():
            print(f'  SKIP: source not found: {source}')
            continue

        content = source_file.read_text(encoding='utf-8')
        lines = content.split('\n')

        # The line number is 1-indexed
        idx = lineno - 1
        if idx < 0 or idx >= len(lines):
            print(f'  SKIP: line {lineno} out of range in {source}')
            continue

        line = lines[idx]
        # Replace the old target with new target in markdown links
        # Pattern: (old_target) or (old_target "title")
        old_escaped = re.escape(old_target)
        new_line = re.sub(
            r'\(' + old_escaped + r'(\s|[)"])',
            '(' + new_target + r'\1',
            line
        )

        if new_line != line:
            lines[idx] = new_line
            source_file.write_text('\n'.join(lines), encoding='utf-8')
            files_modified.add(str(source_file))
            print(f'  FIXED: {source}:{lineno}  {old_target} -> {new_target}')
        else:
            print(f'  SKIP: pattern not found in line {lineno} of {source}')
            print(f'    line: {line[:120]}')

    print(f'\nModified {len(files_modified)} files')
