"""High-level desk facade for the web UI and dry-run OK simulation.

Reuses analyze / proof / policy / ticket. Never calls Binance REST or MCP.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from safe_desk.alerts import emit_alert, emit_from_policy, emit_from_proof, read_alerts
from safe_desk.approval import is_bare_approval, parse_cancel_phrase, parse_ok_phrase
from safe_desk.i18n import Lang, norm_lang
from safe_desk.indicators import atr, realized_vol, sma_last
from safe_desk.journal import (
    append_paper_entry,
    append_paper_exit,
    summarize as journal_summary,
)
from safe_desk.log import append_jsonl, append_proposal, read_jsonl
from safe_desk.mcp_input import MCP_ENDPOINT, LiveQuote, load_live_quote
from safe_desk.ohlcv import Bar, load_ohlcv, load_ohlcv_text
from safe_desk.policy import (
    PolicyResult,
    evaluate_policy,
    load_policy,
    resolve_policy_path,
    usage_from_log,
)
from safe_desk.position_sizing import SizeResult, size_spot
from safe_desk.proof import ProofReport, proof_blocks_ticket, run_proof
from safe_desk.risk import SetupReport, evaluate_setup
from safe_desk.ticket import Status, TradeTicket, build_ticket
from safe_desk.why import WhyEntry, explain_why

Side = Literal["BUY", "SELL"]


def find_repo_root(start: Path | None = None) -> Path:
    here = start or Path(__file__).resolve()
    candidates = [here, *here.parents, Path.cwd()]
    for folder in candidates:
        if (folder / "examples" / "btc-ohlcv.csv").is_file():
            return folder
    return Path.cwd()


@dataclass
class DeskPaths:
    root: Path
    log_dir: Path

    @property
    def proposals(self) -> Path:
        return self.log_dir / "proposals.jsonl"

    @property
    def journal(self) -> Path:
        return self.log_dir / "paper_journal.jsonl"

    @property
    def alerts(self) -> Path:
        return self.log_dir / "alerts.jsonl"

    @property
    def tickets(self) -> Path:
        return self.log_dir / "tickets.jsonl"

    @property
    def sample_csv(self) -> Path:
        return self.root / "examples" / "btc-ohlcv.csv"


class Desk:
    """In-process desk: dry-run default, human OK, paper journal."""

    def __init__(self, *, root: Path | None = None, log_dir: Path | None = None) -> None:
        repo = root or find_repo_root()
        logs = log_dir or (Path.cwd() / "logs")
        self.paths = DeskPaths(root=repo, log_dir=Path(logs))
        self.paths.log_dir.mkdir(parents=True, exist_ok=True)
        self.last_proof: ProofReport | None = None
        self.last_policy: PolicyResult | None = None
        self.last_why: WhyEntry | None = None
        # Withdraw checks must not overwrite the last *ticket* policy chip.
        self._tickets: dict[str, dict[str, Any]] = {}
        self._reload_tickets()

    def sample_csv_path(self) -> Path:
        return self.paths.sample_csv

    def policy_config(self):
        path = resolve_policy_path(
            None,
            cwd=self.paths.root,
            env_path=os.environ.get("SAFE_DESK_POLICY"),
        )
        if path is None:
            return None
        return load_policy(path)

    def status(self) -> dict[str, Any]:
        cfg = self.policy_config()
        emergency = bool(cfg.emergency_stop) if cfg is not None else False
        paper = journal_summary(self.paths.journal)
        policy_ok = None if self.last_policy is None else self.last_policy.ok
        return {
            "mode": "dry-run",
            "dry_run": True,
            "live_trading": False,
            "mcp_url": MCP_ENDPOINT,
            "emergency_stop": emergency,
            "policy_source": None if cfg is None else cfg.source,
            "last_proof": None if self.last_proof is None else self.last_proof.summary_dict(),
            "last_policy": None if self.last_policy is None else self.last_policy.to_dict(),
            "last_why": None if self.last_why is None else self.last_why.to_dict(),
            "policy_ok": policy_ok,
            "paper": {
                "label": "PAPER / SIMULATED",
                "running_pnl": paper["running_pnl"],
                "open_count": paper["open_count"],
                "event_count": paper["event_count"],
            },
            "open_tickets": [
                t
                for t in self._tickets.values()
                if t.get("status") == "awaiting_approval"
            ],
            "alert_count": len(read_jsonl(self.paths.alerts)),
            "secrets_stored": False,
        }

    def analyze(
        self,
        *,
        bars: list[Bar] | None = None,
        csv_text: str | None = None,
        use_sample: bool = False,
        symbol: str = "BTCUSDT",
        side: Side = "BUY",
        stop: float | None = None,
        equity: float | None = None,
        risk_pct: float = 1.0,
        price_json: Path | str | dict[str, Any] | None = None,
        balance_json: Path | str | dict[str, Any] | None = None,
        lang: Lang | str = "en",
        run_proof_gate: bool = True,
        run_policy_gate: bool = True,
    ) -> dict[str, Any]:
        language = norm_lang(lang if isinstance(lang, str) else lang)
        loaded = bars
        source = "bars"
        if loaded is None and csv_text:
            loaded = load_ohlcv_text(csv_text)
            source = "upload"
        if loaded is None and use_sample:
            loaded = load_ohlcv(self.paths.sample_csv)
            source = "sample"
        if not loaded:
            raise ValueError("analyze needs a CSV upload, pasted CSV, or use_sample=true")

        live = _optional_live(price_json, balance_json, symbol)
        closes = [b.close for b in loaded]
        highs = [b.high for b in loaded]
        lows = [b.low for b in loaded]
        csv_last = closes[-1]
        last = csv_last if live is None or live.last is None else live.last
        if equity is None and live is not None:
            equity = live.equity

        fast = sma_last(closes, 20)
        slow = sma_last(closes, 50)
        atr_value = atr(highs, lows, closes, 14)
        vol = realized_vol(closes, period=min(20, max(2, len(closes) - 1)))
        setup = evaluate_setup(
            last=last,
            sma_fast=fast,
            sma_slow=slow,
            atr_value=atr_value,
            realized_vol_value=vol,
            side=side,
            stop=stop,
            lang=language,
        )

        proof = None
        if run_proof_gate:
            proof = run_proof(loaded, symbol=symbol, side=side)
            self.last_proof = proof
            emit_from_proof(proof, path=self.paths.alerts, symbol=symbol)

        sized = None
        if equity and stop:
            sized = size_spot(equity, last, stop, risk_pct, lang=language)

        policy = None
        if run_policy_gate:
            daily_loss, daily_volume = usage_from_log(self.paths.proposals)
            policy = evaluate_policy(
                intent="ticket",
                symbol=symbol,
                side=side,
                notional=None if sized is None else sized.notional,
                risk_pct=risk_pct,
                product="SPOT",
                daily_loss=daily_loss,
                daily_volume=daily_volume,
                config=self.policy_config(),
            )
            self.last_policy = policy

        why = explain_why(
            setup=setup,
            proof=proof,
            policy=policy,
            size=sized,
            symbol=symbol,
            lang=language,
        )
        self.last_why = why

        return {
            "symbol": symbol.upper(),
            "side": side,
            "source": source,
            "bars": len(loaded),
            "csv_last": csv_last,
            "last": last,
            "mode": "dry-run",
            "label": "setup only — not an order",
            "setup": _setup_dict(setup),
            "proof": None if proof is None else proof.summary_dict(),
            "policy": None if policy is None else policy.to_dict(),
            "size": None if sized is None else _size_dict(sized),
            "why": why.to_dict(),
            "live": None if live is None else live.to_dict(),
            "suggested_stop": _suggested_stop(last, atr_value, side),
            "mcp_url": MCP_ENDPOINT,
            "offline": live is None,
        }

    def create_ticket(
        self,
        *,
        symbol: str,
        side: Side = "BUY",
        entry: float | None = None,
        stop: float,
        equity: float | None = None,
        take_profit: float | None = None,
        risk_pct: float = 1.0,
        rationale: str = "",
        csv_text: str | None = None,
        use_sample: bool = False,
        price_json: Path | str | dict[str, Any] | None = None,
        balance_json: Path | str | dict[str, Any] | None = None,
        require_proof: bool = False,
        lang: Lang | str = "en",
    ) -> dict[str, Any]:
        language = norm_lang(lang if isinstance(lang, str) else lang)
        live = _optional_live(price_json, balance_json, symbol)
        if equity is None and live is not None:
            equity = live.equity
        if entry is None and live is not None:
            entry = live.last
        if equity is None or entry is None:
            raise ValueError("ticket needs equity and entry (or MCP-shaped price/balance JSON)")

        extra_notes: list[str] = []
        if live is not None:
            extra_notes.extend(live.notes)

        sized = size_spot(equity, entry, stop, risk_pct, lang=language)
        daily_loss, daily_volume = usage_from_log(self.paths.proposals)
        policy = evaluate_policy(
            intent="ticket",
            symbol=symbol,
            side=side,
            notional=sized.notional,
            risk_pct=risk_pct,
            product="SPOT",
            daily_loss=daily_loss,
            daily_volume=daily_volume,
            config=self.policy_config(),
        )
        self.last_policy = policy

        proof = None
        bars = _load_optional_bars(self, csv_text, use_sample)
        if bars:
            proof = run_proof(bars, symbol=symbol, side=side)
            self.last_proof = proof
            extra_notes.append(
                f"Proof {proof.verdict} receipt={proof.receipt_hash}: {proof.rationale}"
            )

        status: Status = "awaiting_approval"
        blocked: list[str] = []
        if not policy.ok:
            status = "blocked"
            for v in policy.violations:
                blocked.append(f"Policy {v.code}: {v.message}")
                extra_notes.append(f"Policy {v.code}: {v.message}")
        proof_blocked, proof_note = proof_blocks_ticket(
            proof,
            mode="dry-run",
            require_proof=require_proof,
        )
        if proof_note:
            extra_notes.append(proof_note)
        if proof_blocked:
            status = "blocked"
            blocked.append(proof_note or "proof gate")

        ticket = build_ticket(
            symbol=symbol,
            side=side,
            entry=entry,
            stop=stop,
            equity=equity,
            take_profit=take_profit,
            risk_pct=risk_pct,
            mode="dry-run",
            rationale=rationale,
            when=datetime.now(timezone.utc),
            lang=language,
            extra_notes=extra_notes,
            size=sized,
            status=status,
            proof=None if proof is None else proof.summary_dict(),
            policy=policy.to_dict(),
        )
        why = explain_why(
            setup=None,
            proof=proof,
            policy=policy,
            size=sized,
            symbol=symbol,
            lang=language,
        )
        # Prefer analyze setup if we have bars
        if bars:
            analysis = self.analyze(
                bars=bars,
                symbol=symbol,
                side=side,
                stop=stop,
                equity=equity,
                risk_pct=risk_pct,
                lang=language,
                run_proof_gate=False,
                run_policy_gate=False,
            )
            why = explain_why(
                setup=_setup_from_analysis(analysis),
                proof=proof,
                policy=policy,
                size=sized,
                symbol=symbol,
                lang=language,
            )
        self.last_why = why

        action = "blocked" if status == "blocked" else "proposed"
        append_proposal(ticket, action=action, path=self.paths.proposals)
        self._save_ticket(ticket)
        if status == "blocked":
            emit_from_policy(policy, path=self.paths.alerts, ticket_id=ticket.id, symbol=symbol)
            emit_from_proof(proof, path=self.paths.alerts, ticket_id=ticket.id, symbol=symbol)

        return {
            "ticket": ticket.to_dict(),
            "render": ticket.render(),
            "why": why.to_dict(),
            "blocked_reasons": blocked,
            "ok_phrase": f"OK {ticket.id}",
            "label": "DRY-RUN ticket. Not an order until OK TKT-…",
        }

    def approve(self, phrase: str, *, ticket_id: str | None = None) -> dict[str, Any]:
        parsed = parse_ok_phrase(phrase)
        if parsed is None:
            kind = "bare" if is_bare_approval(phrase) else "invalid"
            emit_alert(
                "APPROVAL_REJECTED",
                "A bare OK is not enough. Type OK plus the ticket id (OK TKT-…).",
                severity="warn",
                ticket_id=ticket_id,
                path=self.paths.alerts,
                details={"phrase": phrase, "reason": kind},
            )
            return {
                "ok": False,
                "reason": kind,
                "message": "Type OK TKT-… with the full ticket id. A bare “ok” is rejected.",
            }
        if ticket_id and parsed != ticket_id.upper():
            emit_alert(
                "APPROVAL_REJECTED",
                f"Phrase OK {parsed} does not match ticket {ticket_id}.",
                severity="warn",
                ticket_id=ticket_id,
                path=self.paths.alerts,
            )
            return {
                "ok": False,
                "reason": "mismatch",
                "message": f"That OK is for {parsed}, not {ticket_id}.",
            }
        record = self._tickets.get(parsed)
        if record is None:
            return {"ok": False, "reason": "unknown", "message": f"No ticket {parsed} on this desk."}
        if record.get("status") == "blocked":
            return {"ok": False, "reason": "blocked", "message": "This ticket is BLOCKED. No place path."}
        if record.get("status") != "awaiting_approval":
            return {
                "ok": False,
                "reason": "not_awaiting",
                "message": f"Ticket is {record.get('status')}, not awaiting approval.",
            }

        record = dict(record)
        record["status"] = "simulated"
        record["mcp_action"] = "simulated — dry-run did not call a Trade tool"
        self._tickets[parsed] = record
        append_jsonl(self.paths.tickets, record)
        ticket_obj = _ticket_from_record(record)
        append_proposal(ticket_obj, action="simulated", path=self.paths.proposals)

        event = append_paper_entry(
            ticket_id=parsed,
            symbol=str(record["symbol"]),
            side=str(record["side"]),
            quantity=float(record["quantity"]),
            price=float(record["entry"]),
            path=self.paths.journal,
        )
        payload = {
            "status": "simulated",
            "label": "SIMULATED / PAPER",
            "note": (
                "Dry-run. Exact arguments we would send to the official Binance "
                f"Agent OS MCP ({MCP_ENDPOINT}). No Trade tool was called. Not a live fill."
            ),
            "tool": "<discover at runtime from the official MCP client — do not invent names>",
            "arguments": {
                "symbol": record["symbol"],
                "side": record["side"],
                "type": record.get("order_type") or "LIMIT",
                "quantity": record["quantity"],
                "price": record["entry"],
                "newClientOrderId": parsed,
            },
        }
        return {
            "ok": True,
            "ticket": record,
            "simulated": payload,
            "journal": event.to_dict(),
            "paper_label": "PAPER / SIMULATED",
        }

    def cancel(self, phrase: str | None = None, *, ticket_id: str | None = None) -> dict[str, Any]:
        parsed = parse_cancel_phrase(phrase) if phrase else None
        tid = (parsed or ticket_id or "").upper()
        if not tid:
            return {"ok": False, "message": "Need CANCEL TKT-… or a ticket id."}
        record = self._tickets.get(tid)
        if record is None:
            return {"ok": False, "message": f"No ticket {tid}."}
        record = dict(record)
        record["status"] = "cancelled"
        self._tickets[tid] = record
        append_jsonl(self.paths.tickets, record)
        append_proposal(_ticket_from_record(record), action="cancelled", path=self.paths.proposals)
        return {"ok": True, "ticket": record}

    def refuse_withdraw(self, *, note: str = "withdraw") -> dict[str, Any]:
        policy = evaluate_policy(intent="withdraw", config=self.policy_config())
        emit_from_policy(policy, path=self.paths.alerts)
        return {
            "ok": False,
            "refused": True,
            "label": "WITHDRAW REFUSED",
            "message": (
                "Safe Desk never withdraws, never transfers out, and never pulls "
                "main→Agentic. Move leftover funds yourself in the Binance UI."
            ),
            "policy": policy.to_dict(),
            "intent": note,
        }

    def close_paper(
        self,
        ticket_id: str,
        *,
        exit_price: float | None = None,
        reason: Literal["stop", "take_profit", "manual", "mark"] = "manual",
    ) -> dict[str, Any]:
        record = self._tickets.get(ticket_id.upper())
        price = exit_price
        if price is None and record is not None:
            if reason == "stop":
                price = float(record["stop_loss"])
            elif reason == "take_profit" and record.get("take_profit") is not None:
                price = float(record["take_profit"])
            else:
                price = float(record["entry"])
        if price is None:
            raise ValueError("exit_price is required")
        event = append_paper_exit(
            ticket_id=ticket_id.upper(),
            exit_price=price,
            reason=reason,
            path=self.paths.journal,
        )
        return {"ok": True, "event": event.to_dict(), "paper": journal_summary(self.paths.journal)}

    def journal(self) -> dict[str, Any]:
        return journal_summary(self.paths.journal)

    def alerts(self, *, limit: int = 50) -> list[dict[str, Any]]:
        return read_alerts(self.paths.alerts, limit=limit)

    def ticket(self, ticket_id: str) -> dict[str, Any] | None:
        return self._tickets.get(ticket_id.upper())

    def _save_ticket(self, ticket: TradeTicket) -> None:
        data = ticket.to_dict()
        self._tickets[ticket.id] = data
        append_jsonl(self.paths.tickets, data)

    def _reload_tickets(self) -> None:
        for row in read_jsonl(self.paths.tickets):
            tid = row.get("id") or row.get("ticket_id")
            if tid:
                self._tickets[str(tid).upper()] = row


def _optional_live(
    price_json: Path | str | dict[str, Any] | None,
    balance_json: Path | str | dict[str, Any] | None,
    symbol: str | None,
) -> LiveQuote | None:
    if price_json is None and balance_json is None:
        return None
    return load_live_quote(
        price_source=price_json,
        balance_source=balance_json,
        symbol=symbol,
    )


def _load_optional_bars(desk: Desk, csv_text: str | None, use_sample: bool) -> list[Bar] | None:
    if csv_text:
        return load_ohlcv_text(csv_text)
    if use_sample and desk.paths.sample_csv.is_file():
        return load_ohlcv(desk.paths.sample_csv)
    return None


def _setup_dict(setup: SetupReport) -> dict[str, Any]:
    return {
        "last": setup.last,
        "sma_fast": setup.sma_fast,
        "sma_slow": setup.sma_slow,
        "atr": setup.atr,
        "atr_pct": setup.atr_pct,
        "realized_vol": setup.realized_vol,
        "trend": setup.trend,
        "vol_regime": setup.vol_regime,
        "risk_score": setup.risk_score,
        "signal": setup.signal,
        "reasons": list(setup.reasons),
    }


def _size_dict(sized: SizeResult) -> dict[str, Any]:
    return {
        "equity": sized.equity,
        "risk_pct": sized.risk_pct,
        "risk_quote": sized.risk_quote,
        "entry": sized.entry,
        "stop": sized.stop,
        "stop_distance": sized.stop_distance,
        "stop_pct": sized.stop_pct,
        "quantity": sized.quantity,
        "notional": sized.notional,
        "clamped_to_equity": sized.clamped_to_equity,
        "notes": list(sized.notes),
    }


def _suggested_stop(last: float, atr_value: float | None, side: Side) -> float | None:
    if atr_value is None or atr_value <= 0:
        return None
    if side == "BUY":
        return last - 2.0 * atr_value
    return last + 2.0 * atr_value


def _setup_from_analysis(analysis: dict[str, Any]) -> SetupReport:
    raw = analysis["setup"]
    return SetupReport(
        last=float(raw["last"]),
        sma_fast=raw.get("sma_fast"),
        sma_slow=raw.get("sma_slow"),
        atr=raw.get("atr"),
        atr_pct=raw.get("atr_pct"),
        realized_vol=raw.get("realized_vol"),
        trend=str(raw["trend"]),
        vol_regime=raw["vol_regime"],
        risk_score=int(raw["risk_score"]),
        signal=raw["signal"],
        reasons=tuple(raw.get("reasons") or ()),
    )


def _ticket_from_record(record: dict[str, Any]) -> TradeTicket:
    """Rebuild a TradeTicket for the proposal log (status may have changed)."""
    from safe_desk.i18n import t

    lang: Lang = "en"
    return TradeTicket(
        id=str(record["id"]),
        created_at=str(record.get("created_at") or ""),
        mode=record.get("mode") or "dry-run",
        status=record.get("status") or "simulated",
        venue=str(record.get("venue") or t(lang, "venue")),
        product=str(record.get("product") or "SPOT"),
        symbol=str(record["symbol"]),
        side=record["side"],
        order_type=str(record.get("order_type") or "LIMIT"),
        entry=float(record["entry"]),
        stop_loss=float(record["stop_loss"]),
        take_profit=record.get("take_profit"),
        equity_quote=float(record.get("equity_quote") or 0),
        risk_pct=float(record.get("risk_pct") or 1),
        risk_quote=float(record.get("risk_quote") or 0),
        quantity=float(record["quantity"]),
        notional=float(record["notional"]),
        reward_risk=record.get("reward_risk"),
        rationale=str(record.get("rationale") or ""),
        invalidation=str(record.get("invalidation") or ""),
        notes=list(record.get("notes") or []),
        mcp_action=str(record.get("mcp_action") or ""),
        disclaimer=str(record.get("disclaimer") or ""),
        proof=record.get("proof"),
        policy=record.get("policy"),
    )


def dumps_pretty(data: dict[str, Any]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)
