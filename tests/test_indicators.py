from safe_desk.indicators import atr, realized_vol, sma, trend_state


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
