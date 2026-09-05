"""Spot position sizing from wallet equity and a hard stop."""

from __future__ import annotations

from dataclasses import dataclass

from safe_desk.i18n import Lang, t

DEFAULT_RISK_PCT = 1.0
MAX_RISK_PCT = 1.0


@dataclass(frozen=True)
class SizeResult:
    equity: float
    risk_pct: float
    risk_quote: float
    entry: float
    stop: float
    stop_distance: float
    stop_pct: float
    quantity: float
    notional: float
    clamped_to_equity: bool
    notes: tuple[str, ...]


def size_spot(
    equity: float,
    entry: float,
    stop: float,
    risk_pct: float = DEFAULT_RISK_PCT,
    *,
    max_risk_pct: float = MAX_RISK_PCT,
    allow_over_equity: bool = False,
    lang: Lang = "en",
) -> SizeResult:
    """Size a spot order so a stop hit loses about `risk_pct` of equity.

    Quantity is `risk_quote / abs(entry - stop)`. If that notional exceeds
    equity, quantity is clamped to a full-wallet spot buy unless
    `allow_over_equity` is True (never used by the CLI).
    """
    notes: list[str] = []
    if equity <= 0:
        raise ValueError("equity must be > 0")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry and stop must be > 0")
    if entry == stop:
        raise ValueError("stop must differ from entry")
    if risk_pct <= 0:
        raise ValueError("risk_pct must be > 0")
    if risk_pct > max_risk_pct:
        notes.append(t(lang, "risk_capped", requested=risk_pct, max=max_risk_pct))
        risk_pct = max_risk_pct

    risk_quote = equity * (risk_pct / 100.0)
    stop_distance = abs(entry - stop)
    stop_pct = 100.0 * stop_distance / entry
    quantity = risk_quote / stop_distance
    notional = quantity * entry
    clamped = False
    if notional > equity and not allow_over_equity:
        quantity = equity / entry
        notional = equity
        clamped = True
        notes.append(t(lang, "clamped"))
    if stop_pct < 0.15:
        notes.append(t(lang, "stop_tight"))
    if stop_pct > 12:
        notes.append(t(lang, "stop_wide"))
    return SizeResult(
        equity=equity,
        risk_pct=risk_pct,
        risk_quote=risk_quote,
        entry=entry,
        stop=stop,
        stop_distance=stop_distance,
        stop_pct=stop_pct,
        quantity=quantity,
        notional=notional,
        clamped_to_equity=clamped,
        notes=tuple(notes),
    )
