#!/usr/bin/env python3
"""Analyze ONGC candle at 12:45 - what indicator showed the move?"""
import sys
sys.path.insert(0, '.')

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from src.api.stock_analyzer import (
    calculate_adx, calculate_vwap, calculate_supertrend_simple,
    calculate_rsi, calculate_bollinger_bands
)

symbol = "ONGC"
ticker = yf.Ticker(f"{symbol}.NS")

# Get 5-minute intraday data
hist = ticker.history(period="5d", interval="5m")

if hist.empty:
    print(f"ERROR: No data for {symbol}")
else:
    print(f"\n=== {symbol} Analysis Around 12:45 ===\n")
    
    # Filter for today's data around 12:45
    today = datetime.now().date()
    
    # Find candles around 12:30 - 13:00
    target_candles = []
    for idx, row in hist.iterrows():
        # Convert to IST (UTC+5:30)
        candle_time = idx.to_pydatetime()
        hour = candle_time.hour
        minute = candle_time.minute
        
        # Look for candles between 12:30 and 13:00
        if hour == 12 and minute >= 30:
            target_candles.append((idx, row))
        elif hour == 13 and minute <= 15:
            target_candles.append((idx, row))
    
    if not target_candles:
        print("No candles found around 12:45. Showing last 10 candles:")
        for idx, row in hist.tail(10).iterrows():
            candle_range = row['High'] - row['Low']
            body = abs(row['Close'] - row['Open'])
            is_green = row['Close'] > row['Open']
            color = "🟢" if is_green else "🔴"
            print(f"{idx}: {color} O:{row['Open']:.2f} H:{row['High']:.2f} L:{row['Low']:.2f} C:{row['Close']:.2f} | Body: {body:.2f} | Vol: {row['Volume']:,.0f}")
    else:
        print(f"Found {len(target_candles)} candles around 12:30-13:00:\n")
        
        for idx, row in target_candles:
            candle_range = row['High'] - row['Low']
            body = abs(row['Close'] - row['Open'])
            is_green = row['Close'] > row['Open']
            color = "🟢 GREEN" if is_green else "🔴 RED"
            body_pct = (body / row['Open']) * 100
            
            print(f"⏰ {idx}")
            print(f"   {color} candle")
            print(f"   Open: ₹{row['Open']:.2f}")
            print(f"   High: ₹{row['High']:.2f}")
            print(f"   Low: ₹{row['Low']:.2f}")
            print(f"   Close: ₹{row['Close']:.2f}")
            print(f"   Body: ₹{body:.2f} ({body_pct:.2f}%)")
            print(f"   Range: ₹{candle_range:.2f}")
            print(f"   Volume: {row['Volume']:,.0f}")
            print()
    
    # Now analyze what indicators showed BEFORE the move
    print("\n=== INDICATOR ANALYSIS ===\n")
    
    # Get data up to 12:45 to see what indicators showed
    ltp = hist['Close'].iloc[-1]
    
    # 1. Volume Analysis
    avg_vol = hist['Volume'].rolling(20).mean()
    recent_vol = hist['Volume'].iloc[-5:].mean()
    vol_ratio = recent_vol / avg_vol.iloc[-1] if avg_vol.iloc[-1] > 0 else 1
    print(f"1. VOLUME:")
    print(f"   Volume Ratio: {vol_ratio:.2f}x average")
    print(f"   {'🔥 VOLUME SURGE!' if vol_ratio > 1.5 else '⚡ Above avg' if vol_ratio > 1.2 else '📊 Normal'}")
    
    # 2. VWAP Analysis
    try:
        typical_price = (hist['High'] + hist['Low'] + hist['Close']) / 3
        vwap = (typical_price * hist['Volume']).cumsum() / hist['Volume'].cumsum()
        current_vwap = vwap.iloc[-1]
        vwap_distance = ((ltp - current_vwap) / current_vwap) * 100
        print(f"\n2. VWAP:")
        print(f"   VWAP: ₹{current_vwap:.2f}")
        print(f"   LTP: ₹{ltp:.2f}")
        print(f"   Distance: {vwap_distance:+.2f}%")
        print(f"   {'🟢 ABOVE VWAP (Bullish)' if ltp > current_vwap else '🔴 BELOW VWAP (Bearish)'}")
    except Exception as e:
        print(f"\n2. VWAP: Error - {e}")
    
    # 3. RSI Analysis
    try:
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        prev_rsi = rsi.iloc[-2]
        rsi_change = current_rsi - prev_rsi
        print(f"\n3. RSI (14):")
        print(f"   Current RSI: {current_rsi:.1f}")
        print(f"   Previous RSI: {prev_rsi:.1f}")
        print(f"   Change: {rsi_change:+.1f}")
        if current_rsi > 70:
            print(f"   ⚠️ OVERBOUGHT")
        elif current_rsi < 30:
            print(f"   ⚠️ OVERSOLD - Bounce potential!")
        elif rsi_change > 5:
            print(f"   🚀 RSI SURGING - Strong momentum!")
        else:
            print(f"   📊 Normal range")
    except Exception as e:
        print(f"\n3. RSI: Error - {e}")
    
    # 4. Bollinger Bands
    try:
        sma_20 = hist['Close'].rolling(20).mean()
        std_20 = hist['Close'].rolling(20).std()
        bb_upper = sma_20 + (std_20 * 2)
        bb_lower = sma_20 - (std_20 * 2)
        bb_width = ((bb_upper - bb_lower) / sma_20) * 100
        prev_bb_width = bb_width.iloc[-5]
        current_bb_width = bb_width.iloc[-1]
        
        print(f"\n4. BOLLINGER BANDS:")
        print(f"   Upper: ₹{bb_upper.iloc[-1]:.2f}")
        print(f"   Middle: ₹{sma_20.iloc[-1]:.2f}")
        print(f"   Lower: ₹{bb_lower.iloc[-1]:.2f}")
        print(f"   LTP: ₹{ltp:.2f}")
        print(f"   Band Width: {current_bb_width:.2f}%")
        
        if current_bb_width > prev_bb_width * 1.3:
            print(f"   🔥 BAND EXPANSION - Breakout happening!")
        elif current_bb_width < 2:
            print(f"   ⚡ SQUEEZE - Big move coming!")
        
        if ltp > bb_upper.iloc[-1]:
            print(f"   🚀 PRICE ABOVE UPPER BAND - Strong momentum!")
        elif ltp < bb_lower.iloc[-1]:
            print(f"   📉 PRICE BELOW LOWER BAND - Oversold bounce?")
    except Exception as e:
        print(f"\n4. BB: Error - {e}")
    
    # 5. Price Momentum (Rate of Change)
    try:
        roc_5 = ((ltp - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6]) * 100
        roc_10 = ((ltp - hist['Close'].iloc[-11]) / hist['Close'].iloc[-11]) * 100
        print(f"\n5. MOMENTUM (ROC):")
        print(f"   5-candle ROC: {roc_5:+.2f}%")
        print(f"   10-candle ROC: {roc_10:+.2f}%")
        if roc_5 > 0.5:
            print(f"   🚀 STRONG BULLISH MOMENTUM!")
        elif roc_5 < -0.5:
            print(f"   📉 STRONG BEARISH MOMENTUM!")
    except Exception as e:
        print(f"\n5. ROC: Error - {e}")
    
    # 6. Candle Pattern Analysis
    print(f"\n6. CANDLE PATTERN (Last 5 candles):")
    for i in range(-5, 0):
        row = hist.iloc[i]
        body = abs(row['Close'] - row['Open'])
        wick_upper = row['High'] - max(row['Close'], row['Open'])
        wick_lower = min(row['Close'], row['Open']) - row['Low']
        body_pct = (body / row['Open']) * 100
        is_green = row['Close'] > row['Open']
        
        pattern = ""
        if body_pct > 0.5:
            pattern = "🟢 BULLISH" if is_green else "🔴 BEARISH"
            if body_pct > 1.0:
                pattern += " MARUBOZU (Strong!)"
        elif wick_lower > body * 2 and is_green:
            pattern = "🔨 HAMMER (Bullish reversal)"
        elif wick_upper > body * 2 and not is_green:
            pattern = "⭐ SHOOTING STAR (Bearish reversal)"
        else:
            pattern = "📊 Doji/Neutral"
        
        print(f"   {hist.index[i]}: {pattern} | Body: {body_pct:.2f}%")
    
    print(f"\n=== SUMMARY ===")
    print(f"The big green candle at 12:45 was likely triggered by:")
    print(f"1. Volume surge (institutional buying)")
    print(f"2. VWAP breakout (if price crossed above VWAP)")
    print(f"3. RSI momentum surge")
    print(f"4. Bollinger Band expansion (breakout from squeeze)")
    print(f"\nCheck WHICH indicator showed this BEFORE the move to use it next time!")
