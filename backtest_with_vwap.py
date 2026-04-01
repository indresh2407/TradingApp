"""
Backtest Comparison: Strategy with VWAP vs Without VWAP
Tests if adding VWAP improved accuracy
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Test stocks
TEST_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "TATAMOTORS", "AXISBANK", "MARUTI", "TITAN", "WIPRO",
    "SUNPHARMA", "LT", "ONGC", "NTPC", "POWERGRID"
]


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series, 
                         period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)
    
    for i in range(period, len(close)):
        if basic_upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]
        
        if basic_lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]
        
        if i == period:
            if close.iloc[i] <= final_upper.iloc[i]:
                supertrend.iloc[i] = final_upper.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = final_lower.iloc[i]
                direction.iloc[i] = 1
        else:
            if supertrend.iloc[i-1] == final_upper.iloc[i-1]:
                if close.iloc[i] > final_upper.iloc[i]:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
            else:
                if close.iloc[i] < final_lower.iloc[i]:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
    
    return supertrend, direction


def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Calculate VWAP"""
    typical_price = (high + low + close) / 3
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    vwap = cumulative_tp_vol / cumulative_vol
    return vwap


def backtest_without_vwap(symbol: str, direction: str = "LONG") -> Dict[str, Any]:
    """Strategy with Supertrend ONLY (no VWAP)"""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="6mo", interval="1d")
        
        if hist.empty or len(hist) < 30:
            return {"status": "error", "trades": 0, "wins": 0}
        
        # Calculate indicators
        hist['rsi'] = calculate_rsi(hist['Close'])
        hist['sma_20'] = hist['Close'].rolling(20).mean()
        hist['sma_5'] = hist['Close'].rolling(5).mean()
        hist['prev_close'] = hist['Close'].shift(1)
        hist['rsi_prev'] = hist['rsi'].shift(1)
        
        # Supertrend
        supertrend, st_direction = calculate_supertrend(hist['High'], hist['Low'], hist['Close'])
        hist['st_direction'] = st_direction
        
        if direction == "LONG":
            # Conditions: Supertrend bullish + other factors
            cond_st = (hist['st_direction'] == 1).astype(int) * 3
            cond1 = (hist['Close'] > hist['sma_20']).astype(int)
            cond2 = ((hist['rsi'] < 50) & (hist['rsi'] > hist['rsi_prev'])).astype(int)
            cond3 = (hist['Close'] > hist['sma_5']).astype(int)
            hist['score'] = cond_st + cond1 + cond2 + cond3
            hist['signal'] = (hist['score'] >= 4).astype(int)
        else:
            cond_st = (hist['st_direction'] == -1).astype(int) * 3
            cond1 = (hist['Close'] < hist['sma_20']).astype(int)
            cond2 = ((hist['rsi'] > 50) & (hist['rsi'] < hist['rsi_prev'])).astype(int)
            cond3 = (hist['Close'] < hist['sma_5']).astype(int)
            hist['score'] = cond_st + cond1 + cond2 + cond3
            hist['signal'] = (hist['score'] >= 4).astype(int)
        
        return execute_trades(hist, direction)
        
    except Exception as e:
        return {"status": "error", "trades": 0, "wins": 0, "error": str(e)}


def backtest_with_vwap(symbol: str, direction: str = "LONG") -> Dict[str, Any]:
    """Strategy with Supertrend + VWAP"""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        hist = ticker.history(period="6mo", interval="1d")
        
        if hist.empty or len(hist) < 30:
            return {"status": "error", "trades": 0, "wins": 0}
        
        # Calculate indicators
        hist['rsi'] = calculate_rsi(hist['Close'])
        hist['sma_20'] = hist['Close'].rolling(20).mean()
        hist['sma_5'] = hist['Close'].rolling(5).mean()
        hist['prev_close'] = hist['Close'].shift(1)
        hist['rsi_prev'] = hist['rsi'].shift(1)
        
        # Supertrend
        supertrend, st_direction = calculate_supertrend(hist['High'], hist['Low'], hist['Close'])
        hist['st_direction'] = st_direction
        
        # VWAP (simulated daily reset using rolling)
        hist['vwap'] = calculate_vwap(hist['High'], hist['Low'], hist['Close'], hist['Volume'])
        hist['above_vwap'] = (hist['Close'] > hist['vwap']).astype(int)
        hist['below_vwap'] = (hist['Close'] < hist['vwap']).astype(int)
        
        # VWAP crossover detection
        hist['vwap_prev'] = hist['vwap'].shift(1)
        hist['close_prev'] = hist['Close'].shift(1)
        hist['vwap_cross_up'] = ((hist['close_prev'] <= hist['vwap_prev']) & (hist['Close'] > hist['vwap'])).astype(int)
        hist['vwap_cross_down'] = ((hist['close_prev'] >= hist['vwap_prev']) & (hist['Close'] < hist['vwap'])).astype(int)
        
        if direction == "LONG":
            # Conditions: Supertrend + VWAP aligned
            cond_st = (hist['st_direction'] == 1).astype(int) * 3
            cond_vwap = hist['above_vwap'] * 2  # VWAP confirmation
            cond_vwap_cross = hist['vwap_cross_up'] * 1  # VWAP crossover bonus
            cond1 = (hist['Close'] > hist['sma_20']).astype(int)
            cond2 = ((hist['rsi'] < 50) & (hist['rsi'] > hist['rsi_prev'])).astype(int)
            hist['score'] = cond_st + cond_vwap + cond_vwap_cross + cond1 + cond2
            # Higher threshold since we have more points possible
            hist['signal'] = (hist['score'] >= 5).astype(int)
        else:
            cond_st = (hist['st_direction'] == -1).astype(int) * 3
            cond_vwap = hist['below_vwap'] * 2  # VWAP confirmation
            cond_vwap_cross = hist['vwap_cross_down'] * 1  # VWAP crossover bonus
            cond1 = (hist['Close'] < hist['sma_20']).astype(int)
            cond2 = ((hist['rsi'] > 50) & (hist['rsi'] < hist['rsi_prev'])).astype(int)
            hist['score'] = cond_st + cond_vwap + cond_vwap_cross + cond1 + cond2
            hist['signal'] = (hist['score'] >= 5).astype(int)
        
        return execute_trades(hist, direction)
        
    except Exception as e:
        return {"status": "error", "trades": 0, "wins": 0, "error": str(e)}


def execute_trades(hist: pd.DataFrame, direction: str, 
                   holding_period: int = 5, stoploss_pct: float = 2.0, 
                   target_pct: float = 2.0) -> Dict[str, Any]:
    """Execute trades and calculate results"""
    trades = []
    i = 25
    
    while i < len(hist) - holding_period:
        if hist['signal'].iloc[i] == 1:
            entry_price = hist['Close'].iloc[i]
            
            if direction == "LONG":
                stoploss = entry_price * (1 - stoploss_pct / 100)
                target = entry_price * (1 + target_pct / 100)
            else:
                stoploss = entry_price * (1 + stoploss_pct / 100)
                target = entry_price * (1 - target_pct / 100)
            
            exit_price = None
            exit_reason = "holding_period"
            
            for j in range(1, min(holding_period + 1, len(hist) - i)):
                low = hist['Low'].iloc[i + j]
                high = hist['High'].iloc[i + j]
                
                if direction == "LONG":
                    if low <= stoploss:
                        exit_price = stoploss
                        exit_reason = "stoploss"
                        break
                    elif high >= target:
                        exit_price = target
                        exit_reason = "target"
                        break
                else:
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
            
            if direction == "LONG":
                profit_pct = ((exit_price - entry_price) / entry_price) * 100
            else:
                profit_pct = ((entry_price - exit_price) / entry_price) * 100
            
            trades.append({
                "profit_pct": profit_pct,
                "exit_reason": exit_reason,
                "win": profit_pct > 0
            })
            
            i += holding_period
        else:
            i += 1
    
    if not trades:
        return {"status": "no_trades", "trades": 0, "wins": 0, "win_rate": 0}
    
    wins = sum(1 for t in trades if t['win'])
    total = len(trades)
    target_hits = sum(1 for t in trades if t['exit_reason'] == 'target')
    
    return {
        "status": "success",
        "trades": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round((wins / total) * 100, 1),
        "avg_profit": round(sum(t['profit_pct'] for t in trades) / total, 2),
        "target_hits": target_hits,
        "target_hit_rate": round((target_hits / total) * 100, 1) if total > 0 else 0
    }


def run_comparison():
    """Run full comparison"""
    print("=" * 80)
    print("🔬 BACKTEST: SUPERTREND vs SUPERTREND + VWAP")
    print("=" * 80)
    print(f"Testing {len(TEST_STOCKS)} stocks over 6 months")
    print("Settings: SL 2%, Target 2%, Hold 5 days")
    print("-" * 80)
    
    without_vwap = {"long": [], "short": []}
    with_vwap = {"long": [], "short": []}
    
    print("\n📊 Running backtests...\n")
    
    for i, symbol in enumerate(TEST_STOCKS):
        print(f"[{i+1}/{len(TEST_STOCKS)}] {symbol}...", end=" ")
        
        # Test LONG
        r1 = backtest_without_vwap(symbol, "LONG")
        r2 = backtest_with_vwap(symbol, "LONG")
        
        if r1.get("trades", 0) > 0:
            without_vwap["long"].append(r1)
        if r2.get("trades", 0) > 0:
            with_vwap["long"].append(r2)
        
        # Test SHORT
        r1 = backtest_without_vwap(symbol, "SHORT")
        r2 = backtest_with_vwap(symbol, "SHORT")
        
        if r1.get("trades", 0) > 0:
            without_vwap["short"].append(r1)
        if r2.get("trades", 0) > 0:
            with_vwap["short"].append(r2)
        
        print("✓")
    
    # Calculate results
    def aggregate(results):
        if not results:
            return {"trades": 0, "wins": 0, "win_rate": 0, "target_hits": 0}
        total_trades = sum(r["trades"] for r in results)
        total_wins = sum(r["wins"] for r in results)
        total_targets = sum(r.get("target_hits", 0) for r in results)
        avg_wr = sum(r["win_rate"] for r in results) / len(results)
        return {
            "trades": total_trades,
            "wins": total_wins,
            "win_rate": round(avg_wr, 1),
            "target_hits": total_targets,
            "target_rate": round((total_targets / total_trades) * 100, 1) if total_trades > 0 else 0
        }
    
    # WITHOUT VWAP
    wo_long = aggregate(without_vwap["long"])
    wo_short = aggregate(without_vwap["short"])
    wo_total_trades = wo_long["trades"] + wo_short["trades"]
    wo_total_wins = wo_long["wins"] + wo_short["wins"]
    wo_wr = round((wo_total_wins / wo_total_trades) * 100, 1) if wo_total_trades > 0 else 0
    
    # WITH VWAP
    w_long = aggregate(with_vwap["long"])
    w_short = aggregate(with_vwap["short"])
    w_total_trades = w_long["trades"] + w_short["trades"]
    w_total_wins = w_long["wins"] + w_short["wins"]
    w_wr = round((w_total_wins / w_total_trades) * 100, 1) if w_total_trades > 0 else 0
    
    # Display results
    print("\n" + "=" * 80)
    print("📈 RESULTS")
    print("=" * 80)
    
    print("\n🔵 WITHOUT VWAP (Supertrend + RSI + MA only):")
    print(f"   LONG:  {wo_long['trades']} trades | {wo_long['wins']} wins | Win Rate: {wo_long['win_rate']}%")
    print(f"   SHORT: {wo_short['trades']} trades | {wo_short['wins']} wins | Win Rate: {wo_short['win_rate']}%")
    print(f"   📊 TOTAL: {wo_total_trades} trades | {wo_total_wins} wins | Win Rate: {wo_wr}%")
    
    print("\n🟢 WITH VWAP (Supertrend + VWAP + RSI + MA):")
    print(f"   LONG:  {w_long['trades']} trades | {w_long['wins']} wins | Win Rate: {w_long['win_rate']}%")
    print(f"   SHORT: {w_short['trades']} trades | {w_short['wins']} wins | Win Rate: {w_short['win_rate']}%")
    print(f"   📊 TOTAL: {w_total_trades} trades | {w_total_wins} wins | Win Rate: {w_wr}%")
    
    # Comparison
    print("\n" + "=" * 80)
    print("📊 COMPARISON")
    print("=" * 80)
    
    wr_diff = w_wr - wo_wr
    trades_diff = wo_total_trades - w_total_trades
    
    if wr_diff > 0:
        print(f"\n✅ VWAP IMPROVED win rate by +{wr_diff:.1f}%")
        print(f"   {wo_wr}% → {w_wr}%")
    elif wr_diff < 0:
        print(f"\n❌ VWAP DECREASED win rate by {wr_diff:.1f}%")
        print(f"   {wo_wr}% → {w_wr}%")
    else:
        print(f"\n➖ No change in win rate: {wo_wr}%")
    
    if trades_diff > 0:
        print(f"\n📉 VWAP filtered out {trades_diff} trades ({trades_diff/wo_total_trades*100:.0f}% fewer)")
        print("   → More selective = higher quality signals")
    else:
        print(f"\n📈 VWAP added {abs(trades_diff)} more trade signals")
    
    # Quality analysis
    print("\n📊 QUALITY ANALYSIS:")
    print(f"   Without VWAP: {wo_total_wins} wins from {wo_total_trades} trades")
    print(f"   With VWAP:    {w_total_wins} wins from {w_total_trades} trades")
    
    efficiency_wo = (wo_total_wins / wo_total_trades * 100) if wo_total_trades > 0 else 0
    efficiency_w = (w_total_wins / w_total_trades * 100) if w_total_trades > 0 else 0
    
    print(f"\n   Efficiency: {efficiency_wo:.1f}% → {efficiency_w:.1f}%")
    
    print("\n" + "=" * 80)
    
    # Verdict
    print("🏆 VERDICT:")
    if wr_diff >= 3:
        print("   ✅ VWAP significantly improved accuracy! Keep it.")
    elif wr_diff >= 1:
        print("   ✅ VWAP slightly improved accuracy. Recommended to keep.")
    elif wr_diff >= -1:
        print("   ➖ VWAP had minimal impact. Can keep for additional confirmation.")
    else:
        print("   ⚠️ VWAP may need parameter tuning for this market condition.")
    
    print("=" * 80)
    
    return {
        "without_vwap": {"win_rate": wo_wr, "trades": wo_total_trades, "wins": wo_total_wins},
        "with_vwap": {"win_rate": w_wr, "trades": w_total_trades, "wins": w_total_wins},
        "improvement": wr_diff
    }


if __name__ == "__main__":
    print("\n🚀 Starting VWAP Backtest Comparison...\n")
    results = run_comparison()
