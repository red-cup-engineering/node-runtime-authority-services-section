from __future__ import annotations

"""
High-level universe publishing entrypoints.

This module orchestrates:
- loading universes from markdown (or other backends in future), and
- publishing those universes via the universe publishing views.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .markdown_universe import build_universe, build_universe_for_file, load_config
from .universe_ops import project_universe
from .universe_publish import default_targets_for_mode, export_all, normalize_targets
from .linting import lint_universe
from .model import Config


@dataclass
class PublishOptions:
    config_path: Optional[Path] = None
    vault_dir: Optional[Path] = None
    output_dir: Optional[Path] = None
    targets: Optional[List[str]] = None
    publish_statuses: Optional[List[str]] = None
    draft_statuses: Optional[List[str]] = None
    allow_pandoc: bool = False
    concept_id: Optional[str] = None
    dry_run: bool = False
    clean: bool = False
    strict: bool = False
    mode: Optional[str] = None
    project: Optional[str] = None


@dataclass
class FilePublishOptions:
    """Options for publishing a single markdown file."""

    config_path: Optional[Path] = None
    vault_dir: Optional[Path] = None
    input_file: Optional[Path] = None
    output_dir: Optional[Path] = None
    targets: Optional[List[str]] = None
    publish_statuses: Optional[List[str]] = None
    draft_statuses: Optional[List[str]] = None
    allow_pandoc: bool = False
    concept_id: Optional[str] = None
    dry_run: bool = False
    clean: bool = False
    strict: bool = False
    mode: Optional[str] = None
    project: Optional[str] = None


def publish_site(options: PublishOptions) -> None:
    """Publish a site using the same pipeline as the CLI `publish` command."""

    config = load_config(options.config_path) if options.config_path else Config()
    if options.mode is not None:
        config.mode = options.mode
    if options.vault_dir is not None:
        config.vault_dir = str(options.vault_dir)
    if options.output_dir is not None:
        config.output_dir = str(options.output_dir)

    vault_arg = options.vault_dir or (Path(config.vault_dir) if config.vault_dir else None)
    output_arg = options.output_dir or (Path(config.output_dir) if config.output_dir else None)
    if vault_arg is None or output_arg is None:
        raise SystemExit("Vault and output directories must be provided via options or config.")

    vault_dir = Path(vault_arg).resolve()
    output_dir = Path(output_arg).resolve()

    targets = options.targets or normalize_targets(config.targets) or default_targets_for_mode(config.mode)

    # Handle cleaning of the output directory.
    if options.clean and not options.dry_run and output_dir.exists():
        import shutil

        print(f"[{config.site_title}] Cleaning output directory {output_dir}")
        shutil.rmtree(output_dir)

    # Status filters.
    publish_statuses = options.publish_statuses or list(config.publish_statuses or [])
    draft_statuses = options.draft_statuses or list(config.draft_statuses or [])

    universe = build_universe(vault_dir, config, log=(lambda m: print(f"[phase] {m}")))
    if options.project:
        project_cfg = (config.projects or {}).get(options.project)
        if project_cfg is None:
            raise SystemExit(f"Unknown project '{options.project}' in configuration.")
        # Allow project to override presentation settings.
        if "base_url" in project_cfg:
            config.base_url = project_cfg["base_url"]
        if "site_title" in project_cfg:
            config.site_title = project_cfg["site_title"]
        if "theme" in project_cfg:
            config.theme = project_cfg["theme"]
        if "targets" in project_cfg:
            targets = normalize_targets(project_cfg["targets"])
        if "publish_statuses" in project_cfg:
            publish_statuses = list(project_cfg["publish_statuses"])
        if "draft_statuses" in project_cfg:
            draft_statuses = list(project_cfg["draft_statuses"])
        universe = project_universe(universe, options.project, project_cfg)
    print(f"[{config.site_title}] Loaded {len(universe.concepts)} concepts; {len(universe.atoms)} atoms.")

    # Lint, respecting strictness.
    try:
        lint_universe(universe)
    except SystemExit as exc:
        if options.strict or config.lint_strict:
            raise
        print(str(exc))

    if options.dry_run:
        print(f"[{config.site_title}] Dry run enabled; no files will be written.")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    export_all(
        universe,
        output_dir,
        targets=targets,
        dry_run=options.dry_run,
        allow_pandoc=options.allow_pandoc,
        concept_id=options.concept_id,
        publish_statuses=publish_statuses,
        draft_statuses=draft_statuses,
    )


def publish_file_site(options: FilePublishOptions) -> None:
    """Publish a site universe built from a single markdown file."""

    if options.input_file is None:
        raise SystemExit("input_file must be provided for single-file publishing.")

    config = load_config(options.config_path) if options.config_path else Config()
    if options.mode is not None:
        config.mode = options.mode
    if options.vault_dir is not None:
        config.vault_dir = str(options.vault_dir)
    if options.output_dir is not None:
        config.output_dir = str(options.output_dir)

    input_file = options.input_file.resolve()

    # Determine vault root: prefer explicit vault_dir/config, else fall back to the file's directory.
    vault_root = (
        options.vault_dir
        or (Path(config.vault_dir) if config.vault_dir else None)
        or input_file.parent
    )
    output_arg = options.output_dir or (Path(config.output_dir) if config.output_dir else None)
    if vault_root is None or output_arg is None:
        raise SystemExit("Vault/root and output directories must be provided via options or config.")

    vault_root = Path(vault_root).resolve()
    output_dir = Path(output_arg).resolve()

    targets = options.targets or normalize_targets(config.targets) or default_targets_for_mode(config.mode)

    # Handle cleaning of the output directory.
    if options.clean and not options.dry_run and output_dir.exists():
        import shutil

        print(f"[{config.site_title}] Cleaning output directory {output_dir}")
        shutil.rmtree(output_dir)

    publish_statuses = options.publish_statuses or list(config.publish_statuses or [])
    draft_statuses = options.draft_statuses or list(config.draft_statuses or [])

    universe = build_universe_for_file(input_file, vault_root, config, log=(lambda m: print(f"[phase] {m}")))
    if options.project:
        project_cfg = (config.projects or {}).get(options.project)
        if project_cfg is None:
            raise SystemExit(f"Unknown project '{options.project}' in configuration.")
        if "base_url" in project_cfg:
            config.base_url = project_cfg["base_url"]
        if "site_title" in project_cfg:
            config.site_title = project_cfg["site_title"]
        if "theme" in project_cfg:
            config.theme = project_cfg["theme"]
        if "targets" in project_cfg:
            targets = normalize_targets(project_cfg["targets"])
        if "publish_statuses" in project_cfg:
            publish_statuses = list(project_cfg["publish_statuses"])
        if "draft_statuses" in project_cfg:
            draft_statuses = list(project_cfg["draft_statuses"])
        universe = project_universe(universe, options.project, project_cfg)
    print(f"[{config.site_title}] Loaded {len(universe.concepts)} concepts; {len(universe.atoms)} atoms.")

    # Lint, respecting strictness.
    try:
        lint_universe(universe)
    except SystemExit as exc:
        if options.strict or config.lint_strict:
            raise
        print(str(exc))

    if options.dry_run:
        print(f"[{config.site_title}] Dry run enabled; no files will be written.")
    else:
        output_dir.mkdir(parents=True, exist_ok=True)

    export_all(
        universe,
        output_dir,
        targets=targets,
        dry_run=options.dry_run,
        allow_pandoc=options.allow_pandoc,
        concept_id=options.concept_id,
        publish_statuses=publish_statuses,
        draft_statuses=draft_statuses,
    )
