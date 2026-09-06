"""Simple desk alerts. Written when a gate fires — not market spam."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from safe_desk.log import append_jsonl, read_jsonl
from safe_desk.policy import PolicyResult
from safe_desk.proof import ProofReport

DEFAULT_ALERTS = Path("logs/alerts.jsonl")

AlertKind = Literal[
    "PROOF_REJECT",
    "POLICY_BLOCKED",
    "WITHDRAW_REFUSED",
    "DAILY_CAP",
    "EMERGENCY_STOP",
    "APPROVAL_REJECTED",
]
Severity = Literal["info", "warn", "block"]


def alerts_path(path: Path | str | None = None) -> Path:
    return Path(path) if path is not None else DEFAULT_ALERTS


def read_alerts(path: Path | str | None = None, *, limit: int | None = 50) -> list[dict[str, Any]]:
    rows = read_jsonl(alerts_path(path))
    rows.reverse()
    if limit is None:
        return rows
    return rows[:limit]


def emit_alert(
    kind: AlertKind | str,
    message: str,
    *,
    severity: Severity = "warn",
    ticket_id: str | None = None,
    symbol: str | None = None,
    details: dict[str, Any] | None = None,
    path: Path | str | None = None,
    ts: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ts": ts or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": str(kind),
        "severity": severity,
        "message": message,
        "ticket_id": ticket_id,
        "symbol": None if symbol is None else symbol.upper(),
        "details": details or {},
    }
    append_jsonl(alerts_path(path), row)
    return row


def emit_from_proof(
    proof: ProofReport | dict[str, Any] | None,
    *,
    path: Path | str | None = None,
    ticket_id: str | None = None,
    symbol: str | None = None,
) -> dict[str, Any] | None:
    if proof is None:
        return None
    if isinstance(proof, dict):
        verdict = str(proof.get("verdict") or "")
        rationale = str(proof.get("rationale") or "Proof REJECT")
        receipt = proof.get("receipt_hash")
        sym = symbol or proof.get("symbol")
    else:
        verdict = proof.verdict
        rationale = proof.rationale
        receipt = proof.receipt_hash
        sym = symbol or proof.symbol
    if verdict != "REJECT":
        return None
    return emit_alert(
        "PROOF_REJECT",
        rationale,
        severity="block",
        ticket_id=ticket_id,
        symbol=sym,
        details={"receipt_hash": receipt, "verdict": verdict},
        path=path,
    )


def emit_from_policy(
    policy: PolicyResult | dict[str, Any] | None,
    *,
    path: Path | str | None = None,
    ticket_id: str | None = None,
    symbol: str | None = None,
) -> list[dict[str, Any]]:
    if policy is None:
        return []
    if isinstance(policy, dict):
        if policy.get("ok", True):
            return []
        violations = policy.get("violations") or []
        rows = []
        for raw in violations:
            if isinstance(raw, dict):
                code = str(raw.get("code") or "POLICY_BLOCKED")
                message = str(raw.get("message") or code)
            else:
                code = "POLICY_BLOCKED"
                message = str(raw)
            rows.append(_emit_policy_violation(code, message, path=path, ticket_id=ticket_id, symbol=symbol))
        return rows
    if policy.ok:
        return []
    return [
        _emit_policy_violation(
            v.code,
            v.message,
            path=path,
            ticket_id=ticket_id,
            symbol=symbol,
        )
        for v in policy.violations
    ]


def _emit_policy_violation(
    code: str,
    message: str,
    *,
    path: Path | str | None,
    ticket_id: str | None,
    symbol: str | None,
) -> dict[str, Any]:
    kind: AlertKind
    if code == "FORBIDDEN_INTENT":
        kind = "WITHDRAW_REFUSED"
    elif code in {"DAILY_LOSS_CAP", "DAILY_VOLUME_CAP"}:
        kind = "DAILY_CAP"
    elif code == "EMERGENCY_STOP":
        kind = "EMERGENCY_STOP"
    else:
        kind = "POLICY_BLOCKED"
    return emit_alert(
        kind,
        message,
        severity="block",
        ticket_id=ticket_id,
        symbol=symbol,
        details={"code": code},
        path=path,
    )
