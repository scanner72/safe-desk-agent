"""ATR SL / TP1 / TP2 math. Distances must be exact multiples of ATR."""

import pytest

from safe_desk.indicators import atr
from safe_desk.levels import (
    DEFAULT_K_SL,
    DEFAULT_K_TP1,
    DEFAULT_K_TP2,
    AtrMultipliers,
    atr_levels,
    levels_from_bars,
    parse_multipliers,
    refresh_atr_levels,
    try_atr_levels,
)
from safe_desk.ohlcv import load_ohlcv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "examples" / "btc-ohlcv.csv"


def test_default_multipliers_in_suggested_bands():
    assert 1.0 <= DEFAULT_K_SL <= 1.5
    assert 1.0 <= DEFAULT_K_TP1 <= 1.5
    assert 2.0 <= DEFAULT_K_TP2 <= 3.0
    assert DEFAULT_K_SL == 1.2
    assert DEFAULT_K_TP1 == 1.5
    assert DEFAULT_K_TP2 == 2.5


def test_buy_distances_are_k_times_atr():
    entry, atr_value = 100_000.0, 1_000.0
    levels = atr_levels(entry, atr_value, "BUY")
    assert levels.sl == pytest.approx(entry - DEFAULT_K_SL * atr_value)
    assert levels.tp1 == pytest.approx(entry + DEFAULT_K_TP1 * atr_value)
    assert levels.tp2 == pytest.approx(entry + DEFAULT_K_TP2 * atr_value)
    assert levels.sl_distance == pytest.approx(DEFAULT_K_SL * atr_value)
    assert levels.tp1_distance == pytest.approx(DEFAULT_K_TP1 * atr_value)
    assert levels.tp2_distance == pytest.approx(DEFAULT_K_TP2 * atr_value)
    assert levels.sl < entry < levels.tp1 < levels.tp2


def test_sell_distances_are_k_times_atr():
    entry, atr_value = 100_000.0, 1_000.0
    levels = atr_levels(entry, atr_value, "SELL")
    assert levels.sl == pytest.approx(entry + DEFAULT_K_SL * atr_value)
    assert levels.tp1 == pytest.approx(entry - DEFAULT_K_TP1 * atr_value)
    assert levels.tp2 == pytest.approx(entry - DEFAULT_K_TP2 * atr_value)
    assert levels.sl_distance == pytest.approx(DEFAULT_K_SL * atr_value)
    assert levels.tp1_distance == pytest.approx(DEFAULT_K_TP1 * atr_value)
    assert levels.tp2_distance == pytest.approx(DEFAULT_K_TP2 * atr_value)
    assert levels.tp2 < levels.tp1 < entry < levels.sl


def test_custom_multipliers():
    mult = AtrMultipliers(k_sl=1.0, k_tp1=1.0, k_tp2=3.0)
    levels = atr_levels(50.0, 2.0, "BUY", mult)
    assert levels.sl == pytest.approx(48.0)
    assert levels.tp1 == pytest.approx(52.0)
    assert levels.tp2 == pytest.approx(56.0)


def test_trail_refresh_uses_latest_atr():
    first = atr_levels(100.0, 2.0, "BUY")
    later = refresh_atr_levels(100.0, 3.0, "BUY")
    assert later.trail is True
    assert later.sl_distance == pytest.approx(DEFAULT_K_SL * 3.0)
    assert later.sl_distance > first.sl_distance
    assert later.tp1 == pytest.approx(100.0 + DEFAULT_K_TP1 * 3.0)
    assert later.tp2 == pytest.approx(100.0 + DEFAULT_K_TP2 * 3.0)


def test_reject_non_positive_multipliers():
    with pytest.raises(ValueError, match="k_sl"):
        AtrMultipliers(k_sl=0)
    with pytest.raises(ValueError, match="k_tp2"):
        parse_multipliers(k_tp2=-1)


def test_try_atr_levels_none_when_cold():
    assert try_atr_levels(100.0, None) is None
    assert try_atr_levels(100.0, 0.0) is None


def test_sample_csv_levels_match_atr14():
    bars = load_ohlcv(CSV)
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    closes = [b.close for b in bars]
    atr14 = atr(highs, lows, closes, 14)
    assert atr14 is not None
    levels = levels_from_bars(highs, lows, closes, "BUY")
    assert levels is not None
    last = closes[-1]
    assert last == pytest.approx(102450.0)
    assert levels.sl == pytest.approx(last - DEFAULT_K_SL * atr14)
    assert levels.tp1 == pytest.approx(last + DEFAULT_K_TP1 * atr14)
    assert levels.tp2 == pytest.approx(last + DEFAULT_K_TP2 * atr14)
    assert levels.trail is True
