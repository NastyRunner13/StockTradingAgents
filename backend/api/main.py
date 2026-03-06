"""
NexusTrade — FastAPI Server
REST API + WebSocket for the trading agents pipeline.
"""

import asyncio
import json
import math
import traceback
import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import CORS_ORIGINS, API_HOST, API_PORT
from graph.pipeline import TradingPipeline
from memory.trade_db import TradeDB
from data.stock_provider import StockProvider
from data.crypto_provider import CryptoProvider
from data.ticker_search import search_tickers

# ─── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)-20s │ %(levelname)-5s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nexustrade.api")


# ─── Request/Response Models ──────────────────────────────────

class AnalyzeRequest(BaseModel):
    ticker: str
    asset_type: str = "stock"  # "stock" or "crypto"
    trade_date: Optional[str] = None
    selected_analysts: Optional[list[str]] = None  # e.g. ["market", "news"]

class TradeApprovalRequest(BaseModel):
    approval: str = "approve"  # "approve" or "reject"

class WatchlistRequest(BaseModel):
    tickers: list[str]


# ─── Global State ─────────────────────────────────────────────

pipeline: Optional[TradingPipeline] = None
trade_db: Optional[TradeDB] = None
stock_provider = StockProvider()
crypto_provider = CryptoProvider()
active_connections: list[WebSocket] = []


# ─── Lifespan ─────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup."""
    global pipeline, trade_db
    
    trade_db = TradeDB()
    await trade_db.initialize()
    
    pipeline = TradingPipeline()
    await pipeline.initialize()
    
    yield


# ─── App ──────────────────────────────────────────────────────

app = FastAPI(
    title="NexusTrade API",
    description="Multi-Agent LLM Trading Framework — Powered by Groq",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── WebSocket Manager ────────────────────────────────────────

async def broadcast(message: dict):
    """Broadcast a message to all connected WebSocket clients."""
    text = json.dumps(message, default=str)
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_text(text)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        active_connections.remove(ws)


# ─── WebSocket Endpoint ───────────────────────────────────────

@app.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming commands from frontend
            msg = json.loads(data)
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)


# ─── REST Endpoints ───────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "NexusTrade API",
        "version": "1.0.0",
        "status": "running",
        "agents": ["market", "sentiment", "news", "fundamentals"],
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.get("/search")
async def search_ticker(
    q: str = Query(default="", min_length=1, max_length=20),
    asset_type: str = Query(default="all"),
    limit: int = Query(default=8, le=20),
):
    """Search for tickers by keyword (auto-suggest)."""
    results = search_tickers(q, asset_type=asset_type, limit=limit)
    return results


@app.post("/analyze")
async def analyze_ticker(request: AnalyzeRequest):
    """Run the full agent pipeline for a ticker."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    # Unique session ID for this analysis (prevents cross-tab event mixing)
    import uuid
    analysis_id = str(uuid.uuid4())[:12]

    logger.info("━" * 60)
    logger.info(f"🚀 ANALYSIS STARTED — {request.ticker} ({request.asset_type}) [session: {analysis_id}]")
    logger.info("━" * 60)

    # Broadcast analysis start
    await broadcast({
        "type": "analysis_start",
        "analysis_id": analysis_id,
        "data": {"ticker": request.ticker, "asset_type": request.asset_type},
    })

    try:
        import time
        start_time = time.time()

        # Log callback: broadcast each agent event via WebSocket (scoped to this analysis)
        async def log_callback(agent: str, stage: str, message: str, details: str = ""):
            await broadcast({
                "type": "analysis_log",
                "analysis_id": analysis_id,
                "data": {
                    "agent": agent,
                    "stage": stage,
                    "message": message,
                    "details": details[:500] if details else "",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            })

        result = await pipeline.analyze(
            ticker=request.ticker,
            asset_type=request.asset_type,
            trade_date=request.trade_date or datetime.utcnow().strftime("%Y-%m-%d"),
            log_callback=log_callback,
            selected_analysts=request.selected_analysts,
        )

        elapsed = time.time() - start_time
        logger.info("━" * 60)
        logger.info(f"✅ ANALYSIS COMPLETE — {request.ticker} in {elapsed:.1f}s")

        # Log key results
        trade_signal = result.get("trade_signal")
        if trade_signal:
            s = trade_signal if isinstance(trade_signal, dict) else trade_signal.model_dump()
            logger.info(f"   Action: {s.get('action')} | Confidence: {s.get('confidence')}")
            logger.info(f"   Entry: ${s.get('entry_price')} | Target: ${s.get('target_price')} | Stop: ${s.get('stop_loss')}")
        
        approved = result.get("trade_approved", False)
        logger.info(f"   Trade Approved: {'✅ YES' if approved else '❌ NO'}")
        logger.info("━" * 60)

        # Serialize the result
        serialized = _serialize_state(result)

        # Save to database
        if trade_db:
            await trade_db.save_analysis_log(
                request.ticker, request.asset_type,
                request.trade_date or datetime.utcnow().strftime("%Y-%m-%d"),
                serialized,
            )

        # Broadcast result
        await broadcast({
            "type": "analysis_complete",
            "data": serialized,
        })

        return serialized

    except Exception as e:
        error_str = str(e).lower()
        is_rate_limit = (
            "rate_limit" in error_str
            or "rate limit" in error_str
            or "429" in error_str
            or "too many requests" in error_str
            or "resource_exhausted" in error_str
        )

        if is_rate_limit:
            error_msg = (
                "Groq API rate limit reached. The system retried automatically but the limit persists. "
                "Please wait 1-2 minutes before trying again."
            )
            logger.warning(f"⚠️ Rate limit — {request.ticker}: {e}")
            await broadcast({"type": "analysis_error", "data": {"error": error_msg, "retry_after": 60}})
            raise HTTPException(status_code=429, detail=error_msg)

        traceback.print_exc()
        error_msg = f"Analysis failed: {str(e)}"
        logger.error(f"❌ {error_msg}")
        await broadcast({"type": "analysis_error", "data": {"error": error_msg}})
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/portfolio")
async def get_portfolio():
    """Get current portfolio state."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    history = await trade_db.get_portfolio_history(limit=1)
    if history:
        return history[0]
    return {
        "cash": 100000.0,
        "equity": 0.0,
        "total_value": 100000.0,
        "positions": [],
        "daily_pnl": 0.0,
        "total_pnl": 0.0,
    }


@app.get("/portfolio/history")
async def get_portfolio_history(limit: int = Query(default=100, le=500)):
    """Get portfolio value history for charting."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return await trade_db.get_portfolio_history(limit=limit)


@app.get("/trades")
async def get_trades(ticker: Optional[str] = None, limit: int = Query(default=50, le=200)):
    """Get trade history."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    return await trade_db.get_trades(ticker=ticker, limit=limit)


@app.get("/price/{ticker}")
async def get_price(ticker: str, asset_type: str = "stock"):
    """Get current price for a ticker."""
    if asset_type == "crypto":
        price = crypto_provider.get_current_price(ticker)
        info = crypto_provider.get_ticker_info(ticker)
        return {"ticker": ticker, "price": price, "info": info}
    else:
        price = stock_provider.get_current_price(ticker)
        fundamentals = stock_provider.get_fundamentals(ticker)
        return {"ticker": ticker, "price": price, "fundamentals": fundamentals}


@app.get("/indicators/{ticker}")
async def get_indicators(ticker: str, asset_type: str = "stock"):
    """Get technical indicators for a ticker."""
    if asset_type == "crypto":
        return crypto_provider.get_technical_indicators(ticker)
    else:
        return stock_provider.get_technical_indicators(ticker)


# ─── Phase 3: Chart Data + Analysis History ────────────────────

@app.get("/price/{ticker}/chart")
async def get_price_chart(ticker: str, asset_type: str = "stock"):
    """Get OHLCV data formatted for lightweight-charts candlestick."""
    try:
        if asset_type == "crypto":
            df = crypto_provider.get_price_data(ticker)
        else:
            df = stock_provider.get_price_data(ticker)

        if df.empty:
            return []

        records = []
        for date, row in df.iterrows():
            records.append({
                "time": date.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row.get("Volume", 0)) if "Volume" in row else None,
            })
        return records
    except Exception as e:
        logger.error(f"Chart data error for {ticker}: {e}")
        return []


@app.get("/analysis/history")
async def get_analysis_history(
    ticker: Optional[str] = None,
    limit: int = Query(default=20, le=100),
):
    """Get past analysis summaries for the history timeline."""
    if not trade_db:
        raise HTTPException(status_code=503, detail="Database not initialized")
    try:
        logs = await trade_db.get_analysis_logs(ticker=ticker, limit=limit)
        return logs
    except Exception as e:
        logger.error(f"Analysis history error: {e}")
        return []

@app.post("/trades/{thread_id}/approve")
async def approve_trade(thread_id: str, request: TradeApprovalRequest):
    """Approve or reject a paused trade (HITL).
    
    When a trade has lower confidence than AUTO_TRADE_CONFIDENCE,
    the pipeline pauses and waits for human approval.
    Call this endpoint with the thread_id to resume.
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    # Check the current state
    state = await pipeline.get_state(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No analysis found for thread {thread_id}")

    if state.get("status") != "interrupted":
        raise HTTPException(
            status_code=400,
            detail=f"Analysis is not waiting for approval (status: {state.get('status')})"
        )

    logger.info(f"{'✅' if request.approval == 'approve' else '❌'} Trade approval for {thread_id}: {request.approval}")

    try:
        from langgraph.types import Command
        config = {"configurable": {"thread_id": thread_id}}
        result = await pipeline.graph.ainvoke(
            Command(resume=request.approval),
            config=config,
        )
        serialized = _serialize_state(result)

        await broadcast({
            "type": "trade_approved" if request.approval == "approve" else "trade_rejected",
            "data": {"thread_id": thread_id, **serialized},
        })

        return {"status": "ok", "thread_id": thread_id, "decision": request.approval, **serialized}

    except Exception as e:
        logger.error(f"Error resuming thread {thread_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to resume: {str(e)}")


@app.get("/analysis/{thread_id}/state")
async def get_analysis_state(thread_id: str):
    """Get the current state of an analysis pipeline.
    
    Useful for checking if a trade is waiting for approval,
    or inspecting the full state of a completed analysis.
    """
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    state = await pipeline.get_state(thread_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No analysis found for thread {thread_id}")

    return _serialize_state(state)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ─── Helpers ──────────────────────────────────────────────────

def _serialize_state(state: dict) -> dict:
    """Serialize pipeline state for JSON response, handling Pydantic, enums, NaN/Inf."""
    import enum

    def _sanitize(obj):
        if obj is None:
            return None
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, bool):
            return obj
        if isinstance(obj, int):
            return obj
        if isinstance(obj, str):
            return obj
        if isinstance(obj, enum.Enum):
            return obj.value
        if hasattr(obj, "model_dump"):
            return _sanitize(obj.model_dump())
        if isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_sanitize(v) for v in obj]
        # Last resort — stringify
        return str(obj)

    return {k: _sanitize(v) for k, v in state.items()}


# ─── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host=API_HOST, port=API_PORT, reload=True)
