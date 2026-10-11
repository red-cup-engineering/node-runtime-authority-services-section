#!/usr/bin/env python3
"""Generate consolidated statement manifest with context for comparison."""

import re
import json
import sys
from pathlib import Path
from typing import List, Dict

def extract_statements_with_context(filepath: str) -> List[Dict]:
    """Extract formal statements with surrounding context."""
    content = Path(filepath).read_text()
    lines = content.split('\n')
    
    # Patterns for formal statements
    patterns = {
        'axiom': [r'^>\s*Axiom\s+(\d+)\s*\(([^)]+)\)', r'^-\s+Axiom\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)'],
        'theorem': [r'^>\s*Theorem\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)', r'^-\s+Theorem\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)'],
        'lemma': [r'^>\s*Lemma\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)', r'^-\s+Lemma\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)'],
        'corollary': [r'^>\s*Corollary\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)', r'^-\s+Corollary\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)'],
        'definition': [r'^>\s*Definition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)', r'^-\s+Definition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)'],
        'proposition': [r'^>\s*Proposition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)', r'^-\s+Proposition\s+(\d+(?:\.\d+)?)\s*\(([^)]+)\)'],
    }
    
    statements = []
    
    for line_num, line in enumerate(lines):
        for stmt_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.match(pattern, line)
                if match:
                    number = match.group(1) if match.lastindex >= 1 else "?"
                    name = match.group(2) if match.lastindex >= 2 else "unnamed"
                    
                    # Extract context: 3 lines before, statement, 10 lines after
                    context_start = max(0, line_num - 3)
                    context_end = min(len(lines), line_num + 11)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    # Find enclosing section (look backwards for ##)
                    section = "Unknown Section"
                    for i in range(line_num, max(0, line_num - 100), -1):
                        if lines[i].startswith('## '):
                            section = lines[i][3:].strip()
                            break
                    
                    # Normalize name for matching
                    normalized_name = name.lower().replace('–', '-').replace('—', '-').strip()
                    
                    statements.append({
                        'file': Path(filepath).name,
                        'type': stmt_type,
                        'number': number,
                        'name': name,
                        'normalized_name': normalized_name,
                        'line': line_num + 1,
                        'section': section,
                        'context': context,
                        'identifier': f"{stmt_type.upper()} {number} ({name})"
                    })
                    break
    
    return statements

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_statement_manifest.py <file1.md> [file2.md ...] > manifest.json")
        sys.exit(1)
    
    all_statements = []
    
    for filepath in sys.argv[1:]:
        statements = extract_statements_with_context(filepath)
        all_statements.extend(statements)
    
    # Output JSON
    print(json.dumps(all_statements, indent=2))

if __name__ == '__main__':
    main()
