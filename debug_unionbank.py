"""
Debug UNIONBANK LONG Signal at 10:08 AM
Analyze what went wrong
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz

IST = pytz.timezone('Asia/Kolkata')

def calculate_supertrend(df, period=10, multiplier=3):
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
    print("UNIONBANK LONG SIGNAL ANALYSIS - 10:08 AM")
    print("=" * 80)
    print()
    
    # User's trade details
    entry_price = 174.09
    exit_price = 173.43
    entry_time = "10:08"
    exit_time = "10:20"
    loss = entry_price - exit_price
    loss_pct = (loss / entry_price) * 100
    
    print(f"YOUR TRADE:")
    print(f"  LONG Entry: ₹{entry_price} at {entry_time}")
    print(f"  Exit (Loss): ₹{exit_price} at {exit_time}")
    print(f"  Loss: ₹{loss:.2f} ({loss_pct:.2f}%)")
    print()
    
    # Fetch data - try different symbol formats
    symbols_to_try = ["UNIONBANK.NS", "UCOBANK.NS", "BANKBARODA.NS"]
    
    # Most likely it's UNIONBANK or could be BANKINDIA
    ticker = yf.Ticker("UNIONBANK.NS")
    df_5m = ticker.history(period="1d", interval="5m")
    
    if len(df_5m) < 10:
        print("Trying alternate symbol...")
        # Try PSU Bank symbols
        for sym in ["BANKINDIA.NS", "UCOBANK.NS", "CANBK.NS", "MAHABANK.NS"]:
            ticker = yf.Ticker(sym)
            df_5m = ticker.history(period="1d", interval="5m")
            if len(df_5m) > 10:
                # Check if price is around 174
                if 170 < df_5m['Close'].iloc[-1] < 180:
                    print(f"Found matching symbol: {sym}")
                    break
    
    if len(df_5m) < 20:
        print("ERROR: Not enough data for UNIONBANK")
        print("Note: The symbol might be different. Common PSU bank symbols:")
        print("  - UNIONBANK.NS, BANKINDIA.NS, CANBK.NS, PNB.NS")
        return
    
    # Calculate indicators
    df_5m['VWAP'] = calculate_vwap(df_5m)
    df_5m['ST'], df_5m['ST_Dir'], df_5m['ATR'] = calculate_supertrend(df_5m, 10, 3)
    df_5m['ADX'], df_5m['Plus_DI'], df_5m['Minus_DI'] = calculate_adx(df_5m, 10, 10)
    df_5m['RSI'] = calculate_rsi(df_5m, 14)
    
    print("=" * 80)
    print("5-MINUTE DATA (9:45 AM - 10:30 AM)")
    print("=" * 80)
    print()
    
    # Filter for relevant time
    try:
        analysis_df = df_5m.between_time('09:45', '10:30')
    except:
        analysis_df = df_5m.tail(20)
    
    print(f"{'Time':<12} {'Close':>10} {'VWAP':>10} {'ST':>10} {'ST Dir':>8} {'ADX':>8} {'+DI':>8} {'-DI':>8} {'RSI':>8}")
    print("-" * 95)
    
    for idx, row in analysis_df.iterrows():
        try:
            time_str = idx.strftime('%H:%M')
        except:
            time_str = str(idx)[:5]
        
        st_dir = "BULL" if row['ST_Dir'] == 1 else "BEAR" if row['ST_Dir'] == -1 else "N/A"
        
        # Highlight entry and exit times
        highlight = ""
        if "10:05" <= time_str <= "10:10":
            highlight = " <-- ENTRY"
        elif "10:15" <= time_str <= "10:20":
            highlight = " <-- EXIT"
        
        adx_val = f"{row['ADX']:.1f}" if not pd.isna(row['ADX']) else "nan"
        plus_di = f"{row['Plus_DI']:.1f}" if not pd.isna(row['Plus_DI']) else "nan"
        minus_di = f"{row['Minus_DI']:.1f}" if not pd.isna(row['Minus_DI']) else "nan"
        rsi_val = f"{row['RSI']:.1f}" if not pd.isna(row['RSI']) else "nan"
        st_val = f"{row['ST']:.2f}" if not pd.isna(row['ST']) else "nan"
        
        print(f"{time_str:<12} {row['Close']:>10.2f} {row['VWAP']:>10.2f} {st_val:>10} {st_dir:>8} {adx_val:>8} {plus_di:>8} {minus_di:>8} {rsi_val:>8}{highlight}")
    
    print()
    print("=" * 80)
    print("ANALYSIS AT ENTRY TIME (~10:08)")
    print("=" * 80)
    
    # Get data around 10:05-10:10
    try:
        entry_candles = df_5m.between_time('10:05', '10:10')
        if len(entry_candles) > 0:
            entry_candle = entry_candles.iloc[0]
            
            print()
            print(f"AT SIGNAL TIME (~10:05-10:10):")
            print(f"  Close: ₹{entry_candle['Close']:.2f}")
            print(f"  VWAP:  ₹{entry_candle['VWAP']:.2f}")
            
            st_dir_text = "BULLISH" if entry_candle['ST_Dir'] == 1 else "BEARISH" if entry_candle['ST_Dir'] == -1 else "N/A"
            print(f"  Supertrend: ₹{entry_candle['ST']:.2f} ({st_dir_text})")
            print(f"  ADX: {entry_candle['ADX']:.1f}")
            print(f"  +DI: {entry_candle['Plus_DI']:.1f}, -DI: {entry_candle['Minus_DI']:.1f}")
            print(f"  RSI: {entry_candle['RSI']:.1f}")
            
            print()
            print("SIGNAL CONDITIONS CHECK:")
            
            # Price vs VWAP
            above_vwap = entry_candle['Close'] > entry_candle['VWAP']
            print(f"  Price > VWAP: {'✅ YES' if above_vwap else '❌ NO'} ({entry_candle['Close']:.2f} vs {entry_candle['VWAP']:.2f})")
            
            # Supertrend
            st_bullish = entry_candle['ST_Dir'] == 1
            print(f"  Supertrend Bullish: {'✅ YES' if st_bullish else '❌ NO'}")
            
            # ADX
            adx_ok = entry_candle['ADX'] >= 20
            print(f"  ADX >= 20: {'✅ YES' if adx_ok else '❌ NO'} ({entry_candle['ADX']:.1f})")
            
            # DI
            plus_di_higher = entry_candle['Plus_DI'] > entry_candle['Minus_DI']
            print(f"  +DI > -DI (Bullish): {'✅ YES' if plus_di_higher else '❌ NO'} ({entry_candle['Plus_DI']:.1f} vs {entry_candle['Minus_DI']:.1f})")
            
            # ADX Rising check
            if len(df_5m) > 1:
                prev_idx = df_5m.index.get_loc(entry_candle.name) - 1
                if prev_idx >= 0:
                    adx_prev = df_5m['ADX'].iloc[prev_idx]
                    adx_change = entry_candle['ADX'] - adx_prev
                    adx_rising = adx_change > 0.5
                    print(f"  ADX Rising: {'✅ YES' if adx_rising else '❌ NO'} (Change: {adx_change:+.1f})")
            
            # RSI analysis
            rsi = entry_candle['RSI']
            if rsi > 70:
                rsi_status = "⚠️ OVERBOUGHT - risky for LONG"
            elif rsi > 60:
                rsi_status = "Elevated"
            elif rsi < 30:
                rsi_status = "Oversold - good for LONG"
            else:
                rsi_status = "Neutral"
            print(f"  RSI: {rsi:.1f} ({rsi_status})")
    except Exception as e:
        print(f"Error analyzing entry time: {e}")
    
    # What happened after
    print()
    print("=" * 80)
    print("WHAT HAPPENED AFTER (Price Action)")
    print("=" * 80)
    
    try:
        post_entry = df_5m.between_time('10:10', '10:30')
        if len(post_entry) > 0:
            high_after = post_entry['High'].max()
            low_after = post_entry['Low'].min()
            
            print(f"  Entry Price: ₹{entry_price}")
            print(f"  High reached: ₹{high_after:.2f}")
            print(f"  Low reached: ₹{low_after:.2f}")
            print(f"  You exited at: ₹{exit_price}")
            print()
            
            favorable_move = high_after - entry_price
            adverse_move = entry_price - low_after
            
            print(f"  Max favorable move (up): ₹{favorable_move:.2f} ({favorable_move/entry_price*100:.2f}%)")
            print(f"  Max adverse move (down): ₹{adverse_move:.2f} ({adverse_move/entry_price*100:.2f}%)")
            
            if favorable_move > 0:
                print(f"\n  💡 Stock DID move up to ₹{high_after:.2f} - you may have exited too early")
    except Exception as e:
        print(f"Error analyzing post-entry: {e}")
    
    print()
    print("=" * 80)
    print("ROOT CAUSE ANALYSIS")
    print("=" * 80)
    
    # Check overall trend
    try:
        morning_high = df_5m.between_time('09:15', '10:00')['High'].max()
        morning_low = df_5m.between_time('09:15', '10:00')['Low'].min()
        
        print()
        print(f"MORNING SESSION (9:15-10:00):")
        print(f"  High: ₹{morning_high:.2f}")
        print(f"  Low: ₹{morning_low:.2f}")
        print(f"  Range: ₹{morning_high - morning_low:.2f}")
        
        # Check if entry was near high
        if entry_price > morning_high * 0.998:
            print(f"\n  ⚠️ You entered near the morning HIGH - risky!")
    except:
        pass
    
    print()
    print("POSSIBLE ISSUES:")
    print("-" * 40)
    print("  1. Entry near day's high = limited upside")
    print("  2. Quick reversal = normal intraday volatility")
    print("  3. May have exited too early if stock recovered")
    print()
    print("RECOMMENDATIONS:")
    print("  ✅ Set stoploss and wait for target instead of panic exit")
    print("  ✅ Don't enter if price is already up significantly from open")
    print("  ✅ Check if stock already moved 1%+ before entering")

if __name__ == "__main__":
    main()
