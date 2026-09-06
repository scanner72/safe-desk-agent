from pathlib import Path

from safe_desk.alerts import emit_alert, emit_from_policy, emit_from_proof, read_alerts
from safe_desk.policy import PolicyResult, PolicyViolation, evaluate_policy
from safe_desk.proof import ProofReport


def _proof(verdict: str) -> ProofReport:
    return ProofReport(
        symbol="BTCUSDT",
        side="BUY",
        verdict=verdict,  # type: ignore[arg-type]
        rationale="Analogs oppose BUY.",
        n_analogs=8,
        k=8,
        window=10,
        horizon=5,
        median_forward_return=-0.02,
        hit_rate=0.2,
        query_features=(),
        analogs=(),
        receipt_hash="deadbeef",
    )


def test_emit_proof_reject_and_ignore_approve(tmp_path: Path):
    path = tmp_path / "alerts.jsonl"
    assert emit_from_proof(_proof("APPROVE"), path=path) is None
    row = emit_from_proof(_proof("REJECT"), path=path, ticket_id="TKT-1")
    assert row is not None
    assert row["kind"] == "PROOF_REJECT"
    assert row["severity"] == "block"
    assert row["ticket_id"] == "TKT-1"
    assert read_alerts(path)[0]["kind"] == "PROOF_REJECT"


def test_policy_kinds(tmp_path: Path):
    path = tmp_path / "alerts.jsonl"
    withdraw = evaluate_policy(intent="withdraw")
    rows = emit_from_policy(withdraw, path=path)
    assert rows and rows[0]["kind"] == "WITHDRAW_REFUSED"

    daily = PolicyResult(
        ok=False,
        intent="ticket",
        violations=(PolicyViolation(code="DAILY_LOSS_CAP", message="Daily loss exceeds cap."),),
        config_source="test",
        emergency_stop=False,
    )
    rows = emit_from_policy(daily, path=path)
    assert rows[0]["kind"] == "DAILY_CAP"

    stop = PolicyResult(
        ok=False,
        intent="ticket",
        violations=(PolicyViolation(code="EMERGENCY_STOP", message="halt"),),
        config_source="test",
        emergency_stop=True,
    )
    assert emit_from_policy(stop, path=path)[0]["kind"] == "EMERGENCY_STOP"

    other = PolicyResult(
        ok=False,
        intent="ticket",
        violations=(PolicyViolation(code="SYMBOL_NOT_ALLOWLISTED", message="nope"),),
        config_source="test",
        emergency_stop=False,
    )
    assert emit_from_policy(other, path=path)[0]["kind"] == "POLICY_BLOCKED"


def test_bare_ok_alert(tmp_path: Path):
    path = tmp_path / "alerts.jsonl"
    emit_alert("APPROVAL_REJECTED", "Type OK TKT-…", severity="warn", path=path)
    assert read_alerts(path)[0]["kind"] == "APPROVAL_REJECTED"
