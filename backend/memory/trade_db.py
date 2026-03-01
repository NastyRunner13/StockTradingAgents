"""
NexusTrade — Trade Database
SQLite database for structured trade history, portfolio snapshots, and agent accuracy.
"""

import aiosqlite
import json
from datetime import datetime
from typing import Optional
from config import SQLITE_DB_PATH


class TradeDB:
    """Async SQLite database for trade records and portfolio state."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(SQLITE_DB_PATH)

    async def initialize(self):
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    asset_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    confidence REAL,
                    reasoning TEXT,
                    approval_status TEXT DEFAULT 'pending',
                    pnl REAL,
                    created_at TEXT NOT NULL,
                    executed_at TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cash REAL,
                    equity REAL,
                    total_value REAL,
                    positions_json TEXT,
                    daily_pnl REAL,
                    total_pnl REAL,
                    timestamp TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS agent_accuracy (
                    agent_name TEXT PRIMARY KEY,
                    total_predictions INTEGER DEFAULT 0,
                    correct_predictions INTEGER DEFAULT 0,
                    accuracy REAL DEFAULT 0.0,
                    weight REAL DEFAULT 1.0,
                    last_updated TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS analysis_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    asset_type TEXT,
                    trade_date TEXT,
                    full_state_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.commit()

    async def insert_trade(self, ticker: str, asset_type: str, action: str,
                           quantity: float, price: float, confidence: float = 0,
                           reasoning: str = "", approval_status: str = "pending") -> int:
        """Insert a trade record and return its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO trades (ticker, asset_type, action, quantity, price, 
                   confidence, reasoning, approval_status, created_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ticker, asset_type, action, quantity, price, confidence,
                 reasoning, approval_status, datetime.utcnow().isoformat()),
            )
            await db.commit()
            return cursor.lastrowid

    async def get_trades(self, ticker: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Get trade history."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            if ticker:
                cursor = await db.execute(
                    "SELECT * FROM trades WHERE ticker = ? ORDER BY created_at DESC LIMIT ?",
                    (ticker, limit),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,)
                )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def save_portfolio_snapshot(self, cash: float, equity: float,
                                     total_value: float, positions: list,
                                     daily_pnl: float, total_pnl: float):
        """Save a portfolio snapshot."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO portfolio_snapshots 
                   (cash, equity, total_value, positions_json, daily_pnl, total_pnl, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (cash, equity, total_value, json.dumps(positions),
                 daily_pnl, total_pnl, datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def get_portfolio_history(self, limit: int = 100) -> list[dict]:
        """Get portfolio snapshot history."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def save_analysis_log(self, ticker: str, asset_type: str, 
                                trade_date: str, state_dict: dict):
        """Save a full analysis pipeline state for review."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO analysis_logs (ticker, asset_type, trade_date, full_state_json, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (ticker, asset_type, trade_date,
                 json.dumps(state_dict, default=str),
                 datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def update_agent_accuracy(self, agent_name: str, total: int,
                                    correct: int, accuracy: float, weight: float):
        """Upsert agent accuracy record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO agent_accuracy (agent_name, total_predictions, correct_predictions, accuracy, weight, last_updated)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(agent_name) DO UPDATE SET
                   total_predictions=?, correct_predictions=?, accuracy=?, weight=?, last_updated=?""",
                (agent_name, total, correct, accuracy, weight, datetime.utcnow().isoformat(),
                 total, correct, accuracy, weight, datetime.utcnow().isoformat()),
            )
            await db.commit()
