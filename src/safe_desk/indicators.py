"""Simple indicators. No look-ahead; series pad with None until warm."""

from __future__ import annotations

from collections.abc import Sequence

Number = float | int


def _as_floats(values: Sequence[Number]) -> list[float]:
    return [float(v) for v in values]


def sma(values: Sequence[Number], period: int) -> list[float | None]:
    """Simple moving average. Leading values are None until `period` bars."""
    if period < 1:
        raise ValueError("period must be >= 1")
    xs = _as_floats(values)
    out: list[float | None] = [None] * len(xs)
    running = 0.0
    for i, price in enumerate(xs):
        running += price
        if i >= period:
            running -= xs[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def sma_last(values: Sequence[Number], period: int) -> float | None:
    series = sma(values, period)
    return series[-1] if series else None


def realized_vol(closes: Sequence[Number], period: int = 20) -> float | None:
    """Annualized close-to-close volatility from the last `period` returns.

    Uses 365-day crypto convention. Returns None if not enough bars.
    """
    xs = _as_floats(closes)
    if period < 2 or len(xs) < period + 1:
        return None
    window = xs[-(period + 1) :]
    rets = []
    for prev, cur in zip(window, window[1:]):
        if prev <= 0:
            return None
        rets.append((cur / prev) - 1.0)
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return (var**0.5) * (365**0.5)


def true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(
    highs: Sequence[Number],
    lows: Sequence[Number],
    closes: Sequence[Number],
    period: int = 14,
) -> float | None:
    """Wilder ATR of the last available bar. None until warm."""
    if period < 1:
        raise ValueError("period must be >= 1")
    hs, ls, cs = _as_floats(highs), _as_floats(lows), _as_floats(closes)
    n = min(len(hs), len(ls), len(cs))
    if n < period + 1:
        return None
    trs: list[float] = []
    for i in range(1, n):
        trs.append(true_range(hs[i], ls[i], cs[i - 1]))
    # Seed with SMA of first `period` TRs, then Wilder smooth the rest.
    atr_val = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val


def atr_pct(atr_value: float | None, last_price: float) -> float | None:
    if atr_value is None or last_price <= 0:
        return None
    return 100.0 * atr_value / last_price


def trend_state(
    last: float,
    sma_fast: float | None,
    sma_slow: float | None,
) -> str:
    """BULL, BEAR, or MIXED. MIXED if either SMA is missing."""
    if sma_fast is None or sma_slow is None:
        return "MIXED"
    if last > sma_fast > sma_slow:
        return "BULL"
    if last < sma_fast < sma_slow:
        return "BEAR"
    return "MIXED"
