"""Tiny OHLCV CSV loader. Columns: date,open,high,low,close,volume."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Bar:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


def load_ohlcv(path: Path) -> list[Bar]:
    return load_ohlcv_text(Path(path).read_text(encoding="utf-8"), name=str(path))


def load_ohlcv_text(text: str, *, name: str = "<csv>") -> list[Bar]:
    """Parse OHLCV CSV text (upload / paste). Same columns as load_ohlcv."""
    bars: list[Bar] = []
    reader = csv.DictReader(text.splitlines())
    required = {"open", "high", "low", "close"}
    if reader.fieldnames is None or not required.issubset(
        {name.strip().lower() for name in reader.fieldnames}
    ):
        raise ValueError("CSV must include open,high,low,close columns")
    for row in reader:
        keys = {k.strip().lower(): v for k, v in row.items() if k}
        bars.append(
            Bar(
                date=str(keys.get("date") or keys.get("time") or ""),
                open=float(keys["open"]),
                high=float(keys["high"]),
                low=float(keys["low"]),
                close=float(keys["close"]),
                volume=float(keys.get("volume") or 0),
            )
        )
    if not bars:
        raise ValueError(f"no rows in {name}")
    return bars
