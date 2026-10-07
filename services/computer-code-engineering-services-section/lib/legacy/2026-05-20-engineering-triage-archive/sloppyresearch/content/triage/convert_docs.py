from pathlib import Path
import subprocess
import sys

SRC_DIR = Path(__file__).resolve().parent
DST_DIR = SRC_DIR / 'markdown'
DST_DIR.mkdir(parents=True, exist_ok=True)

doc_files = sorted(SRC_DIR.glob('*.docx'))
if not doc_files:
    print('No .docx files found in triage/. Add Word exports next to the PDFs.', file=sys.stderr)
    sys.exit(1)

for docx_path in doc_files:
    out_path = DST_DIR / (docx_path.stem + '.md')
    print(f'[pandoc] {docx_path.name} -> {out_path}')
    result = subprocess.run(
        ['pandoc', str(docx_path), '-t', 'gfm', '-o', str(out_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
