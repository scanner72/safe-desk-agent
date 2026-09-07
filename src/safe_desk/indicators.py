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


def _rsi_from_avgs(avg_gain: float, avg_loss: float) -> float:
    if avg_loss <= 0 and avg_gain <= 0:
        return 50.0
    if avg_loss <= 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def rsi(closes: Sequence[Number], period: int = 14) -> list[float | None]:
    """Wilder RSI. Leading values are None until `period` changes exist."""
    if period < 1:
        raise ValueError("period must be >= 1")
    xs = _as_floats(closes)
    out: list[float | None] = [None] * len(xs)
    if len(xs) < period + 1:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for prev, cur in zip(xs, xs[1:]):
        delta = cur - prev
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    out[period] = _rsi_from_avgs(avg_gain, avg_loss)
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = _rsi_from_avgs(avg_gain, avg_loss)
    return out


def rsi_last(closes: Sequence[Number], period: int = 14) -> float | None:
    series = rsi(closes, period)
    return series[-1] if series else None


def rsi_state(
    value: float | None,
    *,
    overbought: float = 70.0,
    oversold: float = 30.0,
) -> str:
    """OVERBOUGHT, OVERSOLD, NEUTRAL, or UNKNOWN."""
    if value is None:
        return "UNKNOWN"
    if value >= overbought:
        return "OVERBOUGHT"
    if value <= oversold:
        return "OVERSOLD"
    return "NEUTRAL"


def volume_ratio(volumes: Sequence[Number], lookback: int = 20) -> float | None:
    """Last bar volume divided by the average of the prior `lookback` bars."""
    if lookback < 1:
        raise ValueError("lookback must be >= 1")
    xs = _as_floats(volumes)
    if len(xs) < lookback + 1:
        return None
    prior = xs[-(lookback + 1) : -1]
    avg = sum(prior) / lookback
    if avg <= 0:
        return None
    return xs[-1] / avg


def volume_flag(
    ratio: float | None,
    *,
    spike: float = 2.0,
    quiet: float = 0.5,
) -> str:
    """SPIKE, QUIET, NORMAL, or UNKNOWN. Context only — not a trade trigger."""
    if ratio is None:
        return "UNKNOWN"
    if ratio >= spike:
        return "SPIKE"
    if ratio <= quiet:
        return "QUIET"
    return "NORMAL"
