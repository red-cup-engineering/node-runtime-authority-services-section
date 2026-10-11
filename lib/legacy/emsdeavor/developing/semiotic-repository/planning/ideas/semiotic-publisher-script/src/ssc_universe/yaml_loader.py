from __future__ import annotations

import ast
from typing import Any

try:  # pragma: no cover - prefer real YAML
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


def safe_load(text: str) -> Any:
    if yaml is not None:
        return yaml.safe_load(text)
    # Minimal fallback parser for simple YAML subsets
    lines = [(_indent(raw), raw.strip()) for raw in text.splitlines() if raw.strip()]

    def parse_block(idx: int, indent: int):
        obj: Any = {}
        i = idx
        while i < len(lines):
            ind, line = lines[i]
            if ind < indent:
                break
            if line.startswith("- "):
                # list item assumed already in list container
                break
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip()
                if val == "":
                    # check for list block
                    if i + 1 < len(lines) and lines[i + 1][0] > ind and lines[i + 1][1].startswith("- "):
                        lst = []
                        i += 1
                        while i < len(lines) and lines[i][0] > ind and lines[i][1].startswith("- "):
                            lst.append(_parse_scalar(lines[i][1][2:].strip()))
                            i += 1
                        obj[key] = lst
                        continue
                    child, i = parse_block(i + 1, ind + 2)
                    obj[key] = child
                    continue
                else:
                    obj[key] = _parse_scalar(val)
                    i += 1
            else:
                i += 1
        return obj, i

    parsed, _ = parse_block(0, 0)
    return parsed


def _indent(raw: str) -> int:
    return len(raw) - len(raw.lstrip(" "))


def _parse_scalar(val: str):
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        parts = [p.strip().strip("'\"") for p in inner.split(",")]
        return parts
    if val.startswith("{") and val.endswith("}"):
        inner = val[1:-1].strip()
        if not inner:
            return {}
        result = {}
        for part in inner.split(","):
            if ":" in part:
                k, v = part.split(":", 1)
                result[k.strip()] = _parse_scalar(v.strip())
        return result
    try:
        return ast.literal_eval(val)
    except Exception:
        return val.strip().strip("'\"")
