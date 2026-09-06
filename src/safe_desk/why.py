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
) -> Action:
    if policy_ok is False:
        return "SKIP"
    if signal == "AVOID" or proof_verdict == "REJECT":
        return "SKIP"
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
    proof_verdict = _proof_verdict(proof)
    policy_ok, policy_reason = _policy_view(policy)
    action = decide_action(signal=signal, proof_verdict=proof_verdict, policy_ok=policy_ok)

    sentences: list[str] = []
    if setup is not None:
        sentences.append(_trend_sentence(setup.trend, language))
        if setup.vol_regime in {"HIGH", "UNKNOWN"} or action == "SKIP":
            sentences.append(_vol_sentence(setup.vol_regime, language))
    sentences.append(_action_sentence(action, proof_verdict, language))

    if policy_ok is False:
        sentences.append(t(language, "why_policy_fail", reason=policy_reason or "blocked"))
    elif size is not None:
        sentences.append(
            t(
                language,
                "why_size",
                risk=size.risk_pct,
                equity=_money(size.equity),
                qty=_qty(size.quantity),
                asset=base_asset(symbol),
                worth=_money(size.notional),
            )
        )
    elif action != "SKIP":
        sentences.append(t(language, "why_size_none"))

    # Keep 2–4 sentences. Drop the optional vol line if we overflow.
    if len(sentences) > 4:
        sentences = [sentences[0], sentences[2], sentences[3]]
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
