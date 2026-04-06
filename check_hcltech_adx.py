#!/usr/bin/env python3
"""Check HCLTECH ADX values"""
import sys
sys.path.insert(0, '.')

import yfinance as yf
from src.api.stock_analyzer import calculate_adx

symbol = "HCLTECH"
ticker = yf.Ticker(f"{symbol}.NS")

# Get daily data for ADX calculation
hist = ticker.history(period="1mo", interval="1d")

if hist.empty:
    print(f"ERROR: No data for {symbol}")
else:
    print(f"\n=== {symbol} ADX Analysis ===\n")
    print(f"Data points: {len(hist)}")
    print(f"Last close: ₹{hist['Close'].iloc[-1]:.2f}")
    print(f"Previous close: ₹{hist['Close'].iloc[-2]:.2f}")
    print(f"Change: {((hist['Close'].iloc[-1] / hist['Close'].iloc[-2]) - 1) * 100:.2f}%")
    
    # Calculate ADX with 7/7 settings (current)
    adx_data_7 = calculate_adx(
        hist['High'], 
        hist['Low'], 
        hist['Close'],
        di_length=7, 
        adx_smoothing=7
    )
    
    print(f"\n--- ADX (DI=7, Smooth=7) - FAST ---")
    print(f"ADX Value: {adx_data_7['adx']}")
    print(f"Previous ADX: {adx_data_7['prev_adx']}")
    print(f"ADX Change: {adx_data_7['adx_change']:+.1f}")
    print(f"Trend Strength: {adx_data_7['trend_strength']}")
    print(f"+DI: {adx_data_7['plus_di']}")
    print(f"-DI: {adx_data_7['minus_di']}")
    print(f"Direction: {adx_data_7['trend_direction']}")
    print(f"Rising: {adx_data_7['rising']}")
    print(f"Weakening: {adx_data_7['weakening']}")
    
    # Calculate ADX with 14/14 settings (standard)
    adx_data_14 = calculate_adx(
        hist['High'], 
        hist['Low'], 
        hist['Close'],
        di_length=14, 
        adx_smoothing=14
    )
    
    print(f"\n--- ADX (DI=14, Smooth=14) - STANDARD ---")
    print(f"ADX Value: {adx_data_14['adx']}")
    print(f"Previous ADX: {adx_data_14['prev_adx']}")
    print(f"ADX Change: {adx_data_14['adx_change']:+.1f}")
    print(f"Trend Strength: {adx_data_14['trend_strength']}")
    print(f"+DI: {adx_data_14['plus_di']}")
    print(f"-DI: {adx_data_14['minus_di']}")
    print(f"Direction: {adx_data_14['trend_direction']}")
    print(f"Rising: {adx_data_14['rising']}")
    print(f"Weakening: {adx_data_14['weakening']}")
    
    # Show last 5 days of ADX values
    print(f"\n--- ADX History (last 5 days, DI=14) ---")
    for i in range(-5, 0):
        temp_hist = hist.iloc[:len(hist)+i+1]
        if len(temp_hist) >= 20:
            temp_adx = calculate_adx(
                temp_hist['High'], 
                temp_hist['Low'], 
                temp_hist['Close'],
                di_length=14, 
                adx_smoothing=14
            )
            date = hist.index[i].strftime('%Y-%m-%d')
            print(f"{date}: ADX={temp_adx['adx']:.1f}, +DI={temp_adx['plus_di']:.1f}, -DI={temp_adx['minus_di']:.1f}")
    
    print(f"\n=== COMPARISON ===")
    print(f"7-period ADX: {adx_data_7['adx']:.1f} (faster, more sensitive)")
    print(f"14-period ADX: {adx_data_14['adx']:.1f} (standard, smoother)")
    print(f"\nIf you see different ADX on chart, check if chart uses DI=14 (standard)")
