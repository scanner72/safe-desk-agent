"""Trade ticket model. Never sends an order — that is the MCP + human step."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from safe_desk.i18n import Lang, t
from safe_desk.position_sizing import SizeResult, size_spot

Mode = Literal["dry-run", "live"]
Status = Literal["awaiting_approval", "cancelled", "simulated", "rejected"]
Side = Literal["BUY", "SELL"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ticket_id(when: datetime | None = None) -> str:
    ts = (when or utc_now()).strftime("%Y%m%d-%H%M%S")
    return f"TKT-{ts}"


@dataclass(frozen=True)
class TradeTicket:
    id: str
    created_at: str
    mode: Mode
    status: Status
    venue: str
    product: str
    symbol: str
    side: Side
    order_type: str
    entry: float
    stop_loss: float
    take_profit: float | None
    equity_quote: float
    risk_pct: float
    risk_quote: float
    quantity: float
    notional: float
    reward_risk: float | None
    rationale: str
    invalidation: str
    notes: list[str]
    mcp_action: str
    disclaimer: str
    lang: Lang = "en"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("lang", None)
        return data

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False, ensure_ascii=False)

    def render(self) -> str:
        lang = self.lang
        tp = "\u2014" if self.take_profit is None else _num(self.take_profit)
        rr = "\u2014" if self.reward_risk is None else f"{self.reward_risk:.2f}"
        note_block = "\n".join(f"  - {n}" for n in self.notes) or f"  - {t(lang, 'none_notes')}"
        return f"""TICKET {self.id}
{t(lang, 'ticket_status'):<13}{self.status.upper()}
{t(lang, 'ticket_mode'):<13}{self.mode.upper()}
{t(lang, 'ticket_venue'):<13}{self.venue}
{t(lang, 'ticket_product'):<13}{self.product}
{t(lang, 'ticket_symbol'):<13}{self.symbol}
{t(lang, 'ticket_side'):<13}{self.side}
{t(lang, 'ticket_type'):<13}{self.order_type}
{t(lang, 'entry'):<13}{_num(self.entry)}
{t(lang, 'ticket_sl'):<13}{_num(self.stop_loss)}
{t(lang, 'ticket_tp'):<13}{tp}
{t(lang, 'equity'):<13}{_num(self.equity_quote)}
{t(lang, 'risk_pct'):<13}{self.risk_pct:g}%  ({_num(self.risk_quote)} quote)
{t(lang, 'quantity'):<13}{_qty(self.quantity)}
{t(lang, 'notional'):<13}{_num(self.notional)}
{t(lang, 'ticket_rr'):<13}{rr}
{t(lang, 'ticket_rationale'):<13}{self.rationale}
{t(lang, 'ticket_invalidation'):<13}{self.invalidation}
{t(lang, 'ticket_mcp'):<13}{self.mcp_action}

{t(lang, 'notes')}
{note_block}

{self.disclaimer}

{t(lang, 'reply_ok', ticket_id=self.id)}
{t(lang, 'reply_cancel', ticket_id=self.id)}
"""


def reward_risk(entry: float, stop: float, take_profit: float | None, side: Side) -> float | None:
    if take_profit is None:
        return None
    risk = abs(entry - stop)
    if risk <= 0:
        return None
    if side == "BUY":
        reward = take_profit - entry
    else:
        reward = entry - take_profit
    if reward <= 0:
        return None
    return reward / risk


def build_ticket(
    *,
    symbol: str,
    side: Side,
    entry: float,
    stop: float,
    equity: float,
    take_profit: float | None = None,
    risk_pct: float = 1.0,
    mode: Mode = "dry-run",
    product: str = "SPOT",
    order_type: str = "LIMIT",
    rationale: str = "",
    invalidation: str = "",
    extra_notes: list[str] | None = None,
    size: SizeResult | None = None,
    when: datetime | None = None,
    lang: Lang = "en",
) -> TradeTicket:
    when = when or utc_now()
    sized = size or size_spot(equity, entry, stop, risk_pct, lang=lang)
    rr = reward_risk(entry, stop, take_profit, side)
    notes = list(sized.notes)
    if extra_notes:
        notes.extend(extra_notes)
    if rr is not None and rr < 1.0:
        notes.append(t(lang, "rr_low", rr=rr))
    if mode == "live":
        notes.append(t(lang, "live_still_waits"))
    rationale = rationale or t(lang, "default_rationale")
    invalidation = invalidation or t(lang, "default_invalidation", stop=stop)
    return TradeTicket(
        id=ticket_id(when),
        created_at=when.isoformat(timespec="seconds"),
        mode=mode,
        status="awaiting_approval",
        venue=t(lang, "venue"),
        product=product,
        symbol=symbol.upper(),
        side=side,
        order_type=order_type,
        entry=float(entry),
        stop_loss=float(stop),
        take_profit=None if take_profit is None else float(take_profit),
        equity_quote=sized.equity,
        risk_pct=sized.risk_pct,
        risk_quote=sized.risk_quote,
        quantity=sized.quantity,
        notional=sized.notional,
        reward_risk=rr,
        rationale=rationale,
        invalidation=invalidation,
        notes=notes,
        mcp_action=t(lang, "mcp_action"),
        disclaimer=t(lang, "disclaimer"),
        lang=lang,
    )


def _num(value: float) -> str:
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if abs(value) >= 1:
        return f"{value:,.4f}"
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _qty(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
