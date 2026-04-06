"""
Test new DI Gap and ADX Exhaustion filters on today's trades
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

IST = pytz.timezone('Asia/Kolkata')

def calculate_adx_with_gap(high, low, close, di_length=10, adx_smoothing=10):
    """Calculate ADX with DI gap analysis"""
    if len(close) < di_length + adx_smoothing + 5:
        return None
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=di_length).mean()
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    plus_dm_smooth = plus_dm.rolling(window=di_length).mean()
    minus_dm_smooth = minus_dm.rolling(window=di_length).mean()
    
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
    adx = dx.rolling(window=adx_smoothing).mean()
    
    return adx, plus_di, minus_di

def analyze_trade(symbol, entry_time, direction, entry_price, exit_price):
    """Analyze a single trade with new filters"""
    print(f"\n{'='*60}")
    print(f"{symbol} - {direction} at {entry_time}")
    print(f"{'='*60}")
    
    loss = exit_price - entry_price if direction == "SHORT" else entry_price - exit_price
    loss_pct = (loss / entry_price) * 100
    print(f"Entry: ₹{entry_price}, Exit: ₹{exit_price}, Loss: {loss_pct:.2f}%")
    
    ticker = yf.Ticker(f"{symbol}.NS")
    df = ticker.history(period="1d", interval="5m")
    
    if len(df) < 25:
        print("Not enough data")
        return
    
    today = datetime.now(IST).date()
    df_today = df[df.index.date == today].copy()
    
    result = calculate_adx_with_gap(df_today['High'], df_today['Low'], df_today['Close'])
    if result is None:
        print("Could not calculate ADX")
        return
    
    adx, plus_di, minus_di = result
    
    # Find the entry candle
    try:
        entry_candles = df_today.between_time(entry_time.replace(':', ':'), 
                                               entry_time[:3] + str(int(entry_time[3:5])+5).zfill(2))
    except:
        entry_candles = df_today.tail(10)
    
    if len(entry_candles) == 0:
        print(f"No candle found at {entry_time}")
        return
    
    idx = df_today.index.get_loc(entry_candles.index[0])
    
    # Get current and previous values
    curr_adx = adx.iloc[idx]
    curr_plus_di = plus_di.iloc[idx]
    curr_minus_di = minus_di.iloc[idx]
    prev_plus_di = plus_di.iloc[idx-1] if idx > 0 else curr_plus_di
    prev_minus_di = minus_di.iloc[idx-1] if idx > 0 else curr_minus_di
    
    # Calculate DI gap
    curr_gap = abs(curr_plus_di - curr_minus_di)
    prev_gap = abs(prev_plus_di - prev_minus_di)
    gap_change = curr_gap - prev_gap
    gap_narrowing = gap_change < -1.0
    
    print(f"\nAT ENTRY TIME ({entry_time}):")
    print(f"  ADX: {curr_adx:.1f}")
    print(f"  +DI: {curr_plus_di:.1f} (prev: {prev_plus_di:.1f})")
    print(f"  -DI: {curr_minus_di:.1f} (prev: {prev_minus_di:.1f})")
    print(f"  DI Gap: {curr_gap:.1f} (prev: {prev_gap:.1f}, change: {gap_change:+.1f})")
    
    print(f"\nNEW FILTER CHECKS:")
    
    # Check ADX Exhaustion (> 80)
    adx_exhausted = curr_adx > 80
    print(f"  1. ADX Exhaustion (>80): {'⛔ BLOCKED' if adx_exhausted else '✅ OK'} (ADX={curr_adx:.1f})")
    
    # Check DI Gap Narrowing
    gap_blocked = gap_narrowing and curr_gap < 15
    gap_warning = gap_narrowing and not gap_blocked
    if gap_blocked:
        print(f"  2. DI Gap Narrowing: ⛔ BLOCKED (gap={curr_gap:.1f}, change={gap_change:+.1f})")
    elif gap_warning:
        print(f"  2. DI Gap Narrowing: ⚠️ WARNING (gap={curr_gap:.1f}, change={gap_change:+.1f})")
    else:
        print(f"  2. DI Gap Narrowing: ✅ OK (gap={curr_gap:.1f}, change={gap_change:+.1f})")
    
    # Final verdict
    blocked = adx_exhausted or gap_blocked
    print(f"\n  FINAL: {'⛔ WOULD BE BLOCKED' if blocked else '✅ WOULD PASS'}")
    
    return blocked

def main():
    print("="*60)
    print("TESTING NEW FILTERS ON TODAY'S TRADES")
    print("="*60)
    print("\nNEW FILTERS ADDED:")
    print("  1. ADX Exhaustion: Block when ADX > 80 (trend exhausted)")
    print("  2. DI Gap Narrowing: Block when gap shrinking + gap < 15")
    
    trades = [
        ("ONGC", "12:40", "SHORT", 281.5, 282.31),      # Trade 6
        ("HCLTECH", "13:05", "SHORT", 1404.0, 1406.25), # Trade 7
        ("HAPPSTMNDS", "14:55", "SHORT", 384.37, 386.15) # Trade 9
    ]
    
    results = []
    for symbol, time, direction, entry, exit in trades:
        blocked = analyze_trade(symbol, time, direction, entry, exit)
        results.append((symbol, blocked))
    
    print("\n" + "="*60)
    print("SUMMARY - NEW FILTERS")
    print("="*60)
    print("\n| Trade | Stock       | Would Block? |")
    print("|-------|-------------|--------------|")
    trade_nums = [6, 7, 9]  # Trade numbers for ONGC, HCLTECH, HAPPSTMNDS
    for i, (symbol, blocked) in enumerate(results):
        status = "⛔ YES" if blocked else "✅ NO"
        trade_num = trade_nums[i]
        print(f"| #{trade_num}     | {symbol:<11} | {status:<12} |")
    
    blocked_count = sum(1 for _, b in results if b)
    print(f"\nNew filters would block {blocked_count}/3 additional trades")

if __name__ == "__main__":
    main()
