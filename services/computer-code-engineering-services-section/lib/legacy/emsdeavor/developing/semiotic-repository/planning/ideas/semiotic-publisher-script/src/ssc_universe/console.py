from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TextIO


@dataclass
class ConsoleReporter:
    """Lightweight stderr reporter for user-facing CLI progress.

    Keeps stdout free for machine-readable outputs (manifests, JSON) while
    surfacing human-readable progress updates and diagnostics during
    evaluation and projection builds.
    """

    stream: TextIO = sys.stderr

    def section(self, title: str) -> None:
        self._emit(f"\n==> {title}")

    def info(self, message: str) -> None:
        self._emit(f" • {message}")

    def success(self, message: str) -> None:
        self._emit(f" ✓ {message}")

    def warning(self, message: str) -> None:
        self._emit(f" ! {message}")

    def error(self, message: str) -> None:
        self._emit(f" ✖ {message}")

    def detail(self, message: str) -> None:
        self._emit(f"   - {message}")

    def _emit(self, text: str) -> None:
        print(text, file=self.stream)
