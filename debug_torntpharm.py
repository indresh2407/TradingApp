"""
Debug TORNTPHARM SHORT Signal at 11:25 AM
"""

import yfinance as yf
import pandas as pd
import numpy as np
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
    high, low, close = df['High'], df['Low'], df['Close']
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
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
    print("TORNTPHARM SHORT SIGNAL ANALYSIS - 11:25 AM")
    print("=" * 80)
    print()
    
    # User's trade
    entry_price = 3957.0
    exit_price = 3973.81
    loss = exit_price - entry_price
    loss_pct = (loss / entry_price) * 100
    
    print(f"YOUR TRADE:")
    print(f"  SHORT Entry: ₹{entry_price} at 11:25")
    print(f"  Exit (Loss): ₹{exit_price} at 11:33")
    print(f"  Loss: ₹{loss:.2f} ({loss_pct:.2f}%) ❌")
    print()
    
    # Fetch TORNTPHARM data
    ticker = yf.Ticker("TORNTPHARM.NS")
    df_5m = ticker.history(period="1d", interval="5m")
    
    if len(df_5m) < 20:
        print("ERROR: Not enough data for TORNTPHARM")
        return
    
    print(f"TORNTPHARM price range today: ₹{df_5m['Close'].min():.2f} - ₹{df_5m['Close'].max():.2f}")
    print()
    
    # Calculate indicators
    df_5m['VWAP'] = calculate_vwap(df_5m)
    df_5m['ST'], df_5m['ST_Dir'], df_5m['ATR'] = calculate_supertrend(df_5m, 10, 3)
    df_5m['ADX'], df_5m['Plus_DI'], df_5m['Minus_DI'] = calculate_adx(df_5m, 10, 10)
    df_5m['RSI'] = calculate_rsi(df_5m, 14)
    
    print("=" * 80)
    print("TORNTPHARM 5-MINUTE DATA (11:00 AM - 11:45 AM)")
    print("=" * 80)
    print()
    
    try:
        analysis_df = df_5m.between_time('11:00', '11:45')
    except:
        analysis_df = df_5m.tail(15)
    
    print(f"{'Time':<12} {'Close':>10} {'VWAP':>10} {'ST':>10} {'ST Dir':>8} {'ADX':>8} {'+DI':>8} {'-DI':>8} {'RSI':>8}")
    print("-" * 95)
    
    for idx, row in analysis_df.iterrows():
        try:
            time_str = idx.strftime('%H:%M')
        except:
            time_str = str(idx)[:5]
        
        st_dir = "BULL" if row['ST_Dir'] == 1 else "BEAR" if row['ST_Dir'] == -1 else "N/A"
        
        highlight = ""
        if "11:25" <= time_str <= "11:30":
            highlight = " <-- ENTRY"
        elif "11:30" <= time_str <= "11:35":
            highlight = " <-- EXIT"
        
        adx_val = f"{row['ADX']:.1f}" if not pd.isna(row['ADX']) else "nan"
        plus_di = f"{row['Plus_DI']:.1f}" if not pd.isna(row['Plus_DI']) else "nan"
        minus_di = f"{row['Minus_DI']:.1f}" if not pd.isna(row['Minus_DI']) else "nan"
        rsi_val = f"{row['RSI']:.1f}" if not pd.isna(row['RSI']) else "nan"
        st_val = f"{row['ST']:.2f}" if not pd.isna(row['ST']) else "nan"
        
        print(f"{time_str:<12} {row['Close']:>10.2f} {row['VWAP']:>10.2f} {st_val:>10} {st_dir:>8} {adx_val:>8} {plus_di:>8} {minus_di:>8} {rsi_val:>8}{highlight}")
    
    print()
    print("=" * 80)
    print("ANALYSIS AT ENTRY TIME (~11:25)")
    print("=" * 80)
    
    try:
        entry_candles = df_5m.between_time('11:20', '11:30')
        if len(entry_candles) > 0:
            entry_candle = entry_candles.iloc[0]
            
            print()
            print(f"AT SIGNAL TIME (~11:20-11:25):")
            print(f"  Close: ₹{entry_candle['Close']:.2f}")
            print(f"  VWAP:  ₹{entry_candle['VWAP']:.2f}")
            
            st_dir_text = "BULLISH" if entry_candle['ST_Dir'] == 1 else "BEARISH" if entry_candle['ST_Dir'] == -1 else "N/A"
            st_val = entry_candle['ST'] if not pd.isna(entry_candle['ST']) else 0
            st_is_nan = pd.isna(entry_candle['ST'])
            print(f"  Supertrend: ₹{st_val:.2f} ({st_dir_text}) {'⚠️ NaN!' if st_is_nan else ''}")
            
            adx = entry_candle['ADX'] if not pd.isna(entry_candle['ADX']) else 0
            adx_is_nan = pd.isna(entry_candle['ADX'])
            plus_di = entry_candle['Plus_DI'] if not pd.isna(entry_candle['Plus_DI']) else 0
            minus_di = entry_candle['Minus_DI'] if not pd.isna(entry_candle['Minus_DI']) else 0
            rsi = entry_candle['RSI'] if not pd.isna(entry_candle['RSI']) else 50
            
            print(f"  ADX: {adx:.1f} {'⚠️ NaN!' if adx_is_nan else ''}")
            print(f"  +DI: {plus_di:.1f}, -DI: {minus_di:.1f}")
            print(f"  RSI: {rsi:.1f}")
            
            print()
            print("SIGNAL CONDITIONS CHECK FOR SHORT:")
            
            below_vwap = entry_candle['Close'] < entry_candle['VWAP']
            print(f"  Price < VWAP: {'✅ YES' if below_vwap else '❌ NO'} ({entry_candle['Close']:.2f} vs {entry_candle['VWAP']:.2f})")
            
            st_bearish = entry_candle['ST_Dir'] == -1
            print(f"  Supertrend Bearish: {'✅ YES' if st_bearish else '❌ NO'} {'(NaN!)' if st_is_nan else ''}")
            
            adx_ok = adx >= 20 and not adx_is_nan
            print(f"  ADX >= 20: {'✅ YES' if adx_ok else '❌ NO'} ({adx:.1f})")
            
            adx_not_nan = not adx_is_nan
            st_not_nan = not st_is_nan
            print(f"  ADX Not NaN: {'✅ YES' if adx_not_nan else '❌ NO'}")
            print(f"  ST Not NaN: {'✅ YES' if st_not_nan else '❌ NO'}")
            
            minus_di_higher = minus_di > plus_di
            print(f"  -DI > +DI (Bearish): {'✅ YES' if minus_di_higher else '❌ NO'} ({minus_di:.1f} vs {plus_di:.1f})")
            
            # Count valid confirmations
            confirmations = sum([below_vwap, st_bearish and st_not_nan, adx_ok, minus_di_higher])
            print(f"\n  TOTAL VALID CONFIRMATIONS: {confirmations}/4")
            
            if st_is_nan or adx_is_nan:
                print("  ⛔ SHOULD BE BLOCKED: Indicators NaN!")
            elif adx < 20:
                print("  ⛔ SHOULD BE BLOCKED: ADX < 20 (no trend)")
            elif confirmations < 4:
                print(f"  ⚠️ WEAK SIGNAL: Only {confirmations} confirmations")
            else:
                print("  ✅ Valid signal")
                
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    print("=" * 80)
    print("WHAT HAPPENED AFTER")
    print("=" * 80)
    
    try:
        post_entry = df_5m.between_time('11:25', '11:45')
        if len(post_entry) > 0:
            high_after = post_entry['High'].max()
            low_after = post_entry['Low'].min()
            
            print(f"\n  Entry Price: ₹{entry_price}")
            print(f"  High reached: ₹{high_after:.2f} (adverse for SHORT)")
            print(f"  Low reached: ₹{low_after:.2f} (favorable for SHORT)")
            print(f"  You exited at: ₹{exit_price}")
            
            favorable_move = entry_price - low_after
            adverse_move = high_after - entry_price
            
            print(f"\n  Max favorable move (down): ₹{favorable_move:.2f} ({favorable_move/entry_price*100:.2f}%)")
            print(f"  Max adverse move (up): ₹{adverse_move:.2f} ({adverse_move/entry_price*100:.2f}%)")
    except Exception as e:
        print(f"Error: {e}")
    
    print()
    print("=" * 80)
    print("SUMMARY: YOUR 4 TRADES TODAY")
    print("=" * 80)
    print()
    print("| Trade           | Time  | ADX   | ST    | Result      |")
    print("|-----------------|-------|-------|-------|-------------|")
    print("| POLICYBZR SHORT | 9:27  | NaN   | NaN   | -1.92% LOSS |")
    print("| UNIONBANK LONG  | 10:08 | NaN   | NaN   | -0.38% LOSS |")
    print("| KOTAKBANK SHORT | 10:47 | 12.2  | NaN   | +0.14% WIN  |")
    print(f"| TORNTPHARM SHORT| 11:25 | ???   | ???   | -{loss_pct:.2f}% LOSS |")
    print()
    print("NET RESULT: Likely NEGATIVE due to bad signals")

if __name__ == "__main__":
    main()
