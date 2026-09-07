"""Tiny OHLCV CSV loader. Columns: date,open,high,low,close,volume."""

from __future__ import annotations

import csv
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime
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


def resample_weekly(bars: list[Bar]) -> list[Bar]:
    """Aggregate daily (or finer) bars into weekly OHLCV.

    Groups by ISO calendar week when `date` parses as YYYY-MM-DD.
    Otherwise packs every 7 bars in order. Incomplete weeks are kept so
    the current week still has a slower-trend read.
    """
    if not bars:
        return []

    parsed: list[tuple[datetime, Bar]] = []
    use_dates = True
    for bar in bars:
        raw = (bar.date or "").strip()[:10]
        try:
            parsed.append((datetime.strptime(raw, "%Y-%m-%d"), bar))
        except ValueError:
            use_dates = False
            break

    groups: OrderedDict[tuple[int, int], list[Bar]] = OrderedDict()
    if use_dates and parsed:
        for dt, bar in parsed:
            iso = dt.isocalendar()
            key = (iso.year, iso.week)
            groups.setdefault(key, []).append(bar)
    else:
        for i, bar in enumerate(bars):
            groups.setdefault((0, i // 7), []).append(bar)

    weekly: list[Bar] = []
    for chunk in groups.values():
        weekly.append(
            Bar(
                date=chunk[0].date,
                open=chunk[0].open,
                high=max(b.high for b in chunk),
                low=min(b.low for b in chunk),
                close=chunk[-1].close,
                volume=sum(b.volume for b in chunk),
            )
        )
    return weekly
