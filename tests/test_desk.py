from pathlib import Path

from safe_desk.desk import DeskSession, handle_phrase, propose_ticket, run_analyze, run_policy_gate, run_proof_gate


def test_analyze_matches_offline_csv():
    card = run_analyze()
    assert card["last"] == 102450.0
    assert card["trend"] == "BULL"
    assert card["signal"] == "BUY"
    assert card["path"] == "offline"
    assert "not an order" in card["note"].lower() or "Setup only" in card["note"]


def test_proof_and_policy_pass_for_demo():
    proof = run_proof_gate()
    assert proof["verdict"] == "APPROVE"
    assert proof["receipt_hash"] == "05b628112ce384a6"
    policy = run_policy_gate(intent="ticket")
    assert policy["ok"] is True
    refused = run_policy_gate(intent="withdraw")
    assert refused["ok"] is False


def test_ticket_then_bare_ok_then_ok_id(tmp_path: Path):
    session = DeskSession()
    log = tmp_path / "ui.jsonl"
    proposed = propose_ticket(session, log=log)
    ticket_id = proposed["ticket"]["id"]
    assert proposed["ticket"]["status"] == "awaiting_approval"
    assert proposed["ticket"]["mode"] == "dry-run"

    bare = handle_phrase(session, "ok", log=log)
    assert bare["kind"] == "bare_ok"
    assert bare["ok"] is False

    approved = handle_phrase(session, f"OK {ticket_id}", log=log)
    assert approved["kind"] == "simulated"
    assert approved["payload"]["status"] == "simulated"
    assert approved["ticket"]["id"] == ticket_id
    assert "Not a fill" in approved["message"]

    withdraw = handle_phrase(session, "withdraw 50 USDT to my wallet", log=log)
    assert withdraw["kind"] == "withdraw_refused"
    assert withdraw["ok"] is False
