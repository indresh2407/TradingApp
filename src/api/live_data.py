"""
Live Market Data Provider
Fetches real-time stock prices from Yahoo Finance
"""

import yfinance as yf
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger


# NSE symbol to Yahoo Finance symbol mapping
NSE_TO_YAHOO = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "INFY": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "ITC": "ITC.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "LT": "LT.NS",
    "AXISBANK": "AXISBANK.NS",
    "MARUTI": "MARUTI.NS",
    "WIPRO": "WIPRO.NS",
    "HCLTECH": "HCLTECH.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "TITAN": "TITAN.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    # Indices
    "NIFTY 50": "^NSEI",
    "NIFTY BANK": "^NSEBANK",
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
}


class LiveDataProvider:
    """Provides live market data from Yahoo Finance"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 60  # Cache for 60 seconds
        self._last_fetch: Dict[str, datetime] = {}
    
    def _get_yahoo_symbol(self, nse_symbol: str) -> str:
        """Convert NSE symbol to Yahoo Finance symbol"""
        symbol = nse_symbol.upper().strip()
        if symbol in NSE_TO_YAHOO:
            return NSE_TO_YAHOO[symbol]
        # Default: append .NS for NSE stocks
        return f"{symbol}.NS"
    
    def _is_cache_valid(self, symbol: str) -> bool:
        """Check if cached data is still valid"""
        if symbol not in self._last_fetch:
            return False
        elapsed = (datetime.now() - self._last_fetch[symbol]).seconds
        return elapsed < self._cache_ttl
    
    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get live quote for a single symbol
        
        Returns:
            Dict with ltp, open, high, low, close, volume, change, change_pct
        """
        # Check cache
        if self._is_cache_valid(symbol) and symbol in self._cache:
            return self._cache[symbol]
        
        try:
            yahoo_symbol = self._get_yahoo_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            
            # Get current data
            info = ticker.fast_info
            hist = ticker.history(period="2d")
            
            if hist.empty:
                return None
            
            current_price = float(info.last_price) if hasattr(info, 'last_price') else float(hist['Close'].iloc[-1])
            prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
            
            quote = {
                "symbol": symbol,
                "ltp": current_price,
                "open": float(hist['Open'].iloc[-1]),
                "high": float(hist['High'].iloc[-1]),
                "low": float(hist['Low'].iloc[-1]),
                "close": current_price,
                "prev_close": prev_close,
                "volume": int(hist['Volume'].iloc[-1]),
                "change": current_price - prev_close,
                "change_pct": ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            # Cache the result
            self._cache[symbol] = quote
            self._last_fetch[symbol] = datetime.now()
            
            return quote
            
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            return None
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get quotes for multiple symbols"""
        results = {}
        
        # Convert symbols
        yahoo_symbols = [self._get_yahoo_symbol(s) for s in symbols]
        
        try:
            # Batch download
            data = yf.download(
                yahoo_symbols,
                period="2d",
                progress=False,
                threads=True
            )
            
            for i, symbol in enumerate(symbols):
                yahoo_sym = yahoo_symbols[i]
                
                try:
                    if len(symbols) == 1:
                        hist = data
                    else:
                        hist = data.xs(yahoo_sym, axis=1, level=1) if yahoo_sym in data.columns.get_level_values(1) else None
                    
                    if hist is None or hist.empty:
                        continue
                    
                    current_price = float(hist['Close'].iloc[-1])
                    prev_close = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current_price
                    
                    results[symbol] = {
                        "symbol": symbol,
                        "ltp": current_price,
                        "open": float(hist['Open'].iloc[-1]),
                        "high": float(hist['High'].iloc[-1]),
                        "low": float(hist['Low'].iloc[-1]),
                        "close": current_price,
                        "prev_close": prev_close,
                        "volume": int(hist['Volume'].iloc[-1]),
                        "change": current_price - prev_close,
                        "change_pct": ((current_price - prev_close) / prev_close) * 100 if prev_close > 0 else 0,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Cache
                    self._cache[symbol] = results[symbol]
                    self._last_fetch[symbol] = datetime.now()
                    
                except Exception as e:
                    logger.debug(f"Failed to process {symbol}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to fetch batch quotes: {e}")
            # Fall back to individual fetches
            for symbol in symbols:
                quote = self.get_quote(symbol)
                if quote:
                    results[symbol] = quote
        
        return results
    
    def get_historical(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Get historical OHLCV data
        
        Args:
            symbol: Stock symbol
            period: Valid periods: 1d,5d,1mo,3mo,6mo,1y,2y,5y,10y,ytd,max
            interval: Valid intervals: 1m,2m,5m,15m,30m,60m,90m,1h,1d,5d,1wk,1mo,3mo
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            yahoo_symbol = self._get_yahoo_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return None
            
            # Rename columns to lowercase
            hist.columns = [c.lower() for c in hist.columns]
            
            return hist
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data for {symbol}: {e}")
            return None
    
    def get_index_value(self, index: str = "NIFTY 50") -> Optional[Dict[str, Any]]:
        """Get current index value"""
        return self.get_quote(index)


# Singleton instance
_live_data_provider: Optional[LiveDataProvider] = None


def get_live_data_provider() -> LiveDataProvider:
    """Get singleton LiveDataProvider instance"""
    global _live_data_provider
    if _live_data_provider is None:
        _live_data_provider = LiveDataProvider()
    return _live_data_provider
