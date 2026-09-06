"""Append-only JSONL logs. One JSON object per line."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from safe_desk.ticket import TradeTicket

DEFAULT_LOG = Path("logs/proposals.jsonl")


def append_jsonl(path: Path, row: dict[str, Any]) -> Path:
    """Append one JSON object. Creates parent directories as needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")
    return target


def read_jsonl(path: Path | str | None) -> list[dict[str, Any]]:
    """Read a JSONL file. Missing or empty → []. Skips bad lines."""
    if path is None:
        return []
    target = Path(path)
    if not target.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def append_proposal(
    ticket: TradeTicket,
    action: str = "proposed",
    path: Path | None = None,
    extra: dict[str, Any] | None = None,
) -> Path:
    """Append a ticket event. Creates parent directories as needed."""
    target = path or DEFAULT_LOG
    target.parent.mkdir(parents=True, exist_ok=True)
    row: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "action": action,
        "ticket_id": ticket.id,
        "mode": ticket.mode,
        "status": ticket.status,
        "symbol": ticket.symbol,
        "side": ticket.side,
        "entry": ticket.entry,
        "stop_loss": ticket.stop_loss,
        "take_profit": ticket.take_profit,
        "quantity": ticket.quantity,
        "notional": ticket.notional,
        "risk_pct": ticket.risk_pct,
        "risk_quote": ticket.risk_quote,
    }
    if extra:
        row.update(extra)
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, separators=(",", ":")) + "\n")
    return target
