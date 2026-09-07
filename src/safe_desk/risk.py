"""Setup quality / danger score. Higher = more dangerous or lower quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from safe_desk.i18n import Lang, t
from safe_desk.indicators import atr_pct, rsi_state, trend_state, volume_flag

Side = Literal["BUY", "SELL"]
Signal = Literal["BUY", "HOLD", "AVOID"]
VolRegime = Literal["LOW", "NORMAL", "HIGH", "UNKNOWN"]
RsiState = Literal["OVERBOUGHT", "OVERSOLD", "NEUTRAL", "UNKNOWN"]
VolumeFlag = Literal["SPIKE", "QUIET", "NORMAL", "UNKNOWN"]


@dataclass(frozen=True)
class SetupReport:
    last: float
    sma_fast: float | None
    sma_slow: float | None
    atr: float | None
    atr_pct: float | None
    realized_vol: float | None
    trend: str
    vol_regime: VolRegime
    risk_score: int
    signal: Signal
    reasons: tuple[str, ...]
    rsi: float | None = None
    rsi_state: RsiState = "UNKNOWN"
    volume_ratio: float | None = None
    volume_flag: VolumeFlag = "UNKNOWN"


def vol_regime(atr_percent: float | None) -> VolRegime:
    if atr_percent is None:
        return "UNKNOWN"
    if atr_percent < 1.5:
        return "LOW"
    if atr_percent < 3.5:
        return "NORMAL"
    return "HIGH"


def risk_score(
    *,
    trend: str,
    side: Side,
    atr_percent: float | None,
    stop_distance: float | None,
    atr_value: float | None,
    rsi_value: float | None = None,
    volume_ratio: float | None = None,
    lang: Lang = "en",
) -> tuple[int, list[str]]:
    """0–100 danger / quality score. 100 = do not touch.

    RSI and volume are context: they can nudge the score and reasons, but
    they do not create a BUY and do not flip SMA/ATR trend or vol regime.
    """
    score = 30
    reasons: list[str] = []

    aligned = (side == "BUY" and trend == "BULL") or (
        side == "SELL" and trend == "BEAR"
    )
    if trend == "MIXED":
        score += 20
        reasons.append(t(lang, "mixed_trend"))
    elif aligned:
        score -= 10
        reasons.append(t(lang, "aligned", trend=trend, side=side))
    else:
        score += 18
        reasons.append(t(lang, "fights", trend=trend, side=side))

    regime = vol_regime(atr_percent)
    if regime == "HIGH":
        score += 25
        reasons.append(t(lang, "vol_high", atr=atr_percent))
    elif regime == "NORMAL":
        score += 8
        reasons.append(t(lang, "vol_normal", atr=atr_percent))
    elif regime == "LOW":
        reasons.append(t(lang, "vol_low", atr=atr_percent))
    else:
        score += 10
        reasons.append(t(lang, "vol_unknown"))

    rstate = rsi_state(rsi_value)
    if rstate == "OVERBOUGHT":
        score += 6
        reasons.append(t(lang, "rsi_overbought", rsi=rsi_value))
    elif rstate == "OVERSOLD":
        score += 4
        reasons.append(t(lang, "rsi_oversold", rsi=rsi_value))

    vflag = volume_flag(volume_ratio)
    if vflag == "SPIKE":
        score += 5
        reasons.append(t(lang, "volume_spike", ratio=volume_ratio))
    elif vflag == "QUIET":
        score += 3
        reasons.append(t(lang, "volume_quiet", ratio=volume_ratio))

    if (
        stop_distance is not None
        and atr_value is not None
        and atr_value > 0
        and stop_distance > 0
    ):
        multiple = stop_distance / atr_value
        if multiple < 0.4:
            score += 15
            reasons.append(t(lang, "stop_vs_atr_tight", multiple=multiple))
        elif multiple > 3.0:
            score += 10
            reasons.append(t(lang, "stop_vs_atr_wide", multiple=multiple))
        else:
            reasons.append(t(lang, "stop_vs_atr_ok", multiple=multiple))

    score = max(0, min(100, score))
    return score, reasons


def decide_signal(trend: str, regime: VolRegime, score: int, side: Side) -> Signal:
    if score >= 70 or regime == "HIGH":
        return "AVOID"
    if side == "BUY" and trend == "BULL" and score < 60:
        return "BUY"
    return "HOLD"


def evaluate_setup(
    *,
    last: float,
    sma_fast: float | None,
    sma_slow: float | None,
    atr_value: float | None,
    realized_vol_value: float | None,
    side: Side = "BUY",
    stop: float | None = None,
    rsi_value: float | None = None,
    volume_ratio: float | None = None,
    lang: Lang = "en",
) -> SetupReport:
    trend = trend_state(last, sma_fast, sma_slow)
    pct = atr_pct(atr_value, last)
    regime = vol_regime(pct)
    stop_distance = abs(last - stop) if stop is not None else None
    rstate: RsiState = rsi_state(rsi_value)  # type: ignore[assignment]
    vflag: VolumeFlag = volume_flag(volume_ratio)  # type: ignore[assignment]
    score, reasons = risk_score(
        trend=trend,
        side=side,
        atr_percent=pct,
        stop_distance=stop_distance,
        atr_value=atr_value,
        rsi_value=rsi_value,
        volume_ratio=volume_ratio,
        lang=lang,
    )
    # Signal stays SMA/ATR/score based. RSI and volume do not force BUY/SELL.
    signal = decide_signal(trend, regime, score, side)
    if signal == "BUY":
        reasons.append(t(lang, "sig_buy"))
    elif signal == "AVOID":
        reasons.append(t(lang, "sig_avoid"))
    else:
        reasons.append(t(lang, "sig_hold"))
    return SetupReport(
        last=last,
        sma_fast=sma_fast,
        sma_slow=sma_slow,
        atr=atr_value,
        atr_pct=pct,
        realized_vol=realized_vol_value,
        trend=trend,
        vol_regime=regime,
        risk_score=score,
        signal=signal,
        reasons=tuple(reasons),
        rsi=rsi_value,
        rsi_state=rstate,
        volume_ratio=volume_ratio,
        volume_flag=vflag,
    )
