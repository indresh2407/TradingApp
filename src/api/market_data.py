"""
Market Data Handler
Fetches and processes market data for trading decisions
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
import ta


class MarketData:
    """Handles market data retrieval and technical analysis"""
    
    def __init__(self, kotak_client):
        self.client = kotak_client
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 1
        
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """Get Last Traded Price for a symbol"""
        try:
            quote = self.client.get_quote(symbol, exchange)
            if quote and "data" in quote:
                return float(quote["data"].get("ltp", 0))
            return None
        except Exception as e:
            logger.error(f"Failed to get LTP for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Get full quote data for a symbol"""
        cache_key = f"{exchange}:{symbol}"
        
        if cache_key in self._quote_cache:
            cached = self._quote_cache[cache_key]
            if (datetime.now() - cached["timestamp"]).seconds < self._cache_ttl_seconds:
                return cached["data"]
        
        try:
            quote = self.client.get_quote(symbol, exchange)
            if quote and "data" in quote:
                self._quote_cache[cache_key] = {
                    "data": quote["data"],
                    "timestamp": datetime.now()
                }
                return quote["data"]
            return None
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    def get_ohlc(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, float]]:
        """Get OHLC data for a symbol"""
        quote = self.get_quote(symbol, exchange)
        if quote:
            return {
                "open": float(quote.get("open", 0)),
                "high": float(quote.get("high", 0)),
                "low": float(quote.get("low", 0)),
                "close": float(quote.get("ltp", 0)),
                "volume": int(quote.get("volume", 0))
            }
        return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators on OHLC data
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
            
        Returns:
            DataFrame with added indicator columns
        """
        if df.empty or len(df) < 20:
            logger.warning("Insufficient data for indicator calculation")
            return df
        
        df = df.copy()
        
        # Moving Averages
        df["ema_9"] = ta.trend.ema_indicator(df["close"], window=9)
        df["ema_21"] = ta.trend.ema_indicator(df["close"], window=21)
        df["sma_50"] = ta.trend.sma_indicator(df["close"], window=50)
        
        # RSI
        df["rsi"] = ta.momentum.rsi(df["close"], window=14)
        
        # MACD
        macd = ta.trend.MACD(df["close"])
        df["macd"] = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        df["macd_histogram"] = macd.macd_diff()
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df["close"], window=20)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_middle"] = bb.bollinger_mavg()
        df["bb_lower"] = bb.bollinger_lband()
        
        # ATR for volatility
        df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
        
        # Volume indicators
        df["volume_sma"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma"]
        
        return df
    
    def get_signal_rsi(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate RSI-based trading signal
        
        Returns:
            Dict with signal, strength, and reasoning
        """
        if df.empty or "rsi" not in df.columns:
            return {"signal": "HOLD", "strength": 0, "reason": "Insufficient data"}
        
        current_rsi = df["rsi"].iloc[-1]
        prev_rsi = df["rsi"].iloc[-2] if len(df) > 1 else current_rsi
        
        if current_rsi < 30 and prev_rsi < current_rsi:
            return {
                "signal": "BUY",
                "strength": min((30 - current_rsi) / 10, 1.0),
                "reason": f"RSI oversold at {current_rsi:.1f}, showing reversal"
            }
        elif current_rsi > 70 and prev_rsi > current_rsi:
            return {
                "signal": "SELL",
                "strength": min((current_rsi - 70) / 10, 1.0),
                "reason": f"RSI overbought at {current_rsi:.1f}, showing reversal"
            }
        else:
            return {
                "signal": "HOLD",
                "strength": 0,
                "reason": f"RSI neutral at {current_rsi:.1f}"
            }
    
    def get_signal_ema_crossover(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate EMA crossover signal (9/21)
        
        Returns:
            Dict with signal, strength, and reasoning
        """
        if df.empty or "ema_9" not in df.columns or "ema_21" not in df.columns:
            return {"signal": "HOLD", "strength": 0, "reason": "Insufficient data"}
        
        ema_9 = df["ema_9"].iloc[-1]
        ema_21 = df["ema_21"].iloc[-1]
        prev_ema_9 = df["ema_9"].iloc[-2] if len(df) > 1 else ema_9
        prev_ema_21 = df["ema_21"].iloc[-2] if len(df) > 1 else ema_21
        
        current_diff = ema_9 - ema_21
        prev_diff = prev_ema_9 - prev_ema_21
        
        # Bullish crossover
        if prev_diff <= 0 and current_diff > 0:
            return {
                "signal": "BUY",
                "strength": 0.8,
                "reason": f"EMA 9 crossed above EMA 21 (bullish)"
            }
        # Bearish crossover
        elif prev_diff >= 0 and current_diff < 0:
            return {
                "signal": "SELL",
                "strength": 0.8,
                "reason": f"EMA 9 crossed below EMA 21 (bearish)"
            }
        # Trend continuation
        elif current_diff > 0:
            return {
                "signal": "HOLD",
                "strength": 0.3,
                "reason": f"Bullish trend continues (EMA 9 > EMA 21)"
            }
        else:
            return {
                "signal": "HOLD",
                "strength": 0.3,
                "reason": f"Bearish trend continues (EMA 9 < EMA 21)"
            }
    
    def get_combined_signal(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        """Combine multiple signals for a final recommendation"""
        rsi_signal = self.get_signal_rsi(symbol, df)
        ema_signal = self.get_signal_ema_crossover(symbol, df)
        
        signals = [rsi_signal, ema_signal]
        
        buy_score = sum(1 for s in signals if s["signal"] == "BUY")
        sell_score = sum(1 for s in signals if s["signal"] == "SELL")
        
        if buy_score >= 2:
            return {
                "signal": "STRONG_BUY",
                "strength": 0.9,
                "reasons": [s["reason"] for s in signals if s["signal"] == "BUY"]
            }
        elif buy_score == 1 and sell_score == 0:
            return {
                "signal": "BUY",
                "strength": 0.6,
                "reasons": [s["reason"] for s in signals if s["signal"] == "BUY"]
            }
        elif sell_score >= 2:
            return {
                "signal": "STRONG_SELL",
                "strength": 0.9,
                "reasons": [s["reason"] for s in signals if s["signal"] == "SELL"]
            }
        elif sell_score == 1 and buy_score == 0:
            return {
                "signal": "SELL",
                "strength": 0.6,
                "reasons": [s["reason"] for s in signals if s["signal"] == "SELL"]
            }
        else:
            return {
                "signal": "HOLD",
                "strength": 0,
                "reasons": ["Mixed signals - no clear direction"]
            }


class PaperMarketData:
    """
    Market data provider for paper trading mode.
    Uses Yahoo Finance (via LiveDataProvider) instead of Kotak API.
    """
    
    def __init__(self):
        from .live_data import get_live_data_provider
        self.live_provider = get_live_data_provider()
        self._quote_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 5
        
    def get_ltp(self, symbol: str, exchange: str = "NSE") -> Optional[float]:
        """Get Last Traded Price for a symbol"""
        try:
            quote = self.live_provider.get_quote(symbol)
            if quote:
                return float(quote.get("ltp", 0))
            return None
        except Exception as e:
            logger.error(f"Failed to get LTP for {symbol}: {e}")
            return None
    
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, Any]]:
        """Get full quote data for a symbol"""
        try:
            quote = self.live_provider.get_quote(symbol)
            return quote
        except Exception as e:
            logger.error(f"Failed to get quote for {symbol}: {e}")
            return None
    
    def get_ohlc(self, symbol: str, exchange: str = "NSE") -> Optional[Dict[str, float]]:
        """Get OHLC data for a symbol"""
        try:
            quote = self.get_quote(symbol, exchange)
            if quote:
                return {
                    "open": float(quote.get("open", 0)),
                    "high": float(quote.get("high", 0)),
                    "low": float(quote.get("low", 0)),
                    "close": float(quote.get("ltp", quote.get("close", 0))),
                    "volume": int(quote.get("volume", 0))
                }
            logger.debug(f"No quote data available for {symbol}")
            return None
        except Exception as e:
            logger.debug(f"Error getting OHLC for {symbol}: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate technical indicators on OHLC data
        Uses the same logic as MarketData
        """
        if df.empty or len(df) < 1:
            return df
        
        try:
            # For single row data, just return basic columns
            if len(df) == 1:
                df = df.copy()
                df["rsi"] = 50.0  # Neutral
                df["sma_5"] = df["close"].iloc[0]
                df["sma_20"] = df["close"].iloc[0]
                df["ema_9"] = df["close"].iloc[0]
                df["ema_21"] = df["close"].iloc[0]
                df["atr"] = (df["high"].iloc[0] - df["low"].iloc[0]) * 0.5
                df["volume_sma"] = df["volume"].iloc[0]
                df["volume_ratio"] = 1.0
                return df
                
            # For multiple rows, calculate actual indicators
            df = df.copy()
            
            # RSI
            if len(df) >= 14:
                df["rsi"] = ta.momentum.rsi(df["close"], window=14)
            else:
                df["rsi"] = 50.0
            
            # Moving Averages
            df["sma_5"] = df["close"].rolling(window=min(5, len(df))).mean()
            df["sma_20"] = df["close"].rolling(window=min(20, len(df))).mean()
            df["ema_9"] = df["close"].ewm(span=min(9, len(df)), adjust=False).mean()
            df["ema_21"] = df["close"].ewm(span=min(21, len(df)), adjust=False).mean()
            
            # ATR
            if len(df) >= 14:
                df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            else:
                df["atr"] = (df["high"] - df["low"]).mean()
            
            # Volume analysis
            df["volume_sma"] = df["volume"].rolling(window=min(20, len(df))).mean()
            df["volume_ratio"] = df["volume"] / df["volume_sma"].replace(0, 1)
            
            # Fill NaN values
            df = df.fillna(method='bfill').fillna(method='ffill')
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df
