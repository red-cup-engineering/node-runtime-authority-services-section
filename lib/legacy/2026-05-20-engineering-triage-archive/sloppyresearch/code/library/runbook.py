from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from rich.console import Console

from code.library import publish as publishing
from code.library.authoring import lint_paper
from code.library.config import get_default_config
from code.library.database import Database


@dataclass
class RunbookStep:
    op: str
    args: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    when: Optional[str] = None


@dataclass
class Runbook:
    version: int
    name: str
    description: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    policy: Dict[str, Any] = field(default_factory=dict)
    steps: List[RunbookStep] = field(default_factory=list)
    outputs: List[Any] = field(default_factory=list)


@dataclass
class RunbookContext:
    path: Path
    variables: Dict[str, Any]
    apply: bool
    console: Console


RUNBOOK_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


def load_runbook(path: Path) -> Runbook:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    steps = [
        RunbookStep(
            op=step.get("op"),
            args=step.get("args", {}) or {},
            outputs=step.get("outputs", {}) or {},
            when=step.get("when"),
        )
        for step in data.get("steps", [])
    ]
    return Runbook(
        version=data.get("version", 1),
        name=data.get("name", path.stem),
        description=data.get("description", ""),
        inputs=data.get("inputs", {}) or {},
        policy=data.get("policy", {}) or {},
        steps=steps,
        outputs=data.get("outputs", []) or [],
    )


def _collect_git_metadata() -> Dict[str, str]:
    meta = publishing.get_git_metadata()
    meta.setdefault("branch", "")
    meta.setdefault("commit", "")
    meta["shortsha"] = meta.get("commit", "")[:8]
    return meta


def _build_variables(runbook: Runbook, overrides: Dict[str, str], extra_vars: Dict[str, str]) -> Dict[str, Any]:
    variables: Dict[str, Any] = dict(os.environ)
    variables.update({k: str(v) for k, v in runbook.inputs.items()})
    variables.update(overrides)
    variables.update(extra_vars)

    now = datetime.utcnow()
    variables.setdefault("DATE", now.strftime("%Y-%m-%d"))
    variables.setdefault("DATETIME", now.isoformat())
    variables.setdefault("TIME", now.strftime("%H:%M:%S"))

    git_meta = _collect_git_metadata()
    variables.setdefault("GIT_BRANCH", git_meta["branch"])
    variables.setdefault("GIT_COMMIT", git_meta["commit"])
    variables.setdefault("SHORTSHA", git_meta["shortsha"])
    variables.setdefault("project_root", str(Path(".").resolve()))
    return variables


def _resolve_value(value: Any, variables: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        def repl(match: re.Match[str]) -> str:
            key = match.group(1)
            return str(variables.get(key, match.group(0)))

        return RUNBOOK_VAR_PATTERN.sub(repl, value)
    if isinstance(value, list):
        return [_resolve_value(item, variables) for item in value]
    if isinstance(value, dict):
        return {k: _resolve_value(v, variables) for k, v in value.items()}
    return value


def _should_run_step(step: RunbookStep, variables: Dict[str, Any]) -> bool:
    if not step.when:
        return True
    key = step.when.strip()
    return bool(variables.get(key))


def _invoke_cli(args: List[str], *, apply: bool, console: Console):
    console.print(f"[cyan]rrpr {' '.join(args)}[/cyan] (apply={apply})")
    if not apply:
        return
    cmd = [sys.executable, "-m", "code.library.cli.main", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        console.print(result.stdout)
        console.print(result.stderr)
        raise RuntimeError(f"Command {' '.join(args)} failed with code {result.returncode}")
    if result.stdout.strip():
        console.print(result.stdout)


def _run_ingest(args: Dict[str, Any], _outputs: Dict[str, Any], ctx: RunbookContext):
    cli_args = ["ingest", "repo"]
    if branch := args.get("branch"):
        cli_args += ["--branch", str(branch)]
    if commit := args.get("commit"):
        cli_args += ["--commit", str(commit)]
    _invoke_cli(cli_args, apply=ctx.apply, console=ctx.console)


def _run_publish(args: Dict[str, Any], _outputs: Dict[str, Any], ctx: RunbookContext):
    formats = args.get("format", ["pdf", "html"])
    out_dir = args.get("out_dir", "dist")
    cli_args = ["publish", "docs", "--out", str(out_dir)]
    for fmt in formats:
        cli_args += ["--format", str(fmt)]
    if ctx.apply:
        cli_args.append("--apply")
    _invoke_cli(cli_args, apply=True, console=ctx.console)


def _glob_paths(patterns: Iterable[str]) -> List[Path]:
    paths: List[Path] = []
    for pattern in patterns:
        paths.extend(Path().glob(pattern))
    return sorted(set(paths))


def _run_lint(args: Dict[str, Any], outputs: Dict[str, Any], ctx: RunbookContext):
    paths = _glob_paths(args.get("paths", []))
    if not paths:
        ctx.console.print("[yellow]No files matched lint paths[/yellow]")
        return
    records = []
    for path in paths:
        if not ctx.apply:
            ctx.console.print(f"[cyan]lint (dry-run):[/cyan] {path}")
            records.append({"path": str(path), "ok": True, "errors": [], "warnings": []})
            continue
        result = lint_paper(path)
        record = {
            "path": str(path),
            "ok": result.ok,
            "errors": result.errors,
            "warnings": result.warnings,
        }
        records.append(record)
        if result.ok:
            ctx.console.print(f"[green]✓ lint:[/green] {path}")
        else:
            ctx.console.print(f"[red]✗ lint:[/red] {path}")
            for error in result.errors:
                ctx.console.print(f"  - {error}")
    if report_path := outputs.get("report"):
        target = Path(report_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(records, indent=2), encoding="utf-8")
        ctx.console.print(f"[blue]Lint report written to {target}[/blue]")


def _write_status(out_path: Path, variables: Dict[str, Any], stats: Dict[str, Any]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    block = [
        f"- Date: {variables.get('DATE')}",
        f"- Commit: {variables.get('SHORTSHA')}",
        f"- Branch: {variables.get('GIT_BRANCH')}",
        f"- Documents: {stats.get('documents_with_metadata', 'N/A')}",
        f"- Virtual Cells: {stats.get('virtual_relcells', 'N/A')}",
        f"- Edges: {stats.get('total_edges', 'N/A')}",
        "- Notes:",
        f"  - Runbook execution on {variables.get('DATE')} (auto status entry)",
    ]
    content = "\n".join(block) + "\n"
    text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    marker = "## Snapshots"
    if marker in text:
        head, tail = text.split(marker, 1)
        new_text = f"{head}{marker}\n\n{content}{tail.lstrip()}"
    else:
        new_text = text + "\n\n" + marker + "\n\n" + content
    out_path.write_text(new_text.strip() + "\n", encoding="utf-8")


def _append_changelog(out_path: Path, variables: Dict[str, Any], summary: str):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    entry = "\n".join(
        [
            f"### {variables.get('DATE')} {variables.get('SHORTSHA')}",
            f"- Summary: {summary}",
            "",
        ]
    )
    text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    marker = "- Newest at top."
    if marker in text:
        head, tail = text.split(marker, 1)
        new_text = f"{head}{marker}\n\n{entry}{tail.lstrip()}"
    else:
        new_text = text + "\n\n" + entry
    out_path.write_text(new_text.strip() + "\n", encoding="utf-8")


def _run_status(args: Dict[str, Any], _outputs: Dict[str, Any], ctx: RunbookContext):
    config = get_default_config()
    db = Database(config.db_path)
    if not db.db_path.exists():
        ctx.console.print(f"[yellow]Skipping status: database not found at {db.db_path}[/yellow]")
        return
    db.connect()
    try:
        stats = db.get_stats()
    finally:
        db.disconnect()
    out_path = Path(args.get("out", "docs/for-agents/log.agent-status.md"))
    if not ctx.apply:
        ctx.console.print(f"[cyan]status (dry-run) →[/cyan] {out_path}")
        ctx.console.print(stats)
        return
    _write_status(out_path, ctx.variables, stats)
    ctx.console.print(f"[green]Status updated at {out_path}[/green]")


def _run_changelog(args: Dict[str, Any], _outputs: Dict[str, Any], ctx: RunbookContext):
    out_path = Path(args.get("out", "docs/for-agents/log.agent-changelog.md"))
    summary = args.get("summary", "Runbook execution")
    if not ctx.apply:
        ctx.console.print(f"[cyan]changelog (dry-run)[/cyan] {summary}")
        return
    _append_changelog(out_path, ctx.variables, summary)
    ctx.console.print(f"[green]Changelog updated at {out_path}[/green]")


def _run_todos(args: Dict[str, Any], _outputs: Dict[str, Any], ctx: RunbookContext):
    out_path = Path(args.get("out", "docs/for-agents/log.agent-todo.md"))
    section = args.get("section", "Next")
    additions = args.get("entries", [])
    if not additions:
        ctx.console.print(f"[yellow]TODO update skipped: no entries provided (see {out_path})[/yellow]")
        return
    if not ctx.apply:
        ctx.console.print(f"[cyan]todos (dry-run) →[/cyan] {out_path}")
        for entry in additions:
            ctx.console.print(f"  - [ ] {entry}")
        return
    text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
    marker = f"## {section}"
    if marker not in text:
        ctx.console.print(f"[yellow]Section '{section}' not found in {out_path}; creating it.[/yellow]")
        text += f"\n\n{marker}\n"
    head, tail = text.split(marker, 1)
    rest = tail.split("\n##", 1)
    current = rest[0].strip("\n")
    remainder = f"\n##{rest[1]}" if len(rest) > 1 else ""
    block_lines = current.splitlines()
    for entry in additions:
        block_lines.insert(0, f"- [ ] {entry}")
    updated_block = "\n".join(line.strip() for line in block_lines if line.strip())
    new_text = f"{head}{marker}\n{updated_block}\n{remainder}".strip("\n") + "\n"
    out_path.write_text(new_text, encoding="utf-8")
    ctx.console.print(f"[green]TODOs updated at {out_path}[/green]")


STEP_HANDLERS = {
    "ingest": _run_ingest,
    "lint": _run_lint,
    "publish": _run_publish,
    "status": _run_status,
    "changelog": _run_changelog,
    "todos": _run_todos,
}


def execute_runbook(
    runbook: Runbook,
    *,
    runbook_path: Path,
    apply: bool,
    input_overrides: Dict[str, str],
    set_variables: Dict[str, str],
    console: Optional[Console] = None,
):
    console = console or Console()
    variables = _build_variables(runbook, input_overrides, set_variables)
    policy_apply = runbook.policy.get("apply", False)
    effective_apply = apply or policy_apply
    ctx = RunbookContext(path=runbook_path, variables=variables, apply=effective_apply, console=console)

    console.print(f"[bold]Runbook:[/bold] {runbook.name}")
    console.print(f"Description: {runbook.description}")
    console.print(f"Mode: {'APPLY' if effective_apply else 'DRY-RUN'}")

    for idx, step in enumerate(runbook.steps, start=1):
        if not _should_run_step(step, variables):
            console.print(f"[yellow]Skipping step {idx} ({step.op}) due to when-condition[/yellow]")
            continue

        resolved_args = _resolve_value(step.args, variables)
        resolved_outputs = _resolve_value(step.outputs, variables)
        merged_step = RunbookStep(op=step.op, args=resolved_args, outputs=resolved_outputs, when=step.when)

        console.print(f"[blue]Step {idx}/{len(runbook.steps)}:[/blue] {merged_step.op}")
        handler = STEP_HANDLERS.get(merged_step.op)
        if not handler:
            console.print(f"[red]No handler for op '{merged_step.op}'. Skipping.[/red]")
            continue

        try:
            handler(
                merged_step.args,
                merged_step.outputs,
                ctx,
            )
        except Exception as exc:
            console.print(f"[red]Step '{merged_step.op}' failed:[/red] {exc}")
            raise

    if ctx.apply and runbook.policy.get("commit"):
        ctx.console.print("[yellow]Runbook policy requires committing changes.[/yellow]")
        ctx.console.print("Run `git status` to review and `git commit -am \"runbook: ...\"` to finalize.")

    console.print("[green]Runbook completed.[/green]")
