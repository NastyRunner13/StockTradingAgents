"""
NexusTrade — Stock Data Provider
Wraps yfinance for stock market data, technicals, and fundamentals.
"""

import yfinance as yf
import pandas as pd
from stockstats import StockDataFrame
from datetime import datetime, timedelta
from typing import Optional


class StockProvider:
    """Provides stock market data via yfinance."""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def get_price_data(self, ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
        """Get OHLCV price data."""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            return df
        except Exception as e:
            return pd.DataFrame()

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current/latest price."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get("currentPrice") or info.get("regularMarketPrice")
        except Exception:
            return None

    def get_technical_indicators(self, ticker: str, period: str = "6mo") -> dict:
        """Calculate technical indicators using stockstats."""
        df = self.get_price_data(ticker, period=period)
        if df.empty:
            return {}

        try:
            sdf = StockDataFrame.retype(df.copy())
            indicators = {
                "rsi_14": float(sdf["rsi_14"].iloc[-1]) if len(sdf) > 14 else None,
                "macd": float(sdf["macd"].iloc[-1]) if len(sdf) > 26 else None,
                "macd_signal": float(sdf["macds"].iloc[-1]) if len(sdf) > 26 else None,
                "macd_hist": float(sdf["macdh"].iloc[-1]) if len(sdf) > 26 else None,
                "sma_20": float(df["Close"].rolling(20).mean().iloc[-1]) if len(df) > 20 else None,
                "sma_50": float(df["Close"].rolling(50).mean().iloc[-1]) if len(df) > 50 else None,
                "ema_12": float(df["Close"].ewm(span=12).mean().iloc[-1]) if len(df) > 12 else None,
                "bollinger_upper": None,
                "bollinger_lower": None,
                "volume_avg_20": float(df["Volume"].rolling(20).mean().iloc[-1]) if len(df) > 20 else None,
                "current_price": float(df["Close"].iloc[-1]),
                "price_change_1d": float((df["Close"].iloc[-1] / df["Close"].iloc[-2] - 1) * 100) if len(df) > 1 else 0,
                "price_change_5d": float((df["Close"].iloc[-1] / df["Close"].iloc[-5] - 1) * 100) if len(df) > 5 else 0,
                "price_change_1m": float((df["Close"].iloc[-1] / df["Close"].iloc[-21] - 1) * 100) if len(df) > 21 else 0,
            }

            # Bollinger Bands
            if len(df) > 20:
                sma20 = df["Close"].rolling(20).mean()
                std20 = df["Close"].rolling(20).std()
                indicators["bollinger_upper"] = float((sma20 + 2 * std20).iloc[-1])
                indicators["bollinger_lower"] = float((sma20 - 2 * std20).iloc[-1])

            return indicators
        except Exception as e:
            return {"error": str(e)}

    def get_fundamentals(self, ticker: str) -> dict:
        """Get fundamental company data."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "eps": info.get("trailingEps"),
                "revenue": info.get("totalRevenue"),
                "profit_margin": info.get("profitMargins"),
                "roe": info.get("returnOnEquity"),
                "debt_to_equity": info.get("debtToEquity"),
                "current_ratio": info.get("currentRatio"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "full_name": info.get("longName"),
                "description": info.get("longBusinessSummary", "")[:500],
            }
        except Exception as e:
            return {"error": str(e)}

    def get_balance_sheet(self, ticker: str) -> dict:
        """Get balance sheet data."""
        try:
            stock = yf.Ticker(ticker)
            bs = stock.balance_sheet
            if bs.empty:
                return {}
            latest = bs.iloc[:, 0]
            return {k: float(v) if pd.notna(v) else None for k, v in latest.items()}
        except Exception:
            return {}

    def get_cashflow(self, ticker: str) -> dict:
        """Get cash flow statement."""
        try:
            stock = yf.Ticker(ticker)
            cf = stock.cashflow
            if cf.empty:
                return {}
            latest = cf.iloc[:, 0]
            return {k: float(v) if pd.notna(v) else None for k, v in latest.items()}
        except Exception:
            return {}

    def get_income_statement(self, ticker: str) -> dict:
        """Get income statement."""
        try:
            stock = yf.Ticker(ticker)
            inc = stock.income_stmt
            if inc.empty:
                return {}
            latest = inc.iloc[:, 0]
            return {k: float(v) if pd.notna(v) else None for k, v in latest.items()}
        except Exception:
            return {}

    def get_news(self, ticker: str) -> list[dict]:
        """Get recent news for ticker."""
        try:
            stock = yf.Ticker(ticker)
            news = stock.news or []
            return [
                {
                    "title": item.get("title", ""),
                    "publisher": item.get("publisher", ""),
                    "link": item.get("link", ""),
                    "published": item.get("providerPublishTime", ""),
                    "type": item.get("type", ""),
                }
                for item in news[:10]
            ]
        except Exception:
            return []

    def get_insider_transactions(self, ticker: str) -> list[dict]:
        """Get insider transactions."""
        try:
            stock = yf.Ticker(ticker)
            insiders = stock.insider_transactions
            if insiders is None or insiders.empty:
                return []
            return insiders.head(10).to_dict("records")
        except Exception:
            return []
