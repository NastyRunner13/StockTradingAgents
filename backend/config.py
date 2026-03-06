"""
NexusTrade — Central Configuration
Loads environment variables and provides default settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
_backend_dir = Path(__file__).parent
load_dotenv(_backend_dir / ".env")

# ─── Directories ───────────────────────────────────────────────
PROJECT_DIR = _backend_dir
DATA_DIR = PROJECT_DIR / "data_cache"
DB_DIR = PROJECT_DIR / "db"
CHROMA_DIR = PROJECT_DIR / "chroma_store"

# Create directories
for d in [DATA_DIR, DB_DIR, CHROMA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─── Groq LLM ─────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# DEEP_THINK_MODEL = "moonshotai/kimi-k2-instruct-0905"   # Complex reasoning
# QUICK_THINK_MODEL = "moonshotai/kimi-k2-instruct-0905"   # Fast tasks (llama3-70b-8192 was retired)
DEEP_THINK_MODEL = "openai/gpt-oss-120b"   # Complex reasoning
QUICK_THINK_MODEL = "openai/gpt-oss-20b"   # Fast tasks (llama3-70b-8192 was retired)
LLM_TEMPERATURE = 0.7
LLM_MAX_RETRIES = 3

# ─── Agent Pipeline ───────────────────────────────────────────
MAX_DEBATE_ROUNDS = 2          # Bull/Bear debate rounds
MAX_RISK_DEBATE_ROUNDS = 2     # Risk team debate rounds
ANALYST_TIMEOUT = 60           # Seconds per analyst
AUTO_TRADE_CONFIDENCE = 0.85   # Auto-execute above this confidence
APPROVAL_QUEUE_TTL = 300       # Seconds before pending approval expires

# ─── LangGraph Advanced ──────────────────────────────────────
CHECKPOINT_DB_PATH = DB_DIR / "checkpoints.db"
ENABLE_HITL = True             # Human-in-the-loop trade approval
DEFAULT_ANALYSTS = ["market", "sentiment", "news", "fundamentals"]

# ─── Alpha Vantage (Stock Data) ────────────────────────────────
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")

# ─── Finnhub (News & Sentiment) ───────────────────────────────
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
NEWS_MAX_ARTICLES = 25             # Combined max from all sources
NEWS_LOOKBACK_DAYS = 7             # How far back to fetch news

# ─── Alerts ────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

# ─── Trading Loop ─────────────────────────────────────────────
TRADING_LOOP_INTERVAL = 300    # Seconds between analysis cycles
WATCHLIST_DEFAULT = ["AAPL", "NVDA", "TSLA", "BTC/USD", "ETH/USD"]

# ─── Database ─────────────────────────────────────────────────
SQLITE_DB_PATH = DB_DIR / "nexustrade.db"

# ─── Server ───────────────────────────────────────────────────
API_HOST = "0.0.0.0"
API_PORT = 8000
CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
