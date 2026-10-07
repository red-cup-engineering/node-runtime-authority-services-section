#!/usr/bin/env python3
"""
Audit duplicate files in the corpus.

Compares .md and .org versions to identify:
- Identical files (safe to delete .org)
- Diverged files (need manual review)
- Size differences
"""

import hashlib
from pathlib import Path
from collections import defaultdict

def get_file_hash(filepath: Path) -> str:
    """Get SHA256 hash of file content."""
    return hashlib.sha256(filepath.read_bytes()).hexdigest()

def find_duplicate_pairs(base_dir: Path = Path("txt")):
    """Find files with same basename but different extensions."""
    files_by_basename = defaultdict(list)
    
    # Find all .md and .org files
    for ext in [".md", ".org"]:
        for filepath in base_dir.rglob(f"*{ext}"):
            basename = str(filepath.with_suffix(""))
            files_by_basename[basename].append(filepath)
    
    # Keep only basenames with multiple versions
    duplicates = {k: v for k, v in files_by_basename.items() if len(v) > 1}
    return duplicates

def audit_duplicates():
    """Audit all duplicate file pairs."""
    duplicates = find_duplicate_pairs()
    
    print(f"Found {len(duplicates)} file pairs with multiple versions\n")
    print("=" * 80)
    
    identical = []
    diverged = []
    
    for basename, files in sorted(duplicates.items()):
        files = sorted(files)  # Ensure consistent ordering
        
        print(f"\n{basename}")
        print("-" * 80)
        
        # Get file info
        for f in files:
            size = f.stat().st_size
            print(f"  {f.suffix:5} - {size:8,d} bytes - {f}")
        
        # Compare content if we have exactly 2 files
        if len(files) == 2:
            hash1 = get_file_hash(files[0])
            hash2 = get_file_hash(files[1])
            
            if hash1 == hash2:
                print("  ✅ IDENTICAL - Safe to delete .org version")
                identical.append(basename)
            else:
                print("  ⚠️  DIVERGED - Needs manual review")
                diverged.append(basename)
        else:
            print(f"  ⚠️  MULTIPLE VERSIONS ({len(files)} files)")
            diverged.append(basename)
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total duplicate pairs: {len(duplicates)}")
    print(f"Identical (safe to delete .org): {len(identical)}")
    print(f"Diverged (needs review): {len(diverged)}")
    
    if identical:
        print("\n" + "=" * 80)
        print("IDENTICAL FILES (safe to delete .org):")
        print("=" * 80)
        for basename in identical:
            print(f"  {basename}.org")
    
    if diverged:
        print("\n" + "=" * 80)
        print("DIVERGED FILES (needs manual review):")
        print("=" * 80)
        for basename in diverged:
            print(f"  {basename}")
    
    return identical, diverged

if __name__ == "__main__":
    identical, diverged = audit_duplicates()
