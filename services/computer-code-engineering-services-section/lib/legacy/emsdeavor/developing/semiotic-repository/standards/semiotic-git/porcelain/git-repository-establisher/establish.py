#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


def _require(module_name: str, import_name: Optional[str] = None):
    try:
        return __import__(import_name or module_name)
    except ModuleNotFoundError as e:
        raise SystemExit(
            f"Missing dependency: {module_name}\n"
            f"Install with: pip install {module_name}\n"
            f"(Suggested: pip install jinja2 pyyaml)\n"
        ) from e


jinja2 = _require("jinja2")


def _load_yaml(path: Path) -> Any:
    yaml = _require("pyyaml", "yaml")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _slugify(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "repo"


def _python_ident(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9_]+", "_", s)
    s = re.sub(r"_{2,}", "_", s).strip("_")
    if not s:
        s = "package"
    if re.match(r"^[0-9]", s):
        s = f"pkg_{s}"
    return s


def _parse_date(value: Any) -> Optional[dt.date]:
    if value is None:
        return None
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        return value
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        try:
            return dt.date.fromisoformat(v)
        except ValueError as e:
            raise SystemExit(f"metadata.created must be ISO date YYYY-MM-DD; got {value!r}") from e
    raise SystemExit(f"metadata.created must be a date or ISO string; got {type(value).__name__}")


def _run(cmd: List[str], *, cwd: Path) -> None:
    p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(cmd)}\n\nstderr:\n{p.stderr}")


def _git_init(repo_dir: Path) -> None:
    try:
        _run(["git", "init", "-b", "main"], cwd=repo_dir)
    except SystemExit:
        _run(["git", "init"], cwd=repo_dir)
        try:
            _run(["git", "checkout", "-b", "main"], cwd=repo_dir)
        except SystemExit:
            pass


def _git_initial_commit(repo_dir: Path, message: str = "chore: initial commit") -> None:
    _run(["git", "add", "-A"], cwd=repo_dir)
    _run(["git", "commit", "-m", message], cwd=repo_dir)


def _git_enable_hooks(repo_dir: Path) -> None:
    _run(["git", "config", "core.hooksPath", ".githooks"], cwd=repo_dir)


def _chmod_executable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode | 0o111)
    except OSError:
        # Best-effort: permissions can fail on some filesystems.
        pass


@dataclass(frozen=True)
class RepoConfig:
    template: str
    output_path: Path
    project: Mapping[str, Any]
    github: Mapping[str, Any]
    license: Mapping[str, Any]
    metadata: Mapping[str, Any]
    init_git: bool
    initial_commit: bool
    force: bool
    dry_run: bool


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


@dataclass(frozen=True)
class RuntimePaths:
    templates_dir: Path
    licenses_dir: Path


def _default_templates_root() -> Path:
    env = (os.environ.get("ESTABLISH_TEMPLATES_DIR", "") or os.environ.get("PREREPO_TEMPLATES_DIR", "")).strip()
    if env:
        return Path(env).expanduser()
    return _repo_root() / "templates"


def _default_licenses_root() -> Path:
    env = (os.environ.get("ESTABLISH_LICENSES_DIR", "") or os.environ.get("PREREPO_LICENSES_DIR", "")).strip()
    if env:
        return Path(env).expanduser()
    return _repo_root() / "licenses"


def _shared_root(paths: RuntimePaths) -> Path:
    return paths.templates_dir / "_shared"

def _bundles_root(paths: RuntimePaths) -> Path:
    return paths.templates_dir / "_bundles"


def _template_dir(paths: RuntimePaths, name: str) -> Path:
    path = paths.templates_dir / name
    if not path.is_dir():
        raise SystemExit(f"Unknown template {name!r}; expected directory: {path}")
    return path


def _load_template_manifest(template_path: Path) -> Mapping[str, Any]:
    manifest_path = template_path / "template.yaml"
    if not manifest_path.is_file():
        return {}
    data = _load_yaml(manifest_path)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"template.yaml must be a mapping/object: {manifest_path}")
    bundles = data.get("bundles", [])
    if bundles is None:
        bundles = []
    if not isinstance(bundles, list) or not all(isinstance(x, str) for x in bundles):
        raise SystemExit(f"template.yaml bundles must be a list of strings: {manifest_path}")
    return data


def _jinja_env(paths: RuntimePaths, loader_roots: List[Path]) -> "jinja2.Environment":
    loader = jinja2.FileSystemLoader([str(p) for p in loader_roots])
    env = jinja2.Environment(
        loader=loader,
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        lstrip_blocks=True,
        trim_blocks=True,
    )
    env.filters["slugify"] = _slugify
    env.filters["python_ident"] = _python_ident
    env.filters["urlquote"] = lambda s: urllib.parse.quote(str(s), safe="")
    return env


def _coerce_mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise SystemExit(f"{name} must be a mapping/object; got {type(value).__name__}")
    return value


def _read_config_yaml(path: Path) -> Tuple[Mapping[str, Any], RepoConfig]:
    data = _load_yaml(path)
    if not isinstance(data, dict):
        raise SystemExit("config YAML must be a YAML mapping/object at top level")

    template = str(data.get("template", "")).strip()
    if not template:
        raise SystemExit("Missing required field: template")

    output_path_raw = data.get("output_path")
    if output_path_raw is None:
        raise SystemExit("Missing required field: output_path")
    output_path = Path(str(output_path_raw)).expanduser()

    project = _coerce_mapping(data.get("project"), name="project")
    license_cfg = _coerce_mapping(data.get("license"), name="license")
    metadata = _coerce_mapping(data.get("metadata"), name="metadata")
    github = _coerce_mapping(data.get("github"), name="github")

    init_git = bool(data.get("init_git", True))
    initial_commit = bool(data.get("initial_commit", False))

    cfg = RepoConfig(
        template=template,
        output_path=output_path,
        project=project,
        github=github,
        license=license_cfg,
        metadata=metadata,
        init_git=init_git,
        initial_commit=initial_commit,
        force=False,
        dry_run=False,
    )
    return data, cfg


def _default_context(cfg: RepoConfig) -> Dict[str, Any]:
    project_name = str(cfg.project.get("name", "")).strip() or cfg.output_path.name
    description = str(cfg.project.get("description", "")).strip()
    author = str(cfg.project.get("author", "")).strip() or os.environ.get("GIT_AUTHOR_NAME", "").strip()
    contact_email = str(cfg.project.get("contact_email", "")).strip() or os.environ.get("GIT_AUTHOR_EMAIL", "").strip()
    organization = str(cfg.project.get("organization", "")).strip()

    license_id = str(cfg.license.get("id", "")).strip() or "MIT"

    created = _parse_date(cfg.metadata.get("created")) or dt.date.today()
    status = str(cfg.metadata.get("status", "")).strip()
    tags = cfg.metadata.get("tags", [])
    if tags is None:
        tags_list: List[str] = []
    elif isinstance(tags, list):
        tags_list = [str(t).strip() for t in tags if str(t).strip()]
    else:
        raise SystemExit("metadata.tags must be a list of strings")

    slug = _slugify(project_name)
    python_pkg = _python_ident(slug.replace("-", "_"))

    github_owner = str(cfg.github.get("owner", "")).strip()
    github_repo = str(cfg.github.get("repo", "")).strip()
    github_default_branch = str(cfg.github.get("default_branch", "")).strip() or "main"
    github_badges = cfg.github.get("badges", {})
    if github_badges is None:
        github_badges = {}
    if not isinstance(github_badges, dict):
        raise SystemExit("github.badges must be a mapping/object")

    include_codeowners = cfg.github.get("include_codeowners")
    if include_codeowners is None:
        include_codeowners = True
    include_funding = cfg.github.get("include_funding")
    if include_funding is None:
        include_funding = False

    badges_tags = github_badges.get("tags")
    if badges_tags is None:
        badges_tags = False

    return {
        "template": cfg.template,
        "output_path": str(cfg.output_path),
        "project": {
            "name": project_name,
            "slug": slug,
            "description": description,
            "author": author or "Your Name",
            "contact_email": contact_email,
            "organization": organization,
            "python_package": python_pkg,
        },
        "github": {
            "owner": github_owner or organization,
            "repo": github_repo or slug,
            "default_branch": github_default_branch,
            "include_codeowners": bool(include_codeowners),
            "include_funding": bool(include_funding),
            "badges": {
                "tags": bool(badges_tags),
            },
        },
        "license": {
            "id": license_id,
            "year": int(created.year),
        },
        "metadata": {
            "created": created.isoformat(),
            "status": status,
            "tags": tags_list,
        },
        "now": dt.datetime.now().isoformat(timespec="seconds"),
    }


def _render_string(env: "jinja2.Environment", text: str, context: Mapping[str, Any]) -> str:
    return env.from_string(text).render(**context)


def _should_render_path(rel_posix: str) -> bool:
    return ("{{" in rel_posix) or ("{%" in rel_posix)


def _iter_template_files(template_path: Path) -> Iterable[Path]:
    for p in sorted(template_path.rglob("*")):
        # Skip dirs and editor artifacts.
        if p.is_dir():
            continue
        if p.name in {".DS_Store"}:
            continue
        if p.name == "template.yaml":
            continue
        yield p


def _copy_tree_rendered(
    *,
    paths: RuntimePaths,
    template_name: str,
    dest: Path,
    context: Mapping[str, Any],
    force: bool,
    dry_run: bool,
) -> None:
    template_path = _template_dir(paths, template_name)
    manifest = _load_template_manifest(template_path)
    bundle_names = list(manifest.get("bundles", [])) if isinstance(manifest, dict) else []

    bundle_dirs: List[Path] = []
    bundles_root = _bundles_root(paths)
    for b in bundle_names:
        bpath = bundles_root / b
        if not bpath.is_dir():
            raise SystemExit(f"Unknown bundle {b!r} for template {template_name!r}; expected: {bpath}")
        bundle_dirs.append(bpath)

    # Bundles first, then template overrides.
    source_roots: List[Path] = [*bundle_dirs, template_path]

    # Allow includes from: template, bundles, _shared, licenses.
    env = _jinja_env(paths, [template_path, *bundle_dirs, _shared_root(paths), paths.licenses_dir])

    if dest.exists() and not force:
        raise SystemExit(f"Refusing to write into existing path: {dest} (use --force)")

    if dry_run:
        print(f"[dry-run] template={template_name} -> {dest}")

    plan: Dict[str, Path] = {}  # out_rel_posix -> src_path (later roots win)
    for root in source_roots:
        for src in _iter_template_files(root):
            rel = src.relative_to(root)
            rel_posix = rel.as_posix()
            if _should_render_path(rel_posix):
                rel_posix = _render_string(env, rel_posix, context)
            out_rel = Path(rel_posix)
            if out_rel.suffix == ".j2":
                out_rel = out_rel.with_suffix("")
            plan[out_rel.as_posix()] = src

    for out_rel_posix in sorted(plan.keys()):
        src = plan[out_rel_posix]
        out_rel = Path(out_rel_posix)
        out_path = dest / out_rel
        is_j2 = src.name.endswith(".j2")

        if dry_run:
            action = "render" if is_j2 else "copy"
            print(f"[dry-run] {action}: {out_rel}")
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        if is_j2:
            text = src.read_text(encoding="utf-8")
            rendered = env.from_string(text).render(**context)
            out_path.write_text(rendered, encoding="utf-8", newline="\n")
        else:
            shutil.copy2(src, out_path)


def _postprocess_generated_repo(dest: Path) -> None:
    # Make hook/setup scripts executable (best-effort).
    for p in dest.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(dest).as_posix()
        if rel.startswith(".githooks/") or rel == "scripts/setup-git-hooks":
            _chmod_executable(p)


def _list_templates(paths: RuntimePaths) -> List[str]:
    root = paths.templates_dir
    if not root.is_dir():
        return []
    names: List[str] = []
    for p in sorted(root.iterdir()):
        if not p.is_dir():
            continue
        if p.name.startswith("_"):
            continue
        names.append(p.name)
    return names


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="establish.py", description="Establish a repository from filesystem templates.")
    p.add_argument("--templates-dir", type=str, default="", help="Override templates root directory.")
    p.add_argument("--licenses-dir", type=str, default="", help="Override licenses root directory.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-templates", help="List available templates.")

    init = sub.add_parser("init", help="Create a repo from a YAML config (or CLI flags).")
    init.add_argument("--config", type=str, default="", help="Path to config YAML (alternative to CLI fields).")

    init.add_argument("--template", type=str, default="", help="Template name (CLI mode).")
    init.add_argument("--output-path", type=str, default="", help="Destination directory path (CLI mode).")
    init.add_argument("--name", type=str, default="", help="Project name (CLI mode).")
    init.add_argument("--description", type=str, default="", help="Project description (CLI mode).")
    init.add_argument("--author", type=str, default="", help="Project author (CLI mode).")
    init.add_argument("--contact-email", dest="contact_email", type=str, default="", help="Project contact email (CLI mode).")
    init.add_argument("--organization", type=str, default="", help="Project organization (CLI mode).")
    init.add_argument("--github-owner", type=str, default="", help="GitHub owner/org (CLI mode).")
    init.add_argument("--github-repo", type=str, default="", help="GitHub repo name (CLI mode).")
    init.add_argument("--license-id", type=str, default="", help="License id (CLI mode), e.g. MIT, Apache-2.0, CC-BY-4.0")
    init.add_argument("--created", type=str, default="", help="metadata.created (YYYY-MM-DD, CLI mode)")
    init.add_argument("--status", type=str, default="", help="metadata.status (CLI mode)")
    init.add_argument("--tag", action="append", default=[], help="metadata.tags (repeatable, CLI mode)")
    init.add_argument("--no-git", action="store_true", help="Do not run git init (CLI mode).")
    init.add_argument("--initial-commit", action="store_true", help="Create an initial commit (CLI mode).")

    init.add_argument("--force", action="store_true", help="Allow writing into existing output path.")
    init.add_argument("--dry-run", action="store_true", help="Print actions without writing.")

    return p


def _ensure_config_mode_only(args: argparse.Namespace) -> None:
    forbidden = []
    for key in (
        "template",
        "output_path",
        "name",
        "description",
        "author",
        "contact_email",
        "organization",
        "github_owner",
        "github_repo",
        "license_id",
        "created",
        "status",
    ):
        if getattr(args, key):
            forbidden.append(f"--{key.replace('_', '-')}")
    if args.tag:
        forbidden.append("--tag")
    if args.no_git:
        forbidden.append("--no-git")
    if args.initial_commit:
        forbidden.append("--initial-commit")

    if forbidden:
        raise SystemExit(
            "When using --config, do not pass CLI template/project/license/metadata fields.\n"
            f"Remove: {' '.join(forbidden)}\n"
            "Edit the YAML instead (or omit --config and use CLI mode)."
        )


def _runtime_paths_from_args(args: argparse.Namespace) -> RuntimePaths:
    templates_dir = Path(args.templates_dir).expanduser() if args.templates_dir else _default_templates_root()
    licenses_dir = Path(args.licenses_dir).expanduser() if args.licenses_dir else _default_licenses_root()
    return RuntimePaths(templates_dir=templates_dir, licenses_dir=licenses_dir)


def _validate_preflight(paths: RuntimePaths, cfg: RepoConfig, context: Mapping[str, Any]) -> None:
    if not paths.templates_dir.is_dir():
        raise SystemExit(f"templates dir not found: {paths.templates_dir}")
    if not paths.licenses_dir.is_dir():
        raise SystemExit(f"licenses dir not found: {paths.licenses_dir}")

    # Ensure selected template exists.
    _template_dir(paths, cfg.template)

    license_id = str(context.get("license", {}).get("id", "")).strip()
    if not license_id:
        raise SystemExit("license.id is required")

    license_path = paths.licenses_dir / f"{license_id}.j2"
    if not license_path.is_file():
        raise SystemExit(
            f"Unknown license id {license_id!r}; expected file: {license_path}\n"
            "Add a matching template in the licenses directory, or change license.id."
        )


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    paths = _runtime_paths_from_args(args)

    if args.cmd == "list-templates":
        for t in _list_templates(paths):
            print(t)
        return 0

    if args.cmd == "init":
        if args.config:
            _ensure_config_mode_only(args)
            _, cfg0 = _read_config_yaml(Path(args.config))
            cfg = RepoConfig(
                template=cfg0.template,
                output_path=cfg0.output_path,
                project=cfg0.project,
                github=cfg0.github,
                license=cfg0.license,
                metadata=cfg0.metadata,
                init_git=cfg0.init_git,
                initial_commit=cfg0.initial_commit,
                force=bool(args.force),
                dry_run=bool(args.dry_run),
            )
        else:
            if not args.template:
                raise SystemExit("--template is required in CLI mode (or pass --config).")
            if not args.output_path:
                raise SystemExit("--output-path is required in CLI mode (or pass --config).")

            cfg = RepoConfig(
                template=args.template,
                output_path=Path(args.output_path).expanduser(),
                project={
                    "name": args.name,
                    "description": args.description,
                    "author": args.author,
                    "contact_email": getattr(args, "contact_email", ""),
                    "organization": args.organization,
                },
                github={
                    "owner": args.github_owner,
                    "repo": args.github_repo,
                    "default_branch": "main",
                },
                license={"id": args.license_id},
                metadata={"created": args.created, "status": args.status, "tags": list(args.tag)},
                init_git=not bool(args.no_git),
                initial_commit=bool(args.initial_commit),
                force=bool(args.force),
                dry_run=bool(args.dry_run),
            )

        context = _default_context(cfg)
        _validate_preflight(paths, cfg, context)
        dest = cfg.output_path
        _copy_tree_rendered(
            paths=paths,
            template_name=cfg.template,
            dest=dest,
            context=context,
            force=cfg.force,
            dry_run=cfg.dry_run,
        )

        if cfg.dry_run:
            return 0

        _postprocess_generated_repo(dest)

        if cfg.init_git:
            _git_init(dest)
            _git_enable_hooks(dest)
            if cfg.initial_commit:
                _git_initial_commit(dest)

        print(f"Created: {dest}")
        return 0

    raise SystemExit(f"Unknown command: {args.cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
