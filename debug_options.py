#!/usr/bin/env python3
"""
Debug Options Strategy - See why no signals are generated
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Test just 5 liquid stocks
TEST_STOCKS = ["RELIANCE", "TCS", "HDFCBANK", "SBIN", "INFY"]

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def calculate_supertrend(high, low, close, period=10, mult=3.0):
    hl2 = (high + low) / 2
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    
    direction = pd.Series(index=close.index, dtype=int)
    for i in range(period, len(close)):
        if close.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1] if i > period else 1
    
    d = direction.iloc[-1] if len(direction) > 0 else 0
    return "BULLISH" if d == 1 else "BEARISH"

def debug_stock(symbol):
    print(f"\n{'='*50}")
    print(f"📊 Debugging: {symbol}")
    print('='*50)
    
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        h5 = ticker.history(period="5d", interval="5m")
        
        if h5.empty:
            print("❌ No data returned from Yahoo Finance!")
            return
        
        print(f"✅ Data received: {len(h5)} candles")
        print(f"   Last candle: {h5.index[-1]}")
        print(f"   LTP: ₹{h5['Close'].iloc[-1]:.2f}")
        
        # Check ATR
        atr = calculate_atr(h5['High'], h5['Low'], h5['Close'])
        atr_pct = (atr / h5['Close'].iloc[-1]) * 100
        print(f"\n📈 ATR Analysis:")
        print(f"   ATR: ₹{atr:.2f}")
        print(f"   ATR%: {atr_pct:.2f}%")
        print(f"   Pass 0.8% filter? {'✅ YES' if atr_pct >= 0.8 else '❌ NO'}")
        
        # Check VWAP
        tp = (h5['High'] + h5['Low'] + h5['Close']) / 3
        vwap = (tp * h5['Volume']).cumsum() / h5['Volume'].cumsum()
        vwap_val = vwap.iloc[-1]
        ltp = h5['Close'].iloc[-1]
        vwap_signal = "BULLISH" if ltp > vwap_val * 1.002 else "BEARISH" if ltp < vwap_val * 0.998 else "NEUTRAL"
        print(f"\n📊 VWAP:")
        print(f"   VWAP: ₹{vwap_val:.2f}")
        print(f"   LTP vs VWAP: {((ltp - vwap_val) / vwap_val * 100):+.2f}%")
        print(f"   Signal: {vwap_signal}")
        
        # Check Supertrend
        st_signal = calculate_supertrend(h5['High'], h5['Low'], h5['Close'])
        print(f"\n📈 Supertrend (5m): {st_signal}")
        
        # Resample to 15m
        h15 = h5.resample('15min').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min',
            'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if len(h15) >= 20:
            st15_signal = calculate_supertrend(h15['High'], h15['Low'], h15['Close'])
            print(f"📈 Supertrend (15m): {st15_signal}")
        
        # Calculate scores
        call_score = 0
        put_score = 0
        
        if vwap_signal == "BULLISH": call_score += 1
        if vwap_signal == "BEARISH": put_score += 1
        
        if st_signal == "BULLISH": call_score += 1
        if st_signal == "BEARISH": put_score += 1
        
        if len(h15) >= 20:
            if st15_signal == "BULLISH": call_score += 1
            if st15_signal == "BEARISH": put_score += 1
        
        print(f"\n🎯 Scores:")
        print(f"   CALL Score: {call_score}")
        print(f"   PUT Score: {put_score}")
        print(f"   Need: 4 for signal")
        
        # Why no signal?
        print(f"\n❓ Why no signal?")
        issues = []
        if atr_pct < 0.8:
            issues.append(f"   - ATR too low ({atr_pct:.2f}% < 0.8%)")
        if max(call_score, put_score) < 4:
            issues.append(f"   - Score too low (max {max(call_score, put_score)} < 4)")
        if vwap_signal == "NEUTRAL":
            issues.append(f"   - VWAP neutral (price near VWAP)")
        if st_signal != st15_signal if len(h15) >= 20 else False:
            issues.append(f"   - Timeframe conflict (5m: {st_signal}, 15m: {st15_signal})")
        
        if issues:
            for issue in issues:
                print(issue)
        else:
            print("   ✅ Should generate signal! Check main code.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    print("\n" + "="*60)
    print("🔍 OPTIONS STRATEGY DEBUG")
    print("="*60)
    print("Checking why no signals are generated...")
    
    for symbol in TEST_STOCKS:
        debug_stock(symbol)
    
    print("\n" + "="*60)
    print("💡 Common reasons for no signals:")
    print("   1. Market closed - data is from last trading day")
    print("   2. Low volatility day - ATR below threshold")
    print("   3. Sideways market - no clear trend")
    print("   4. Timeframe conflict - 5m and 15m disagree")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
