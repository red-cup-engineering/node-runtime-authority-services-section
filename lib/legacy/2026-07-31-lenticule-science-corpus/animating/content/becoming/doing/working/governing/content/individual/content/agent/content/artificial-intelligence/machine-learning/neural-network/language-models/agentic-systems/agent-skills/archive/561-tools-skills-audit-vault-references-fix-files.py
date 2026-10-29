"""
Pass 1: Add title (and date-created if no frontmatter at all) to files missing it.
Pass 2: Rename non-slug files using git mv.
Skips: SKILL.md, README.md, GLOSSARY.md, SPECIFICATIONS.md
"""
import os, re, subprocess, sys
from datetime import date

SKIP_NAMES = {'SKILL.md', 'README.md', 'GLOSSARY.md', 'SPECIFICATIONS.md'}
TODAY = date.today().isoformat() + 'T00:00:00'

# ── helpers ──────────────────────────────────────────────────────────────────

def is_slug_name(name):
    """True if the filename (without .md) is already a slug."""
    stem = name[:-3]
    return bool(re.match(r'^[a-z0-9][a-z0-9\-]*$', stem))

def slugify_filename(stem):
    """Convert any filename stem to a slug."""
    s = stem.lower()
    s = re.sub(r"[''`°©®™]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-') + '.md'

def derive_title(stem, filepath):
    """Derive a human-readable title from the file stem."""
    name = stem
    # For encyclopedia/events: strip leading date prefix "YYYY-MM-DD, "
    if 'encyclopedia' in filepath.replace('\\', '/') and re.match(r'\d{4}-\d{2}-\d{2},\s+', name):
        name = re.sub(r'^\d{4}-\d{2}-\d{2},\s+', '', name)
    # If already has some uppercase, assume it's properly cased
    if any(c.isupper() for c in name):
        return name.strip()
    # All-lowercase: replace hyphens/underscores with spaces, title-case
    name = re.sub(r'[-_]+', ' ', name)
    return name.strip().title()

def read_file(path):
    with open(path, encoding='utf-8') as f:
        return f.read()

def write_file(path, text):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)

def has_title(text):
    if not text.startswith('---'):
        return False
    end = text.find('\n---', 3)
    if end == -1:
        return False
    fm = text[3:end]
    return bool(re.search(r'^title\s*:', fm, re.MULTILINE))

def add_title_to_file(path, title):
    text = read_file(path)
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            # Insert title as first field in existing frontmatter
            new_text = '---\ntitle: ' + title + '\n' + text[4:end] + text[end:]
            write_file(path, new_text)
            return
    # No valid frontmatter — prepend a new block
    new_text = '---\ntitle: ' + title + '\ndate-created: ' + TODAY + '\n---\n' + text
    write_file(path, new_text)

def git_mv(src, dst):
    r = subprocess.run(['git', 'mv', src, dst], capture_output=True, text=True)
    if r.returncode != 0:
        print(f'  ERROR: git mv {src!r} -> {dst!r}')
        print('  ' + r.stderr.strip())
        return False
    return True

# ── collect files ─────────────────────────────────────────────────────────────

all_md = []
for root, dirs, files in os.walk('content'):
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    parts = root.replace('\\', '/').split('/')
    if 'private' in parts:
        continue
    for f in files:
        if not f.endswith('.md'):
            continue
        if f in SKIP_NAMES:
            continue
        all_md.append(os.path.join(root, f))

# ── pass 1: add missing titles ────────────────────────────────────────────────

print('=== Pass 1: Adding missing titles ===')
title_count = 0
for path in all_md:
    text = read_file(path)
    if has_title(text):
        continue
    stem = os.path.basename(path)[:-3]
    title = derive_title(stem, path)
    add_title_to_file(path, title)
    print(f'  title added: {os.path.basename(path)!r} -> {title!r}')
    title_count += 1
print(f'  {title_count} files updated\n')

# ── pass 2: rename non-slug files ─────────────────────────────────────────────

print('=== Pass 2: Renaming non-slug files ===')
rename_count = 0
error_count = 0

# Track substitutions for path correction (same logic as rename-dirs.py)
substitutions = []

# Sort by path depth then name so parents come first within a directory
all_md.sort(key=lambda p: (p.count(os.sep), p))

for path in all_md:
    fname = os.path.basename(path)
    if is_slug_name(fname):
        continue

    stem = fname[:-3]
    new_name = slugify_filename(stem)
    if new_name == fname:
        continue

    # Apply substitutions to directory
    dirpath = os.path.dirname(path).replace('\\', '/')
    current_dir = dirpath
    changed = True
    while changed:
        changed = False
        for old_p, new_p in substitutions:
            if current_dir == old_p or current_dir.startswith(old_p + '/'):
                current_dir = new_p + current_dir[len(old_p):]
                changed = True
                break

    old_full = current_dir + '/' + fname
    new_full = current_dir + '/' + new_name

    ok = git_mv(old_full, new_full)
    if ok:
        print(f'  renamed: {fname!r} -> {new_name!r}')
        substitutions.append((old_full, new_full))
        rename_count += 1
    else:
        error_count += 1

print(f'\n  {rename_count} files renamed, {error_count} errors')
