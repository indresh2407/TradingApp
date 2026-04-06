"""
Analyze Directional Success of User's Trades
Check if price moved in the right direction immediately after entry
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

# User's 9 trades today
USER_TRADES = [
    {"symbol": "POLICYBZR", "time": "09:27", "direction": "SHORT", "entry": 1411.50, "exit": 1438.62},
    {"symbol": "UNIONBANK", "time": "10:08", "direction": "LONG", "entry": 174.09, "exit": 173.43},
    {"symbol": "KOTAKBANK", "time": "10:47", "direction": "SHORT", "entry": 352.50, "exit": 352.00},
    {"symbol": "TORNTPHARM", "time": "11:25", "direction": "SHORT", "entry": 3957.00, "exit": 3973.81},
    {"symbol": "HINDUNILVR", "time": "11:40", "direction": "SHORT", "entry": 2047.54, "exit": 2049.80},
    {"symbol": "ONGC", "time": "12:41", "direction": "SHORT", "entry": 281.50, "exit": 282.31},
    {"symbol": "HCLTECH", "time": "13:07", "direction": "SHORT", "entry": 1404.00, "exit": 1406.25},
    {"symbol": "ICICIBANK", "time": "13:42", "direction": "SHORT", "entry": 1224.00, "exit": 1226.50},
    {"symbol": "HAPPSTMNDS", "time": "14:58", "direction": "SHORT", "entry": 384.37, "exit": 386.15},
]

def analyze_trade_direction(trade):
    """Analyze if price moved in the right direction immediately after entry"""
    
    symbol = trade["symbol"]
    entry_time = trade["time"]
    direction = trade["direction"]
    entry_price = trade["entry"]
    
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(period="5d", interval="5m")
        
        if len(df) < 10:
            return None
        
        # Get last trading day
        last_day = df.index[-1].date()
        df_today = df[df.index.date == last_day].copy()
        
        # Find entry candle
        entry_hour = int(entry_time.split(":")[0])
        entry_min = int(entry_time.split(":")[1])
        
        entry_idx = None
        for i, idx in enumerate(df_today.index):
            if idx.hour == entry_hour and abs(idx.minute - entry_min) <= 5:
                entry_idx = i
                break
        
        if entry_idx is None:
            return None
        
        # Get prices for next 3, 5, 10 candles
        results = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "entry_time": entry_time,
        }
        
        # Immediate direction (next candle)
        if entry_idx + 1 < len(df_today):
            next_close = df_today['Close'].iloc[entry_idx + 1]
            if direction == "LONG":
                results["1_candle_correct"] = next_close > entry_price
                results["1_candle_move"] = ((next_close - entry_price) / entry_price) * 100
            else:  # SHORT
                results["1_candle_correct"] = next_close < entry_price
                results["1_candle_move"] = ((entry_price - next_close) / entry_price) * 100
        
        # 3 candles later
        if entry_idx + 3 < len(df_today):
            candle_3 = df_today['Close'].iloc[entry_idx + 3]
            if direction == "LONG":
                results["3_candle_correct"] = candle_3 > entry_price
                results["3_candle_move"] = ((candle_3 - entry_price) / entry_price) * 100
            else:
                results["3_candle_correct"] = candle_3 < entry_price
                results["3_candle_move"] = ((entry_price - candle_3) / entry_price) * 100
        
        # 5 candles later (25 min)
        if entry_idx + 5 < len(df_today):
            candle_5 = df_today['Close'].iloc[entry_idx + 5]
            if direction == "LONG":
                results["5_candle_correct"] = candle_5 > entry_price
                results["5_candle_move"] = ((candle_5 - entry_price) / entry_price) * 100
            else:
                results["5_candle_correct"] = candle_5 < entry_price
                results["5_candle_move"] = ((entry_price - candle_5) / entry_price) * 100
        
        # Max favorable move (best price in your direction)
        remaining_candles = df_today.iloc[entry_idx+1:]
        if len(remaining_candles) > 0:
            if direction == "LONG":
                best_price = remaining_candles['High'].max()
                results["max_favorable"] = ((best_price - entry_price) / entry_price) * 100
            else:
                best_price = remaining_candles['Low'].min()
                results["max_favorable"] = ((entry_price - best_price) / entry_price) * 100
        
        # Max adverse move (worst price against you)
        if len(remaining_candles) > 0:
            if direction == "LONG":
                worst_price = remaining_candles['Low'].min()
                results["max_adverse"] = ((entry_price - worst_price) / entry_price) * 100
            else:
                worst_price = remaining_candles['High'].max()
                results["max_adverse"] = ((worst_price - entry_price) / entry_price) * 100
        
        return results
        
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        return None

def main():
    print("="*70)
    print("DIRECTIONAL ANALYSIS OF YOUR 9 TRADES")
    print("="*70)
    print()
    print("Checking if price moved in the RIGHT direction immediately after entry")
    print()
    
    all_results = []
    
    for trade in USER_TRADES:
        print(f"Analyzing {trade['symbol']}...", end=" ")
        result = analyze_trade_direction(trade)
        if result:
            all_results.append(result)
            print("✓")
        else:
            print("✗")
    
    print()
    print("="*70)
    print("DIRECTIONAL ACCURACY RESULTS")
    print("="*70)
    print()
    
    print(f"{'#':<3} {'Symbol':<12} {'Dir':<6} {'1 Candle':<12} {'3 Candle':<12} {'5 Candle':<12} {'Max Fav':<10} {'Max Adv':<10}")
    print("-"*85)
    
    correct_1 = 0
    correct_3 = 0
    correct_5 = 0
    
    for i, r in enumerate(all_results):
        c1 = "✅" if r.get("1_candle_correct", False) else "❌"
        c3 = "✅" if r.get("3_candle_correct", False) else "❌"
        c5 = "✅" if r.get("5_candle_correct", False) else "❌"
        
        m1 = f"{r.get('1_candle_move', 0):+.2f}%"
        m3 = f"{r.get('3_candle_move', 0):+.2f}%"
        m5 = f"{r.get('5_candle_move', 0):+.2f}%"
        
        max_fav = f"{r.get('max_favorable', 0):+.2f}%"
        max_adv = f"{r.get('max_adverse', 0):+.2f}%"
        
        if r.get("1_candle_correct", False):
            correct_1 += 1
        if r.get("3_candle_correct", False):
            correct_3 += 1
        if r.get("5_candle_correct", False):
            correct_5 += 1
        
        print(f"{i+1:<3} {r['symbol']:<12} {r['direction']:<6} {c1} {m1:<8} {c3} {m3:<8} {c5} {m5:<8} {max_fav:<10} {max_adv:<10}")
    
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)
    print()
    total = len(all_results)
    print(f"After 1 Candle (5 min):  {correct_1}/{total} correct ({correct_1/total*100:.0f}%)")
    print(f"After 3 Candles (15 min): {correct_3}/{total} correct ({correct_3/total*100:.0f}%)")
    print(f"After 5 Candles (25 min): {correct_5}/{total} correct ({correct_5/total*100:.0f}%)")
    print()
    
    # Calculate average max favorable and adverse
    avg_fav = sum(r.get('max_favorable', 0) for r in all_results) / total
    avg_adv = sum(r.get('max_adverse', 0) for r in all_results) / total
    
    print(f"Avg Max Favorable Move: {avg_fav:+.2f}% (best price in your direction)")
    print(f"Avg Max Adverse Move:   {avg_adv:+.2f}% (worst price against you)")
    print()
    
    # Interpretation
    print("INTERPRETATION:")
    if correct_1 < total / 2:
        print("  ⚠️ Direction was WRONG immediately after entry for most trades")
        print("  → This suggests poor entry timing or wrong direction calls")
    else:
        print("  ✅ Direction was RIGHT immediately for most trades")
        print("  → But you exited too early or SL was too tight")

if __name__ == "__main__":
    main()
