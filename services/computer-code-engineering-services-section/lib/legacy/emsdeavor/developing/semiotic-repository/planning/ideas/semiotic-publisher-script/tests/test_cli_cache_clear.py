from ssc_universe.cli import main

from support import EXAMPLES_ROOT


def test_cache_clear_removes_signature(tmp_path, monkeypatch):
    cache_home = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))

    out_dir = tmp_path / "site"
    exit_code = main(
        [
            "build",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--projection",
            "site:static",
            "--out",
            f"dir:{out_dir}",
        ]
    )
    assert exit_code == 0

    cache_dir = cache_home / "ssc_universe"
    cache_files = list(cache_dir.glob("*.pkl"))
    assert cache_files, "expected a cache artifact to be written"

    clear_exit = main(
        [
            "cache",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
        ]
    )
    assert clear_exit == 0

    assert not cache_files[0].exists()

    # Rebuild to recreate the current signature before clearing another
    main(
        [
            "build",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--projection",
            "site:static",
            "--out",
            f"dir:{out_dir}",
        ]
    )
    current_signature = next(cache_dir.glob("*.pkl")).stem

    # Create an alternate signature artifact and clear just that entry
    other_signature = cache_dir / "other.pkl"
    other_signature.write_bytes(b"placeholder")
    assert other_signature.exists()

    selective_exit = main(
        [
            "cache",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--signature",
            "other",
        ]
    )
    assert selective_exit == 0
    assert not other_signature.exists(), "targeted signature should be removed"

    # Current signature artifact remains until cleared explicitly
    remaining = list(cache_dir.glob("*.pkl"))
    assert any(path.stem == current_signature for path in remaining)

    # Rebuild cache and clear all entries at once
    main(
        [
            "build",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--projection",
            "site:static",
            "--out",
            f"dir:{out_dir}",
        ]
    )
    assert list(cache_dir.glob("*.pkl"))

    clear_all_exit = main(
        [
            "cache",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--all",
        ]
    )
    assert clear_all_exit == 0
    assert not list(cache_dir.glob("*.pkl"))


def test_cache_list_reports_entries(tmp_path, monkeypatch, capsys):
    cache_home = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))

    out_dir = tmp_path / "site"
    main(
        [
            "build",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--projection",
            "site:static",
            "--out",
            f"dir:{out_dir}",
        ]
    )

    cache_dir = cache_home / "ssc_universe"
    cache_files = list(cache_dir.glob("*.pkl"))
    assert cache_files, "expected a cache artifact to be written"

    exit_code = main(
        [
            "cache",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--list",
            "--signature",
            cache_files[0].stem,
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    assert any(str(path) in captured.out for path in cache_files)
    assert any(line.startswith("* ") for line in captured.out.splitlines()), "listed output should mark the requested signature"
    assert cache_files[0].exists(), "listing should not remove cache artifacts"


def test_cache_list_verbose_metadata(tmp_path, monkeypatch, capsys):
    cache_home = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache_home))

    out_dir = tmp_path / "site"
    main(
        [
            "build",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--projection",
            "site:static",
            "--out",
            f"dir:{out_dir}",
        ]
    )

    cache_dir = cache_home / "ssc_universe"
    cache_files = list(cache_dir.glob("*.pkl"))
    assert cache_files, "expected a cache artifact to be written"

    exit_code = main(
        [
            "cache",
            "--config",
            str(EXAMPLES_ROOT / "universe.yaml"),
            "--list",
            "--verbose",
            "--signature",
            cache_files[0].stem,
        ]
    )
    assert exit_code == 0

    captured = capsys.readouterr()
    output = captured.out
    assert "constants=" in output
    assert "fingerprint=" in output
    assert "size=" in output and "mtime=" in output
    assert any(line.startswith("* ") for line in output.splitlines())
