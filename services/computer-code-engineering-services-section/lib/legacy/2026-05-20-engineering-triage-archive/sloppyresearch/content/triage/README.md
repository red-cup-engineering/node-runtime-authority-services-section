++
id = "guide.triage"
title = "Triage Intake"
status = "active"
document_type = "guide"
topics = ["triage", "ingest"]
keywords = ["docx", "conversion", "ingest-pipeline"]
++

# Triage Intake

Use this folder as a staging area when raw artifacts (DOCX, PDF, scans) need to be converted into canonical Markdown.

## Workflow

1. Drop source files (preferably `.docx`) directly under `triage/`.
2. Run `python3 triage/convert_docs.py` to generate GitHub-flavored Markdown in `triage/markdown/`.
3. Review/edit the generated Markdown and move it into the appropriate discipline/concept directory.
4. Delete the temporary `.docx/.pdf` once the content is integrated so this folder stays empty.

For Relationing Markdown syntax and the Pandoc filter, see `docs/dev-guides/relationing-markdown-filter.md`.
