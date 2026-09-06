"""Leakage-safe analog / proof gate run *before* a ticket is proposed.

Inspired by proof-before-trade, not a copy: find similar *past* windows by
returns and realized-vol features, then summarize the *already-known* forward
return of those analogs for the proposed side.

The query window (the most recent bars) never contributes a forward return —
that would be look-ahead. Analog features use only closes at or before the
analog end index.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Literal, Sequence

from safe_desk.ohlcv import Bar

Side = Literal["BUY", "SELL"]
Verdict = Literal["APPROVE", "WAIT", "REJECT"]

DEFAULT_WINDOW = 10
DEFAULT_HORIZON = 5
DEFAULT_K = 8
MIN_ANALOGS = 5


@dataclass(frozen=True)
class AnalogMatch:
    end_index: int
    end_date: str
    distance: float
    forward_return: float
    hit: bool


@dataclass(frozen=True)
class ProofReport:
    symbol: str
    side: Side
    verdict: Verdict
    rationale: str
    n_analogs: int
    k: int
    window: int
    horizon: int
    median_forward_return: float | None
    hit_rate: float | None
    query_features: tuple[float, ...]
    analogs: tuple[AnalogMatch, ...]
    receipt_hash: str
    leakage_safe: bool = True

    def to_dict(self) -> dict:
        data = asdict(self)
        data["analogs"] = [asdict(a) for a in self.analogs]
        data["query_features"] = list(self.query_features)
        return data

    def summary_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "n_analogs": self.n_analogs,
            "median_forward_return": self.median_forward_return,
            "hit_rate": self.hit_rate,
            "receipt_hash": self.receipt_hash,
            "rationale": self.rationale,
        }


def window_features(closes: Sequence[float], end_idx: int, window: int) -> tuple[float, ...]:
    """Returns / vol features using only closes[0 : end_idx + 1]."""
    if end_idx < window:
        raise ValueError("end_idx must be >= window for a full feature window")
    # Need `window` returns → `window + 1` closes ending at end_idx.
    start = end_idx - window
    if start < 0:
        raise ValueError("not enough history for feature window")
    slice_ = [float(c) for c in closes[start : end_idx + 1]]
    if any(p <= 0 for p in slice_):
        raise ValueError("closes must be positive")
    rets = [(slice_[i] / slice_[i - 1]) - 1.0 for i in range(1, len(slice_))]
    ret_fast = (slice_[-1] / slice_[max(0, len(slice_) - 6)]) - 1.0 if len(slice_) > 5 else rets[-1]
    ret_slow = (slice_[-1] / slice_[0]) - 1.0
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / max(1, len(rets) - 1)
    vol = math.sqrt(var)
    return (ret_fast, ret_slow, vol)


def forward_return(closes: Sequence[float], end_idx: int, horizon: int) -> float:
    """Close-to-close return over `horizon` bars *after* end_idx. No feature use."""
    future_idx = end_idx + horizon
    if future_idx >= len(closes):
        raise ValueError("not enough forward bars")
    now = float(closes[end_idx])
    later = float(closes[future_idx])
    if now <= 0:
        raise ValueError("close must be positive")
    return (later / now) - 1.0


def _zscore_rows(rows: list[tuple[float, ...]]) -> list[tuple[float, ...]]:
    if not rows:
        return []
    dim = len(rows[0])
    means: list[float] = []
    stds: list[float] = []
    for j in range(dim):
        col = [r[j] for r in rows]
        mu = sum(col) / len(col)
        var = sum((x - mu) ** 2 for x in col) / max(1, len(col) - 1)
        sd = math.sqrt(var) if var > 0 else 1.0
        means.append(mu)
        stds.append(sd)
    return [tuple((r[j] - means[j]) / stds[j] for j in range(dim)) for r in rows]


def _euclid(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _median(values: Sequence[float]) -> float:
    xs = sorted(values)
    n = len(xs)
    if n == 0:
        raise ValueError("median of empty list")
    mid = n // 2
    if n % 2:
        return xs[mid]
    return 0.5 * (xs[mid - 1] + xs[mid])


def decide_verdict(
    *,
    side: Side,
    n_analogs: int,
    median_forward: float | None,
    hit_rate: float | None,
    min_analogs: int = MIN_ANALOGS,
) -> tuple[Verdict, str]:
    if n_analogs < min_analogs or median_forward is None or hit_rate is None:
        return (
            "WAIT",
            f"Only {n_analogs} leakage-safe analog(s); need {min_analogs}. Not enough history to approve.",
        )

    against = (side == "BUY" and median_forward < 0) or (side == "SELL" and median_forward > 0)
    with_side = not against and median_forward != 0

    if hit_rate < 0.40 and against:
        return (
            "REJECT",
            f"Analogs oppose {side}: hit rate {hit_rate:.0%}, median forward {median_forward:+.2%}.",
        )
    if hit_rate >= 0.55 and with_side:
        return (
            "APPROVE",
            f"Analogs lean {side}: hit rate {hit_rate:.0%}, median forward {median_forward:+.2%}. Setup only — not an order.",
        )
    return (
        "WAIT",
        f"Mixed analog tape for {side}: hit rate {hit_rate:.0%}, median forward {median_forward:+.2%}. Wait for a cleaner window.",
    )


def run_proof(
    bars: Sequence[Bar],
    *,
    symbol: str,
    side: Side,
    window: int = DEFAULT_WINDOW,
    horizon: int = DEFAULT_HORIZON,
    k: int = DEFAULT_K,
    min_analogs: int = MIN_ANALOGS,
) -> ProofReport:
    if window < 3:
        raise ValueError("window must be >= 3")
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    if k < 1:
        raise ValueError("k must be >= 1")
    if side not in {"BUY", "SELL"}:
        raise ValueError("side must be BUY or SELL")

    closes = [b.close for b in bars]
    n = len(closes)
    query_end = n - 1
    if query_end < window:
        verdict, rationale = decide_verdict(side=side, n_analogs=0, median_forward=None, hit_rate=None, min_analogs=min_analogs)
        return _finish(
            symbol=symbol,
            side=side,
            verdict=verdict,
            rationale=rationale,
            window=window,
            horizon=horizon,
            k=k,
            query_features=(),
            analogs=(),
            median=None,
            hit_rate=None,
        )

    query_feat = window_features(closes, query_end, window)

    # Analogs must: (1) have a full feature window, (2) have `horizon` future
    # bars already in the file, (3) not overlap the query feature window.
    last_overlap_free = query_end - window
    last_with_forward = n - 1 - horizon
    max_end = min(last_overlap_free, last_with_forward)

    candidates: list[tuple[int, tuple[float, ...]]] = []
    for end in range(window, max_end + 1):
        try:
            feat = window_features(closes, end, window)
        except ValueError:
            continue
        candidates.append((end, feat))

    if not candidates:
        verdict, rationale = decide_verdict(side=side, n_analogs=0, median_forward=None, hit_rate=None, min_analogs=min_analogs)
        return _finish(
            symbol=symbol,
            side=side,
            verdict=verdict,
            rationale=rationale,
            window=window,
            horizon=horizon,
            k=k,
            query_features=query_feat,
            analogs=(),
            median=None,
            hit_rate=None,
        )

    feature_rows = [feat for _, feat in candidates] + [query_feat]
    z_rows = _zscore_rows(feature_rows)
    z_query = z_rows[-1]
    scored: list[tuple[float, int, tuple[float, ...]]] = []
    for (end, feat), z in zip(candidates, z_rows[:-1]):
        scored.append((_euclid(z, z_query), end, feat))
    scored.sort(key=lambda row: (row[0], row[1]))
    picked = scored[:k]

    matches: list[AnalogMatch] = []
    for dist, end, _feat in picked:
        fwd = forward_return(closes, end, horizon)
        if side == "BUY":
            hit = fwd > 0
        else:
            hit = fwd < 0
        date = bars[end].date
        matches.append(
            AnalogMatch(
                end_index=end,
                end_date=date,
                distance=dist,
                forward_return=fwd,
                hit=hit,
            )
        )

    fwds = [m.forward_return for m in matches]
    median = _median(fwds) if fwds else None
    hit_rate = (sum(1 for m in matches if m.hit) / len(matches)) if matches else None
    verdict, rationale = decide_verdict(
        side=side,
        n_analogs=len(matches),
        median_forward=median,
        hit_rate=hit_rate,
        min_analogs=min_analogs,
    )
    return _finish(
        symbol=symbol,
        side=side,
        verdict=verdict,
        rationale=rationale,
        window=window,
        horizon=horizon,
        k=k,
        query_features=query_feat,
        analogs=tuple(matches),
        median=median,
        hit_rate=hit_rate,
    )


def _finish(
    *,
    symbol: str,
    side: Side,
    verdict: Verdict,
    rationale: str,
    window: int,
    horizon: int,
    k: int,
    query_features: tuple[float, ...],
    analogs: tuple[AnalogMatch, ...],
    median: float | None,
    hit_rate: float | None,
) -> ProofReport:
    core = {
        "symbol": symbol.upper(),
        "side": side,
        "verdict": verdict,
        "window": window,
        "horizon": horizon,
        "k": k,
        "n_analogs": len(analogs),
        "median_forward_return": None if median is None else round(median, 10),
        "hit_rate": None if hit_rate is None else round(hit_rate, 10),
        "analog_ends": [a.end_index for a in analogs],
        "query_features": [round(x, 10) for x in query_features],
    }
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return ProofReport(
        symbol=symbol.upper(),
        side=side,
        verdict=verdict,
        rationale=rationale,
        n_analogs=len(analogs),
        k=k,
        window=window,
        horizon=horizon,
        median_forward_return=median,
        hit_rate=hit_rate,
        query_features=query_features,
        analogs=analogs,
        receipt_hash=digest,
        leakage_safe=True,
    )


def proof_blocks_ticket(
    report: ProofReport | None,
    *,
    mode: str,
    require_proof: bool,
) -> tuple[bool, str | None]:
    """Return (blocked, warning_or_reason).

    - REJECT + `--require-proof` → always block.
    - WAIT (and REJECT without the flag) → block *live*; dry-run may draft with WARNING.
    - APPROVE → never block.
    """
    if report is None:
        if require_proof:
            return True, "require-proof is set but no proof report was produced"
        return False, None
    if report.verdict == "APPROVE":
        return False, None
    if report.verdict == "REJECT" and require_proof:
        return True, f"Proof REJECT ({report.receipt_hash}): {report.rationale}"
    if mode == "live" and report.verdict in {"WAIT", "REJECT"}:
        return True, f"Proof {report.verdict} blocks live tickets: {report.rationale}"
    if report.verdict in {"WAIT", "REJECT"}:
        return False, f"WARNING: proof {report.verdict} ({report.receipt_hash}). Dry-run may still draft. {report.rationale}"
    return False, None
