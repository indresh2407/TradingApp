#!/usr/bin/env python3
"""
Debug DayTrade for NIFTY IT stocks
"""

import yfinance as yf
import pandas as pd
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

IT_STOCKS = ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "LTTS"]

def calculate_vwap(hist):
    typical_price = (hist['High'] + hist['Low'] + hist['Close']) / 3
    vwap = (typical_price * hist['Volume']).cumsum() / hist['Volume'].cumsum()
    current_vwap = vwap.iloc[-1]
    current_price = hist['Close'].iloc[-1]
    
    if current_price > current_vwap * 1.002:
        return "BULLISH", current_vwap, current_price
    elif current_price < current_vwap * 0.998:
        return "BEARISH", current_vwap, current_price
    return "NEUTRAL", current_vwap, current_price

def calculate_supertrend(hist, period=10, multiplier=3.0):
    high, low, close = hist['High'], hist['Low'], hist['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    hl2 = (high + low) / 2
    upper = hl2 + (multiplier * atr)
    lower = hl2 - (multiplier * atr)
    
    ltp = close.iloc[-1]
    st_upper = upper.iloc[-1]
    st_lower = lower.iloc[-1]
    
    if ltp > st_lower:
        return "BULLISH", st_lower
    else:
        return "BEARISH", st_upper

def calculate_bb(close, period=20):
    middle = close.rolling(period).mean().iloc[-1]
    std = close.rolling(period).std().iloc[-1]
    upper = middle + (2 * std)
    lower = middle - (2 * std)
    ltp = close.iloc[-1]
    
    if ltp > upper:
        return "OVERBOUGHT", middle, upper, lower
    elif ltp < lower:
        return "OVERSOLD", middle, upper, lower
    elif ltp > middle:
        return "BULLISH", middle, upper, lower
    else:
        return "BEARISH", middle, upper, lower

print("=" * 80)
print("DAYTRADE DEBUG - NIFTY IT STOCKS")
print("=" * 80)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

for symbol in IT_STOCKS:
    yahoo_symbol = f"{symbol}.NS"
    print(f"\n{'='*80}")
    print(f"📊 {symbol}")
    print("-" * 80)
    
    try:
        ticker = yf.Ticker(yahoo_symbol)
        hist_5m = ticker.history(period="5d", interval="5m")
        
        if hist_5m.empty or len(hist_5m) < 50:
            print(f"  ❌ Not enough 5m data ({len(hist_5m)} bars)")
            continue
        
        # Create 10m data
        hist_10m = hist_5m.resample('10min').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        
        if len(hist_10m) < 20:
            print(f"  ❌ Not enough 10m data ({len(hist_10m)} bars)")
            continue
        
        ltp = hist_5m['Close'].iloc[-1]
        print(f"  LTP: ₹{ltp:,.2f}")
        
        # 5-min analysis
        vwap_5m_signal, vwap_5m, _ = calculate_vwap(hist_5m)
        st_5m_signal, st_5m_val = calculate_supertrend(hist_5m)
        bb_5m_signal, bb_5m_mid, bb_5m_up, bb_5m_low = calculate_bb(hist_5m['Close'])
        
        # 10-min analysis
        vwap_10m_signal, vwap_10m, _ = calculate_vwap(hist_10m)
        st_10m_signal, st_10m_val = calculate_supertrend(hist_10m)
        bb_10m_signal, bb_10m_mid, bb_10m_up, bb_10m_low = calculate_bb(hist_10m['Close'])
        
        print(f"\n  5-MIN ANALYSIS:")
        print(f"    VWAP:       {vwap_5m_signal:10} (VWAP: ₹{vwap_5m:,.2f}, LTP: ₹{ltp:,.2f})")
        print(f"    Supertrend: {st_5m_signal:10} (ST: ₹{st_5m_val:,.2f})")
        print(f"    Bollinger:  {bb_5m_signal:10} (Mid: ₹{bb_5m_mid:,.2f})")
        
        print(f"\n  10-MIN ANALYSIS:")
        print(f"    VWAP:       {vwap_10m_signal:10} (VWAP: ₹{vwap_10m:,.2f})")
        print(f"    Supertrend: {st_10m_signal:10} (ST: ₹{st_10m_val:,.2f})")
        print(f"    Bollinger:  {bb_10m_signal:10} (Mid: ₹{bb_10m_mid:,.2f})")
        
        # Count confirmations
        long_conf = 0
        short_conf = 0
        
        # 5m
        if vwap_5m_signal == "BULLISH": long_conf += 1
        if vwap_5m_signal == "BEARISH": short_conf += 1
        if st_5m_signal == "BULLISH": long_conf += 1
        if st_5m_signal == "BEARISH": short_conf += 1
        if bb_5m_signal in ["BULLISH", "OVERSOLD"]: long_conf += 1
        if bb_5m_signal in ["BEARISH", "OVERBOUGHT"]: short_conf += 1
        
        # 10m
        if vwap_10m_signal == "BULLISH": long_conf += 1
        if vwap_10m_signal == "BEARISH": short_conf += 1
        if st_10m_signal == "BULLISH": long_conf += 1
        if st_10m_signal == "BEARISH": short_conf += 1
        if bb_10m_signal in ["BULLISH", "OVERSOLD"]: long_conf += 1
        if bb_10m_signal in ["OVERBOUGHT", "BEARISH"]: short_conf += 1
        
        print(f"\n  CONFIRMATIONS:")
        print(f"    LONG:  {long_conf}/6 {'✅ SIGNAL!' if long_conf >= 4 else '❌ Need 4+'}")
        print(f"    SHORT: {short_conf}/6 {'✅ SIGNAL!' if short_conf >= 4 else '❌ Need 4+'}")
        
        if long_conf < 4 and short_conf < 4:
            print(f"\n  ⚠️ NO SIGNAL - Indicators not aligned")
            # Show which are misaligned
            print(f"    5m: VWAP={vwap_5m_signal}, ST={st_5m_signal}, BB={bb_5m_signal}")
            print(f"   10m: VWAP={vwap_10m_signal}, ST={st_10m_signal}, BB={bb_10m_signal}")
        
    except Exception as e:
        print(f"  ❌ Error: {e}")

print("\n" + "=" * 80)
print("SUMMARY: If all indicators show different signals (mixed BULLISH/BEARISH/NEUTRAL),")
print("the stock won't qualify. Need 4+ indicators aligned in same direction.")
print("=" * 80)
