# NexusTrade — Multi-Agent LLM Trading Framework

An AI-powered stock and crypto trading analysis platform built with a multi-agent LLM architecture. Multiple specialized AI agents collaborate through structured debates to produce investment recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Analysis Pipeline                     │
├──────────┬──────────┬──────────┬────────────────────────┤
│ Market   │Sentiment │  News    │   Fundamentals         │
│ Analyst  │ Analyst  │ Analyst  │     Analyst            │
│ (parallel execution across all 4 analysts)              │
├─────────────────────────────────────────────────────────┤
│          Bull vs Bear Research Debate                    │
│                  ↓ Research Judge                        │
├─────────────────────────────────────────────────────────┤
│                    Trader Agent                         │
├─────────────────────────────────────────────────────────┤
│     Aggressive vs Conservative vs Neutral Risk Debate   │
│                  ↓ Risk Judge (CRO)                     │
├─────────────────────────────────────────────────────────┤
│              Final Trade Decision                       │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack

**Backend:**
- Python, FastAPI, WebSockets
- LangChain + LangGraph (agent orchestration)
- Groq LLM API (Kimi K2 model)
- yfinance & CCXT (market data)
- ChromaDB (vector memory)
- SQLite (trade history)

**Frontend:**
- Next.js 15/, TypeScript
- Real-time WebSocket dashboard

## Setup

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env    # Add your API keys
python -m uvicorn api.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

Copy `backend/.env.example` to `backend/.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ | Free at [console.groq.com](https://console.groq.com) |
| `ALPACA_API_KEY` | Optional | Paper trading via [Alpaca](https://alpaca.markets) |
| `ALPACA_SECRET_KEY` | Optional | Alpaca secret key |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram alert bot |
| `DISCORD_WEBHOOK_URL` | Optional | Discord alert webhook |

## Key Features

- **Parallel Analysis** — 4 analysts run simultaneously via LangGraph fan-out
- **Adversarial Debates** — Bull vs Bear researchers argue with evidence, judged by a Research Director
- **Risk Management** — Aggressive/Conservative/Neutral risk analysts debate every trade
- **Rate-Limit Resilience** — Exponential backoff + concurrency throttling for Groq API
- **Adaptive Confidence** — Agent weights adjust based on historical accuracy
- **Vector Memory** — ChromaDB stores past analyses for pattern recognition
- **Real-time Dashboard** — WebSocket-powered live updates

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/analyze` | Run full pipeline for a ticker |
| `GET` | `/portfolio` | Current portfolio state |
| `GET` | `/trades` | Trade history |
| `GET` | `/price/{ticker}` | Current price + fundamentals |
| `GET` | `/indicators/{ticker}` | Technical indicators |
| `WS` | `/ws/live` | Real-time updates |

## License

MIT
