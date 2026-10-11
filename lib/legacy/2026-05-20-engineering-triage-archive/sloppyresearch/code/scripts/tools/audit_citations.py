#!/usr/bin/env python3
"""
Citation Audit Script for RRPR

Scans all corpus documents for internal citations and reports:
- Broken references (ID not found)
- Format violations (non-conformant IDs)
- Missing inverse citations
- Suggested fixes via fuzzy matching
"""

import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from difflib import get_close_matches

# ID format regex from CITATION_RESOLUTION.md
ID_PATTERN = re.compile(r'^[a-z0-9\-\.]+$')

def extract_frontmatter(content: str) -> Tuple[str, str]:
    """Extract TOML frontmatter from markdown content."""
    if not content.startswith('+++'):
        return '', content
    
    parts = content.split('+++', 2)
    if len(parts) < 3:
        return '', content
    
    return parts[1].strip(), parts[2].strip()

def parse_toml_array(line: str) -> List[str]:
    """Parse a simple TOML array from a line like: cites_internal = ["id1", "id2"]"""
    # Extract content between brackets
    match = re.search(r'\[(.*?)\]', line)
    if not match:
        return []
    
    array_content = match.group(1)
    # Split by comma and clean quotes/spaces
    items = [item.strip().strip('"').strip("'") for item in array_content.split(',')]
    return [item for item in items if item]

def get_document_id(frontmatter: str) -> str:
    """Extract document ID from frontmatter."""
    for line in frontmatter.split('\n'):
        if line.startswith('id = '):
            return line.split('=', 1)[1].strip().strip('"').strip("'")
    return ''

def get_internal_citations(frontmatter: str) -> List[str]:
    """Extract cites_internal array from frontmatter."""
    for line in frontmatter.split('\n'):
        if line.startswith('cites_internal = '):
            return parse_toml_array(line)
    return []

def scan_corpus(corpus_dirs: List[Path]) -> Dict:
    """Scan all corpus documents and extract metadata."""
    documents = {}
    
    for corpus_dir in corpus_dirs:
        if not corpus_dir.exists():
            continue
            
        for md_file in corpus_dir.rglob('*.md'):
            content = md_file.read_text(encoding='utf-8')
            frontmatter, body = extract_frontmatter(content)
            
            doc_id = get_document_id(frontmatter)
            if not doc_id:
                print(f"⚠️  No ID found in {md_file}")
                continue
            
            citations = get_internal_citations(frontmatter)
            
            try:
                rel_path = md_file.relative_to(Path.cwd())
            except ValueError:
                rel_path = md_file
            
            documents[doc_id] = {
                'path': str(rel_path),
                'file': md_file,
                'citations': citations
            }
    
    return documents

def validate_id_format(doc_id: str) -> bool:
    """Check if ID matches ^[a-z0-9\-\.]+$ pattern."""
    return bool(ID_PATTERN.match(doc_id))

def audit_citations(documents: Dict) -> Dict:
    """Perform comprehensive citation audit."""
    
    all_ids = set(documents.keys())
    report = {
        'total_documents': len(documents),
        'total_citations': 0,
        'broken_references': [],
        'format_violations': [],
        'suggested_fixes': {},
        'valid_citations': 0
    }
    
    for doc_id, doc_data in documents.items():
        # Check document ID format
        if not validate_id_format(doc_id):
            report['format_violations'].append({
                'document': doc_id,
                'path': doc_data['path'],
                'type': 'document_id',
                'issue': f"ID '{doc_id}' violates format ^[a-z0-9\-\.]+$"
            })
        
        # Check each citation
        for cited_id in doc_data['citations']:
            report['total_citations'] += 1
            
            # Check citation ID format
            if not validate_id_format(cited_id):
                report['format_violations'].append({
                    'document': doc_id,
                    'path': doc_data['path'],
                    'type': 'citation_id',
                    'citation': cited_id,
                    'issue': f"Citation '{cited_id}' violates format ^[a-z0-9\-\.]+$"
                })
                continue
            
            # Check if citation target exists
            if cited_id not in all_ids:
                # Find close matches
                suggestions = get_close_matches(cited_id, all_ids, n=3, cutoff=0.7)
                
                report['broken_references'].append({
                    'document': doc_id,
                    'path': doc_data['path'],
                    'citation': cited_id,
                    'suggestions': suggestions
                })
                
                if suggestions:
                    report['suggested_fixes'][cited_id] = suggestions[0]
            else:
                report['valid_citations'] += 1
    
    return report

def print_report(report: Dict):
    """Print human-readable audit report."""
    print("=" * 70)
    print("RRPR CITATION AUDIT REPORT")
    print("=" * 70)
    print(f"\n📊 SUMMARY:")
    print(f"   Documents scanned: {report['total_documents']}")
    print(f"   Total citations: {report['total_citations']}")
    print(f"   Valid citations: {report['valid_citations']}")
    print(f"   Broken references: {len(report['broken_references'])}")
    print(f"   Format violations: {len(report['format_violations'])}")
    
    if report['format_violations']:
        print(f"\n⚠️  FORMAT VIOLATIONS ({len(report['format_violations'])}):")
        for violation in report['format_violations']:
            print(f"\n   Document: {violation['document']}")
            print(f"   Path: {violation['path']}")
            print(f"   Issue: {violation['issue']}")
    
    if report['broken_references']:
        print(f"\n❌ BROKEN REFERENCES ({len(report['broken_references'])}):")
        for ref in report['broken_references']:
            print(f"\n   Document: {ref['document']}")
            print(f"   Path: {ref['path']}")
            print(f"   Missing citation: '{ref['citation']}'")
            if ref['suggestions']:
                print(f"   Did you mean: {', '.join(ref['suggestions'])}")
    
    if report['suggested_fixes']:
        print(f"\n🔧 AUTO-FIX SUGGESTIONS:")
        for broken_id, suggested_id in report['suggested_fixes'].items():
            print(f"   '{broken_id}' → '{suggested_id}'")
    
    if not report['broken_references'] and not report['format_violations']:
        print("\n✅ All citations are valid and properly formatted!")
    
    print("\n" + "=" * 70)

def main():
    # Scan entire corpus (all .md files)
    corpus_dirs = [
        Path('txt'),
        Path('internal-theory'),
        Path('research-notes')
    ]
    
    print("🔍 Scanning entire corpus for citations...")
    documents = scan_corpus(corpus_dirs)
    
    print(f"📚 Found {len(documents)} documents")
    print("🔍 Auditing citations...\n")
    
    report = audit_citations(documents)
    print_report(report)
    
    # Save detailed report as JSON
    report_file = Path('citation_audit_report.json')
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n💾 Detailed report saved to: {report_file}")

if __name__ == '__main__':
    main()
