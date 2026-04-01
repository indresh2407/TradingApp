"""
Simple Backtester
Tests trading signals on historical data to calculate win rate
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI series"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def backtest_long_signal(
    symbol: str,
    lookback_days: int = 365,
    holding_period: int = 5,
    stoploss_pct: float = 2.0,
    target_pct: float = 3.0
) -> Dict[str, Any]:
    """
    Backtest LONG signals for a stock
    
    Signal: RSI < 50 (relaxed) OR price crossed above 5-day MA
    Exit: Hit target, hit stoploss, or holding period ends
    
    Returns:
        Dict with win_rate, total_trades, avg_profit, etc.
    """
    try:
        # Download historical data
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="1y")  # Get 1 year of data
        
        if hist.empty or len(hist) < 30:
            return {"status": "error", "message": "Insufficient data"}
        
        # Calculate indicators
        hist['rsi'] = calculate_rsi(hist['Close'])
        hist['sma_20'] = hist['Close'].rolling(20).mean()
        hist['sma_5'] = hist['Close'].rolling(5).mean()
        hist['prev_close'] = hist['Close'].shift(1)
        
        # IMPROVED STRATEGY - Score-based (need 2+ conditions)
        hist['rsi_prev'] = hist['rsi'].shift(1)
        hist['sma_5_prev'] = hist['sma_5'].shift(1)
        
        # Condition 1: Price above 20-day MA (trend filter)
        cond1 = (hist['Close'] > hist['sma_20']).astype(int)
        
        # Condition 2: RSI below 45 and rising (oversold bounce)
        cond2 = ((hist['rsi'] < 45) & (hist['rsi'] > hist['rsi_prev'])).astype(int)
        
        # Condition 3: Price above 5-day MA (short-term strength)
        cond3 = (hist['Close'] > hist['sma_5']).astype(int)
        
        # Condition 4: Today's close > yesterday's close (momentum)
        cond4 = (hist['Close'] > hist['prev_close']).astype(int)
        
        # Score: sum of conditions (0-4)
        hist['score'] = cond1 + cond2 + cond3 + cond4
        
        # LONG signal: Need score >= 3 (at least 3 out of 4 conditions)
        hist['signal'] = (hist['score'] >= 3).astype(int)
        
        # Track trades
        trades = []
        i = 25  # Start after indicators are valid
        
        while i < len(hist) - holding_period:
            if hist['signal'].iloc[i] == 1:
                entry_price = hist['Close'].iloc[i]
                entry_date = hist.index[i]
                
                stoploss = entry_price * (1 - stoploss_pct / 100)
                target = entry_price * (1 + target_pct / 100)
                
                # Check exit conditions over holding period
                exit_price = None
                exit_reason = "holding_period"
                
                for j in range(1, min(holding_period + 1, len(hist) - i)):
                    low = hist['Low'].iloc[i + j]
                    high = hist['High'].iloc[i + j]
                    
                    if low <= stoploss:
                        exit_price = stoploss
                        exit_reason = "stoploss"
                        break
                    elif high >= target:
                        exit_price = target
                        exit_reason = "target"
                        break
                
                if exit_price is None:
                    exit_price = hist['Close'].iloc[min(i + holding_period, len(hist) - 1)]
                
                profit_pct = ((exit_price - entry_price) / entry_price) * 100
                
                trades.append({
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "profit_pct": profit_pct,
                    "exit_reason": exit_reason,
                    "win": profit_pct > 0
                })
                
                # Skip ahead to avoid overlapping trades
                i += holding_period
            else:
                i += 1
        
        if not trades:
            return {"status": "no_trades", "message": "No signals generated"}
        
        # Calculate statistics
        wins = sum(1 for t in trades if t['win'])
        total = len(trades)
        win_rate = (wins / total) * 100
        avg_profit = sum(t['profit_pct'] for t in trades) / total
        total_profit = sum(t['profit_pct'] for t in trades)
        
        return {
            "status": "success",
            "symbol": symbol,
            "direction": "LONG",
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round(win_rate, 1),
            "avg_profit_pct": round(avg_profit, 2),
            "total_profit_pct": round(total_profit, 2),
            "best_trade": round(max(t['profit_pct'] for t in trades), 2),
            "worst_trade": round(min(t['profit_pct'] for t in trades), 2),
            "lookback_days": lookback_days
        }
        
    except Exception as e:
        logger.error(f"Backtest failed for {symbol}: {e}")
        return {"status": "error", "message": str(e)}


def backtest_short_signal(
    symbol: str,
    lookback_days: int = 365,
    holding_period: int = 5,
    stoploss_pct: float = 2.0,
    target_pct: float = 3.0
) -> Dict[str, Any]:
    """
    Backtest SHORT signals for a stock
    
    Signal: RSI > 55 (relaxed) OR price crossed below 5-day MA
    Exit: Hit target, hit stoploss, or holding period ends
    """
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="1y")  # Get 1 year of data
        
        if hist.empty or len(hist) < 30:
            return {"status": "error", "message": "Insufficient data"}
        
        hist['rsi'] = calculate_rsi(hist['Close'])
        hist['sma_20'] = hist['Close'].rolling(20).mean()
        hist['sma_5'] = hist['Close'].rolling(5).mean()
        hist['prev_close'] = hist['Close'].shift(1)
        
        # IMPROVED STRATEGY - Score-based (need 2+ conditions)
        hist['rsi_prev'] = hist['rsi'].shift(1)
        hist['sma_5_prev'] = hist['sma_5'].shift(1)
        
        # Condition 1: Price below 20-day MA (trend filter)
        cond1 = (hist['Close'] < hist['sma_20']).astype(int)
        
        # Condition 2: RSI above 55 and falling (overbought reversal)
        cond2 = ((hist['rsi'] > 55) & (hist['rsi'] < hist['rsi_prev'])).astype(int)
        
        # Condition 3: Price below 5-day MA (short-term weakness)
        cond3 = (hist['Close'] < hist['sma_5']).astype(int)
        
        # Condition 4: Today's close < yesterday's close (momentum)
        cond4 = (hist['Close'] < hist['prev_close']).astype(int)
        
        # Score: sum of conditions (0-4)
        hist['score'] = cond1 + cond2 + cond3 + cond4
        
        # SHORT signal: Need score >= 3 (at least 3 out of 4 conditions)
        hist['signal'] = (hist['score'] >= 3).astype(int)
        
        trades = []
        i = 25
        
        while i < len(hist) - holding_period:
            if hist['signal'].iloc[i] == 1:
                entry_price = hist['Close'].iloc[i]
                entry_date = hist.index[i]
                
                # For short: stoploss is above, target is below
                stoploss = entry_price * (1 + stoploss_pct / 100)
                target = entry_price * (1 - target_pct / 100)
                
                exit_price = None
                exit_reason = "holding_period"
                
                for j in range(1, min(holding_period + 1, len(hist) - i)):
                    low = hist['Low'].iloc[i + j]
                    high = hist['High'].iloc[i + j]
                    
                    if high >= stoploss:
                        exit_price = stoploss
                        exit_reason = "stoploss"
                        break
                    elif low <= target:
                        exit_price = target
                        exit_reason = "target"
                        break
                
                if exit_price is None:
                    exit_price = hist['Close'].iloc[min(i + holding_period, len(hist) - 1)]
                
                # For short: profit when price goes down
                profit_pct = ((entry_price - exit_price) / entry_price) * 100
                
                trades.append({
                    "entry_date": entry_date,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "profit_pct": profit_pct,
                    "exit_reason": exit_reason,
                    "win": profit_pct > 0
                })
                
                i += holding_period
            else:
                i += 1
        
        if not trades:
            return {"status": "no_trades", "message": "No signals generated"}
        
        wins = sum(1 for t in trades if t['win'])
        total = len(trades)
        win_rate = (wins / total) * 100
        avg_profit = sum(t['profit_pct'] for t in trades) / total
        total_profit = sum(t['profit_pct'] for t in trades)
        
        return {
            "status": "success",
            "symbol": symbol,
            "direction": "SHORT",
            "total_trades": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round(win_rate, 1),
            "avg_profit_pct": round(avg_profit, 2),
            "total_profit_pct": round(total_profit, 2),
            "best_trade": round(max(t['profit_pct'] for t in trades), 2),
            "worst_trade": round(min(t['profit_pct'] for t in trades), 2),
            "lookback_days": lookback_days
        }
        
    except Exception as e:
        logger.error(f"Backtest failed for {symbol}: {e}")
        return {"status": "error", "message": str(e)}


def quick_backtest(symbol: str, direction: str = "LONG") -> Dict[str, Any]:
    """
    Quick backtest for a single stock
    Returns win rate and basic stats
    Uses 1 year of data for better accuracy
    
    Settings optimized for win rate:
    - Stop-loss: 2% (balanced)
    - Target: 2% (achievable)
    - Holding: 5 days
    """
    if direction == "LONG":
        return backtest_long_signal(
            symbol, 
            lookback_days=365, 
            holding_period=5,
            stoploss_pct=2.0,
            target_pct=2.0  # 1:1 risk-reward for higher win rate
        )
    else:
        return backtest_short_signal(
            symbol, 
            lookback_days=365, 
            holding_period=5,
            stoploss_pct=2.0,
            target_pct=2.0
        )


def backtest_tips(long_symbols: List[str], short_symbols: List[str]) -> Dict[str, Any]:
    """
    Backtest all tip symbols and return aggregated results
    """
    results = {
        "long_results": [],
        "short_results": [],
        "overall_stats": {}
    }
    
    # Backtest LONG tips
    for symbol in long_symbols:
        bt = quick_backtest(symbol, "LONG")
        if bt.get("status") == "success":
            results["long_results"].append(bt)
    
    # Backtest SHORT tips
    for symbol in short_symbols:
        bt = quick_backtest(symbol, "SHORT")
        if bt.get("status") == "success":
            results["short_results"].append(bt)
    
    # Calculate overall stats
    all_results = results["long_results"] + results["short_results"]
    if all_results:
        total_trades = sum(r["total_trades"] for r in all_results)
        total_wins = sum(r["wins"] for r in all_results)
        avg_win_rate = sum(r["win_rate"] for r in all_results) / len(all_results)
        
        results["overall_stats"] = {
            "total_backtested": len(all_results),
            "total_trades": total_trades,
            "total_wins": total_wins,
            "avg_win_rate": round(avg_win_rate, 1)
        }
    
    return results
