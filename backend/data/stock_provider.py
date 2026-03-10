"""
NexusTrade — Stock Data Provider (Alpha Vantage)
Wraps Alpha Vantage REST API for stock market data, technicals, and fundamentals.
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
import logging

from config import ALPHA_VANTAGE_API_KEY

logger = logging.getLogger("nexustrade.stockdata")

AV_BASE = "https://www.alphavantage.co/query"


class StockProvider:
    """Provides stock market data via Alpha Vantage."""

    def __init__(self):
        self._api_key = ALPHA_VANTAGE_API_KEY
        self._cache: dict[str, dict] = {}

    def _av_request(self, params: dict) -> dict:
        """Make a request to Alpha Vantage API."""
        params["apikey"] = self._api_key
        try:
            resp = requests.get(AV_BASE, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if "Error Message" in data:
                logger.warning(f"Alpha Vantage error: {data['Error Message']}")
                return {}
            if "Note" in data:
                logger.warning(f"Alpha Vantage rate limit: {data['Note']}")
                return {}
            return data
        except Exception as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            return {}

    def get_price_data(self, ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
        """Get OHLCV price data via Alpha Vantage TIME_SERIES_DAILY."""
        try:
            data = self._av_request({
                "function": "TIME_SERIES_DAILY",
                "symbol": ticker,
                "outputsize": "compact",  # last 100 data points
            })

            ts_key = "Time Series (Daily)"
            if ts_key not in data:
                return pd.DataFrame()

            records = []
            for date_str, values in data[ts_key].items():
                records.append({
                    "Date": pd.Timestamp(date_str),
                    "Open": float(values["1. open"]),
                    "High": float(values["2. high"]),
                    "Low": float(values["3. low"]),
                    "Close": float(values["4. close"]),
                    "Volume": int(values["5. volume"]),
                })

            df = pd.DataFrame(records)
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)
            return df
        except Exception as e:
            logger.error(f"get_price_data failed for {ticker}: {e}")
            return pd.DataFrame()

    def get_current_price(self, ticker: str) -> Optional[float]:
        """Get current/latest price via GLOBAL_QUOTE."""
        try:
            data = self._av_request({
                "function": "GLOBAL_QUOTE",
                "symbol": ticker,
            })
            quote = data.get("Global Quote", {})
            price = quote.get("05. price")
            return float(price) if price else None
        except Exception:
            return None

    def get_technical_indicators(self, ticker: str, period: str = "6mo") -> dict:
        """Calculate technical indicators from price data + Alpha Vantage technicals."""
        df = self.get_price_data(ticker, period=period)
        if df.empty:
            return {}

        try:
            close = df["Close"]
            indicators: dict = {
                "current_price": float(close.iloc[-1]),
                "price_change_1d": float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) > 1 else 0,
                "price_change_5d": float((close.iloc[-1] / close.iloc[-5] - 1) * 100) if len(close) > 5 else 0,
                "price_change_1m": float((close.iloc[-1] / close.iloc[-21] - 1) * 100) if len(close) > 21 else 0,
            }

            # RSI (14-period)
            if len(close) > 14:
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                indicators["rsi_14"] = float((100 - 100 / (1 + rs)).iloc[-1])

            # MACD
            if len(close) > 26:
                ema12 = close.ewm(span=12).mean()
                ema26 = close.ewm(span=26).mean()
                macd_line = ema12 - ema26
                signal_line = macd_line.ewm(span=9).mean()
                indicators["macd"] = float(macd_line.iloc[-1])
                indicators["macd_signal"] = float(signal_line.iloc[-1])
                indicators["macd_hist"] = float((macd_line - signal_line).iloc[-1])

            # SMAs
            if len(close) > 20:
                indicators["sma_20"] = float(close.rolling(20).mean().iloc[-1])
            if len(close) > 50:
                indicators["sma_50"] = float(close.rolling(50).mean().iloc[-1])

            # EMA 12
            if len(close) > 12:
                indicators["ema_12"] = float(close.ewm(span=12).mean().iloc[-1])

            # Bollinger Bands
            if len(close) > 20:
                sma20 = close.rolling(20).mean()
                std20 = close.rolling(20).std()
                indicators["bollinger_upper"] = float((sma20 + 2 * std20).iloc[-1])
                indicators["bollinger_lower"] = float((sma20 - 2 * std20).iloc[-1])

            # Volume average
            if len(df) > 20:
                indicators["volume_avg_20"] = float(df["Volume"].rolling(20).mean().iloc[-1])

            return indicators
        except Exception as e:
            return {"error": str(e)}

    def get_fundamentals(self, ticker: str) -> dict:
        """Get fundamental company data via OVERVIEW endpoint."""
        try:
            data = self._av_request({
                "function": "OVERVIEW",
                "symbol": ticker,
            })
            if not data:
                return {}

            def safe_float(val):
                try:
                    return float(val) if val and val != "None" and val != "-" else None
                except (ValueError, TypeError):
                    return None

            return {
                "market_cap": safe_float(data.get("MarketCapitalization")),
                "pe_ratio": safe_float(data.get("TrailingPE")),
                "forward_pe": safe_float(data.get("ForwardPE")),
                "pb_ratio": safe_float(data.get("PriceToBookRatio")),
                "dividend_yield": safe_float(data.get("DividendYield")),
                "eps": safe_float(data.get("EPS")),
                "revenue": safe_float(data.get("RevenueTTM")),
                "profit_margin": safe_float(data.get("ProfitMargin")),
                "roe": safe_float(data.get("ReturnOnEquityTTM")),
                "debt_to_equity": safe_float(data.get("DebtToEquityRatio") or data.get("DebtToEquity")),
                "current_ratio": safe_float(data.get("CurrentRatio")),
                "sector": data.get("Sector"),
                "industry": data.get("Industry"),
                "full_name": data.get("Name"),
                "description": (data.get("Description") or "")[:500],
                "52_week_high": safe_float(data.get("52WeekHigh")),
                "52_week_low": safe_float(data.get("52WeekLow")),
                "beta": safe_float(data.get("Beta")),
                "ev_to_ebitda": safe_float(data.get("EVToEBITDA")),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_balance_sheet(self, ticker: str) -> dict:
        """Get balance sheet data."""
        try:
            data = self._av_request({
                "function": "BALANCE_SHEET",
                "symbol": ticker,
            })
            reports = data.get("annualReports", [])
            if not reports:
                return {}

            latest = reports[0]
            result = {}
            for k, v in latest.items():
                try:
                    result[k] = float(v) if v and v != "None" else None
                except (ValueError, TypeError):
                    result[k] = v
            return result
        except Exception:
            return {}

    def get_cashflow(self, ticker: str) -> dict:
        """Get cash flow statement."""
        try:
            data = self._av_request({
                "function": "CASH_FLOW",
                "symbol": ticker,
            })
            reports = data.get("annualReports", [])
            if not reports:
                return {}

            latest = reports[0]
            result = {}
            for k, v in latest.items():
                try:
                    result[k] = float(v) if v and v != "None" else None
                except (ValueError, TypeError):
                    result[k] = v
            return result
        except Exception:
            return {}

    def get_income_statement(self, ticker: str) -> dict:
        """Get income statement."""
        try:
            data = self._av_request({
                "function": "INCOME_STATEMENT",
                "symbol": ticker,
            })
            reports = data.get("annualReports", [])
            if not reports:
                return {}

            latest = reports[0]
            result = {}
            for k, v in latest.items():
                try:
                    result[k] = float(v) if v and v != "None" else None
                except (ValueError, TypeError):
                    result[k] = v
            return result
        except Exception:
            return {}

    def get_news(self, ticker: str) -> list[dict]:
        """Get recent news for ticker via NEWS_SENTIMENT."""
        try:
            data = self._av_request({
                "function": "NEWS_SENTIMENT",
                "tickers": ticker,
                "limit": "10",
            })
            feeds = data.get("feed", [])
            return [
                {
                    "title": item.get("title", ""),
                    "publisher": item.get("source", ""),
                    "link": item.get("url", ""),
                    "published": item.get("time_published", ""),
                    "type": "news",
                    "overall_sentiment": item.get("overall_sentiment_label", ""),
                }
                for item in feeds[:10]
            ]
        except Exception:
            return []

    def get_insider_transactions(self, ticker: str) -> list[dict]:
        """Get insider transactions (Alpha Vantage doesn't have this — return empty)."""
        # Alpha Vantage free tier doesn't support insider data
        return []
