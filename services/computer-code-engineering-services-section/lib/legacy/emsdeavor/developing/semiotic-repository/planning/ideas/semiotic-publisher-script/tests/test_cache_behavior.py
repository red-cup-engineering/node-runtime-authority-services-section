import json
import shutil
from pathlib import Path

from ssc_universe.cache import CacheManager
from ssc_universe.cli import main
from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator

from support import EXAMPLES_ROOT


def prepare_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    shutil.copytree(EXAMPLES_ROOT, workspace)
    cache_dir = tmp_path / "cache"
    config_path = workspace / "universe.yaml"
    config_text = config_path.read_text()
    config_text += "\ncache:\n  enabled: true\n  location: {}\n".format(cache_dir)
    config_path.write_text(config_text)
    return workspace


def test_cache_hit_and_miss(tmp_path):
    workspace = prepare_workspace(tmp_path)
    config_path = workspace / "universe.yaml"
    config = UniverseConfig.load(config_path)
    options = EvaluationOptions(
        mode=config.mode(),
        sanitize_html=config.data["html"]["sanitize"],
        html_lang=config.data.get("html", {}).get("lang", "en"),
    )
    evaluator = Evaluator(config, options)
    manager = CacheManager(config, workspace, config.data["sources"])

    # First evaluation should miss and populate cache
    assert manager.load() is None
    instance = evaluator.evaluate(workspace)
    manager.store(instance)
    cached = manager.load()
    assert cached is not None

    # Modifying a source should change the signature and force a miss
    content_file = workspace / "content" / "a.md"
    original = content_file.read_text()
    content_file.write_text(original + "\nExtra line")
    manager_after_change = CacheManager(config, workspace, config.data["sources"])
    assert manager_after_change.load() is None


def test_cli_manifest_reports_cache_status(tmp_path):
    workspace = prepare_workspace(tmp_path)
    out_dir = tmp_path / "site"
    exit_code = main([
        "build",
        "--config",
        str(workspace / "universe.yaml"),
        "--projection",
        "site:static",
        "--out",
        f"dir:{out_dir}",
    ])
    assert exit_code == 0
    manifest_path = out_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["cache"]["status"] == "miss"

    # Second invocation should hit cache
    out_dir_2 = tmp_path / "site2"
    exit_code = main([
        "build",
        "--config",
        str(workspace / "universe.yaml"),
        "--projection",
        "site:static",
        "--out",
        f"dir:{out_dir_2}",
    ])
    assert exit_code == 0
    manifest_path2 = out_dir_2 / "manifest.json"
    manifest2 = json.loads(manifest_path2.read_text())
    assert manifest2["cache"]["status"] == "hit"


def test_manifest_delta_against_cached_state(tmp_path):
    workspace = prepare_workspace(tmp_path)
    out_dir = tmp_path / "first"
    exit_code = main(
        [
            "build",
            "--config",
            str(workspace / "universe.yaml"),
            "--projection",
            "site:static",
            "--out",
            f"dir:{out_dir}",
        ]
    )
    assert exit_code == 0

    content_file = workspace / "content" / "a.md"
    lines = content_file.read_text().splitlines()
    for idx, line in enumerate(lines):
        if line.strip() == "---" and idx > 0:
            lines.insert(idx, "  - \"tag:delta\"")
            break
    content_file.write_text("\n".join(lines))

    out_dir2 = tmp_path / "second"
    exit_code = main(
        [
            "build",
            "--config",
            str(workspace / "universe.yaml"),
            "--projection",
            "site:static",
            "--out",
            f"dir:{out_dir2}",
        ]
    )
    assert exit_code == 0

    manifest = json.loads((out_dir2 / "manifest.json").read_text())
    delta = manifest.get("delta", {})
    assert delta.get("baseline_present") is True
    assert delta.get("ann_changes", {}).get("a") == "changed"
