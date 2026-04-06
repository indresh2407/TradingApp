"""
Debug POLICYBZR SHORT Signal at 9:27am
Analyze what went wrong
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone('Asia/Kolkata')

def calculate_supertrend(df, period=10, multiplier=3):
    """Calculate Supertrend indicator"""
    hl2 = (df['High'] + df['Low']) / 2
    
    tr1 = df['High'] - df['Low']
    tr2 = abs(df['High'] - df['Close'].shift(1))
    tr3 = abs(df['Low'] - df['Close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    upper_band = hl2 + (multiplier * atr)
    lower_band = hl2 - (multiplier * atr)
    
    supertrend = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    
    for i in range(period, len(df)):
        if df['Close'].iloc[i] > upper_band.iloc[i-1]:
            supertrend.iloc[i] = lower_band.iloc[i]
            direction.iloc[i] = 1
        elif df['Close'].iloc[i] < lower_band.iloc[i-1]:
            supertrend.iloc[i] = upper_band.iloc[i]
            direction.iloc[i] = -1
        else:
            supertrend.iloc[i] = supertrend.iloc[i-1]
            direction.iloc[i] = direction.iloc[i-1]
            
            if direction.iloc[i] == 1 and lower_band.iloc[i] > supertrend.iloc[i]:
                supertrend.iloc[i] = lower_band.iloc[i]
            elif direction.iloc[i] == -1 and upper_band.iloc[i] < supertrend.iloc[i]:
                supertrend.iloc[i] = upper_band.iloc[i]
    
    return supertrend, direction, atr

def calculate_vwap(df):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def calculate_adx(df, di_length=10, adx_smoothing=10):
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    atr = tr.rolling(window=di_length).mean()
    plus_di = 100 * (plus_dm.rolling(window=di_length).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(window=di_length).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=adx_smoothing).mean()
    
    return adx, plus_di, minus_di

def calculate_rsi(df, period=14):
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def main():
    print("=" * 80)
    print("POLICYBZR SHORT SIGNAL ANALYSIS - 9:27 AM")
    print("=" * 80)
    print()
    
    # User's trade details
    entry_price = 1411.50
    exit_price = 1438.62
    entry_time = "9:27"
    exit_time = "10:06"
    loss_pct = ((exit_price - entry_price) / entry_price) * 100
    
    print(f"YOUR TRADE:")
    print(f"  SHORT Entry: ₹{entry_price} at {entry_time}")
    print(f"  Exit (Loss): ₹{exit_price} at {exit_time}")
    print(f"  Loss: ₹{exit_price - entry_price:.2f} ({loss_pct:.2f}%)")
    print()
    
    # Fetch data
    ticker = yf.Ticker("POLICYBZR.NS")
    df_5m = ticker.history(period="1d", interval="5m")
    
    if len(df_5m) < 20:
        print("ERROR: Not enough data")
        return
    
    # Calculate indicators
    df_5m['VWAP'] = calculate_vwap(df_5m)
    df_5m['ST'], df_5m['ST_Dir'], df_5m['ATR'] = calculate_supertrend(df_5m, 10, 3)
    df_5m['ADX'], df_5m['Plus_DI'], df_5m['Minus_DI'] = calculate_adx(df_5m, 10, 10)
    df_5m['RSI'] = calculate_rsi(df_5m, 14)
    
    print("=" * 80)
    print("POLICYBZR 5-MINUTE DATA (9:15 AM - 10:30 AM)")
    print("=" * 80)
    print()
    
    # Filter for morning session
    morning_df = df_5m.between_time('09:15', '10:30')
    
    print(f"{'Time':<12} {'Close':>10} {'VWAP':>10} {'ST':>10} {'ST Dir':>8} {'ADX':>8} {'+DI':>8} {'-DI':>8} {'RSI':>8}")
    print("-" * 95)
    
    for idx, row in morning_df.iterrows():
        time_str = idx.strftime('%H:%M')
        st_dir = "BULL" if row['ST_Dir'] == 1 else "BEAR" if row['ST_Dir'] == -1 else "N/A"
        
        # Highlight the entry time (around 9:25-9:30)
        highlight = " <-- ENTRY" if "09:25" <= time_str <= "09:30" else ""
        highlight = " <-- EXIT" if "10:05" <= time_str <= "10:10" else highlight
        
        print(f"{time_str:<12} {row['Close']:>10.2f} {row['VWAP']:>10.2f} {row['ST']:>10.2f} {st_dir:>8} {row['ADX']:>8.1f} {row['Plus_DI']:>8.1f} {row['Minus_DI']:>8.1f} {row['RSI']:>8.1f}{highlight}")
    
    print()
    print("=" * 80)
    print("ANALYSIS: WHY THE SHORT SIGNAL FAILED")
    print("=" * 80)
    
    # Get data around 9:25-9:30
    entry_candles = df_5m.between_time('09:20', '09:35')
    
    if len(entry_candles) > 0:
        entry_candle = entry_candles.iloc[0]
        
        print()
        print(f"AT SIGNAL TIME (~9:25-9:30):")
        print(f"  Close: ₹{entry_candle['Close']:.2f}")
        print(f"  VWAP:  ₹{entry_candle['VWAP']:.2f}")
        print(f"  Supertrend: ₹{entry_candle['ST']:.2f} ({'BULLISH' if entry_candle['ST_Dir'] == 1 else 'BEARISH'})")
        print(f"  ADX: {entry_candle['ADX']:.1f}")
        print(f"  +DI: {entry_candle['Plus_DI']:.1f}, -DI: {entry_candle['Minus_DI']:.1f}")
        print(f"  RSI: {entry_candle['RSI']:.1f}")
        
        # Check conditions
        print()
        print("SIGNAL CONDITIONS CHECK:")
        
        # Price vs VWAP
        below_vwap = entry_candle['Close'] < entry_candle['VWAP']
        print(f"  Price < VWAP: {'✅ YES' if below_vwap else '❌ NO'} ({entry_candle['Close']:.2f} vs {entry_candle['VWAP']:.2f})")
        
        # Supertrend
        st_bearish = entry_candle['ST_Dir'] == -1
        print(f"  Supertrend Bearish: {'✅ YES' if st_bearish else '❌ NO'}")
        
        # ADX
        adx_ok = entry_candle['ADX'] >= 20
        print(f"  ADX >= 20: {'✅ YES' if adx_ok else '❌ NO'} ({entry_candle['ADX']:.1f})")
        
        # DI
        minus_di_higher = entry_candle['Minus_DI'] > entry_candle['Plus_DI']
        print(f"  -DI > +DI (Bearish): {'✅ YES' if minus_di_higher else '❌ NO'} ({entry_candle['Minus_DI']:.1f} vs {entry_candle['Plus_DI']:.1f})")
        
        # Check ADX trend (rising or falling)
        if len(entry_candles) > 1:
            adx_prev = df_5m['ADX'].shift(1).loc[entry_candle.name]
            adx_change = entry_candle['ADX'] - adx_prev
            adx_rising = adx_change > 0.5
            print(f"  ADX Rising: {'✅ YES' if adx_rising else '❌ NO'} (Change: {adx_change:+.1f})")
        
        # RSI analysis
        rsi_overbought = entry_candle['RSI'] > 70
        rsi_oversold = entry_candle['RSI'] < 30
        print(f"  RSI: {entry_candle['RSI']:.1f} ({'Overbought' if rsi_overbought else 'Oversold' if rsi_oversold else 'Neutral'})")
    
    # Check what happened after
    print()
    print("=" * 80)
    print("WHAT HAPPENED AFTER (Price Action)")
    print("=" * 80)
    
    post_entry = df_5m.between_time('09:30', '10:30')
    if len(post_entry) > 0:
        high_after = post_entry['High'].max()
        low_after = post_entry['Low'].min()
        close_at_exit = post_entry.between_time('10:05', '10:10')['Close'].iloc[0] if len(post_entry.between_time('10:05', '10:10')) > 0 else post_entry['Close'].iloc[-1]
        
        print(f"  High reached: ₹{high_after:.2f} (from entry ₹{entry_price})")
        print(f"  Low reached: ₹{low_after:.2f}")
        print(f"  You exited at: ₹{exit_price:.2f}")
        print()
        
        # Did price ever go in favor?
        favorable_move = entry_price - low_after
        adverse_move = high_after - entry_price
        
        print(f"  Max favorable move (down): ₹{favorable_move:.2f} ({favorable_move/entry_price*100:.2f}%)")
        print(f"  Max adverse move (up): ₹{adverse_move:.2f} ({adverse_move/entry_price*100:.2f}%)")
    
    print()
    print("=" * 80)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 80)
    
    # Check opening action
    first_candle = df_5m.iloc[0]
    second_candle = df_5m.iloc[1] if len(df_5m) > 1 else first_candle
    third_candle = df_5m.iloc[2] if len(df_5m) > 2 else first_candle
    
    print()
    print("OPENING ACTION (First 15 minutes):")
    print(f"  9:15 candle: Open ₹{first_candle['Open']:.2f}, Close ₹{first_candle['Close']:.2f}")
    if len(df_5m) > 1:
        print(f"  9:20 candle: Open ₹{second_candle['Open']:.2f}, Close ₹{second_candle['Close']:.2f}")
    if len(df_5m) > 2:
        print(f"  9:25 candle: Open ₹{third_candle['Open']:.2f}, Close ₹{third_candle['Close']:.2f}")
    
    # Check if it was a gap up or gap down
    prev_close = ticker.history(period="5d", interval="1d")['Close'].iloc[-2] if len(ticker.history(period="5d", interval="1d")) > 1 else first_candle['Open']
    gap_pct = ((first_candle['Open'] - prev_close) / prev_close) * 100
    
    print()
    print(f"  Previous Close: ₹{prev_close:.2f}")
    print(f"  Today's Open: ₹{first_candle['Open']:.2f}")
    print(f"  Gap: {gap_pct:+.2f}%")
    
    print()
    print("CONCLUSION:")
    print("-" * 40)
    
    # Analyze the issue
    if gap_pct > 0.5:
        print("⚠️  Stock opened with a GAP UP - shorting gap ups in first 30 min is risky!")
    
    if not st_bearish:
        print("❌ Supertrend was NOT bearish at entry - signal should not have triggered!")
    
    if not below_vwap:
        print("❌ Price was above VWAP - not a valid short!")
    
    if not adx_ok:
        print("❌ ADX was below 20 - no trend, should have been blocked!")
    
    if minus_di_higher:
        print("⚠️  -DI > +DI suggested bearish, but this can be misleading at market open")
    
    print()
    print("RECOMMENDATION:")
    print("  🚫 AVOID trading in first 15-30 minutes of market open")
    print("  🚫 Opening volatility creates false signals")
    print("  ✅ Wait for 9:45 AM for cleaner signals")

if __name__ == "__main__":
    main()
