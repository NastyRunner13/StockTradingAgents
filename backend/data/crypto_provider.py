"""
NexusTrade — Crypto Data Provider
Wraps CCXT for cryptocurrency market data.
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


class CryptoProvider:
    """Provides cryptocurrency market data via CCXT (Binance)."""

    def __init__(self, exchange_id: str = "binance"):
        try:
            self.exchange = getattr(ccxt, exchange_id)({
                "enableRateLimit": True,
            })
        except Exception:
            self.exchange = ccxt.binance({"enableRateLimit": True})

    def get_price_data(self, symbol: str, timeframe: str = "1d", limit: int = 90) -> pd.DataFrame:
        """Get OHLCV candle data.
        
        Args:
            symbol: Trading pair like 'BTC/USDT' or 'ETH/USDT'
            timeframe: Candle timeframe ('1m','5m','1h','4h','1d','1w')
            limit: Number of candles
        """
        try:
            # Normalize symbol format
            symbol = self._normalize_symbol(symbol)
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df
        except Exception as e:
            return pd.DataFrame()

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a crypto pair."""
        try:
            symbol = self._normalize_symbol(symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get("last")
        except Exception:
            return None

    def get_ticker_info(self, symbol: str) -> dict:
        """Get 24h ticker statistics."""
        try:
            symbol = self._normalize_symbol(symbol)
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last_price": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high_24h": ticker.get("high"),
                "low_24h": ticker.get("low"),
                "volume_24h": ticker.get("baseVolume"),
                "change_24h": ticker.get("change"),
                "change_pct_24h": ticker.get("percentage"),
                "vwap": ticker.get("vwap"),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_technical_indicators(self, symbol: str, timeframe: str = "1d", limit: int = 100) -> dict:
        """Calculate basic technical indicators for crypto."""
        df = self.get_price_data(symbol, timeframe, limit)
        if df.empty:
            return {}

        try:
            close = df["close"]
            indicators = {
                "current_price": float(close.iloc[-1]),
                "price_change_24h": float((close.iloc[-1] / close.iloc[-2] - 1) * 100) if len(close) > 1 else 0,
                "price_change_7d": float((close.iloc[-1] / close.iloc[-7] - 1) * 100) if len(close) > 7 else 0,
                "price_change_30d": float((close.iloc[-1] / close.iloc[-30] - 1) * 100) if len(close) > 30 else 0,
            }

            # RSI
            if len(close) > 14:
                delta = close.diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                indicators["rsi_14"] = float((100 - 100 / (1 + rs)).iloc[-1])

            # SMA
            if len(close) > 20:
                indicators["sma_20"] = float(close.rolling(20).mean().iloc[-1])
            if len(close) > 50:
                indicators["sma_50"] = float(close.rolling(50).mean().iloc[-1])

            # Volume profile
            indicators["volume_avg_20"] = float(df["volume"].rolling(20).mean().iloc[-1]) if len(df) > 20 else None

            return indicators
        except Exception as e:
            return {"error": str(e)}

    def get_order_book(self, symbol: str, limit: int = 10) -> dict:
        """Get order book depth."""
        try:
            symbol = self._normalize_symbol(symbol)
            ob = self.exchange.fetch_order_book(symbol, limit=limit)
            return {
                "bids": ob.get("bids", [])[:limit],
                "asks": ob.get("asks", [])[:limit],
                "spread": ob["asks"][0][0] - ob["bids"][0][0] if ob.get("asks") and ob.get("bids") else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol format to CCXT standard (e.g., BTC/USD → BTC/USDT)."""
        symbol = symbol.upper().strip()
        if symbol.endswith("/USD"):
            symbol = symbol.replace("/USD", "/USDT")
        if "/" not in symbol:
            symbol = f"{symbol}/USDT"
        return symbol
