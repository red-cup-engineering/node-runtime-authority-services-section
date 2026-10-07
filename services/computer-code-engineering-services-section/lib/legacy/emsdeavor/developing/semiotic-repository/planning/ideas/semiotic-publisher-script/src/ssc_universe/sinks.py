from __future__ import annotations

import io
import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Tuple
import zipfile


class DirectorySink:
    def __init__(self, target: Path):
        self.target = target

    def write(self, files: List[Tuple[Path, bytes]]) -> List[Path]:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            for relpath, data in files:
                dest = tmp / relpath
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            if self.target.exists():
                shutil.rmtree(self.target)
            shutil.move(str(tmp), self.target)
        return [self.target / relpath for relpath, _ in files]


class FileSink:
    def __init__(self, target: Path):
        self.target = target

    def write(self, content: bytes) -> Path:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_bytes(content)
        return self.target


class ZipSink:
    def __init__(self, target: Path):
        self.target = target

    def write(self, files: List[Tuple[Path, bytes]]) -> Path:
        self.target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.target, "w") as zf:
            for relpath, data in files:
                zf.writestr(str(relpath), data)
        return self.target


class StdoutSink:
    def write(self, content: bytes) -> None:
        print(content.decode("utf-8"))
