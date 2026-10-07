import json

from ssc_universe.cli import main

from support import EXAMPLES_ROOT


def test_eval_lang_override_json(capsys):
    exit_code = main(
        [
            "eval",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--format",
            "json",
            "--lang",
            "de",
            "--no-cache",
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data.get("html_lang") == "de"


def test_build_single_lang_override(tmp_path):
    target = tmp_path / "lang.html"
    exit_code = main(
        [
            "build",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--projection",
            "single:html",
            "--out",
            f"file:{target}",
            "--lang",
            "pt",
            "--no-cache",
        ]
    )
    assert exit_code == 0
    html = target.read_text()
    assert "<html lang=\"pt\"" in html or "<html lang='pt'" in html
