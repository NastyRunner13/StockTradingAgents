<p align="center">
  <h1 align="center">🧠 NexusTrade</h1>
  <p align="center"><strong>Multi-Agent LLM Trading Framework</strong></p>
  <p align="center">
    An AI-powered stock & crypto analysis platform where specialized LLM agents collaborate through structured adversarial debates to produce investment recommendations.
  </p>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Next.js-16-black?logo=next.js" alt="Next.js" />
  <img src="https://img.shields.io/badge/LangGraph-Agent%20Pipeline-green" alt="LangGraph" />
  <img src="https://img.shields.io/badge/Groq-Kimi%20K2-orange" alt="Groq" />
  <img src="https://img.shields.io/badge/license-MIT-purple" alt="License" />
</p>

---

## 📖 Overview

NexusTrade is **not** a single-prompt trading bot. It orchestrates **13 specialized AI agents** through a multi-stage pipeline with parallel execution, adversarial debates, and adaptive confidence scoring — mimicking the structure of a real trading desk:

| Role               | Agents | What they do |
|:-------------------|:------:|:-------------|
| **Analysts**       | 4      | Gather & interpret market data, sentiment, news, and fundamentals — all running *in parallel* |
| **Researchers**    | 3      | Bull & Bear advocates debate the evidence; a Research Judge delivers a verdict |
| **Trader**         | 1      | Converts the research thesis into a concrete trade plan with entry, target, stop-loss, and position sizing |
| **Risk Committee** | 5      | Aggressive, Conservative, and Neutral risk analysts debate the trade; a CRO Judge makes the final risk-adjusted decision |

The entire flow is compiled into a single **LangGraph** state machine and executed asynchronously, with results streamed to the frontend in real-time via WebSockets.

---

## 🏗️ Architecture

### High-Level Pipeline

```
                          ┌──────────────────┐
                          │   User Request    │
                          │  (ticker + type)  │
                          └────────┬─────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
     ┌────────▼────────┐ ┌────────▼────────┐  ┌────────▼─────────┐
     │  Market Analyst  │ │Sentiment Analyst│  │   News Analyst   │
     │  (technicals,    │ │  (social buzz,  │  │  (headlines,     │
     │   price action)  │ │   market mood)  │  │   press, filings)│
     └────────┬────────┘ └────────┬────────┘  └────────┬─────────┘
              │                    │                     │
              │         ┌─────────▼─────────┐           │
              │         │ Fundamentals       │           │
              │         │  Analyst (P/E,     │           │
              │         │  revenue, margins) │           │
              │         └─────────┬─────────┘           │
              │                   │                      │
              └───────────────────┼──────────────────────┘
                                  │  (parallel fan-out / merge)
                                  ▼
                    ┌─────────────────────────────┐
                    │    📊 Merge Analyst Reports  │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     🐂 Bull Researcher       │◄──┐
                    │   (builds bullish case)       │   │
                    └──────────────┬───────────────┘   │
                                   │                    │  debate
                    ┌──────────────▼──────────────┐    │  loop
                    │     🐻 Bear Researcher       │   │  (2 rounds)
                    │   (builds bearish case)       │───┘
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     ⚖️  Research Judge        │
                    │  (verdict + thesis + conf.)  │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     💰 Trader Agent           │
                    │  (action, entry, target,     │
                    │   stop-loss, position size)   │
                    └──────────────┬───────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
     ┌────────▼────────┐ ┌────────▼────────┐  ┌────────▼─────────┐
     │   🔥 Aggressive  │ │   🛡️ Conservative│  │   ⚖️ Neutral     │
     │   Risk Analyst   │ │   Risk Analyst  │  │   Risk Analyst   │◄─┐
     └────────┬────────┘ └────────┬────────┘  └────────┬─────────┘  │
              │                    │                     │  risk      │
              └────────────────────┼────────────────────┘  debate    │
                                   │                       loop     │
                                   │                       (2 rds)  │
                    ┌──────────────▼──────────────┐                 │
                    │     🏛️  Risk Judge (CRO)     │─────────────────┘
                    │  (approved / modified /      │
                    │   rejected + final sizing)   │
                    └──────────────┬───────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │     ✅ Final Trade Decision   │
                    └─────────────────────────────┘
```

### System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            FRONTEND (Next.js 16)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Dashboard    │  │  Agents View │  │  Trades  │  │  Settings    │   │
│  │  (live data,  │  │  (agent      │  │  History │  │              │   │
│  │   charts,     │  │   reasoning, │  │          │  │              │   │
│  │   portfolio)  │  │   debates)   │  │          │  │              │   │
│  └──────┬───────┘  └──────┬───────┘  └────┬─────┘  └──────────────┘   │
│         │                  │               │                            │
│         └──────────────────┼───────────────┘                            │
│                            │ WebSocket + REST                           │
└────────────────────────────┼────────────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                                    │
│                            │                                            │
│  ┌─────────────────────────▼──────────────────────────────────┐        │
│  │                   API Layer (api/main.py)                   │        │
│  │  REST: /analyze, /portfolio, /trades, /price, /indicators   │        │
│  │  WS:   /ws/live (real-time broadcast)                       │        │
│  └───────────────────────────┬────────────────────────────────┘        │
│                              │                                          │
│  ┌───────────────────────────▼────────────────────────────────┐        │
│  │            LangGraph Pipeline (graph/pipeline.py)           │        │
│  │  Compiles all agent nodes into a DAG with conditional edges │        │
│  └───────────────────────────┬────────────────────────────────┘        │
│                              │                                          │
│  ┌───────────┬───────────────┼───────────────┬───────────────┐         │
│  │           │               │               │               │         │
│  │  Analysts │  Researchers  │    Trader     │ Risk Debaters │         │
│  │  (4 LLM   │  (Bull, Bear, │  (trade plan │ (Agg, Cons,   │         │
│  │   nodes)  │   Judge)      │   generator) │  Neutral,     │         │
│  │           │               │              │  Risk Judge)   │         │
│  └───────────┴───────────────┴──────────────┴───────────────┘          │
│                              │                                          │
│  ┌──────────────┬────────────┼────────────┬──────────────────┐         │
│  │  LLM Client  │  Data      │  Memory    │  Confidence      │         │
│  │  (Groq +     │  Providers │  Layer     │  Tracker         │         │
│  │   rate-limit  │ (yfinance, │ (ChromaDB, │ (EMA weights,   │         │
│  │   backoff)   │  CCXT)     │  SQLite)   │  Kelly sizing)   │         │
│  └──────────────┴────────────┴────────────┴──────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Project Structure

```
StockTradingAgents/
├── backend/
│   ├── agents/
│   │   ├── analysts/              # 4 parallel analyst agents
│   │   │   ├── market_analyst.py      # Technical indicators, price action, momentum
│   │   │   ├── sentiment_analyst.py   # Social sentiment, market mood
│   │   │   ├── news_analyst.py        # Headlines, press releases, filings
│   │   │   └── fundamentals_analyst.py # P/E, revenue, margins, balance sheet
│   │   ├── researchers/           # Adversarial debate system
│   │   │   └── researchers.py         # Bull researcher, Bear researcher, Research Judge
│   │   ├── traders/               # Trade execution layer
│   │   │   ├── trader.py              # Converts thesis → trade plan
│   │   │   └── risk_debaters.py       # Aggressive, Conservative, Neutral analysts + CRO Judge
│   │   └── confidence.py          # Adaptive weight scoring + Kelly Criterion sizing
│   ├── api/
│   │   └── main.py                # FastAPI server — REST + WebSocket endpoints
│   ├── data/
│   │   ├── stock_provider.py      # yfinance wrapper (OHLCV, fundamentals, technicals)
│   │   └── crypto_provider.py     # CCXT wrapper (Binance data, order books)
│   ├── graph/
│   │   └── pipeline.py            # LangGraph state machine — compiles all agents into a DAG
│   ├── memory/
│   │   ├── vector_store.py        # ChromaDB semantic memory for past trade contexts
│   │   └── trade_db.py            # SQLite async DB for trades, portfolio, agent accuracy
│   ├── models/
│   │   └── schemas.py             # Pydantic models (20+ types: reports, debates, signals, etc.)
│   ├── utils/
│   │   └── json_parser.py         # Resilient JSON extraction from LLM output
│   ├── config.py                  # Central config (env vars, pipeline params, paths)
│   ├── llm_client.py              # Groq LLM client with rate-limit backoff + concurrency throttle
│   └── requirements.txt
├── frontend/
│   ├── app/                       # Next.js 16 App Router pages
│   │   ├── page.tsx                   # Landing / dashboard
│   │   ├── agents/                    # Agent reasoning & debate viewer
│   │   ├── trades/                    # Trade history table
│   │   └── settings/                  # Configuration panel
│   ├── components/
│   │   ├── DashboardContent.tsx       # Main dashboard with charts & portfolio
│   │   ├── Sidebar.tsx                # Navigation sidebar
│   │   ├── AppShell.tsx               # Layout wrapper
│   │   └── ParticleScene.tsx          # Three.js particle background
│   └── public/                    # Static assets
└── README.md
```

---

## ⚙️ How the Pipeline Works

### 1. Parallel Analysis (Fan-Out)

All four analysts **execute simultaneously** using LangGraph's fan-out pattern. Each analyst uses a `quick_thinker` LLM (optimized for speed) and generates a structured `AnalystReport` with sentiment, confidence, key findings, and raw data:

| Analyst | Data Source | Key Metrics |
|:--------|:-----------|:------------|
| **Market** | yfinance / CCXT | RSI, MACD, Bollinger Bands, SMA crossovers, volume profile |
| **Sentiment** | Market mood analysis | Social buzz, fear/greed signals, momentum sentiment |
| **News** | Headlines & filings | Event impact, catalyst identification, headline sentiment |
| **Fundamentals** | Company financials | P/E, revenue growth, margins, debt-to-equity, cash flow |

### 2. Investment Debate (Bull vs Bear)

The analyst reports are fed into an **adversarial debate**:

- **Bull Researcher** — constructs the strongest bullish case using analyst evidence
- **Bear Researcher** — directly counters with bearish arguments, risks, and red flags
- The debate runs for **2 configurable rounds** of back-and-forth
- **Research Judge** — a `deep_thinker` LLM evaluates both sides and delivers:
  - A verdict (`bullish` / `bearish` / `neutral`)
  - A confidence score
  - A synthesized investment thesis

### 3. Trade Planning

The **Trader Agent** receives the research thesis and converts it into a concrete, actionable trade plan:

- **Action**: `buy`, `sell`, `hold`, `short`, or `cover`
- **Entry price**, **target price**, **stop-loss**
- **Position size** (capped at 30% of portfolio)
- Consults **vector memory** for similar past trades to avoid repeating mistakes

### 4. Risk Debate (Three-Way)

Before any trade is finalized, three risk analysts debate it:

- **Aggressive** — argues for larger positions, acceptable drawdowns
- **Conservative** — argues for smaller positions, tighter stops
- **Neutral** — balances risk and reward objectively

After **2 rounds**, the **Risk Judge (CRO)** makes the final call:
- Approve, modify, or reject the trade
- Set final position size and stop-loss parameters
- Calculate max portfolio risk percentage

### 5. Adaptive Confidence

Agents have **adaptive weights** that evolve based on accuracy:

- Predictions are tracked over time via `ConfidenceTracker`
- Weights adjust using an EMA-like formula: `weight = 0.5 + accuracy`
- Position sizing uses the **Kelly Criterion** (half-Kelly for safety, capped at 25%)

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|:------|:-----------|:--------|
| **Agent Framework** | LangChain + LangGraph | Agent nodes, state management, parallel DAG execution |
| **LLM Provider** | Groq (Kimi K2) | Fast inference with rate-limit-resilient wrapper |
| **API Server** | FastAPI + WebSockets | REST endpoints + real-time streaming |
| **Stock Data** | yfinance + stockstats | OHLCV, fundamentals, technical indicators, news |
| **Crypto Data** | CCXT (Binance) | Candles, ticker info, order books |
| **Vector Memory** | ChromaDB | Semantic search over past trade situations |
| **Trade Database** | SQLite (aiosqlite) | Trade history, portfolio snapshots, agent accuracy |
| **Frontend** | Next.js 16, TypeScript | App Router, server/client components |
| **UI Libraries** | Recharts, Three.js, Framer Motion | Charts, 3D particle effects, animations |
| **Styling** | Tailwind CSS 4 | Utility-first responsive design |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- A free [Groq API key](https://console.groq.com)

### Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env    # Add your API keys
python -m uvicorn api.main:app --reload
```

The backend runs at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:3000`.

### Environment Variables

Copy `backend/.env.example` → `backend/.env` and configure:

| Variable | Required | Description |
|:---------|:--------:|:------------|
| `GROQ_API_KEY` | ✅ | Free at [console.groq.com](https://console.groq.com) |
| `ALPACA_API_KEY` | ❌ | Paper trading via [Alpaca](https://alpaca.markets) |
| `ALPACA_SECRET_KEY` | ❌ | Alpaca secret key |
| `TELEGRAM_BOT_TOKEN` | ❌ | Telegram alert notifications |
| `DISCORD_WEBHOOK_URL` | ❌ | Discord alert webhook |

---

## 📡 API Reference

### REST Endpoints

| Method | Endpoint | Description |
|:------:|:---------|:------------|
| `POST` | `/analyze` | Run the full 13-agent pipeline for a ticker |
| `GET` | `/portfolio` | Current portfolio state (cash, positions, P&L) |
| `GET` | `/portfolio/history` | Portfolio value history for charting |
| `GET` | `/trades` | Trade history with optional ticker filter |
| `GET` | `/price/{ticker}` | Current price + fundamental data |
| `GET` | `/indicators/{ticker}` | Technical indicators (RSI, MACD, Bollinger, etc.) |
| `GET` | `/health` | Health check |

### WebSocket

| Protocol | Endpoint | Description |
|:--------:|:---------|:------------|
| `WS` | `/ws/live` | Real-time broadcast of analysis updates, trade signals, and portfolio changes |

**Message types**: `analysis_update`, `trade_signal`, `portfolio_update`, `agent_reasoning`

---

## ✨ Key Features

- **🔀 Parallel Execution** — 4 analysts run simultaneously via LangGraph fan-out, cutting analysis time by ~4×
- **⚔️ Adversarial Debates** — Bull vs Bear researchers argue with evidence across multiple rounds, judged by a Research Director
- **🛡️ Risk Committee** — Every trade goes through a 3-way risk debate before approval
- **⏳ Rate-Limit Resilience** — Exponential backoff + jitter + concurrency semaphore for Groq API
- **📈 Adaptive Confidence** — Agent weights evolve based on historical accuracy using EMA smoothing
- **🧠 Vector Memory** — ChromaDB stores past analyses for semantic retrieval, preventing repeated mistakes
- **📊 Real-time Dashboard** — WebSocket-powered live updates with portfolio charts and agent reasoning
- **🪙 Dual Asset Support** — Stocks (yfinance) and crypto (CCXT/Binance) in the same pipeline
- **📐 Kelly Criterion Sizing** — Position sizes calculated using half-Kelly with 25% cap for safety

---

## ⚙️ Configuration

Key pipeline parameters in `backend/config.py`:

| Parameter | Default | Description |
|:----------|:-------:|:------------|
| `MAX_DEBATE_ROUNDS` | 2 | Bull/Bear research debate rounds |
| `MAX_RISK_DEBATE_ROUNDS` | 2 | Risk committee debate rounds |
| `ANALYST_TIMEOUT` | 60s | Max seconds per analyst agent |
| `AUTO_TRADE_CONFIDENCE` | 0.85 | Auto-approve trades above this confidence |
| `APPROVAL_QUEUE_TTL` | 300s | Seconds before pending approvals expire |
| `LLM_TEMPERATURE` | 0.7 | LLM creativity (higher = more varied analysis) |

---

## 📄 License

MIT
