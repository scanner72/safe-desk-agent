"""Minimal YAML subset reader. Stdlib only — no PyYAML.

Supports the shapes used by `config/policy.example.yaml`:

- mappings and nested mappings (indent)
- lists (`- item`)
- scalars: bool, null, int, float, quoted or bare strings
- `#` comments

Does not support anchors, tags, multiline `|` / `>`, or flow `[a, b]` / `{k: v}`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_yaml_lite(path: Path | str) -> Any:
    text = Path(path).read_text(encoding="utf-8")
    return parse_yaml_lite(text)


def parse_yaml_lite(text: str) -> Any:
    lines = _prep_lines(text)
    if not lines:
        return {}
    value, _ = _parse_block(lines, 0, 0)
    return value


def _prep_lines(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for raw in text.splitlines():
        stripped = _strip_comment(raw.rstrip())
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        if "\t" in stripped[:indent]:
            raise ValueError("yaml_lite does not allow tabs for indentation")
        out.append((indent, stripped[indent:]))
    return out


def _strip_comment(line: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return line[:i].rstrip()
    return line


def _parse_block(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[Any, int]:
    if idx >= len(lines):
        return {}, idx
    cur_indent, content = lines[idx]
    if cur_indent < indent:
        return {}, idx
    if content.startswith("- "):
        return _parse_list(lines, idx, cur_indent)
    return _parse_map(lines, idx, cur_indent)


def _parse_map(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[dict[str, Any], int]:
    result: dict[str, Any] = {}
    while idx < len(lines):
        cur_indent, content = lines[idx]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise ValueError(f"unexpected indent at {content!r}")
        if content.startswith("- "):
            raise ValueError(f"list item where a mapping key was expected: {content!r}")
        key, _, rest = content.partition(":")
        key = key.strip()
        if not key or _ == "":
            raise ValueError(f"expected 'key:' in {content!r}")
        rest = rest.strip()
        idx += 1
        if rest:
            result[key] = _parse_scalar(rest)
            continue
        if idx >= len(lines) or lines[idx][0] <= indent:
            result[key] = {}
            continue
        child, idx = _parse_block(lines, idx, lines[idx][0])
        result[key] = child
    return result, idx


def _parse_list(lines: list[tuple[int, str]], idx: int, indent: int) -> tuple[list[Any], int]:
    result: list[Any] = []
    while idx < len(lines):
        cur_indent, content = lines[idx]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise ValueError(f"unexpected indent at {content!r}")
        if not content.startswith("- "):
            break
        rest = content[2:].strip()
        idx += 1
        if rest:
            if ":" in rest and not rest.startswith(("'", '"')):
                # inline map item: `- key: value` plus optional nested keys
                key, _, val = rest.partition(":")
                item: dict[str, Any] = {key.strip(): _parse_scalar(val.strip())}
                if idx < len(lines) and lines[idx][0] > indent:
                    nested, idx = _parse_map(lines, idx, lines[idx][0])
                    item.update(nested)
                result.append(item)
            else:
                result.append(_parse_scalar(rest))
            continue
        if idx >= len(lines) or lines[idx][0] <= indent:
            result.append(None)
            continue
        child, idx = _parse_block(lines, idx, lines[idx][0])
        result.append(child)
    return result, idx


def _parse_scalar(raw: str) -> Any:
    if raw == "":
        return ""
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1]
    lowered = raw.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    if raw.startswith("0") and raw != "0" and not raw.startswith("0."):
        return raw
    try:
        if any(ch in raw for ch in ".eE"):
            return float(raw)
        return int(raw)
    except ValueError:
        return raw
