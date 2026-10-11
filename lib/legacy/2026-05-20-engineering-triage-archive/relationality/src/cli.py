from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Optional

from .site_publish import FilePublishOptions, PublishOptions, publish_file_site, publish_site
from .universe_validate import ValidateOptions, validate_vault


def _parse_status_list(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    return [s.strip() for s in value.split(",") if s.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Semiotic publisher CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # publish / build (auto / vault)
    pub = subparsers.add_parser(
        "publish",
        help="Publish semiotic site or document (auto-detect file vs vault)",
    )
    pub.add_argument("vault_dir", nargs="?", help="Path to markdown vault directory or file (or set in config)")
    pub.add_argument("output_dir", nargs="?", help="Directory for generated site/API (or set in config)")
    pub.add_argument("--config", help="Optional YAML config file", default=None)
    pub.add_argument("--dry-run", action="store_true", help="Run full pipeline without writing files")
    pub.add_argument("--targets", help="Comma-separated targets (html,json,rdf,openapi,pandoc)")
    pub.add_argument("--mode", help="Override mode (site or doc)")
    pub.add_argument("--allow-pandoc", action="store_true", help="Allow invoking pandoc if configured")
    pub.add_argument("--concept", help="Restrict to a single concept for pandoc export")
    pub.add_argument(
        "--status",
        help="Comma-separated statuses to publish (overrides publish_statuses in config)",
    )
    pub.add_argument(
        "--draft-statuses",
        help="Comma-separated statuses treated as drafts for styling (overrides draft_statuses in config)",
    )
    pub.add_argument(
        "--strict",
        action="store_true",
        help="Treat lint warnings as fatal and abort export",
    )
    pub.add_argument(
        "--clean",
        action="store_true",
        help="Delete output directory before publishing (no-op in dry-run)",
    )

    # explicit vault-only publish
    pub_vault = subparsers.add_parser("publish-vault", help="Publish a vault (all markdown under a directory)")
    for arg in pub._actions[1:]:
        pub_vault._add_action(arg)

    # backward compatible alias for vault publish
    build = subparsers.add_parser("build", help="Alias for publish-vault")
    for arg in pub._actions[1:]:
        build._add_action(arg)

    # publish a single file
    pub_file = subparsers.add_parser("publish-file", help="Publish site outputs for a single markdown file")
    pub_file.add_argument("input_file", help="Path to markdown file to publish")
    pub_file.add_argument("output_dir", nargs="?", help="Directory for generated site/API (or set in config)")
    pub_file.add_argument("--config", help="Optional YAML config file", default=None)
    pub_file.add_argument(
        "--vault-dir",
        help="Vault root for interpreting folders/ids (defaults to config.vault_dir or file parent)",
        default=None,
    )
    pub_file.add_argument("--dry-run", action="store_true", help="Run full pipeline without writing files")
    pub_file.add_argument("--targets", help="Comma-separated targets (html,json,rdf,openapi,pandoc)")
    pub_file.add_argument("--mode", help="Override mode (site or doc)")
    pub_file.add_argument("--allow-pandoc", action="store_true", help="Allow invoking pandoc if configured")
    pub_file.add_argument(
        "--status",
        help="Comma-separated statuses to publish (overrides publish_statuses in config)",
    )
    pub_file.add_argument(
        "--draft-statuses",
        help="Comma-separated statuses treated as drafts for styling (overrides draft_statuses in config)",
    )
    pub_file.add_argument(
        "--strict",
        action="store_true",
        help="Treat lint warnings as fatal and abort export",
    )
    pub_file.add_argument(
        "--clean",
        action="store_true",
        help="Delete output directory before publishing (no-op in dry-run)",
    )

    # validate
    val = subparsers.add_parser("validate", help="Validate vault (no export)")
    val.add_argument("vault_dir", nargs="?", help="Path to markdown vault directory (or set in config)")
    val.add_argument("--config", help="Optional YAML config file", default=None)
    val.add_argument(
        "--strict",
        action="store_true",
        help="Treat lint warnings as fatal",
    )

    args = parser.parse_args()

    if args.command in ("publish-vault", "build"):
        options = PublishOptions(
            config_path=Path(args.config).resolve() if args.config else None,
            vault_dir=Path(args.vault_dir).resolve() if args.vault_dir else None,
            output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
            targets=[t.strip() for t in args.targets.split(",")] if args.targets else None,
            publish_statuses=_parse_status_list(args.status),
            draft_statuses=_parse_status_list(args.draft_statuses),
            allow_pandoc=bool(args.allow_pandoc),
            concept_id=args.concept,
            dry_run=bool(args.dry_run),
            clean=bool(args.clean),
            strict=bool(args.strict),
            mode=args.mode,
        )
        publish_site(options)
    elif args.command == "publish":
        # Auto-detect whether the input path is a file or a vault directory.
        input_path = Path(args.vault_dir).resolve() if args.vault_dir else None
        if input_path is not None and input_path.is_file():
            options = FilePublishOptions(
                config_path=Path(args.config).resolve() if args.config else None,
                vault_dir=None,
                input_file=input_path,
                output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
                targets=[t.strip() for t in args.targets.split(",")] if args.targets else None,
                publish_statuses=_parse_status_list(args.status),
                draft_statuses=_parse_status_list(args.draft_statuses),
                allow_pandoc=bool(args.allow_pandoc),
                concept_id=None,
                dry_run=bool(args.dry_run),
                clean=bool(args.clean),
                strict=bool(args.strict),
                mode=args.mode,
            )
            publish_file_site(options)
        else:
            options = PublishOptions(
                config_path=Path(args.config).resolve() if args.config else None,
                vault_dir=input_path,
                output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
                targets=[t.strip() for t in args.targets.split(",")] if args.targets else None,
                publish_statuses=_parse_status_list(args.status),
                draft_statuses=_parse_status_list(args.draft_statuses),
                allow_pandoc=bool(args.allow_pandoc),
                concept_id=args.concept,
                dry_run=bool(args.dry_run),
                clean=bool(args.clean),
                strict=bool(args.strict),
                mode=args.mode,
            )
            publish_site(options)
    elif args.command == "publish-file":
        options = FilePublishOptions(
            config_path=Path(args.config).resolve() if args.config else None,
            vault_dir=Path(args.vault_dir).resolve() if getattr(args, "vault_dir", None) else None,
            input_file=Path(args.input_file).resolve(),
            output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
            targets=[t.strip() for t in args.targets.split(",")] if args.targets else None,
            publish_statuses=_parse_status_list(args.status),
            draft_statuses=_parse_status_list(args.draft_statuses),
            allow_pandoc=bool(args.allow_pandoc),
            concept_id=None,
            dry_run=bool(args.dry_run),
            clean=bool(args.clean),
            strict=bool(args.strict),
            mode=args.mode,
        )
        publish_file_site(options)
    elif args.command == "validate":
        options = ValidateOptions(
            config_path=Path(args.config).resolve() if args.config else None,
            vault_dir=Path(args.vault_dir).resolve() if args.vault_dir else None,
            strict=bool(args.strict),
        )
        validate_vault(options)


if __name__ == "__main__":
    main()
