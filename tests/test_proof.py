from pathlib import Path

from safe_desk.cli import main
from safe_desk.ohlcv import Bar, load_ohlcv
from safe_desk.proof import (
    decide_verdict,
    forward_return,
    proof_blocks_ticket,
    run_proof,
    window_features,
)

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "examples" / "btc-ohlcv.csv"


def _bars(closes: list[float]) -> list[Bar]:
    return [
        Bar(date=f"d{i}", open=c, high=c, low=c, close=c, volume=1.0)
        for i, c in enumerate(closes)
    ]


def test_window_features_do_not_read_past_end():
    closes = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 100.0]
    feat = window_features(closes, end_idx=5, window=4)
    # Uses closes[1:6] == 11..15 only. The 100 at the end must not appear.
    assert feat[1] == (15.0 / 11.0) - 1.0
    later = window_features(closes, end_idx=6, window=4)
    assert later != feat


def test_forward_return_uses_only_future_close():
    closes = [100.0, 100.0, 100.0, 110.0]
    assert abs(forward_return(closes, end_idx=2, horizon=1) - 0.10) < 1e-12


def test_analogs_never_overlap_query_window_or_use_query_future():
    # Unique spike in the middle so the matcher has something to grab.
    closes = [100.0] * 20 + [101.0, 102.0, 104.0, 107.0, 110.0] + [110.0] * 20
    # Stretch so query is a similar rise at the end.
    closes = closes + [111.0, 112.0, 114.0, 117.0, 120.0]
    report = run_proof(_bars(closes), symbol="TESTUSDT", side="BUY", window=4, horizon=3, k=5)
    query_end = len(closes) - 1
    for analog in report.analogs:
        assert analog.end_index + 3 <= query_end
        assert analog.end_index <= query_end - 4
        # Feature window of analog does not include query bars.
        assert analog.end_index < query_end - 3


def test_decide_verdict_thresholds():
    v, _ = decide_verdict(side="BUY", n_analogs=8, median_forward=0.01, hit_rate=0.62)
    assert v == "APPROVE"
    v, _ = decide_verdict(side="BUY", n_analogs=8, median_forward=-0.02, hit_rate=0.25)
    assert v == "REJECT"
    v, _ = decide_verdict(side="BUY", n_analogs=2, median_forward=0.05, hit_rate=1.0)
    assert v == "WAIT"
    v, _ = decide_verdict(side="SELL", n_analogs=8, median_forward=-0.01, hit_rate=0.60)
    assert v == "APPROVE"


def test_proof_blocks_live_wait_but_warns_dry_run():
    from safe_desk.proof import AnalogMatch, ProofReport

    wait = ProofReport(
        symbol="BTCUSDT",
        side="BUY",
        verdict="WAIT",
        rationale="mixed",
        n_analogs=8,
        k=8,
        window=10,
        horizon=5,
        median_forward_return=0.0,
        hit_rate=0.5,
        query_features=(),
        analogs=(
            AnalogMatch(end_index=1, end_date="x", distance=0.1, forward_return=0.0, hit=False),
        ),
        receipt_hash="abc",
    )
    blocked, note = proof_blocks_ticket(wait, mode="live", require_proof=False)
    assert blocked is True
    blocked, note = proof_blocks_ticket(wait, mode="dry-run", require_proof=False)
    assert blocked is False
    assert note is not None and note.startswith("WARNING")

    reject = ProofReport(
        symbol="BTCUSDT",
        side="BUY",
        verdict="REJECT",
        rationale="against",
        n_analogs=8,
        k=8,
        window=10,
        horizon=5,
        median_forward_return=-0.02,
        hit_rate=0.2,
        query_features=(),
        analogs=(),
        receipt_hash="def",
    )
    blocked, _ = proof_blocks_ticket(reject, mode="dry-run", require_proof=True)
    assert blocked is True
    blocked, note = proof_blocks_ticket(reject, mode="dry-run", require_proof=False)
    assert blocked is False
    assert note is not None and "WARNING" in note


def test_sample_csv_proof_is_deterministic():
    bars = load_ohlcv(CSV)
    a = run_proof(bars, symbol="BTCUSDT", side="BUY")
    b = run_proof(bars, symbol="BTCUSDT", side="BUY")
    assert a.receipt_hash == b.receipt_hash
    assert a.verdict == b.verdict
    assert a.leakage_safe is True
    assert a.n_analogs == 8
    assert a.verdict == "APPROVE"
    assert a.hit_rate == 1.0
    assert a.receipt_hash == "05b628112ce384a6"


def test_cli_proof_sample(capsys):
    rc = main(["proof", str(CSV), "--symbol", "BTCUSDT", "--side", "BUY"])
    out = capsys.readouterr().out
    assert rc in {0, 2}
    assert "Proof gate" in out
    assert "BTCUSDT" in out
    assert "Receipt" in out
    assert "Leakage-safe" in out
