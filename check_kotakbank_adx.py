#!/usr/bin/env python3
"""Quick check of KOTAKBANK ADX values"""
import sys
sys.path.insert(0, '.')

import yfinance as yf
from src.api.stock_analyzer import calculate_adx

symbol = "KOTAKBANK"
ticker = yf.Ticker(f"{symbol}.NS")

# Get daily data for ADX calculation
hist = ticker.history(period="1mo", interval="1d")

if hist.empty:
    print(f"ERROR: No data for {symbol}")
else:
    print(f"\n=== {symbol} ADX Analysis ===\n")
    print(f"Data points: {len(hist)}")
    print(f"Last close: ₹{hist['Close'].iloc[-1]:.2f}")
    print(f"Change: {((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100:.2f}%")
    
    # Calculate ADX with 7/7 settings (current)
    adx_data = calculate_adx(
        hist['High'], 
        hist['Low'], 
        hist['Close'],
        di_length=7, 
        adx_smoothing=7
    )
    
    print(f"\n--- ADX (DI=7, Smooth=7) ---")
    print(f"ADX Value: {adx_data['adx']}")
    print(f"Previous ADX: {adx_data['prev_adx']}")
    print(f"ADX Change: {adx_data['adx_change']:+.1f}")
    print(f"Trend Strength: {adx_data['trend_strength']}")
    print(f"+DI: {adx_data['plus_di']}")
    print(f"-DI: {adx_data['minus_di']}")
    print(f"Direction: {adx_data['trend_direction']}")
    print(f"\n--- ADX Flags ---")
    print(f"Rising: {adx_data['rising']}")
    print(f"Weakening: {adx_data['weakening']}")
    print(f"Flat: {adx_data['flat']}")
    print(f"No Trend: {adx_data['no_trend']}")
    
    # Check if signal should be blocked
    print(f"\n--- Signal Check ---")
    adx_value = adx_data['adx']
    adx_rising = adx_data['rising']
    adx_weakening = adx_data['weakening']
    adx_no_trend = adx_data['no_trend']
    adx_change = adx_data['adx_change']
    
    should_block = False
    reason = ""
    
    if adx_no_trend:
        should_block = True
        reason = f"No Trend (ADX {adx_value:.0f} < 20)"
    elif adx_weakening:
        should_block = True
        reason = f"ADX Falling ({adx_change:+.1f})"
    elif not adx_rising and adx_value < 30:
        should_block = True
        reason = f"ADX Not Rising ({adx_value:.0f}, {adx_change:+.1f})"
    
    if should_block:
        print(f"⛔ SHOULD BE BLOCKED: {reason}")
    else:
        print(f"✅ SIGNAL ALLOWED: ADX {adx_value:.0f} Rising={adx_rising}")
