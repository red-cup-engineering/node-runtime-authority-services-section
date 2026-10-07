import json
from pathlib import Path

from ssc_universe.cli import main

from support import EXAMPLES_ROOT


def test_build_site_static_writes_manifest(tmp_path):
    out_dir = tmp_path / "site"
    exit_code = main([
        "build",
        "--config",
        str(EXAMPLES_ROOT / "universe.yaml"),
        "--projection",
        "site:static",
        "--out",
        f"dir:{out_dir}",
    ])
    assert exit_code == 0
    manifest_path = out_dir / "manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["projection"] == "site:static"
    assert "index.html" in data["artifacts"]
    assert data.get("assets")
    assert data["repo"]["fingerprint"]
    assert "b" in data["equivalence_classes"]
    assert "b-alias" in data["equivalence_classes"]["b"]


def test_build_single_html_writes_manifest_next_to_file(tmp_path):
    target = tmp_path / "book.html"
    exit_code = main([
        "build",
        "--config",
        str(EXAMPLES_ROOT / "universe.yaml"),
        "--projection",
        "single:html",
        "--out",
        f"file:{target}",
    ])
    assert exit_code == 0
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text())
    assert data["projection"] == "single:html"
    assert target.name in data["artifacts"]
    assert data["repo"]["fingerprint"]
    assert "b-alias" in data["equivalence_classes"].get("b", [])
