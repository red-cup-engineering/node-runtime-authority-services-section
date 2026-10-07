#!/usr/bin/env python3
"""Extract theorem structures from Markdown papers for comparison."""

import re
import sys
from pathlib import Path

def extract_formal_statements(filepath):
    """Extract axioms, theorems, lemmas, corollaries, definitions."""
    content = Path(filepath).read_text()
    
    # Patterns for formal statements - handle both blockquote and bullet formats
    patterns = {
        'axiom': [
            r'^>\s*Axiom\s+(\d+)\s*\(([^)]+)\)',
            r'^-\s+Axiom\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
        ],
        'theorem': [
            r'^>\s*Theorem\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
            r'^-\s+Theorem\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
        ],
        'lemma': [
            r'^>\s*Lemma\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
            r'^-\s+Lemma\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
        ],
        'corollary': [
            r'^>\s*Corollary\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
            r'^-\s+Corollary\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
        ],
        'definition': [
            r'^>\s*Definition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
            r'^-\s+Definition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
        ],
        'proposition': [
            r'^>\s*Proposition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
            r'^-\s+Proposition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)',
        ],
    }
    
    statements = []
    
    for line_num, line in enumerate(content.split('\n'), 1):
        for stmt_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    number = match.group(1) if match.lastindex >= 1 else "?"
                    name = match.group(2) if match.lastindex >= 2 else "unnamed"
                    statements.append({
                        'type': stmt_type,
                        'number': number,
                        'name': name,
                        'line': line_num
                    })
                    break
    
    return {'statements': statements}

def format_output(filepath, data):
    """Format extraction results."""
    print(f"\n{'='*80}")
    print(f"FILE: {Path(filepath).name}")
    print(f"{'='*80}\n")
    
    print(f"FORMAL STATEMENTS ({len(data['statements'])}):\n")
    
    # Group by type
    by_type = {}
    for stmt in data['statements']:
        by_type.setdefault(stmt['type'], []).append(stmt)
    
    for stmt_type in ['axiom', 'definition', 'lemma', 'theorem', 'corollary', 'proposition']:
        if stmt_type in by_type:
            print(f"{stmt_type.upper()}S ({len(by_type[stmt_type])}):")
            for stmt in by_type[stmt_type]:
                print(f"  {stmt['number']:5s} | {stmt['name']}")
            print()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_theorems.py <file1.md> [file2.md ...]")
        sys.exit(1)
    
    all_data = {}
    for filepath in sys.argv[1:]:
        data = extract_formal_statements(filepath)
        all_data[filepath] = data
        format_output(filepath, data)
    
    # Summary comparison
    print(f"\n{'='*80}")
    print("SUMMARY COMPARISON")
    print(f"{'='*80}\n")
    for filepath, data in all_data.items():
        print(f"{Path(filepath).name:50s} : {len(data['statements']):3d} formal statements")
