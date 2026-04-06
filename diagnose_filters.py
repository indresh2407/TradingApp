"""
Diagnose why no trades are being generated
Check each filter step by step
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import warnings
warnings.filterwarnings('ignore')

IST = pytz.timezone('Asia/Kolkata')

# Test with fewer stocks first
TEST_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", 
    "KOTAKBANK", "HCLTECH", "ONGC", "SBIN"
]

def calculate_supertrend(high, low, close, period=10, multiplier=3.0):
    if len(close) < period + 5:
        return pd.Series([np.nan]*len(close)), pd.Series([0]*len(close))
    
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)
    
    for i in range(period, len(close)):
        if basic_upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]
        
        if basic_lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]
        
        if i == period:
            if close.iloc[i] <= final_upper.iloc[i]:
                supertrend.iloc[i] = final_upper.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = final_lower.iloc[i]
                direction.iloc[i] = 1
        else:
            if supertrend.iloc[i-1] == final_upper.iloc[i-1]:
                if close.iloc[i] > final_upper.iloc[i]:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
                else:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
            else:
                if close.iloc[i] < final_lower.iloc[i]:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1
                else:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1
    
    return supertrend, direction

def calculate_vwap(df):
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def calculate_adx(high, low, close, di_length=10, adx_smoothing=10):
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

def diagnose_stock(symbol):
    """Diagnose a single stock"""
    
    print(f"\n{'='*60}")
    print(f"DIAGNOSING: {symbol}")
    print(f"{'='*60}")
    
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(period="5d", interval="5m")
        
        print(f"Total data fetched: {len(df)} candles")
        
        if len(df) < 25:
            print("❌ Not enough data")
            return
        
        # Get the LAST trading day
        last_trading_day = df.index[-1].date()
        df_today = df[df.index.date == last_trading_day].copy()
        
        print(f"Last trading day: {last_trading_day}")
        print(f"Today's candles: {len(df_today)}")
        
        if len(df_today) < 25:
            print("❌ Not enough today's data")
            return
        
        # Calculate indicators
        df_today['VWAP'] = calculate_vwap(df_today)
        st, st_dir = calculate_supertrend(df_today['High'], df_today['Low'], df_today['Close'])
        df_today['ST'] = st
        df_today['ST_Dir'] = st_dir
        
        adx_result = calculate_adx(df_today['High'], df_today['Low'], df_today['Close'])
        if adx_result is None:
            print("❌ Could not calculate ADX")
            return
        
        adx, plus_di, minus_di = adx_result
        
        # Check last few candles
        print(f"\nLAST 5 CANDLES:")
        print(f"{'Time':<8} {'Close':>10} {'ADX':>8} {'+DI':>8} {'-DI':>8} {'ST Dir':>8}")
        print("-"*55)
        
        for i in range(-5, 0):
            idx = len(df_today) + i
            time_str = df_today.index[idx].strftime('%H:%M')
            close = df_today['Close'].iloc[idx]
            curr_adx = adx.iloc[idx] if not pd.isna(adx.iloc[idx]) else 0
            curr_plus = plus_di.iloc[idx] if not pd.isna(plus_di.iloc[idx]) else 0
            curr_minus = minus_di.iloc[idx] if not pd.isna(minus_di.iloc[idx]) else 0
            curr_st = "BULL" if st_dir.iloc[idx] == 1 else "BEAR" if st_dir.iloc[idx] == -1 else "N/A"
            
            print(f"{time_str:<8} {close:>10.2f} {curr_adx:>8.1f} {curr_plus:>8.1f} {curr_minus:>8.1f} {curr_st:>8}")
        
        # Count filter blocks throughout the day
        print(f"\nFILTER ANALYSIS (from candle 20 to end):")
        
        blocks = {
            'nan_adx': 0,
            'adx_low': 0,
            'adx_falling': 0,
            'adx_not_rising': 0,
            'adx_exhausted': 0,
            'di_gap_narrow': 0,
            'no_signal': 0,
            'st_mismatch': 0,
            'passed': 0
        }
        
        for idx in range(20, len(df_today)):
            curr_adx = adx.iloc[idx]
            prev_adx = adx.iloc[idx-1] if idx > 0 else curr_adx
            curr_plus = plus_di.iloc[idx]
            curr_minus = minus_di.iloc[idx]
            prev_plus = plus_di.iloc[idx-1] if idx > 0 else curr_plus
            prev_minus = minus_di.iloc[idx-1] if idx > 0 else curr_minus
            curr_st = st_dir.iloc[idx]
            curr_close = df_today['Close'].iloc[idx]
            curr_vwap = df_today['VWAP'].iloc[idx]
            
            # Check filters
            if pd.isna(curr_adx) or curr_adx == 0:
                blocks['nan_adx'] += 1
                continue
            
            if curr_adx < 20:
                blocks['adx_low'] += 1
                continue
            
            adx_change = curr_adx - prev_adx
            if adx_change < -0.5 and curr_adx > 15:
                blocks['adx_falling'] += 1
                continue
            
            if adx_change <= 0.5 and curr_adx < 30:
                blocks['adx_not_rising'] += 1
                continue
            
            if curr_adx > 80:
                blocks['adx_exhausted'] += 1
                continue
            
            curr_gap = abs(curr_plus - curr_minus)
            prev_gap = abs(prev_plus - prev_minus)
            gap_change = curr_gap - prev_gap
            if gap_change < -1.0 and curr_gap < 15:
                blocks['di_gap_narrow'] += 1
                continue
            
            # Generate signal
            signal = None
            if curr_st == 1 and curr_close > curr_vwap and curr_plus > curr_minus:
                signal = "LONG"
            elif curr_st == -1 and curr_close < curr_vwap and curr_minus > curr_plus:
                signal = "SHORT"
            
            if signal is None:
                blocks['no_signal'] += 1
                continue
            
            # Check ST direction match
            if signal == "LONG" and curr_st != 1:
                blocks['st_mismatch'] += 1
                continue
            if signal == "SHORT" and curr_st != -1:
                blocks['st_mismatch'] += 1
                continue
            
            blocks['passed'] += 1
        
        total_candles = len(df_today) - 20
        print(f"  Total candles checked: {total_candles}")
        print(f"  ❌ NaN ADX: {blocks['nan_adx']}")
        print(f"  ❌ ADX < 20: {blocks['adx_low']}")
        print(f"  ❌ ADX Falling: {blocks['adx_falling']}")
        print(f"  ❌ ADX Not Rising: {blocks['adx_not_rising']}")
        print(f"  ❌ ADX > 80: {blocks['adx_exhausted']}")
        print(f"  ❌ DI Gap Narrow: {blocks['di_gap_narrow']}")
        print(f"  ❌ No Signal (VWAP/DI): {blocks['no_signal']}")
        print(f"  ❌ ST Mismatch: {blocks['st_mismatch']}")
        print(f"  ✅ PASSED ALL: {blocks['passed']}")
        
        return blocks
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("="*60)
    print("FILTER DIAGNOSTIC REPORT")
    print("="*60)
    print(f"Testing {len(TEST_STOCKS)} stocks to see where signals are blocked")
    
    total_blocks = {
        'nan_adx': 0,
        'adx_low': 0,
        'adx_falling': 0,
        'adx_not_rising': 0,
        'adx_exhausted': 0,
        'di_gap_narrow': 0,
        'no_signal': 0,
        'st_mismatch': 0,
        'passed': 0
    }
    
    for symbol in TEST_STOCKS:
        blocks = diagnose_stock(symbol)
        if blocks:
            for key in total_blocks:
                total_blocks[key] += blocks.get(key, 0)
    
    print("\n" + "="*60)
    print("AGGREGATE SUMMARY")
    print("="*60)
    total = sum(total_blocks.values())
    print(f"\nTotal candles analyzed: {total}")
    print(f"\nBLOCK REASONS:")
    for key, val in total_blocks.items():
        if key != 'passed':
            pct = (val / total * 100) if total > 0 else 0
            print(f"  {key}: {val} ({pct:.1f}%)")
    
    pct_passed = (total_blocks['passed'] / total * 100) if total > 0 else 0
    print(f"\n✅ PASSED ALL FILTERS: {total_blocks['passed']} ({pct_passed:.1f}%)")
    
    if total_blocks['passed'] == 0:
        print("\n⚠️ NO SIGNALS PASSED!")
        print("The most common block reason is:", max(total_blocks, key=lambda k: total_blocks[k] if k != 'passed' else 0))

if __name__ == "__main__":
    main()
