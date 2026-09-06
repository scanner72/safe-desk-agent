"""AfriAgent-style desk policy. Pure checks — no MCP, no secrets.

Hard rules that cannot be relaxed by a config file:

- withdrawals / transfer-out / main→Agentic pull always refuse
- max risk percent never above 1%
- emergency_stop blocks every place-path ticket

File-based knobs (allowlist, notional, daily caps) sit on top.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Sequence

from safe_desk.yaml_lite import load_yaml_lite

HARD_MAX_RISK_PCT = 1.0
FORBIDDEN_INTENTS = frozenset(
    {
        "withdraw",
        "withdrawal",
        "withdrawals",
        "send_out",
        "send-out",
        "sendout",
        "cash_out",
        "cash-out",
        "transfer_out",
        "transfer-out",
        "transferout",
        "main_to_agentic",
        "main-to-agentic",
        "sweep_main",
        "sweep-main",
        "travel_rule",
    }
)
PLACE_INTENTS = frozenset({"ticket", "place", "order", "trade", "propose"})

IntentKind = Literal["ticket", "withdraw", "transfer_out", "main_to_agentic", "other"]


@dataclass(frozen=True)
class PolicyConfig:
    version: int = 1
    emergency_stop: bool = False
    product_default: str = "SPOT"
    venue: str = "agentic_subaccount_only"
    symbols_allowlist: frozenset[str] = field(default_factory=frozenset)
    max_risk_pct: float = HARD_MAX_RISK_PCT
    max_notional_quote: float | None = None
    max_loss_quote: float | None = None
    max_volume_quote: float | None = None
    source: str = "hard-rules"

    def __post_init__(self) -> None:
        capped = min(float(self.max_risk_pct), HARD_MAX_RISK_PCT)
        if capped != self.max_risk_pct:
            object.__setattr__(self, "max_risk_pct", capped)


@dataclass(frozen=True)
class PolicyViolation:
    code: str
    message: str


@dataclass(frozen=True)
class PolicyResult:
    ok: bool
    intent: str
    violations: tuple[PolicyViolation, ...]
    config_source: str
    emergency_stop: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "intent": self.intent,
            "violations": [asdict(v) for v in self.violations],
            "config_source": self.config_source,
            "emergency_stop": self.emergency_stop,
        }


def classify_intent(intent: str | None) -> IntentKind:
    if not intent:
        return "ticket"
    key = intent.strip().lower().replace(" ", "_")
    compact = key.replace("-", "_")
    if compact in {"withdraw", "withdrawal", "withdrawals", "cash_out", "send_out", "sendout"}:
        return "withdraw"
    if compact in {"transfer_out", "transferout", "sweep_main"}:
        return "transfer_out"
    if compact in {"main_to_agentic", "pull_from_main", "fund_from_main"}:
        return "main_to_agentic"
    if compact in PLACE_INTENTS:
        return "ticket"
    if compact in FORBIDDEN_INTENTS:
        return "withdraw"
    return "other"


def hard_policy() -> PolicyConfig:
    return PolicyConfig(source="hard-rules")


def load_policy(path: Path | str) -> PolicyConfig:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"policy file not found: {target}")
    suffix = target.suffix.lower()
    if suffix == ".json":
        raw = json.loads(target.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        raw = load_yaml_lite(target)
    else:
        raise ValueError(f"policy file must be .yaml, .yml, or .json (got {suffix})")
    if not isinstance(raw, dict):
        raise ValueError("policy file must be a mapping")
    return policy_from_dict(raw, source=str(target))


def policy_from_dict(raw: dict[str, Any], *, source: str) -> PolicyConfig:
    symbols = raw.get("symbols") or {}
    allow = symbols.get("allowlist") if isinstance(symbols, dict) else None
    if allow is None:
        allow = raw.get("allowlist") or raw.get("symbols_allowlist") or []
    allowlist = frozenset(str(s).upper() for s in allow)

    risk = raw.get("risk") if isinstance(raw.get("risk"), dict) else {}
    daily = raw.get("daily_caps") if isinstance(raw.get("daily_caps"), dict) else {}

    max_risk = risk.get("max_risk_pct", raw.get("max_risk_pct", HARD_MAX_RISK_PCT))
    try:
        max_risk_f = float(max_risk)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_risk_pct must be a number") from exc

    return PolicyConfig(
        version=int(raw.get("version") or 1),
        emergency_stop=bool(raw.get("emergency_stop", False)),
        product_default=str(raw.get("product_default") or "SPOT").upper(),
        venue=str(raw.get("venue") or "agentic_subaccount_only"),
        symbols_allowlist=allowlist,
        max_risk_pct=max_risk_f,
        max_notional_quote=_optional_float(risk.get("max_notional_quote", raw.get("max_notional_quote"))),
        max_loss_quote=_optional_float(daily.get("max_loss_quote", raw.get("max_loss_quote"))),
        max_volume_quote=_optional_float(daily.get("max_volume_quote", raw.get("max_volume_quote"))),
        source=source,
    )


def resolve_policy_path(
    explicit: Path | str | None = None,
    *,
    cwd: Path | None = None,
    env_path: str | None = None,
) -> Path | None:
    if explicit is not None:
        return Path(explicit)
    if env_path:
        return Path(env_path)
    root = cwd or Path.cwd()
    for candidate in (
        root / "config" / "policy.yaml",
        root / "config" / "policy.yml",
        root / "config" / "policy.json",
        root / "config" / "policy.example.yaml",
        root / "config" / "policy.example.json",
    ):
        if candidate.is_file():
            return candidate
    return None


def evaluate_policy(
    *,
    intent: str = "ticket",
    symbol: str | None = None,
    side: str | None = None,
    notional: float | None = None,
    risk_pct: float | None = None,
    product: str = "SPOT",
    daily_loss: float = 0.0,
    daily_volume: float = 0.0,
    config: PolicyConfig | None = None,
) -> PolicyResult:
    cfg = config or hard_policy()
    violations: list[PolicyViolation] = []
    kind = classify_intent(intent)

    if kind in {"withdraw", "transfer_out", "main_to_agentic"}:
        violations.append(
            PolicyViolation(
                code="FORBIDDEN_INTENT",
                message=(
                    f"Intent {kind} is always refused. "
                    "Safe Desk never withdraws, never transfers out, and never pulls main→Agentic."
                ),
            )
        )

    if cfg.emergency_stop and kind in {"ticket", "other"}:
        violations.append(
            PolicyViolation(
                code="EMERGENCY_STOP",
                message="emergency_stop is set in the policy file. All place-path tickets are blocked.",
            )
        )

    if kind == "ticket":
        if product and product.upper() != cfg.product_default:
            violations.append(
                PolicyViolation(
                    code="PRODUCT_NOT_ALLOWED",
                    message=f"Product {product.upper()} is not the desk default {cfg.product_default}.",
                )
            )
        if symbol and cfg.symbols_allowlist and symbol.upper() not in cfg.symbols_allowlist:
            allowed = ", ".join(sorted(cfg.symbols_allowlist))
            violations.append(
                PolicyViolation(
                    code="SYMBOL_NOT_ALLOWLISTED",
                    message=f"{symbol.upper()} is not on the allowlist ({allowed}).",
                )
            )
        if risk_pct is not None:
            if risk_pct <= 0:
                violations.append(PolicyViolation(code="RISK_INVALID", message="risk_pct must be > 0."))
            elif risk_pct > cfg.max_risk_pct:
                violations.append(
                    PolicyViolation(
                        code="RISK_CAP",
                        message=f"Requested risk {risk_pct:g}% exceeds desk max {cfg.max_risk_pct:g}%.",
                    )
                )
        if notional is not None:
            if notional <= 0:
                violations.append(PolicyViolation(code="NOTIONAL_INVALID", message="notional must be > 0."))
            elif cfg.max_notional_quote is not None and notional > cfg.max_notional_quote:
                violations.append(
                    PolicyViolation(
                        code="MAX_NOTIONAL",
                        message=(
                            f"Notional {notional:.4f} exceeds max_notional_quote {cfg.max_notional_quote:g}."
                        ),
                    )
                )
        if cfg.max_volume_quote is not None and (daily_volume + (notional or 0.0)) > cfg.max_volume_quote:
            violations.append(
                PolicyViolation(
                    code="DAILY_VOLUME_CAP",
                    message=(
                        f"Daily volume {daily_volume:.4f} + this notional "
                        f"exceeds max_volume_quote {cfg.max_volume_quote:g}."
                    ),
                )
            )
        if cfg.max_loss_quote is not None and daily_loss > cfg.max_loss_quote:
            violations.append(
                PolicyViolation(
                    code="DAILY_LOSS_CAP",
                    message=f"Daily loss {daily_loss:.4f} exceeds max_loss_quote {cfg.max_loss_quote:g}.",
                )
            )
        if side is not None and side.upper() not in {"BUY", "SELL"}:
            violations.append(PolicyViolation(code="SIDE_INVALID", message=f"side {side!r} is not BUY or SELL."))

    return PolicyResult(
        ok=not violations,
        intent=kind,
        violations=tuple(violations),
        config_source=cfg.source,
        emergency_stop=cfg.emergency_stop,
    )


def usage_from_log(
    path: Path | str | None,
    *,
    day: str | None = None,
    actions: Sequence[str] = ("simulated", "placed"),
) -> tuple[float, float]:
    """Sum today's notional (volume) and optional realized_loss from a JSONL log.

    Returns (daily_loss, daily_volume). Missing file → (0, 0).
    """
    if path is None:
        return 0.0, 0.0
    target = Path(path)
    if not target.is_file():
        return 0.0, 0.0
    stamp = day or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    volume = 0.0
    loss = 0.0
    allowed = set(actions)
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = str(row.get("ts") or row.get("created_at") or "")
        if not ts.startswith(stamp):
            continue
        if row.get("action") not in allowed:
            continue
        try:
            volume += float(row.get("notional") or 0.0)
        except (TypeError, ValueError):
            pass
        try:
            loss += float(row.get("realized_loss") or 0.0)
        except (TypeError, ValueError):
            pass
    return loss, volume


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
