import json

from ssc_universe.cli import main

from support import EXAMPLES_ROOT


def test_eval_json_outputs_fragments_and_semantics(capsys):
    exit_code = main([
        "eval",
        "--config",
        str(EXAMPLES_ROOT / "universe.yaml"),
        "--format",
        "json",
    ])
    assert exit_code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert "constants" in data
    const_a = data["constants"]["a"]
    assert const_a["fragment"]["is_failure"] is False
    assert any("ref" in el for el in const_a["fragment"]["elements"])
    assert data["unresolved"]
    assert "failures" in data
    assert data["repo_fingerprint"]


def test_eval_json_can_write_to_file(tmp_path, capsys):
    output_file = tmp_path / "eval.json"
    exit_code = main(
        [
            "eval",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--format",
            "json",
            "--out",
            str(output_file),
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == ""
    data = json.loads(output_file.read_text())
    assert "constants" in data
    assert data["repo_fingerprint"]
