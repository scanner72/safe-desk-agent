import pytest

from safe_desk.position_sizing import size_spot


def test_one_percent_risk():
    sized = size_spot(equity=10_000, entry=100, stop=99, risk_pct=1.0)
    assert sized.risk_quote == 100
    assert sized.quantity == pytest.approx(100)
    assert sized.notional == pytest.approx(10_000)
    assert sized.clamped_to_equity is False


def test_caps_risk_pct_at_one():
    sized = size_spot(equity=1_000, entry=50, stop=49, risk_pct=5.0)
    assert sized.risk_pct == 1.0
    assert any("exceeds desk max" in n for n in sized.notes)


def test_clamps_notional_to_equity():
    # 1% of 100 = 1 quote risk, stop 0.01 → qty 100, notional 10_000 > equity.
    sized = size_spot(equity=100, entry=100, stop=99.99, risk_pct=1.0)
    assert sized.clamped_to_equity is True
    assert sized.notional == pytest.approx(100)
    assert sized.quantity == pytest.approx(1.0)


def test_rejects_equal_stop():
    with pytest.raises(ValueError):
        size_spot(100, 10, 10, 1.0)
