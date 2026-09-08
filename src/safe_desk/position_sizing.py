"""Spot position sizing from wallet equity and a hard stop."""

from __future__ import annotations

from dataclasses import dataclass

from safe_desk.i18n import Lang, t

DEFAULT_RISK_PCT = 1.0
MAX_RISK_PCT = 1.0
# Float slack so a 1%-sized qty at the same stop does not trip the brake.
RISK_COMPARE_EPS = 1e-9


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
    actual_risk_quote: float = 0.0
    actual_risk_pct: float = 0.0
    quantity_locked: bool = False


def stop_side_ok(side: str | None, entry: float, stop: float) -> bool:
    """BUY stop must sit below entry; SELL stop must sit above. Equal is never ok."""
    if entry == stop:
        return False
    if side is None:
        return True
    key = str(side).strip().upper()
    if key == "BUY":
        return stop < entry
    if key == "SELL":
        return stop > entry
    return False


def capital_at_risk_quote(entry: float, stop: float, quantity: float) -> float:
    """Spot-style capital at risk: qty × |entry − stop|."""
    return abs(float(entry) - float(stop)) * float(quantity)


def actual_risk_pct(equity: float, risk_quote: float) -> float:
    if equity <= 0:
        raise ValueError("equity must be > 0")
    return 100.0 * float(risk_quote) / float(equity)


def max_stop_distance(equity: float, quantity: float, risk_pct: float) -> float:
    """Farthest |entry − stop| allowed for this size at `risk_pct` of equity."""
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if equity <= 0:
        raise ValueError("equity must be > 0")
    if risk_pct <= 0:
        raise ValueError("risk_pct must be > 0")
    return (float(risk_pct) / 100.0) * float(equity) / float(quantity)


def risk_exceeds_limit(actual_pct: float, limit_pct: float) -> bool:
    return float(actual_pct) > float(limit_pct) + RISK_COMPARE_EPS


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

    budget = equity * (risk_pct / 100.0)
    distance = abs(entry - stop)
    stop_pct = 100.0 * distance / entry
    quantity = budget / distance
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
    actual_quote = capital_at_risk_quote(entry, stop, quantity)
    return SizeResult(
        equity=equity,
        risk_pct=risk_pct,
        risk_quote=budget,
        entry=entry,
        stop=stop,
        stop_distance=distance,
        stop_pct=stop_pct,
        quantity=quantity,
        notional=notional,
        clamped_to_equity=clamped,
        notes=tuple(notes),
        actual_risk_quote=actual_quote,
        actual_risk_pct=actual_risk_pct(equity, actual_quote),
        quantity_locked=False,
    )


def size_spot_at_quantity(
    equity: float,
    entry: float,
    stop: float,
    quantity: float,
    risk_pct: float = DEFAULT_RISK_PCT,
    *,
    max_risk_pct: float = MAX_RISK_PCT,
    lang: Lang = "en",
) -> SizeResult:
    """Keep this quantity; report actual capital-at-risk. Never silently re-size.

    A wider stop at the same size can push actual risk above `risk_pct`.
    Policy / create_ticket must block that — do not shrink qty here to hide it.
    """
    notes: list[str] = []
    if equity <= 0:
        raise ValueError("equity must be > 0")
    if entry <= 0 or stop <= 0:
        raise ValueError("entry and stop must be > 0")
    if entry == stop:
        raise ValueError("stop must differ from entry")
    if quantity <= 0:
        raise ValueError("quantity must be > 0")
    if risk_pct <= 0:
        raise ValueError("risk_pct must be > 0")
    limit = min(float(risk_pct), float(max_risk_pct))
    if risk_pct > max_risk_pct:
        notes.append(t(lang, "risk_capped", requested=risk_pct, max=max_risk_pct))

    distance = abs(entry - stop)
    stop_pct = 100.0 * distance / entry
    notional = quantity * entry
    actual_quote = capital_at_risk_quote(entry, stop, quantity)
    actual_pct = actual_risk_pct(equity, actual_quote)
    if risk_exceeds_limit(actual_pct, limit):
        notes.append(t(lang, "stop_risk_block", actual=actual_pct, limit=limit))
    if stop_pct < 0.15:
        notes.append(t(lang, "stop_tight"))
    if stop_pct > 12:
        notes.append(t(lang, "stop_wide"))
    return SizeResult(
        equity=equity,
        risk_pct=limit,
        risk_quote=actual_quote,
        entry=entry,
        stop=stop,
        stop_distance=distance,
        stop_pct=stop_pct,
        quantity=quantity,
        notional=notional,
        clamped_to_equity=False,
        notes=tuple(notes),
        actual_risk_quote=actual_quote,
        actual_risk_pct=actual_pct,
        quantity_locked=True,
    )
