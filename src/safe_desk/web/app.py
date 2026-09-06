"""Minimal local web UI for a regular exchange user.

FastAPI + static HTML/JS. No login wall. No API secrets.
Dry-run stays on. Approve requires typing OK TKT-…
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from safe_desk import __version__
from safe_desk.desk import Desk, find_repo_root
from safe_desk.mcp_input import MCP_ENDPOINT

STATIC_DIR = Path(__file__).resolve().parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


class AnalyzeBody(BaseModel):
    symbol: str = "BTCUSDT"
    side: Literal["BUY", "SELL"] = "BUY"
    use_sample: bool = True
    csv_text: str | None = None
    price_json: dict[str, Any] | str | None = None
    balance_json: dict[str, Any] | str | None = None
    stop: float | None = None
    equity: float | None = None
    risk_pct: float = 1.0
    lang: str = "en"


class TicketBody(BaseModel):
    symbol: str = "BTCUSDT"
    side: Literal["BUY", "SELL"] = "BUY"
    entry: float | None = None
    stop: float
    equity: float | None = None
    take_profit: float | None = None
    risk_pct: float = 1.0
    rationale: str = ""
    use_sample: bool = True
    csv_text: str | None = None
    price_json: dict[str, Any] | str | None = None
    balance_json: dict[str, Any] | str | None = None
    require_proof: bool = False
    lang: str = "en"


class ApproveBody(BaseModel):
    phrase: str = Field(..., min_length=1)
    ticket_id: str | None = None


class CancelBody(BaseModel):
    phrase: str | None = None
    ticket_id: str | None = None


class ClosePaperBody(BaseModel):
    ticket_id: str
    exit_price: float | None = None
    reason: Literal["stop", "take_profit", "manual", "mark"] = "manual"


class WithdrawBody(BaseModel):
    note: str = "withdraw"


def create_app(*, root: Path | None = None, log_dir: Path | None = None) -> FastAPI:
    desk = Desk(root=root or find_repo_root(), log_dir=log_dir)
    application = FastAPI(
        title="Safe Desk",
        version=__version__,
        description="Local dry-run desk for Binance Agent OS. No secrets.",
    )
    application.state.desk = desk

    if STATIC_DIR.is_dir():
        application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/")
    def index() -> FileResponse:
        if not INDEX_HTML.is_file():
            raise HTTPException(500, "web UI files missing")
        return FileResponse(INDEX_HTML)

    @application.get("/health")
    def health() -> dict[str, Any]:
        return {"ok": True, "mode": "dry-run", "mcp_url": MCP_ENDPOINT, "version": __version__}

    @application.get("/api/status")
    def api_status(request: Request) -> dict[str, Any]:
        return _desk(request).status()

    @application.post("/api/analyze")
    def api_analyze(request: Request, body: AnalyzeBody) -> dict[str, Any]:
        try:
            return _desk(request).analyze(
                csv_text=body.csv_text,
                use_sample=body.use_sample and not body.csv_text,
                symbol=body.symbol,
                side=body.side,
                stop=body.stop,
                equity=body.equity,
                risk_pct=body.risk_pct,
                price_json=body.price_json,
                balance_json=body.balance_json,
                lang=body.lang,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @application.post("/api/analyze/upload")
    async def api_analyze_upload(
        request: Request,
        csv: UploadFile = File(...),
        symbol: str = Form("BTCUSDT"),
        side: str = Form("BUY"),
        stop: float | None = Form(None),
        equity: float | None = Form(None),
        risk_pct: float = Form(1.0),
        price_json: str | None = Form(None),
        balance_json: str | None = Form(None),
        lang: str = Form("en"),
    ) -> dict[str, Any]:
        text = (await csv.read()).decode("utf-8")
        price = _maybe_json(price_json)
        balance = _maybe_json(balance_json)
        if side not in {"BUY", "SELL"}:
            raise HTTPException(400, "side must be BUY or SELL")
        try:
            return _desk(request).analyze(
                csv_text=text,
                use_sample=False,
                symbol=symbol,
                side=side,  # type: ignore[arg-type]
                stop=stop,
                equity=equity,
                risk_pct=risk_pct,
                price_json=price,
                balance_json=balance,
                lang=lang,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @application.post("/api/ticket")
    def api_ticket(request: Request, body: TicketBody) -> dict[str, Any]:
        try:
            result = _desk(request).create_ticket(
                symbol=body.symbol,
                side=body.side,
                entry=body.entry,
                stop=body.stop,
                equity=body.equity,
                take_profit=body.take_profit,
                risk_pct=body.risk_pct,
                rationale=body.rationale,
                use_sample=body.use_sample,
                csv_text=body.csv_text,
                price_json=body.price_json,
                balance_json=body.balance_json,
                require_proof=body.require_proof,
                lang=body.lang,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return result

    @application.post("/api/ticket/approve")
    def api_approve(request: Request, body: ApproveBody) -> JSONResponse:
        result = _desk(request).approve(body.phrase, ticket_id=body.ticket_id)
        status = 200 if result.get("ok") else 400
        return JSONResponse(result, status_code=status)

    @application.post("/api/ticket/cancel")
    def api_cancel(request: Request, body: CancelBody) -> JSONResponse:
        result = _desk(request).cancel(body.phrase, ticket_id=body.ticket_id)
        status = 200 if result.get("ok") else 400
        return JSONResponse(result, status_code=status)

    @application.get("/api/journal")
    def api_journal(request: Request) -> dict[str, Any]:
        return _desk(request).journal()

    @application.post("/api/journal/close")
    def api_journal_close(request: Request, body: ClosePaperBody) -> dict[str, Any]:
        try:
            return _desk(request).close_paper(
                body.ticket_id,
                exit_price=body.exit_price,
                reason=body.reason,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @application.get("/api/alerts")
    def api_alerts(request: Request) -> dict[str, Any]:
        rows = _desk(request).alerts()
        return {"alerts": rows, "count": len(rows)}

    @application.post("/api/withdraw")
    def api_withdraw(request: Request, body: WithdrawBody) -> JSONResponse:
        result = _desk(request).refuse_withdraw(note=body.note)
        return JSONResponse(result, status_code=403)

    return application


def _desk(request: Request) -> Desk:
    return request.app.state.desk


def _maybe_json(raw: str | None) -> dict[str, Any] | str | None:
    if raw is None or not raw.strip():
        return None
    stripped = raw.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return stripped
    return stripped


app = create_app()


def run(host: str = "127.0.0.1", port: int = 8765) -> int:
    try:
        import uvicorn
    except ImportError:
        print("Install the web extra: pip install -e \".[dev]\"")
        return 2
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0
