from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import UniverseConfig
from .eval_core import EvaluationOptions, Evaluator
from .cache import CacheManager, resolve_version
from .delta import compute_delta, delta_to_dict
from .manifest import build_manifest
from .serialization import serialize_instance
from .console import ConsoleReporter
from .projections.site_static import render_site
from .projections.single_html import render_single
from .projections.filtering import published_representatives
from .sinks import DirectorySink, FileSink, StdoutSink, ZipSink


def parse_args(argv=None):
    parser = argparse.ArgumentParser(prog="sscu")
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="universe.yaml")
    common.add_argument("--mode", choices=["strict", "permissive"], default=None)
    common.add_argument("--lang", help="override html.lang configuration")
    common.add_argument("--no-cache", action="store_true")

    build = sub.add_parser("build", parents=[common])
    build.add_argument("--projection", required=True)
    build.add_argument("--out", required=True)

    ev = sub.add_parser("eval", parents=[common])
    ev.add_argument("--format", choices=["json", "text"], default="text")
    ev.add_argument("--out", default="stdout")

    cache_cmd = sub.add_parser("cache", parents=[common])
    cache_cmd.add_argument("--all", action="store_true", help="clear all cached evaluations")
    cache_cmd.add_argument("--list", action="store_true", help="list available cached evaluations")
    cache_cmd.add_argument("--signature", help="operate on a specific cache signature")
    cache_cmd.add_argument("--verbose", action="store_true", help="include metadata when listing cache entries")

    return parser.parse_args(argv)


def _sink_from_out(out: str):
    if out.startswith("dir:"):
        return DirectorySink(Path(out.split(":", 1)[1]))
    if out.startswith("file:"):
        return FileSink(Path(out.split(":", 1)[1]))
    if out.startswith("zip:"):
        return ZipSink(Path(out.split(":", 1)[1]))
    if out == "stdout":
        return StdoutSink()
    raise ValueError(
        f"Unknown sink specification '{out}'. Use dir:<path>, file:<path>, zip:<path>, or stdout."
    )


def main(argv=None):
    try:
        return _run(argv)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - passthrough for unexpected failures
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _run(argv=None):
    reporter = ConsoleReporter()
    args = parse_args(argv)
    config_path = Path(args.config)
    reporter.section("Configuration")
    reporter.info(f"Loading configuration from {config_path}")
    config = UniverseConfig.load(config_path)
    reporter.success("Configuration loaded")
    root = config_path.parent.resolve()

    if args.command == "cache":
        cache_enabled = not args.no_cache and config.data.get("cache", {}).get("enabled", True)
        if not cache_enabled:
            print("Caching is disabled in configuration", file=sys.stderr)
            return 0
        cache_manager = CacheManager(config, root, config.data.get("sources", "content/**/*.md"), resolve_version())
        target_signature = args.signature or cache_manager.signature
        if args.list:
            entries = cache_manager.list_entries()
            if entries:
                for path in entries:
                    marker = "*" if path.stem == target_signature else "-"
                    if args.verbose:
                        info = cache_manager.entry_info(path)
                        details = [
                            f"signature={info['signature']}",
                            f"mtime={info['mtime']}",
                            f"size={info['size']}B",
                        ]
                        if "constants" in info:
                            details.append(f"constants={info['constants']}")
                        if info.get("repo_fingerprint"):
                            details.append(f"fingerprint={info['repo_fingerprint']}")
                        detail_str = ", ".join(details)
                        print(f"{marker} {path} ({detail_str})")
                    else:
                        print(f"{marker} {path}")
            else:
                print("No cache entries found")
            return 0
        removed = cache_manager.clear(all_entries=args.all, signature=target_signature)
        if removed:
            print("\n".join(str(p) for p in removed))
        else:
            print("No cache entries found for removal")
        return 0

    mode = args.mode or config.mode()
    html_cfg = config.data.get("html", {})
    options = EvaluationOptions(
        mode=mode,
        sanitize_html=html_cfg.get("sanitize", True),
        html_lang=args.lang or html_cfg.get("lang", "en"),
    )
    evaluator = Evaluator(config, options)

    cache_enabled = not args.no_cache and config.data.get("cache", {}).get("enabled", True)
    cache_status = "disabled"
    cache_manager = None
    baseline = None
    instance = None
    if cache_enabled:
        reporter.section("Cache")
        cache_manager = CacheManager(config, root, config.data.get("sources", "content/**/*.md"), resolve_version())
        cached = cache_manager.load()
        baseline = cached
        if cached:
            instance = cached
            cache_status = "hit"
            reporter.success(f"Cache hit for signature {cache_manager.signature}")
        else:
            cache_status = "miss"
            reporter.info(f"Cache miss for signature {cache_manager.signature}")
            baseline = cache_manager.load_latest()
            if baseline:
                reporter.info("Loaded latest cached baseline for delta computation")

    if instance is None:
        instance = evaluator.evaluate(root, reporter=reporter)
        if cache_manager:
            cache_manager.store(instance)
            reporter.success(f"Cached evaluation to {cache_manager.cache_path}")

    if options.mode == "strict" and instance.unresolved:
        formatted = "; ".join(
            f"{src} -> {target}" + (
                f" (from {instance.source_paths.get(src) or instance.source_paths.get(instance.representative(src))})"
                if getattr(instance, "source_paths", None)
                else ""
            )
            for src, target in instance.unresolved
        )
        raise ValueError(
            f"Unresolved references in strict mode ({len(instance.unresolved)}): {formatted}"
        )

    publish_filters = config.publish_filters()
    include_set = None
    if publish_filters:
        include_set = published_representatives(
            instance,
            publish_to=publish_filters.get("publish_to"),
            statuses=publish_filters.get("status"),
        )

    delta_summary = compute_delta(baseline, instance)
    delta_dict = delta_to_dict(delta_summary)

    reporter.section("Summary")
    reporter.info(
        f"Constants: {len(instance.concepts)} (canonical: {len(instance.canonical_concepts)})"
    )
    if instance.unresolved:
        reporter.warning(f"Unresolved references detected: {len(instance.unresolved)}")
    if instance.failures:
        reporter.warning(f"Failures recorded: {len(instance.failures)}")

    if args.command == "eval":
        if args.format == "json":
            data = serialize_instance(instance)
            data["delta"] = delta_dict
            output = json.dumps(data, indent=2)
        else:
            output = "\n".join(
                [
                    f"Constants: {list(instance.concepts.keys())}",
                    f"Unresolved: {instance.unresolved}",
                    f"Failures: {instance.failures}",
                ]
            )
        if args.out == "stdout":
            print(output)
        else:
            output_path = Path(args.out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output)
            print(f"Wrote evaluation output to {output_path}", file=sys.stderr)
        return 0

    if args.command == "build":
        sink = _sink_from_out(args.out)
        reporter.section("Build")
        reporter.info(f"Projection: {args.projection}")
        reporter.info(f"Sink: {args.out}")
        template_dir = Path(__file__).parent / "templates"
        mathjax = bool(config.data.get("html", {}).get("mathjax", False))
        assets_cfg = config.data.get("html", {}).get("assets", {})
        assets_inline = bool(assets_cfg.get("inline", True))
        assets_minify = bool(assets_cfg.get("minify", False))
        manifest_unresolved = instance.unresolved
        if include_set is not None:
            manifest_unresolved = [
                (src, target)
                for src, target in instance.unresolved
                if instance.representative(src) in include_set
            ]
        build_info = {
            "projection": args.projection,
            "mode": mode,
            "cache_status": cache_status,
            "config_hash": instance.config_hash,
            "repo_fingerprint": instance.repo_fingerprint,
            "sanitize_html": getattr(instance, "sanitize_html", True),
            "html_lang": getattr(instance, "html_lang", "en"),
            "assets_inline": assets_inline,
            "assets_minify": assets_minify,
            "mathjax": mathjax,
            "filters": publish_filters or None,
        }
        manifest_data = None
        if args.projection == "site:static":
            files, assets = render_site(
                instance,
                template_dir,
                mathjax,
                build_info=build_info,
                delta=delta_dict,
                assets_inline=assets_inline,
                assets_minify=assets_minify,
                include=sorted(include_set) if include_set else None,
            )
            artifacts = [str(p) for p, _ in files] + ["manifest.json"]
            manifest_data = build_manifest(
                instance,
                artifacts,
                projection=args.projection,
                mode=mode,
                cache_status=cache_status,
                delta=delta_dict,
                assets=assets,
                constants=sorted(include_set) if include_set else None,
                filters=publish_filters or None,
                unresolved=manifest_unresolved,
            )
            manifest_bytes = json.dumps(manifest_data, indent=2).encode()
            files.append((Path("manifest.json"), manifest_bytes))
            written = sink.write(files) if not isinstance(sink, StdoutSink) else sink.write(b"")
        elif args.projection == "single:html":
            manifest_href = None
            if isinstance(sink, (DirectorySink, ZipSink)):
                manifest_href = "manifest.json"
            elif isinstance(sink, FileSink):
                manifest_href = f"{sink.target.name}.manifest.json"
            name, content = render_single(
                instance,
                template_dir,
                mathjax,
                build_info=build_info,
                delta=delta_dict,
                assets_minify=assets_minify,
                manifest_href=manifest_href,
                include=sorted(include_set) if include_set else None,
            )
            if isinstance(sink, (DirectorySink, ZipSink)):
                artifacts = [name, "manifest.json"]
                manifest_data = build_manifest(
                    instance,
                    artifacts,
                    projection=args.projection,
                    mode=mode,
                    cache_status=cache_status,
                    delta=delta_dict,
                    unresolved=manifest_unresolved,
                )
                manifest_bytes = json.dumps(manifest_data, indent=2).encode()
                written = sink.write([(Path(name), content), (Path("manifest.json"), manifest_bytes)])
            elif isinstance(sink, FileSink):
                written = sink.write(content)
                artifacts = [written.name, f"{written.name}.manifest.json"]
                manifest_data = build_manifest(
                    instance,
                    artifacts,
                    projection=args.projection,
                    mode=mode,
                    cache_status=cache_status,
                    delta=delta_dict,
                    unresolved=manifest_unresolved,
                )
                manifest_path = written.with_suffix(written.suffix + ".manifest.json")
                manifest_path.parent.mkdir(parents=True, exist_ok=True)
                manifest_path.write_bytes(json.dumps(manifest_data, indent=2).encode())
            else:
                sink.write(content)
                artifacts = [name]
                manifest_data = build_manifest(
                    instance,
                    artifacts,
                    projection=args.projection,
                    mode=mode,
                    cache_status=cache_status,
                    delta=delta_to_dict(delta_summary),
                    constants=sorted(include_set) if include_set else None,
                    filters=publish_filters or None,
                    unresolved=manifest_unresolved,
                )
                written = []
        else:
            raise ValueError(
                f"Unknown projection '{args.projection}'. Expected site:static or single:html."
            )
        if isinstance(written, list):
            reporter.success(f"Wrote {len(written)} artifacts to {args.out}")
        elif written:
            reporter.success(f"Wrote artifact to {written}")
        else:
            reporter.success("Build completed (stdout sink)")
        manifest_summary = manifest_data or {}
        print(json.dumps(manifest_summary, indent=2))
        return 0


if __name__ == "__main__":
    sys.exit(main())
