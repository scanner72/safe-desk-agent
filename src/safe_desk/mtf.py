"""Higher-timeframe trend filter. Soft caution only — not a trading system.

Derives a slower trend from the same daily (or primary) OHLCV series:
weekly resample first, then a longer daily SMA stack if the week series
is too short. Conflict biases analyze/why toward WAIT. It does not place
orders and does not replace proof, policy, or OK TKT-…
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from safe_desk.indicators import sma_last, trend_state
from safe_desk.ohlcv import Bar, resample_weekly

Trend = Literal["BULL", "BEAR", "MIXED", "UNKNOWN"]
MtfState = Literal["ALIGNED", "CONFLICT", "UNKNOWN"]
HtfSource = Literal["weekly", "daily_proxy", "unknown"]

# Weekly SMA4/SMA8 ≈ one month / two months on daily bars.
WEEKLY_FAST = 4
WEEKLY_SLOW = 8
# Fallback when there are not enough weekly candles (still works offline).
DAILY_PROXY_FAST = 40
DAILY_PROXY_SLOW = 70


def mtf_alignment(entry_trend: str, htf_trend: str) -> MtfState:
    """ALIGNED if both sides agree; CONFLICT if they differ; else UNKNOWN."""
    entry = (entry_trend or "UNKNOWN").upper()
    htf = (htf_trend or "UNKNOWN").upper()
    if entry == "UNKNOWN" or htf == "UNKNOWN":
        return "UNKNOWN"
    if entry == htf:
        return "ALIGNED"
    return "CONFLICT"


def higher_tf_trend(
    bars: Sequence[Bar],
    *,
    weekly_fast: int = WEEKLY_FAST,
    weekly_slow: int = WEEKLY_SLOW,
) -> tuple[str, HtfSource]:
    """Slower trend from weekly bars, or a longer daily SMA proxy.

    Returns ``(BULL|BEAR|MIXED|UNKNOWN, source)``.
    """
    series = list(bars)
    weekly = resample_weekly(series)
    if len(weekly) >= weekly_slow:
        closes = [b.close for b in weekly]
        trend = trend_state(
            closes[-1],
            sma_last(closes, weekly_fast),
            sma_last(closes, weekly_slow),
        )
        return trend, "weekly"

    closes = [b.close for b in series]
    if len(closes) >= DAILY_PROXY_SLOW:
        trend = trend_state(
            closes[-1],
            sma_last(closes, DAILY_PROXY_FAST),
            sma_last(closes, DAILY_PROXY_SLOW),
        )
        return trend, "daily_proxy"
    return "UNKNOWN", "unknown"
