#!/usr/bin/env python3
"""Search academic literature via Semantic Scholar and arXiv APIs.

Usage:
  python search-academic-literature.py "formal semiotics Peirce"
  python search-academic-literature.py "Heyting algebra closure" --year 2020-2026
  python search-academic-literature.py "semiosis category theory" --arxiv-only
  python search-academic-literature.py "Peirce habit interpretant" --scholar-only
  python search-academic-literature.py "coalgebra semiosis" --bibtex
  python search-academic-literature.py "Zalamea Peirce" --bibtex --append

Options:
  --year RANGE      Filter by year range (e.g., 2020-2026, 2024)
  --limit N         Max results per source (default: 10)
  --arxiv-only      Search only arXiv
  --scholar-only    Search only Semantic Scholar
  --bibtex          Output BibTeX entries
  --append          Append BibTeX to repository bibliography.bib
  --abstracts       Show full abstracts (default: truncated)
  --venue FILTER    Filter Semantic Scholar by venue substring
"""

import argparse
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from textwrap import fill

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent.parent
BIB_PATH = REPO_ROOT / "bibliography.bib"

# ---------------------------------------------------------------------------
# Semantic Scholar API
# ---------------------------------------------------------------------------

S2_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
S2_FIELDS = "title,authors,year,venue,abstract,citationCount,externalIds,url"


def search_semantic_scholar(query, limit=10, year=None, venue=None):
    """Search Semantic Scholar Academic Graph API."""
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": S2_FIELDS,
    }
    if year:
        params["year"] = year

    url = f"{S2_SEARCH}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "emsenn-research/1.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  Semantic Scholar error: {e.code} {e.reason}", file=sys.stderr)
        return []
    except urllib.error.URLError as e:
        print(f"  Semantic Scholar connection error: {e.reason}", file=sys.stderr)
        return []

    results = []
    for paper in data.get("data", []):
        if venue and paper.get("venue"):
            if venue.lower() not in paper["venue"].lower():
                continue

        authors = [a.get("name", "") for a in paper.get("authors", [])]
        ext_ids = paper.get("externalIds", {}) or {}

        results.append({
            "source": "S2",
            "title": paper.get("title", ""),
            "authors": authors,
            "year": paper.get("year"),
            "venue": paper.get("venue", ""),
            "abstract": paper.get("abstract", ""),
            "citations": paper.get("citationCount", 0),
            "doi": ext_ids.get("DOI", ""),
            "arxiv_id": ext_ids.get("ArXiv", ""),
            "url": paper.get("url", ""),
        })

    return results


# ---------------------------------------------------------------------------
# arXiv API
# ---------------------------------------------------------------------------

ARXIV_API = "http://export.arxiv.org/api/query"
ARXIV_NS = {"atom": "http://www.w3.org/2005/Atom"}


def search_arxiv(query, limit=10):
    """Search arXiv API."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": min(limit, 50),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    url = f"{ARXIV_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "emsenn-research/1.0")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            xml_data = resp.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        print(f"  arXiv error: {e}", file=sys.stderr)
        return []

    root = ET.fromstring(xml_data)
    results = []

    for entry in root.findall("atom:entry", ARXIV_NS):
        title_el = entry.find("atom:title", ARXIV_NS)
        title = title_el.text.strip().replace("\n", " ") if title_el is not None else ""

        abstract_el = entry.find("atom:summary", ARXIV_NS)
        abstract = abstract_el.text.strip().replace("\n", " ") if abstract_el is not None else ""

        authors = []
        for author_el in entry.findall("atom:author", ARXIV_NS):
            name_el = author_el.find("atom:name", ARXIV_NS)
            if name_el is not None:
                authors.append(name_el.text.strip())

        published_el = entry.find("atom:published", ARXIV_NS)
        year = None
        if published_el is not None:
            year = int(published_el.text[:4])

        id_el = entry.find("atom:id", ARXIV_NS)
        arxiv_url = id_el.text.strip() if id_el is not None else ""
        arxiv_id = arxiv_url.split("/abs/")[-1] if "/abs/" in arxiv_url else ""

        # Extract categories
        categories = []
        for cat_el in entry.findall("atom:category", ARXIV_NS):
            term = cat_el.get("term", "")
            if term:
                categories.append(term)

        # Look for DOI in links
        doi = ""
        for link_el in entry.findall("atom:link", ARXIV_NS):
            href = link_el.get("href", "")
            if "doi.org" in href:
                doi = href.split("doi.org/")[-1]

        results.append({
            "source": "arXiv",
            "title": title,
            "authors": authors,
            "year": year,
            "venue": ", ".join(categories[:3]),
            "abstract": abstract,
            "citations": None,
            "doi": doi,
            "arxiv_id": arxiv_id,
            "url": arxiv_url,
        })

    return results


# ---------------------------------------------------------------------------
# BibTeX generation
# ---------------------------------------------------------------------------

def make_bibtex_key(paper):
    """Generate a BibTeX citation key."""
    first_author = paper["authors"][0] if paper["authors"] else "Unknown"
    # Last name of first author
    last = first_author.split()[-1] if first_author else "Unknown"
    # Remove non-alphanumeric
    last = re.sub(r"[^a-zA-Z]", "", last)
    year = paper["year"] or "XXXX"
    # First significant word of title
    stop_words = {"a", "an", "the", "of", "in", "on", "for", "and", "to", "with"}
    words = [w for w in paper["title"].split() if w.lower() not in stop_words]
    first_word = re.sub(r"[^a-zA-Z]", "", words[0]) if words else "untitled"
    return f"{last}{year}{first_word}"


def paper_to_bibtex(paper):
    """Convert a paper dict to a BibTeX entry."""
    key = make_bibtex_key(paper)
    authors_str = " and ".join(paper["authors"])
    year = paper["year"] or ""

    entry_type = "article"
    if paper.get("arxiv_id") and not paper.get("doi"):
        entry_type = "misc"

    lines = [f"@{entry_type}{{{key},"]
    lines.append(f"  title = {{{paper['title']}}},")
    lines.append(f"  author = {{{authors_str}}},")
    if year:
        lines.append(f"  year = {{{year}}},")
    if paper.get("venue"):
        if entry_type == "article":
            lines.append(f"  journal = {{{paper['venue']}}},")
        else:
            lines.append(f"  howpublished = {{{paper['venue']}}},")
    if paper.get("doi"):
        lines.append(f"  doi = {{{paper['doi']}}},")
    if paper.get("arxiv_id"):
        lines.append(f"  eprint = {{{paper['arxiv_id']}}},")
        lines.append(f"  archiveprefix = {{arXiv}},")
    if paper.get("url"):
        lines.append(f"  url = {{{paper['url']}}},")
    lines.append("}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_paper(paper, index, show_abstract=False):
    """Print a paper result."""
    src = paper["source"]
    year = paper["year"] or "n.d."
    cites = f", {paper['citations']} cites" if paper["citations"] is not None else ""
    authors = ", ".join(paper["authors"][:4])
    if len(paper["authors"]) > 4:
        authors += " et al."

    print(f"\n  [{index}] ({src}, {year}{cites})")
    print(f"      {paper['title']}")
    print(f"      {authors}")
    if paper.get("venue"):
        print(f"      Venue: {paper['venue']}")
    if paper.get("doi"):
        print(f"      DOI: {paper['doi']}")
    if paper.get("arxiv_id"):
        print(f"      arXiv: {paper['arxiv_id']}")

    if show_abstract and paper.get("abstract"):
        abstract = paper["abstract"][:500]
        if len(paper["abstract"]) > 500:
            abstract += "..."
        print(f"      Abstract: {fill(abstract, width=72, subsequent_indent='        ')}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Search academic literature via Semantic Scholar and arXiv")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--year", default=None,
                        help="Year or range (e.g., 2020-2026)")
    parser.add_argument("--limit", type=int, default=10,
                        help="Max results per source (default: 10)")
    parser.add_argument("--arxiv-only", action="store_true",
                        help="Search only arXiv")
    parser.add_argument("--scholar-only", action="store_true",
                        help="Search only Semantic Scholar")
    parser.add_argument("--bibtex", action="store_true",
                        help="Output BibTeX entries")
    parser.add_argument("--append", action="store_true",
                        help="Append BibTeX to bibliography.bib")
    parser.add_argument("--abstracts", action="store_true",
                        help="Show full abstracts")
    parser.add_argument("--venue", default=None,
                        help="Filter by venue substring")

    args = parser.parse_args()

    all_results = []

    if not args.arxiv_only:
        print(f"\n  Searching Semantic Scholar for: {args.query}")
        s2_results = search_semantic_scholar(
            args.query, limit=args.limit, year=args.year, venue=args.venue)
        all_results.extend(s2_results)
        print(f"  Found {len(s2_results)} results from Semantic Scholar")

    if not args.scholar_only:
        if not args.arxiv_only:
            time.sleep(0.5)  # Be polite between API calls
        print(f"\n  Searching arXiv for: {args.query}")
        arxiv_results = search_arxiv(args.query, limit=args.limit)
        # Filter by year if specified
        if args.year and arxiv_results:
            if "-" in args.year:
                lo, hi = args.year.split("-")
                lo, hi = int(lo), int(hi)
                arxiv_results = [r for r in arxiv_results
                                 if r["year"] and lo <= r["year"] <= hi]
            else:
                yr = int(args.year)
                arxiv_results = [r for r in arxiv_results
                                 if r["year"] == yr]
        all_results.extend(arxiv_results)
        print(f"  Found {len(arxiv_results)} results from arXiv")

    if not all_results:
        print("\n  No results found.")
        return

    # Deduplicate by title similarity
    seen_titles = set()
    unique_results = []
    for r in all_results:
        normalized = re.sub(r"\s+", " ", r["title"].lower().strip())
        if normalized not in seen_titles:
            seen_titles.add(normalized)
            unique_results.append(r)

    # Sort: Semantic Scholar first (has citation counts), then arXiv
    unique_results.sort(
        key=lambda r: (r["citations"] or 0) if r["source"] == "S2" else -1,
        reverse=True)

    print(f"\n  === {len(unique_results)} unique results ===")

    for i, paper in enumerate(unique_results, 1):
        display_paper(paper, i, show_abstract=args.abstracts)

    if args.bibtex:
        print("\n\n  === BibTeX ===\n")
        bib_entries = []
        for paper in unique_results:
            if paper["authors"]:
                bib = paper_to_bibtex(paper)
                bib_entries.append(bib)
                print(bib)
                print()

        if args.append and bib_entries:
            with open(BIB_PATH, "a", encoding="utf-8") as f:
                f.write("\n\n% --- Added by search-academic-literature ---\n")
                for bib in bib_entries:
                    f.write(f"\n{bib}\n")
            print(f"\n  Appended {len(bib_entries)} entries to {BIB_PATH}")

    print()


if __name__ == "__main__":
    main()
