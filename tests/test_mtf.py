"""Higher-TF trend filter: weekly resample, alignment, soft WAIT — not an order."""

from datetime import date, timedelta
from pathlib import Path

from safe_desk.mtf import higher_tf_trend, mtf_alignment
from safe_desk.ohlcv import Bar, load_ohlcv, resample_weekly
from safe_desk.risk import evaluate_setup
from safe_desk.why import decide_action, explain_why

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "examples" / "btc-ohlcv.csv"


def _bar(day: date, close: float) -> Bar:
    return Bar(
        date=day.isoformat(),
        open=close,
        high=close + 10,
        low=close - 10,
        close=close,
        volume=100,
    )


def _series(start: date, closes: list[float]) -> list[Bar]:
    return [_bar(start + timedelta(days=i), px) for i, px in enumerate(closes)]


def test_resample_weekly_groups_iso_weeks():
    start = date(2026, 6, 15)  # Monday
    bars = _series(start, [100.0 + i for i in range(14)])
    weekly = resample_weekly(bars)
    assert len(weekly) == 2
    assert weekly[0].open == 100.0
    assert weekly[0].close == 106.0
    assert weekly[0].high == 106.0 + 10
    assert weekly[1].open == 107.0
    assert weekly[1].close == 113.0
    assert weekly[0].volume == 700


def test_resample_weekly_packs_undated_bars():
    bars = [
        Bar(date="", open=10, high=11, low=9, close=10, volume=1)
        for _ in range(15)
    ]
    weekly = resample_weekly(bars)
    assert len(weekly) == 3
    assert weekly[0].volume == 7
    assert weekly[2].volume == 1


def test_mtf_alignment_matrix():
    assert mtf_alignment("BULL", "BULL") == "ALIGNED"
    assert mtf_alignment("BEAR", "BEAR") == "ALIGNED"
    assert mtf_alignment("MIXED", "MIXED") == "ALIGNED"
    assert mtf_alignment("BULL", "MIXED") == "CONFLICT"
    assert mtf_alignment("BULL", "BEAR") == "CONFLICT"
    assert mtf_alignment("BEAR", "BULL") == "CONFLICT"
    assert mtf_alignment("MIXED", "BULL") == "CONFLICT"
    assert mtf_alignment("BULL", "UNKNOWN") == "UNKNOWN"
    assert mtf_alignment("UNKNOWN", "BULL") == "UNKNOWN"


def test_sample_csv_weekly_aligns_with_daily_bull():
    bars = load_ohlcv(CSV)
    htf, source = higher_tf_trend(bars)
    assert source == "weekly"
    assert htf == "BULL"
    assert mtf_alignment("BULL", htf) == "ALIGNED"
    assert len(resample_weekly(bars)) >= 8


def test_aligned_does_not_raise_score():
    base = evaluate_setup(
        last=110,
        sma_fast=105,
        sma_slow=100,
        atr_value=2.0,
        realized_vol_value=0.4,
        side="BUY",
    )
    aligned = evaluate_setup(
        last=110,
        sma_fast=105,
        sma_slow=100,
        atr_value=2.0,
        realized_vol_value=0.4,
        side="BUY",
        htf_trend="BULL",
        htf_source="weekly",
    )
    assert aligned.mtf_state == "ALIGNED"
    assert aligned.htf_trend == "BULL"
    assert aligned.signal == "BUY"
    assert aligned.risk_score == base.risk_score


def test_conflict_raises_score_and_holds():
    aligned = evaluate_setup(
        last=110,
        sma_fast=105,
        sma_slow=100,
        atr_value=2.0,
        realized_vol_value=0.4,
        side="BUY",
        htf_trend="BULL",
        htf_source="weekly",
    )
    conflict = evaluate_setup(
        last=110,
        sma_fast=105,
        sma_slow=100,
        atr_value=2.0,
        realized_vol_value=0.4,
        side="BUY",
        htf_trend="MIXED",
        htf_source="weekly",
    )
    assert conflict.trend == "BULL"
    assert conflict.htf_trend == "MIXED"
    assert conflict.mtf_state == "CONFLICT"
    assert conflict.risk_score > aligned.risk_score
    assert conflict.signal == "HOLD"
    assert any("disagrees" in r.lower() or "caution" in r.lower() for r in conflict.reasons)


def test_conflict_does_not_bypass_policy_or_proof():
    assert (
        decide_action(
            signal="BUY",
            proof_verdict="APPROVE",
            policy_ok=False,
            mtf_state="CONFLICT",
        )
        == "SKIP"
    )
    assert (
        decide_action(
            signal="BUY",
            proof_verdict="REJECT",
            policy_ok=True,
            mtf_state="ALIGNED",
        )
        == "SKIP"
    )
    assert (
        decide_action(
            signal="BUY",
            proof_verdict="APPROVE",
            policy_ok=True,
            mtf_state="CONFLICT",
        )
        == "WAIT"
    )


def test_conflict_why_is_plain_en_and_ru():
    setup = evaluate_setup(
        last=110,
        sma_fast=105,
        sma_slow=100,
        atr_value=1.0,
        realized_vol_value=0.2,
        side="BUY",
        htf_trend="MIXED",
        htf_source="weekly",
    )
    why = explain_why(setup=setup)
    assert why.action == "WAIT"
    assert why.mtf_state == "CONFLICT"
    blob = " ".join(why.sentences)
    assert "Daily drift is up, but the slower trend still looks mixed — wait." in blob
    assert "sma" not in blob.lower()
    assert "atr" not in blob.lower()

    why_ru = explain_why(setup=setup, lang="ru")
    ru = " ".join(why_ru.sentences)
    assert "подождите" in ru.lower() or "подожд" in ru.lower()
    assert "смешанн" in ru


def test_aligned_why_sentence():
    setup = evaluate_setup(
        last=110,
        sma_fast=105,
        sma_slow=100,
        atr_value=1.0,
        realized_vol_value=0.2,
        side="BUY",
        htf_trend="BULL",
        htf_source="weekly",
    )
    why = explain_why(setup=setup)
    assert why.action in {"ENTER", "WAIT"}
    assert "Daily drift and the slower weekly trend both look up." in why.sentences
    assert why.mtf_state == "ALIGNED"
