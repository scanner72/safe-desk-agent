"""Plain-language 'why enter / wait / skip' for a non-trader.

Turns indicators + optional proof + policy + size into 2–4 short sentences.
No SMA/ATR jargon. A BUY/ENTER label is never an order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from safe_desk.i18n import Lang, norm_lang, t
from safe_desk.policy import PolicyResult
from safe_desk.position_sizing import SizeResult
from safe_desk.proof import ProofReport
from safe_desk.risk import SetupReport

Action = Literal["ENTER", "WAIT", "SKIP"]


@dataclass(frozen=True)
class WhyEntry:
    action: Action
    headline: str
    sentences: tuple[str, ...]
    risk_score: int | None
    signal: str | None
    proof_verdict: str | None
    policy_ok: bool | None
    lang: Lang = "en"
    mtf_state: str | None = None
    htf_trend: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "headline": self.headline,
            "sentences": list(self.sentences),
            "risk_score": self.risk_score,
            "signal": self.signal,
            "proof_verdict": self.proof_verdict,
            "policy_ok": self.policy_ok,
            "lang": self.lang,
            "mtf_state": self.mtf_state,
            "htf_trend": self.htf_trend,
        }

    def render(self) -> str:
        lines = [self.headline, *[f"  - {s}" for s in self.sentences]]
        return "\n".join(lines)


def base_asset(symbol: str | None) -> str:
    if not symbol:
        return "coin"
    upper = symbol.upper()
    for quote in ("USDT", "FDUSD", "USDC", "BUSD"):
        if upper.endswith(quote) and len(upper) > len(quote):
            return upper[: -len(quote)]
    return upper


def decide_action(
    *,
    signal: str | None,
    proof_verdict: str | None,
    policy_ok: bool | None,
    mtf_state: str | None = None,
) -> Action:
    if policy_ok is False:
        return "SKIP"
    if signal == "AVOID" or proof_verdict == "REJECT":
        return "SKIP"
    if mtf_state == "CONFLICT":
        return "WAIT"
    if signal == "HOLD" or proof_verdict == "WAIT":
        return "WAIT"
    if signal == "BUY" and proof_verdict in {None, "APPROVE"}:
        return "ENTER"
    if signal == "SELL":
        return "WAIT"
    return "WAIT"


def explain_why(
    *,
    setup: SetupReport | None = None,
    proof: ProofReport | dict[str, Any] | None = None,
    policy: PolicyResult | dict[str, Any] | None = None,
    size: SizeResult | None = None,
    symbol: str | None = None,
    lang: Lang | str = "en",
) -> WhyEntry:
    """Build 2–4 plain sentences a regular exchange user can read."""
    language = norm_lang(lang if isinstance(lang, str) else lang)
    signal = None if setup is None else setup.signal
    score = None if setup is None else setup.risk_score
    mtf_state = None if setup is None else setup.mtf_state
    htf_trend = None if setup is None else setup.htf_trend
    proof_verdict = _proof_verdict(proof)
    policy_ok, policy_reason = _policy_view(policy)
    action = decide_action(
        signal=signal,
        proof_verdict=proof_verdict,
        policy_ok=policy_ok,
        mtf_state=mtf_state,
    )

    head: list[str] = []
    if setup is not None:
        mtf_line = _mtf_sentence(setup, language)
        head.append(mtf_line or _trend_sentence(setup.trend, language))
    texture = _rsi_volume_sentence(setup, language) if setup is not None else None
    atr_line = None
    if setup is not None and (setup.vol_regime in {"HIGH", "UNKNOWN"} or action == "SKIP"):
        atr_line = _vol_sentence(setup.vol_regime, language)
    action_line = _action_sentence(action, proof_verdict, language)

    if policy_ok is False:
        tail = t(language, "why_policy_fail", reason=policy_reason or "blocked")
    elif size is not None:
        tail = t(
            language,
            "why_size",
            risk=size.risk_pct,
            equity=_money(size.equity),
            qty=_qty(size.quantity),
            asset=base_asset(symbol),
            worth=_money(size.notional),
        )
    elif action != "SKIP":
        tail = t(language, "why_size_none")
    else:
        tail = None

    extras = [line for line in (texture, atr_line) if line]
    sentences = [*head, *extras, action_line, *([tail] if tail else [])]
    # Keep 2–4 sentences. Prefer RSI/volume context over the ATR swing line.
    if len(sentences) > 4:
        extras = [line for line in (texture,) if line]
        sentences = [*head, *extras, action_line, *([tail] if tail else [])]
    if len(sentences) > 4:
        sentences = sentences[:4]
    if len(sentences) < 2:
        sentences.append(t(language, "why_not_order"))

    headline = t(language, f"why_headline_{action.lower()}")
    return WhyEntry(
        action=action,
        headline=headline,
        sentences=tuple(sentences[:4]),
        risk_score=score,
        signal=signal,
        proof_verdict=proof_verdict,
        policy_ok=policy_ok,
        lang=language,
        mtf_state=mtf_state,
        htf_trend=htf_trend,
    )


def _proof_verdict(proof: ProofReport | dict[str, Any] | None) -> str | None:
    if proof is None:
        return None
    if isinstance(proof, dict):
        raw = proof.get("verdict")
        return str(raw).upper() if raw else None
    return proof.verdict


def _policy_view(policy: PolicyResult | dict[str, Any] | None) -> tuple[bool | None, str | None]:
    if policy is None:
        return None, None
    if isinstance(policy, dict):
        ok = policy.get("ok")
        violations = policy.get("violations") or []
        if violations and isinstance(violations[0], dict):
            reason = str(violations[0].get("message") or violations[0].get("code") or "blocked")
        elif violations:
            reason = str(violations[0])
        else:
            reason = None
        return (None if ok is None else bool(ok)), reason
    reason = None
    if policy.violations:
        reason = policy.violations[0].message
    return policy.ok, reason


def _rsi_volume_sentence(setup: SetupReport, lang: Lang) -> str | None:
    """One plain sentence when RSI is stretched or volume is loud/quiet."""
    rsi = setup.rsi_state
    vol = setup.volume_flag
    key = {
        ("OVERBOUGHT", "SPIKE"): "why_rsi_overbought_spike",
        ("OVERBOUGHT", "QUIET"): "why_rsi_overbought_quiet",
        ("OVERSOLD", "SPIKE"): "why_rsi_oversold_spike",
        ("OVERSOLD", "QUIET"): "why_rsi_oversold_quiet",
    }.get((rsi, vol))
    if key is None and rsi == "OVERBOUGHT":
        key = "why_rsi_overbought"
    elif key is None and rsi == "OVERSOLD":
        key = "why_rsi_oversold"
    elif key is None and vol == "SPIKE":
        key = "why_volume_spike"
    elif key is None and vol == "QUIET":
        key = "why_volume_quiet"
    if key is None:
        return None
    return t(lang, key)


def _mtf_sentence(setup: SetupReport, lang: Lang) -> str | None:
    """One plain sentence when daily and the slower trend agree or fight."""
    state = setup.mtf_state
    if state == "ALIGNED":
        if setup.trend == "BULL":
            return t(lang, "why_mtf_aligned_up")
        if setup.trend == "BEAR":
            return t(lang, "why_mtf_aligned_down")
        return t(lang, "why_mtf_aligned_mixed")
    if state != "CONFLICT":
        return None
    key = {
        ("BULL", "MIXED"): "why_mtf_conflict_up_mixed",
        ("BULL", "BEAR"): "why_mtf_conflict_up_down",
        ("BEAR", "MIXED"): "why_mtf_conflict_down_mixed",
        ("BEAR", "BULL"): "why_mtf_conflict_down_up",
        ("MIXED", "BULL"): "why_mtf_conflict_mixed_up",
        ("MIXED", "BEAR"): "why_mtf_conflict_mixed_down",
    }.get((setup.trend, setup.htf_trend), "why_mtf_conflict_up_mixed")
    return t(lang, key)


def _trend_sentence(trend: str, lang: Lang) -> str:
    key = {
        "BULL": "why_trend_bull",
        "BEAR": "why_trend_bear",
    }.get(trend, "why_trend_mixed")
    return t(lang, key)


def _vol_sentence(regime: str, lang: Lang) -> str:
    key = {
        "LOW": "why_vol_low",
        "NORMAL": "why_vol_normal",
        "HIGH": "why_vol_high",
    }.get(regime, "why_vol_unknown")
    return t(lang, key)


def _action_sentence(action: Action, proof_verdict: str | None, lang: Lang) -> str:
    if action == "ENTER":
        if proof_verdict == "APPROVE":
            return t(lang, "why_enter_proof_ok")
        return t(lang, "why_enter")
    if action == "SKIP":
        if proof_verdict == "REJECT":
            return t(lang, "why_skip_proof")
        return t(lang, "why_skip")
    if proof_verdict == "WAIT":
        return t(lang, "why_wait_proof")
    return t(lang, "why_wait")


def _money(value: float) -> str:
    if abs(value) >= 1000:
        return f"{value:,.2f}"
    if abs(value) >= 1:
        return f"{value:,.2f}"
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _qty(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
