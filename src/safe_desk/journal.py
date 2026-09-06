"""PAPER / SIMULATED fill diary. Never a live PnL claim."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from safe_desk.log import append_jsonl, read_jsonl

DEFAULT_JOURNAL = Path("logs/paper_journal.jsonl")
PAPER_LABEL = "PAPER"
SIMULATED_NOTE = (
    "SIMULATED / PAPER fill. Not a live Binance order. Not live profit or loss."
)

Kind = Literal["entry", "exit"]
ExitReason = Literal["stop", "take_profit", "manual", "mark"]


@dataclass(frozen=True)
class JournalEvent:
    ts: str
    kind: Kind
    label: str
    simulated: bool
    ticket_id: str
    symbol: str
    side: str
    quantity: float
    price: float
    notional: float
    pnl: float | None
    running_pnl: float
    reason: str | None
    note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "ts": self.ts,
            "kind": self.kind,
            "label": self.label,
            "simulated": self.simulated,
            "ticket_id": self.ticket_id,
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
            "price": self.price,
            "notional": self.notional,
            "pnl": self.pnl,
            "running_pnl": self.running_pnl,
            "reason": self.reason,
            "note": self.note,
        }


def journal_path(path: Path | str | None = None) -> Path:
    return Path(path) if path is not None else DEFAULT_JOURNAL


def read_journal(path: Path | str | None = None) -> list[dict[str, Any]]:
    return read_jsonl(journal_path(path))


def running_pnl(path: Path | str | None = None) -> float:
    rows = read_journal(path)
    if not rows:
        return 0.0
    last = rows[-1].get("running_pnl")
    try:
        return float(last or 0.0)
    except (TypeError, ValueError):
        return 0.0


def open_positions(path: Path | str | None = None) -> list[dict[str, Any]]:
    """Entries that do not yet have a matching exit (by ticket_id)."""
    closed: set[str] = set()
    entries: dict[str, dict[str, Any]] = {}
    for row in read_journal(path):
        tid = str(row.get("ticket_id") or "")
        if row.get("kind") == "exit" and tid:
            closed.add(tid)
        elif row.get("kind") == "entry" and tid:
            entries[tid] = row
    return [row for tid, row in entries.items() if tid not in closed]


def summarize(path: Path | str | None = None) -> dict[str, Any]:
    rows = read_journal(path)
    realized = running_pnl(path)
    opened = open_positions(path)
    return {
        "label": PAPER_LABEL,
        "simulated": True,
        "note": "PAPER / SIMULATED diary. Not live PnL.",
        "events": rows,
        "event_count": len(rows),
        "open_count": len(opened),
        "open_positions": opened,
        "running_pnl": realized,
        "closed_count": sum(1 for r in rows if r.get("kind") == "exit"),
    }


def paper_pnl(side: str, entry: float, exit_price: float, quantity: float) -> float:
    if side.upper() == "SELL":
        return (entry - exit_price) * quantity
    return (exit_price - entry) * quantity


def append_paper_entry(
    *,
    ticket_id: str,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    path: Path | str | None = None,
    ts: str | None = None,
    note: str | None = None,
) -> JournalEvent:
    target = journal_path(path)
    stamp = ts or datetime.now(timezone.utc).isoformat(timespec="seconds")
    event = JournalEvent(
        ts=stamp,
        kind="entry",
        label=PAPER_LABEL,
        simulated=True,
        ticket_id=ticket_id,
        symbol=symbol.upper(),
        side=side.upper(),
        quantity=float(quantity),
        price=float(price),
        notional=float(quantity) * float(price),
        pnl=None,
        running_pnl=running_pnl(target),
        reason=None,
        note=note or SIMULATED_NOTE,
    )
    append_jsonl(target, event.to_dict())
    return event


def append_paper_exit(
    *,
    ticket_id: str,
    exit_price: float,
    reason: ExitReason = "manual",
    path: Path | str | None = None,
    ts: str | None = None,
    note: str | None = None,
) -> JournalEvent:
    target = journal_path(path)
    opened = {row["ticket_id"]: row for row in open_positions(target)}
    entry = opened.get(ticket_id)
    if entry is None:
        raise ValueError(f"no open PAPER position for {ticket_id}")
    qty = float(entry["quantity"])
    side = str(entry["side"])
    pnl = paper_pnl(side, float(entry["price"]), float(exit_price), qty)
    new_running = running_pnl(target) + pnl
    stamp = ts or datetime.now(timezone.utc).isoformat(timespec="seconds")
    event = JournalEvent(
        ts=stamp,
        kind="exit",
        label=PAPER_LABEL,
        simulated=True,
        ticket_id=ticket_id,
        symbol=str(entry["symbol"]).upper(),
        side=side,
        quantity=qty,
        price=float(exit_price),
        notional=qty * float(exit_price),
        pnl=pnl,
        running_pnl=new_running,
        reason=reason,
        note=note or f"{SIMULATED_NOTE} Exit reason: {reason}.",
    )
    append_jsonl(target, event.to_dict())
    return event
