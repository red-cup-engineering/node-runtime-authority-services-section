#!/usr/bin/env python3
"""Extract section outline to identify structure and Part I/II boundary."""

import re
import sys
from pathlib import Path

def extract_outline(filepath):
    """Extract hierarchical section structure."""
    content = Path(filepath).read_text()
    lines = content.split('\n')
    
    outline = []
    
    for line_num, line in enumerate(lines, 1):
        # Match markdown headers (# through ####)
        match = re.match(r'^(#{1,4})\s+(.+)$', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            outline.append({
                'line': line_num,
                'level': level,
                'title': title
            })
    
    return outline

def format_outline(outline, max_items=None):
    """Format outline with indentation."""
    items = outline[:max_items] if max_items else outline
    
    for item in items:
        indent = "  " * (item['level'] - 1)
        print(f"Line {item['line']:5d} | {'#' * item['level']} {indent}{item['title']}")
    
    if max_items and len(outline) > max_items:
        print(f"\n... and {len(outline) - max_items} more sections")

def identify_boundaries(outline):
    """Identify potential Part I/II boundaries."""
    print("\n" + "="*80)
    print("POTENTIAL PART I / PART II BOUNDARIES")
    print("="*80 + "\n")
    
    # Look for sections with "topos", "presheaf", "cohesive", "sheaf"
    keywords = ['topos', 'presheaf', 'cohesive', 'sheaf', 'construction', 'model']
    
    for i, item in enumerate(outline):
        title_lower = item['title'].lower()
        if any(kw in title_lower for kw in keywords):
            print(f"Line {item['line']:5d} | {'#' * item['level']} {item['title']}")
            print(f"  → Contains: {[kw for kw in keywords if kw in title_lower]}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python extract_section_outline.py <file.md>")
        sys.exit(1)
    
    filepath = sys.argv[1]
    outline = extract_outline(filepath)
    
    print("="*80)
    print(f"SECTION OUTLINE: {Path(filepath).name}")
    print(f"Total sections: {len(outline)}")
    print("="*80 + "\n")
    
    format_outline(outline, max_items=50)
    identify_boundaries(outline)
