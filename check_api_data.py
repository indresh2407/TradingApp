#!/usr/bin/env python3
"""
Quick API Data Check - Verify Yahoo Finance is returning stock data
"""

import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

# Stocks to check (including IDBI)
TEST_STOCKS = ["IDBI", "SBIN", "RELIANCE", "TCS", "HDFCBANK"]

print("=" * 60)
print("YAHOO FINANCE API DATA CHECK")
print("=" * 60)

for symbol in TEST_STOCKS:
    yahoo_symbol = f"{symbol}.NS"
    print(f"\n{'='*60}")
    print(f"Checking: {symbol} ({yahoo_symbol})")
    print("-" * 60)
    
    try:
        ticker = yf.Ticker(yahoo_symbol)
        
        # Get daily data
        hist = ticker.history(period="5d", interval="1d")
        
        if hist.empty:
            print(f"  ❌ NO DATA returned for {symbol}")
            continue
        
        print(f"  ✅ Data received: {len(hist)} days")
        print(f"\n  Latest data (most recent trading day):")
        
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else latest
        
        ltp = latest['Close']
        prev_close = prev['Close']
        change = ltp - prev_close
        change_pct = (change / prev_close) * 100
        
        print(f"    Open:   ₹{latest['Open']:.2f}")
        print(f"    High:   ₹{latest['High']:.2f}")
        print(f"    Low:    ₹{latest['Low']:.2f}")
        print(f"    Close:  ₹{latest['Close']:.2f}")
        print(f"    Volume: {latest['Volume']:,.0f}")
        print(f"    Change: {change:+.2f} ({change_pct:+.2f}%)")
        
        # Day range analysis
        day_range = latest['High'] - latest['Low']
        close_position = (ltp - latest['Low']) / day_range if day_range > 0 else 0.5
        
        print(f"\n  Analysis:")
        print(f"    Day Range:      ₹{day_range:.2f}")
        print(f"    Close Position: {close_position*100:.0f}% (0=low, 100=high)")
        
        if close_position > 0.75:
            print(f"    → Strong Close ✅")
        elif close_position < 0.25:
            print(f"    → Weak Close ⚠️")
        else:
            print(f"    → Neutral Close")
        
        if change_pct > 2:
            print(f"    → BIG MOVE UP! 🚀")
        elif change_pct < -2:
            print(f"    → BIG MOVE DOWN! 📉")
        
        # Show all 5 days
        print(f"\n  Last 5 days:")
        for i, (idx, row) in enumerate(hist.iterrows()):
            day_change = ((row['Close'] - hist.iloc[i-1]['Close']) / hist.iloc[i-1]['Close'] * 100) if i > 0 else 0
            print(f"    {idx.strftime('%Y-%m-%d')}: ₹{row['Close']:.2f} ({day_change:+.1f}%)")
            
    except Exception as e:
        print(f"  ❌ ERROR: {e}")

print("\n" + "=" * 60)
print("API CHECK COMPLETE")
print("=" * 60)
