"""In-memory Safe Desk session for the local UI. Dry-run only. No secrets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from safe_desk.indicators import atr, realized_vol, sma_last
from safe_desk.log import append_proposal
from safe_desk.mcp_input import MCP_ENDPOINT
from safe_desk.ohlcv import load_ohlcv
from safe_desk.paths import default_csv, default_policy, repo_root
from safe_desk.policy import classify_intent, evaluate_policy, load_policy
from safe_desk.position_sizing import size_spot
from safe_desk.proof import proof_blocks_ticket, run_proof
from safe_desk.risk import evaluate_setup
from safe_desk.ticket import TradeTicket, build_ticket

OK_RE = re.compile(r"^\s*ok\s+(TKT-\d{8}-\d{6})\s*$", re.IGNORECASE)
BARE_OK = re.compile(r"^\s*(ok|yes|go|lgtm|fire|approve)\s*[.!]*\s*$", re.IGNORECASE)
WITHDRAW_RE = re.compile(
    r"withdraw|send\s+out|transfer[-_ ]?out|cash\s*out|sweep|0x[0-9a-f]{20,}",
    re.IGNORECASE,
)

DEMO_STOP = 100_200.0
DEMO_TP = 106_950.0
DEMO_EQUITY = 1_000.0
DEMO_RISK = 1.0


def ui_log_path() -> Path:
    preferred = repo_root() / "logs" / "ui-proposals.jsonl"
    try:
        preferred.parent.mkdir(parents=True, exist_ok=True)
        if os.access(preferred.parent, os.W_OK):
            return preferred
    except OSError:
        pass
    return Path("/tmp/safe-desk-ui.jsonl")


@dataclass
class DeskSession:
    """One browser session. Never places a live order."""

    ticket: TradeTicket | None = None
    last_analyze: dict[str, Any] | None = None
    last_proof: dict[str, Any] | None = None
    last_policy: dict[str, Any] | None = None
    last_approval: dict[str, Any] | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    def snapshot(self) -> dict[str, Any]:
        return {
            "mode": "dry-run",
            "mcp_endpoint": MCP_ENDPOINT,
            "simulated": True,
            "ticket": None if self.ticket is None else self.ticket.to_dict(),
            "analyze": self.last_analyze,
            "proof": self.last_proof,
            "policy": self.last_policy,
            "approval": self.last_approval,
            "events": list(self.events[-12:]),
        }


def meta() -> dict[str, Any]:
    root = repo_root()
    return {
        "mode": "dry-run",
        "product": "SPOT",
        "mcp_endpoint": MCP_ENDPOINT,
        "venue": "Binance Agentic subaccount only",
        "simulated": True,
        "disclaimer": (
            "Not financial advice. Demo numbers are SIMULATED. "
            "This UI never calls Binance REST and holds no API keys. "
            "Place path is official MCP after OK TKT-… — dry-run prints a payload only."
        ),
        "csv": str(default_csv().relative_to(root)),
        "policy": str(default_policy().relative_to(root)),
    }


def run_analyze(*, symbol: str = "BTCUSDT", side: str = "BUY") -> dict[str, Any]:
    bars = load_ohlcv(default_csv())
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    last = closes[-1]
    fast = sma_last(closes, 20)
    slow = sma_last(closes, 50)
    atr_value = atr(highs, lows, closes, 14)
    vol = realized_vol(closes, period=min(20, max(2, len(closes) - 1)))
    report = evaluate_setup(
        last=last,
        sma_fast=fast,
        sma_slow=slow,
        atr_value=atr_value,
        realized_vol_value=vol,
        side=side,
        stop=DEMO_STOP,
    )
    return {
        "path": "offline",
        "symbol": symbol.upper(),
        "bars": len(bars),
        "last": last,
        "sma20": fast,
        "sma50": slow,
        "atr": atr_value,
        "atr_pct": report.atr_pct,
        "realized_vol": report.realized_vol,
        "trend": report.trend,
        "vol_regime": report.vol_regime,
        "risk_score": report.risk_score,
        "signal": report.signal,
        "reasons": list(report.reasons),
        "note": "Setup only — not an order. CSV is synthetic. No MCP call was made.",
    }


def run_proof_gate(*, symbol: str = "BTCUSDT", side: str = "BUY") -> dict[str, Any]:
    report = run_proof(load_ohlcv(default_csv()), symbol=symbol, side=side)
    return report.to_dict() | {"note": "Leakage-safe analog gate. Not a live win rate."}


def run_policy_gate(
    *,
    intent: str = "ticket",
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    notional: float | None = 455.0,
    risk_pct: float | None = DEMO_RISK,
) -> dict[str, Any]:
    cfg = load_policy(default_policy())
    result = evaluate_policy(
        intent=intent,
        symbol=symbol,
        side=side,
        notional=notional,
        risk_pct=risk_pct,
        product="SPOT",
        config=cfg,
    )
    return result.to_dict()


def propose_ticket(
    session: DeskSession,
    *,
    symbol: str = "BTCUSDT",
    side: str = "BUY",
    equity: float = DEMO_EQUITY,
    stop: float = DEMO_STOP,
    take_profit: float = DEMO_TP,
    risk_pct: float = DEMO_RISK,
    log: Path | None = None,
) -> dict[str, Any]:
    analyze = run_analyze(symbol=symbol, side=side)
    proof = run_proof(load_ohlcv(default_csv()), symbol=symbol, side=side)
    entry = float(analyze["last"])
    sized = size_spot(equity, entry, stop, risk_pct)
    policy = evaluate_policy(
        intent="ticket",
        symbol=symbol,
        side=side,
        notional=sized.notional,
        risk_pct=risk_pct,
        product="SPOT",
        config=load_policy(default_policy()),
    )
    extra = [
        f"Proof {proof.verdict} receipt={proof.receipt_hash}: {proof.rationale}",
    ]
    status = "awaiting_approval"
    if not policy.ok:
        status = "blocked"
        extra.extend(f"Policy {v.code}: {v.message}" for v in policy.violations)
    blocked, note = proof_blocks_ticket(proof, mode="dry-run", require_proof=False)
    if note:
        extra.append(note)
    if blocked:
        status = "blocked"

    ticket = build_ticket(
        symbol=symbol,
        side=side,
        entry=entry,
        stop=stop,
        equity=equity,
        take_profit=take_profit,
        risk_pct=risk_pct,
        mode="dry-run",
        rationale="Daily SMA stack, ATR LOW, stop ~3.2× ATR. UI rehearsal — not a live order.",
        extra_notes=extra,
        size=sized,
        status=status,
        proof=proof.summary_dict(),
        policy=policy.to_dict(),
        when=datetime.now(timezone.utc),
    )
    session.ticket = ticket
    session.last_analyze = analyze
    session.last_proof = proof.to_dict()
    session.last_policy = policy.to_dict()
    session.last_approval = None
    action = "blocked" if status == "blocked" else "proposed"
    log_path = append_proposal(ticket, action=action, path=log or ui_log_path())
    session.events.append({"action": action, "ticket_id": ticket.id, "status": ticket.status})
    return {
        "ticket": ticket.to_dict(),
        "render": ticket.render(),
        "log": str(log_path),
        "analyze": analyze,
        "proof": proof.summary_dict(),
        "policy": policy.to_dict(),
    }


def handle_phrase(session: DeskSession, phrase: str, *, log: Path | None = None) -> dict[str, Any]:
    text = (phrase or "").strip()
    if not text:
        return {"ok": False, "kind": "empty", "message": "Type a command. Bare 'ok' is not enough."}

    if WITHDRAW_RE.search(text) or classify_intent(text) in {"withdraw", "transfer_out", "main_to_agentic"}:
        policy = run_policy_gate(intent="withdraw")
        result = {
            "ok": False,
            "kind": "withdraw_refused",
            "message": (
                "No. Safe Desk will not withdraw, send out, or transfer to main. "
                "Take leftovers home yourself in Sub-account → Asset Management. "
                "No MCP tool was called."
            ),
            "policy": policy,
        }
        session.last_approval = result
        session.events.append({"action": "withdraw_refused"})
        return result

    match = OK_RE.match(text)
    if match:
        ticket_id = match.group(1).upper()
        if session.ticket is None:
            return {"ok": False, "kind": "no_ticket", "message": "No ticket in this session. Propose first."}
        if session.ticket.status == "blocked":
            return {
                "ok": False,
                "kind": "blocked",
                "message": f"{session.ticket.id} is BLOCKED. Policy or proof closed the place path.",
            }
        if session.ticket.id != ticket_id:
            return {
                "ok": False,
                "kind": "wrong_id",
                "message": f"That id does not match the open ticket {session.ticket.id}.",
            }
        payload = {
            "tool": "spot.place_order",
            "note": "Illustrative name — discover the real MCP tool at runtime.",
            "args": {
                "symbol": session.ticket.symbol,
                "side": session.ticket.side,
                "type": session.ticket.order_type,
                "timeInForce": "GTC",
                "quantity": session.ticket.quantity,
                "price": session.ticket.entry,
                "newClientOrderId": session.ticket.id,
            },
            "status": "simulated",
        }
        when = datetime.strptime(ticket_id.replace("TKT-", ""), "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        session.ticket = build_ticket(
            symbol=session.ticket.symbol,
            side=session.ticket.side,
            entry=session.ticket.entry,
            stop=session.ticket.stop_loss,
            equity=session.ticket.equity_quote,
            take_profit=session.ticket.take_profit,
            risk_pct=session.ticket.risk_pct,
            mode="dry-run",
            rationale=session.ticket.rationale,
            extra_notes=list(session.ticket.notes) + ["DRY-RUN simulated. Not a fill. Not PnL."],
            status="simulated",
            proof=session.ticket.proof,
            policy=session.ticket.policy,
            mcp_action="simulated — payload printed, Trade tool not called",
            when=when,
        )
        append_proposal(
            session.ticket,
            action="simulated",
            path=log or ui_log_path(),
        )
        result = {
            "ok": True,
            "kind": "simulated",
            "message": "DRY-RUN. Simulated MCP payload. Not sent. Not a fill. Not PnL.",
            "payload": payload,
            "ticket": session.ticket.to_dict(),
        }
        session.last_approval = result
        session.events.append({"action": "simulated", "ticket_id": ticket_id})
        return result

    if BARE_OK.match(text):
        needed = "OK TKT-…" if session.ticket is None else f"OK {session.ticket.id}"
        result = {
            "ok": False,
            "kind": "bare_ok",
            "message": f"That is not enough. A bare “ok” is rejected. Reply {needed}.",
        }
        session.last_approval = result
        session.events.append({"action": "bare_ok_rejected"})
        return result

    return {
        "ok": False,
        "kind": "unknown",
        "message": "Unknown command. Try analyze / proof / policy / propose, or OK TKT-… / withdraw.",
    }
