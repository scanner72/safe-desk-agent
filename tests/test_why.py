from safe_desk.i18n import t
from safe_desk.policy import PolicyResult, PolicyViolation, evaluate_policy
from safe_desk.position_sizing import size_spot
from safe_desk.proof import ProofReport
from safe_desk.risk import SetupReport
from safe_desk.why import decide_action, explain_why


def _setup(*, trend="BULL", regime="LOW", score=20, signal="BUY") -> SetupReport:
    return SetupReport(
        last=102450,
        sma_fast=101528,
        sma_slow=99890,
        atr=702,
        atr_pct=0.69,
        realized_vol=0.018,
        trend=trend,
        vol_regime=regime,
        risk_score=score,
        signal=signal,
        reasons=("aligned",),
    )


def _proof(verdict: str) -> ProofReport:
    return ProofReport(
        symbol="BTCUSDT",
        side="BUY",
        verdict=verdict,  # type: ignore[arg-type]
        rationale="test",
        n_analogs=8,
        k=8,
        window=10,
        horizon=5,
        median_forward_return=0.01,
        hit_rate=0.6,
        query_features=(),
        analogs=(),
        receipt_hash="abc",
    )


def test_decide_action_matrix():
    assert decide_action(signal="BUY", proof_verdict="APPROVE", policy_ok=True) == "ENTER"
    assert decide_action(signal="BUY", proof_verdict=None, policy_ok=True) == "ENTER"
    assert decide_action(signal="HOLD", proof_verdict="APPROVE", policy_ok=True) == "WAIT"
    assert decide_action(signal="BUY", proof_verdict="WAIT", policy_ok=True) == "WAIT"
    assert decide_action(signal="BUY", proof_verdict="REJECT", policy_ok=True) == "SKIP"
    assert decide_action(signal="AVOID", proof_verdict="APPROVE", policy_ok=True) == "SKIP"
    assert decide_action(signal="BUY", proof_verdict="APPROVE", policy_ok=False) == "SKIP"


def test_why_enter_is_plain_and_not_an_order():
    sized = size_spot(1000, 102450, 100200, 1.0)
    why = explain_why(
        setup=_setup(),
        proof=_proof("APPROVE"),
        policy=evaluate_policy(intent="ticket", symbol="BTCUSDT", risk_pct=1.0),
        size=sized,
        symbol="BTCUSDT",
    )
    assert why.action == "ENTER"
    assert 2 <= len(why.sentences) <= 4
    blob = " ".join(why.sentences).lower()
    assert "not an order" in blob
    assert "ok tkt" in blob
    assert "sma" not in blob
    assert "atr" not in blob
    assert "0.00444444" in blob or "btc" in blob
    assert why.headline.startswith("Why ENTER")


def test_why_skip_on_policy_and_reject():
    blocked = PolicyResult(
        ok=False,
        intent="ticket",
        violations=(PolicyViolation(code="SYMBOL_NOT_ALLOWLISTED", message="DOGEUSDT is not on the allowlist."),),
        config_source="test",
        emergency_stop=False,
    )
    why = explain_why(
        setup=_setup(signal="BUY"),
        proof=_proof("REJECT"),
        policy=blocked,
        symbol="DOGEUSDT",
    )
    assert why.action == "SKIP"
    blob = " ".join(why.sentences)
    assert "stop sign" in blob or "Skip" in blob
    assert "allowlist" in blob


def test_why_wait_mixed():
    why = explain_why(
        setup=_setup(trend="MIXED", regime="NORMAL", score=50, signal="HOLD"),
        proof=_proof("WAIT"),
    )
    assert why.action == "WAIT"
    assert "wait" in " ".join(why.sentences).lower()


def test_why_russian():
    why = explain_why(setup=_setup(), proof=_proof("APPROVE"), lang="ru")
    assert why.action == "ENTER"
    assert "заявка" in " ".join(why.sentences) or "сетап" in why.headline.lower() or "вход" in why.headline.lower()
    assert t("ru", "why_header")


def test_high_vol_adds_swing_sentence():
    why = explain_why(setup=_setup(regime="HIGH", score=80, signal="AVOID"))
    assert why.action == "SKIP"
    assert any("swings" in s.lower() for s in why.sentences)
