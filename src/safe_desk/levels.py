"""ATR-based stop and take-profit suggestions.

These are **advisory** ticket/UI levels, not exchange trailing orders.
Dry-run / OK TKT-… gates stay unchanged.

Given entry E and ATR(14):

    BUY:  SL  = E − k_sl · ATR
          TP1 = E + k_tp1 · ATR
          TP2 = E + k_tp2 · ATR
    SELL: SL  = E + k_sl · ATR
          TP1 = E − k_tp1 · ATR
          TP2 = E − k_tp2 · ATR

Default multipliers (sane, in the suggested bands):

    k_sl  = 1.2   (suggested band ≈ 1.0–1.5)
    k_tp1 = 1.5   (suggested band ≈ 1.0–1.5)
    k_tp2 = 2.5   (suggested band ≈ 2.0–3.0)

“Скользящие” / ATR-trail: when new bars arrive, recompute from the
latest ATR via ``refresh_atr_levels``. That refreshes the *suggestion*
only. It does not place or amend live orders.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal

from safe_desk.indicators import atr

Side = Literal["BUY", "SELL"]

# Documented defaults — keep in the suggested bands, not magic prices.
DEFAULT_K_SL = 1.2
DEFAULT_K_TP1 = 1.5
DEFAULT_K_TP2 = 2.5
DEFAULT_ATR_PERIOD = 14


@dataclass(frozen=True)
class AtrMultipliers:
    """Configurable ATR multiples. Values must be > 0."""

    k_sl: float = DEFAULT_K_SL
    k_tp1: float = DEFAULT_K_TP1
    k_tp2: float = DEFAULT_K_TP2

    def __post_init__(self) -> None:
        for name, value in (("k_sl", self.k_sl), ("k_tp1", self.k_tp1), ("k_tp2", self.k_tp2)):
            if value <= 0:
                raise ValueError(f"{name} must be > 0")

    def to_dict(self) -> dict[str, float]:
        return {"k_sl": self.k_sl, "k_tp1": self.k_tp1, "k_tp2": self.k_tp2}


def parse_multipliers(
    k_sl: float | None = None,
    k_tp1: float | None = None,
    k_tp2: float | None = None,
) -> AtrMultipliers:
    return AtrMultipliers(
        k_sl=DEFAULT_K_SL if k_sl is None else float(k_sl),
        k_tp1=DEFAULT_K_TP1 if k_tp1 is None else float(k_tp1),
        k_tp2=DEFAULT_K_TP2 if k_tp2 is None else float(k_tp2),
    )


@dataclass(frozen=True)
class AtrLevels:
    entry: float
    atr: float
    side: Side
    sl: float
    tp1: float
    tp2: float
    multipliers: AtrMultipliers
    trail: bool = False

    @property
    def sl_distance(self) -> float:
        return abs(self.entry - self.sl)

    @property
    def tp1_distance(self) -> float:
        return abs(self.tp1 - self.entry)

    @property
    def tp2_distance(self) -> float:
        return abs(self.tp2 - self.entry)

    def to_dict(self) -> dict[str, Any]:
        return {
            "entry": self.entry,
            "atr": self.atr,
            "side": self.side,
            "sl": self.sl,
            "tp1": self.tp1,
            "tp2": self.tp2,
            "sl_distance": self.sl_distance,
            "tp1_distance": self.tp1_distance,
            "tp2_distance": self.tp2_distance,
            "k_sl": self.multipliers.k_sl,
            "k_tp1": self.multipliers.k_tp1,
            "k_tp2": self.multipliers.k_tp2,
            "trail": self.trail,
            "advisory": True,
            "live_trailing_order": False,
            "formula": (
                "BUY: SL=E−k_sl·ATR, TP1=E+k_tp1·ATR, TP2=E+k_tp2·ATR; "
                "SELL: SL=E+k_sl·ATR, TP1=E−k_tp1·ATR, TP2=E−k_tp2·ATR"
            ),
        }


def atr_levels(
    entry: float,
    atr_value: float,
    side: Side = "BUY",
    multipliers: AtrMultipliers | None = None,
    *,
    trail: bool = False,
) -> AtrLevels:
    """Compute SL / TP1 / TP2 from entry and a single ATR reading."""
    if entry <= 0:
        raise ValueError("entry must be > 0")
    if atr_value <= 0:
        raise ValueError("atr_value must be > 0")
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")
    mult = multipliers or AtrMultipliers()
    offset_sl = mult.k_sl * atr_value
    offset_tp1 = mult.k_tp1 * atr_value
    offset_tp2 = mult.k_tp2 * atr_value
    if side == "BUY":
        sl = entry - offset_sl
        tp1 = entry + offset_tp1
        tp2 = entry + offset_tp2
    else:
        sl = entry + offset_sl
        tp1 = entry - offset_tp1
        tp2 = entry - offset_tp2
    if sl <= 0:
        raise ValueError("computed stop is not positive; widen entry or shrink k_sl")
    if tp1 <= 0 or tp2 <= 0:
        raise ValueError("computed take-profit is not positive")
    return AtrLevels(
        entry=float(entry),
        atr=float(atr_value),
        side=side,
        sl=float(sl),
        tp1=float(tp1),
        tp2=float(tp2),
        multipliers=mult,
        trail=trail,
    )


def refresh_atr_levels(
    entry: float,
    atr_value: float,
    side: Side = "BUY",
    multipliers: AtrMultipliers | None = None,
) -> AtrLevels:
    """ATR-trail style refresh: same formulas, latest ATR.

    Call again when a new bar updates ATR. Suggestion only — no live order.
    """
    return atr_levels(entry, atr_value, side, multipliers, trail=True)


def levels_from_bars(
    highs: Sequence[float | int],
    lows: Sequence[float | int],
    closes: Sequence[float | int],
    side: Side = "BUY",
    *,
    entry: float | None = None,
    period: int = DEFAULT_ATR_PERIOD,
    multipliers: AtrMultipliers | None = None,
    trail: bool = True,
) -> AtrLevels | None:
    """Build levels from the latest bar's ATR. None until ATR is warm."""
    atr_value = atr(highs, lows, closes, period)
    if atr_value is None or atr_value <= 0:
        return None
    last = float(closes[-1]) if closes else 0.0
    price = last if entry is None else float(entry)
    fn = refresh_atr_levels if trail else atr_levels
    return fn(price, atr_value, side, multipliers)


def try_atr_levels(
    entry: float,
    atr_value: float | None,
    side: Side = "BUY",
    multipliers: AtrMultipliers | None = None,
    *,
    trail: bool = False,
) -> AtrLevels | None:
    if atr_value is None or atr_value <= 0 or entry <= 0:
        return None
    try:
        return atr_levels(entry, atr_value, side, multipliers, trail=trail)
    except ValueError:
        return None
