from safe_desk.indicators import (
    atr,
    realized_vol,
    rsi,
    rsi_last,
    rsi_state,
    sma,
    trend_state,
    volume_flag,
    volume_ratio,
)


def test_sma_warm_and_last():
    values = [1, 2, 3, 4, 5]
    series = sma(values, 3)
    assert series[:2] == [None, None]
    assert series[2] == 2.0
    assert series[4] == 4.0


def test_atr_known_window():
    # Flat then one expansion bar.
    highs = [10, 10, 10, 10, 12]
    lows = [9, 9, 9, 9, 9]
    closes = [9.5, 9.5, 9.5, 9.5, 11]
    value = atr(highs, lows, closes, period=3)
    assert value is not None
    assert value > 1.0


def test_atr_insufficient():
    assert atr([1, 2], [0.5, 1], [1, 2], period=14) is None


def test_realized_vol_none_on_short_series():
    assert realized_vol([1, 2, 3], period=20) is None


def test_trend_states():
    assert trend_state(110, 105, 100) == "BULL"
    assert trend_state(90, 95, 100) == "BEAR"
    assert trend_state(102, 100, 105) == "MIXED"
    assert trend_state(100, None, 90) == "MIXED"


def test_rsi_all_up_is_100():
    closes = list(range(1, 17))
    value = rsi_last(closes, period=14)
    assert value == 100.0
    series = rsi(closes, period=14)
    assert series[:14] == [None] * 14
    assert series[14] == 100.0


def test_rsi_all_down_is_0():
    closes = list(range(20, 4, -1))
    assert rsi_last(closes, period=14) == 0.0


def test_rsi_insufficient_and_flat():
    assert rsi_last([1, 2, 3], period=14) is None
    flat = [10.0] * 20
    assert rsi_last(flat, period=14) == 50.0


def test_rsi_known_wilder_seed():
    # 15 closes → first RSI after 14 changes. Gains 13×1, one loss of 2.
    closes = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 21]
    value = rsi_last(closes, period=14)
    avg_gain = 13.0 / 14.0
    avg_loss = 2.0 / 14.0
    expected = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    assert value is not None
    assert abs(value - expected) < 1e-9


def test_rsi_state_bands():
    assert rsi_state(None) == "UNKNOWN"
    assert rsi_state(70) == "OVERBOUGHT"
    assert rsi_state(30) == "OVERSOLD"
    assert rsi_state(50) == "NEUTRAL"


def test_volume_ratio_and_flags():
    spike = [10] * 20 + [40]
    quiet = [10] * 20 + [3]
    normal = [10] * 20 + [11]
    assert volume_ratio(spike, 20) == 4.0
    assert volume_ratio(quiet, 20) == 0.3
    assert abs(volume_ratio(normal, 20) - 1.1) < 1e-9
    assert volume_flag(4.0) == "SPIKE"
    assert volume_flag(0.3) == "QUIET"
    assert volume_flag(1.1) == "NORMAL"
    assert volume_flag(None) == "UNKNOWN"
    assert volume_ratio([1, 2, 3], 20) is None
    assert volume_ratio([0] * 20 + [5], 20) is None
