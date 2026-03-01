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

class TradeApprovalRequest(BaseModel):
    trade_id: int
    approved: bool

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


@app.post("/analyze")
async def analyze_ticker(request: AnalyzeRequest):
    """Run the full agent pipeline for a ticker."""
    if not pipeline:
        raise HTTPException(status_code=503, detail="Pipeline not initialized")

    logger.info("━" * 60)
    logger.info(f"🚀 ANALYSIS STARTED — {request.ticker} ({request.asset_type})")
    logger.info("━" * 60)

    # Broadcast analysis start
    await broadcast({
        "type": "analysis_start",
        "data": {"ticker": request.ticker, "asset_type": request.asset_type},
    })

    try:
        import time
        start_time = time.time()

        result = await pipeline.analyze(
            ticker=request.ticker,
            asset_type=request.asset_type,
            trade_date=request.trade_date or datetime.utcnow().strftime("%Y-%m-%d"),
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


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ─── Helpers ──────────────────────────────────────────────────

def _serialize_state(state: dict) -> dict:
    """Serialize pipeline state for JSON response, handling NaN/Inf floats."""
    def _sanitize(obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        elif isinstance(obj, dict):
            return {k: _sanitize(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [_sanitize(v) for v in obj]
        return obj

    result = {}
    for key, value in state.items():
        if value is None:
            result[key] = None
        elif hasattr(value, "model_dump"):
            result[key] = _sanitize(value.model_dump())
        elif isinstance(value, dict):
            result[key] = _sanitize(value)
        else:
            result[key] = str(value)
    return result


# ─── Main ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host=API_HOST, port=API_PORT, reload=True)
