#!/usr/bin/env python3
"""Identify potentially unique statements by comparing normalized names."""

import json
from pathlib import Path
from difflib import SequenceMatcher

def similarity(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a, b).ratio()

def find_matches(target_stmt, candidate_stmts, threshold=0.6):
    """Find similar statements in candidate list."""
    matches = []
    for candidate in candidate_stmts:
        sim = similarity(target_stmt['normalized_name'], candidate['normalized_name'])
        if sim >= threshold:
            matches.append((candidate, sim))
    return sorted(matches, key=lambda x: x[1], reverse=True)

def main():
    data = json.load(open('docs/statement_manifest.json'))
    
    pr_stmts = [s for s in data if s['file'] == 'proposing-relationing.md']
    draft_stmts = [s for s in data if s['file'] == 'proposing-a-reflexive-existence.md']
    
    print("="*80)
    print("UNIQUE STATEMENT ANALYSIS")
    print("="*80)
    print(f"\nProposing Relationing: {len(pr_stmts)} statements")
    print(f"proposing-a-reflexive-existence: {len(draft_stmts)} statements")
    
    # Find draft statements with no good match in PR
    unique_candidates = []
    
    for draft_stmt in draft_stmts:
        matches = find_matches(draft_stmt, pr_stmts, threshold=0.5)
        if not matches:
            unique_candidates.append((draft_stmt, None))
        elif matches[0][1] < 0.7:  # Weak match
            unique_candidates.append((draft_stmt, matches[0]))
    
    print(f"\n{'='*80}")
    print(f"POTENTIALLY UNIQUE STATEMENTS: {len(unique_candidates)}")
    print(f"{'='*80}\n")
    
    # Group by type
    by_type = {}
    for stmt, match in unique_candidates:
        by_type.setdefault(stmt['type'], []).append((stmt, match))
    
    for stmt_type in ['axiom', 'theorem', 'lemma', 'definition', 'corollary']:
        if stmt_type in by_type:
            print(f"\n{stmt_type.upper()}S ({len(by_type[stmt_type])}):\n")
            for stmt, match in by_type[stmt_type]:
                print(f"  {stmt['identifier']}")
                print(f"    Section: {stmt['section']}")
                print(f"    Line: {stmt['line']}")
                if match:
                    matched_stmt, sim = match
                    print(f"    Weak match ({sim:.2f}): {matched_stmt['identifier']}")
                else:
                    print(f"    No match in PR")
                print()

if __name__ == '__main__':
    main()
