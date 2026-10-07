"""
Publishing utilities for RRPR CMS workflows.

Handles generating PDF and HTML outputs from Markdown documents and capturing
the publish manifest for reproducibility.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Dict


SUPPORTED_FORMATS = {"pdf", "html"}
DEFAULT_FORMATS = ["pdf", "html"]
PUBLISH_ROOT = Path("docs/publish")
TEMPLATE_DIR = PUBLISH_ROOT / "templates"
LATEX_TEMPLATE = TEMPLATE_DIR / "rrp.latex"
HTML_TEMPLATE = TEMPLATE_DIR / "rrp.html5"
HTML_CSS = PUBLISH_ROOT / "style.css"


@dataclass
class PublishResult:
    doc_path: Path
    format: str
    output_path: Path
    status: str
    detail: str


def ensure_pandoc() -> None:
    if shutil.which("pandoc") is None:
        raise RuntimeError("pandoc executable not found in PATH")


def _build_metadata_vars(extra: Dict[str, str]) -> List[str]:
    vars_args: List[str] = []
    for key, value in extra.items():
        if value:
            vars_args.extend(["-V", f"{key}={value}"])
    return vars_args


def convert_document(doc_path: Path, out_path: Path, fmt: str, meta: Dict[str, str]) -> None:
    ensure_pandoc()
    args = ["pandoc", str(doc_path), "-o", str(out_path), "--standalone"]
    if fmt == "pdf":
        args.extend(["--pdf-engine=xelatex"])
        if LATEX_TEMPLATE.exists():
            args.extend(["--template", str(LATEX_TEMPLATE)])
    if fmt == "html":
        args.append("--self-contained")
        if HTML_TEMPLATE.exists():
            args.extend(["--template", str(HTML_TEMPLATE)])
        if HTML_CSS.exists():
            args.extend(["--css", str(HTML_CSS)])
    args.extend(_build_metadata_vars(meta))
    subprocess.run(args, check=True, capture_output=True)


def publish_documents(
    doc_paths: Iterable[Path],
    formats: Iterable[str],
    out_dir: Path,
    dry_run: bool = True,
    git_info: Dict[str, str] | None = None,
) -> List[PublishResult]:
    formats = [f.lower() for f in formats]
    for fmt in formats:
        if fmt not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {fmt}")

    results: List[PublishResult] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    repo_root = Path.cwd()

    extra_metadata = git_info or get_git_metadata()

    for doc_path in sorted(doc_paths):
        if not doc_path.is_file():
            continue

        try:
            relative = doc_path.relative_to(repo_root)
        except ValueError:
            relative = doc_path

        for fmt in formats:
            output_path = out_dir / relative.with_suffix(f".{fmt}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            status = "dry-run" if dry_run else "ok"
            detail = "skipped (dry-run)" if dry_run else "generated"

            if not dry_run:
                try:
                    convert_document(
                        doc_path,
                        output_path,
                        fmt,
                        meta={
                            "commit": extra_metadata.get("commit", ""),
                            "branch": extra_metadata.get("branch", ""),
                        },
                    )
                except subprocess.CalledProcessError as exc:
                    stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
                    snippet = "\n".join(stderr.strip().splitlines()[:6])
                    raise RuntimeError(
                        f"Pandoc failed for {doc_path} ({fmt}). "
                        "Fix the document's LaTeX/Markdown markup.\n"
                        f"{snippet}"
                    ) from exc

            results.append(PublishResult(
                doc_path=doc_path,
                format=fmt,
                output_path=output_path,
                status=status,
                detail=detail
            ))

    return results


def get_git_metadata() -> Dict[str, str]:
    def run_git(args: List[str]) -> str:
        output = subprocess.check_output(["git"] + args, text=True).strip()
        return output

    try:
        branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        commit = run_git(["rev-parse", "--short", "HEAD"])
    except subprocess.CalledProcessError:
        branch = "unknown"
        commit = "unknown"

    return {"branch": branch, "commit": commit}


def get_tool_versions() -> Dict[str, str]:
    def safe_call(args: List[str]) -> str:
        try:
            return subprocess.check_output(args, text=True).splitlines()[0]
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"

    pandoc_version = safe_call(["pandoc", "--version"])
    return {
        "pandoc": pandoc_version,
        "python": sys.version.split()[0],
        "rrpr_cli": "0.1.0",
    }


def write_manifest(
    results: List[PublishResult],
    out_path: Path,
    extra: Dict[str, str] | None = None
) -> None:
    extra_copy = dict(extra) if extra else {}
    git_meta = {
        "branch": extra_copy.pop("branch", None),
        "commit": extra_copy.pop("commit", None),
    }

    data = {
        "timestamp": datetime.utcnow().isoformat(),
        "tool": "rrpr publish",
        "tool_versions": get_tool_versions(),
        "git": git_meta,
        "results": [
            {
                "doc": str(result.doc_path),
                "format": result.format,
                "output": str(result.output_path),
                "status": result.status,
                "detail": result.detail
            }
            for result in results
        ]
    }

    if extra_copy:
        data.update(extra_copy)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
