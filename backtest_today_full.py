"""
Backtest DayTrade Strategy on Today's Market
Tests all filters: NaN, ADX, Supertrend, DI Gap Narrowing, ADX Exhaustion
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import warnings
warnings.filterwarnings('ignore')

IST = pytz.timezone('Asia/Kolkata')

# Nifty 100 stocks (sample for speed)
NIFTY_100 = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "ITC", "SBIN", 
    "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "HCLTECH",
    "SUNPHARMA", "TITAN", "ULTRACEMCO", "BAJFINANCE", "WIPRO", "ONGC", "NTPC", 
    "POWERGRID", "M&M", "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS", "TECHM",
    "INDUSINDBK", "HINDALCO", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP", "EICHERMOT",
    "BAJAJFINSV", "NESTLEIND", "GRASIM", "BRITANNIA", "COALINDIA", "BPCL", "TATACONSUM",
    "HEROMOTOCO", "SBILIFE", "HDFCLIFE", "DABUR", "HAVELLS", "PIDILITIND", "SIEMENS",
    "GODREJCP", "MARICO", "BERGEPAINT", "TORNTPHARM", "LUPIN", "ZOMATO", "PAYTM",
    "POLICYBZR", "UNIONBANK", "HAPPSTMNDS"
]

def calculate_supertrend(high, low, close, period=10, multiplier=3.0):
    """Calculate Supertrend indicator"""
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
    """Calculate VWAP"""
    typical_price = (df['High'] + df['Low'] + df['Close']) / 3
    vwap = (typical_price * df['Volume']).cumsum() / df['Volume'].cumsum()
    return vwap

def calculate_adx(high, low, close, di_length=10, adx_smoothing=10):
    """Calculate ADX with DI gap analysis"""
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
    
    return adx, plus_di, minus_di, atr

def calculate_atr(high, low, close, period=14):
    """Calculate ATR"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def check_filters(idx, df, adx, plus_di, minus_di, st_dir):
    """Check all filters at a given index, return (pass, block_reason)"""
    
    # Get values
    curr_adx = adx.iloc[idx]
    curr_plus_di = plus_di.iloc[idx]
    curr_minus_di = minus_di.iloc[idx]
    prev_plus_di = plus_di.iloc[idx-1] if idx > 0 else curr_plus_di
    prev_minus_di = minus_di.iloc[idx-1] if idx > 0 else curr_minus_di
    prev_adx = adx.iloc[idx-1] if idx > 0 else curr_adx
    curr_st_dir = st_dir.iloc[idx]
    
    # 1. NaN check
    if pd.isna(curr_adx) or curr_adx == 0:
        return False, "NaN ADX"
    
    # 2. ADX < 20
    if curr_adx < 20:
        return False, f"ADX<20 ({curr_adx:.0f})"
    
    # 3. ADX falling
    adx_change = curr_adx - prev_adx
    if adx_change < -0.5 and curr_adx > 15:
        return False, f"ADX Falling ({adx_change:+.1f})"
    
    # 4. ADX not rising (unless >= 30)
    if adx_change <= 0.5 and curr_adx < 30:
        return False, f"ADX Not Rising ({curr_adx:.0f})"
    
    # 5. ADX Exhaustion (> 80)
    if curr_adx > 80:
        return False, f"ADX Exhausted ({curr_adx:.0f})"
    
    # 6. DI Gap Narrowing
    curr_gap = abs(curr_plus_di - curr_minus_di)
    prev_gap = abs(prev_plus_di - prev_minus_di)
    gap_change = curr_gap - prev_gap
    if gap_change < -1.0 and curr_gap < 15:
        return False, f"DI Gap Narrow ({curr_gap:.0f})"
    
    return True, None

def generate_signal(idx, df, adx, plus_di, minus_di, st_dir, vwap):
    """Generate signal at given index"""
    
    curr_close = df['Close'].iloc[idx]
    curr_vwap = vwap.iloc[idx]
    curr_st_dir = st_dir.iloc[idx]
    curr_plus_di = plus_di.iloc[idx]
    curr_minus_di = minus_di.iloc[idx]
    
    # Check Supertrend direction
    if curr_st_dir == 1:  # BULLISH
        # For LONG: price > VWAP, +DI > -DI
        if curr_close > curr_vwap and curr_plus_di > curr_minus_di:
            return "LONG"
    elif curr_st_dir == -1:  # BEARISH
        # For SHORT: price < VWAP, -DI > +DI
        if curr_close < curr_vwap and curr_minus_di > curr_plus_di:
            return "SHORT"
    
    return None

def simulate_trade(df, entry_idx, signal, atr_val):
    """Simulate trade outcome from entry to end of day"""
    
    entry_price = df['Close'].iloc[entry_idx]
    
    # Calculate targets and stoploss based on ATR
    if signal == "LONG":
        stoploss = entry_price - (atr_val * 1.5)
        target1 = entry_price + (atr_val * 1.0)
        target2 = entry_price + (atr_val * 1.5)
    else:  # SHORT
        stoploss = entry_price + (atr_val * 1.5)
        target1 = entry_price - (atr_val * 1.0)
        target2 = entry_price - (atr_val * 1.5)
    
    # Simulate from entry to end of day
    for i in range(entry_idx + 1, len(df)):
        high = df['High'].iloc[i]
        low = df['Low'].iloc[i]
        
        if signal == "LONG":
            # Check stoploss first
            if low <= stoploss:
                pnl = ((stoploss - entry_price) / entry_price) * 100
                return "SL_HIT", pnl, i - entry_idx
            # Check T2 (higher target)
            if high >= target2:
                pnl = ((target2 - entry_price) / entry_price) * 100
                return "T2_HIT", pnl, i - entry_idx
            # Check T1
            if high >= target1:
                pnl = ((target1 - entry_price) / entry_price) * 100
                return "T1_HIT", pnl, i - entry_idx
        else:  # SHORT
            # Check stoploss first
            if high >= stoploss:
                pnl = ((entry_price - stoploss) / entry_price) * 100
                return "SL_HIT", pnl, i - entry_idx
            # Check T2
            if low <= target2:
                pnl = ((entry_price - target2) / entry_price) * 100
                return "T2_HIT", pnl, i - entry_idx
            # Check T1
            if low <= target1:
                pnl = ((entry_price - target1) / entry_price) * 100
                return "T1_HIT", pnl, i - entry_idx
    
    # End of day - close at last price
    exit_price = df['Close'].iloc[-1]
    if signal == "LONG":
        pnl = ((exit_price - entry_price) / entry_price) * 100
    else:
        pnl = ((entry_price - exit_price) / entry_price) * 100
    
    return "EOD_EXIT", pnl, len(df) - entry_idx

def backtest_stock(symbol):
    """Backtest a single stock"""
    
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        # Use 5d to get last trading day data (in case today is weekend)
        df = ticker.history(period="5d", interval="5m")
        
        if len(df) < 25:
            return None
        
        # Get the LAST trading day (could be Friday if today is weekend)
        last_trading_day = df.index[-1].date()
        df_today = df[df.index.date == last_trading_day].copy()
        
        if len(df_today) < 25:
            return None
        
        # Calculate indicators
        df_today['VWAP'] = calculate_vwap(df_today)
        st, st_dir = calculate_supertrend(df_today['High'], df_today['Low'], df_today['Close'])
        df_today['ST'] = st
        df_today['ST_Dir'] = st_dir
        
        adx_result = calculate_adx(df_today['High'], df_today['Low'], df_today['Close'])
        if adx_result is None:
            return None
        
        adx, plus_di, minus_di, _ = adx_result
        atr = calculate_atr(df_today['High'], df_today['Low'], df_today['Close'])
        
        trades = []
        
        # Scan from 10:00 AM onwards (after indicators are ready)
        start_idx = 20  # Skip first ~20 candles (9:15 + 100 min = ~10:55)
        last_signal_idx = -10  # Track last signal to avoid duplicates
        
        for idx in range(start_idx, len(df_today) - 5):  # Leave room for trade simulation
            # Skip if too close to last signal
            if idx - last_signal_idx < 3:
                continue
                
            # Check filters
            passes, block_reason = check_filters(idx, df_today, adx, plus_di, minus_di, st_dir)
            
            if not passes:
                continue
            
            # Generate signal
            signal = generate_signal(idx, df_today, adx, plus_di, minus_di, st_dir, df_today['VWAP'])
            
            if signal is None:
                continue
            
            # Check Supertrend direction matches signal
            curr_st_dir = st_dir.iloc[idx]
            if signal == "LONG" and curr_st_dir != 1:
                continue
            if signal == "SHORT" and curr_st_dir != -1:
                continue
            
            # Get ATR for targets
            atr_val = atr.iloc[idx]
            if pd.isna(atr_val) or atr_val == 0:
                continue
            
            # Simulate trade
            outcome, pnl, hold_candles = simulate_trade(df_today, idx, signal, atr_val)
            
            entry_time = df_today.index[idx].strftime('%H:%M')
            entry_price = df_today['Close'].iloc[idx]
            curr_adx = adx.iloc[idx]
            
            trades.append({
                'symbol': symbol,
                'time': entry_time,
                'signal': signal,
                'entry': entry_price,
                'adx': curr_adx,
                'outcome': outcome,
                'pnl': pnl,
                'hold_candles': hold_candles
            })
            
            # Mark this signal to avoid duplicates
            last_signal_idx = idx
        
        return trades
    
    except Exception as e:
        return None

def main():
    print("="*70)
    print("BACKTEST: DayTrade Strategy - Last Trading Day")
    print("="*70)
    
    # Get last trading day from a sample stock
    sample = yf.Ticker("RELIANCE.NS")
    sample_df = sample.history(period="5d", interval="5m")
    if len(sample_df) > 0:
        last_trading_day = sample_df.index[-1].date()
        print(f"Trading Day: {last_trading_day.strftime('%Y-%m-%d (%A)')}")
    else:
        print("Could not determine trading day")
        return
    
    print(f"Testing {len(NIFTY_100)} stocks")
    print()
    print("FILTERS APPLIED:")
    print("  1. ADX >= 20 (minimum trend)")
    print("  2. ADX Rising (or >= 30)")
    print("  3. ADX Not Falling")
    print("  4. ADX < 80 (not exhausted)")
    print("  5. DI Gap Not Narrowing (if gap < 15)")
    print("  6. Supertrend matches signal direction")
    print()
    
    all_trades = []
    processed = 0
    
    for symbol in NIFTY_100:
        processed += 1
        print(f"\rProcessing: {processed}/{len(NIFTY_100)} - {symbol}...", end="", flush=True)
        
        trades = backtest_stock(symbol)
        if trades:
            all_trades.extend(trades)
    
    print(f"\rProcessed {len(NIFTY_100)} stocks" + " " * 30)
    print()
    
    if not all_trades:
        print("No trades generated with current filters")
        return
    
    # Analyze results
    df_trades = pd.DataFrame(all_trades)
    
    print("="*70)
    print("BACKTEST RESULTS")
    print("="*70)
    print()
    
    total_trades = len(df_trades)
    winners = df_trades[df_trades['pnl'] > 0]
    losers = df_trades[df_trades['pnl'] <= 0]
    
    t1_hits = len(df_trades[df_trades['outcome'] == 'T1_HIT'])
    t2_hits = len(df_trades[df_trades['outcome'] == 'T2_HIT'])
    sl_hits = len(df_trades[df_trades['outcome'] == 'SL_HIT'])
    eod_exits = len(df_trades[df_trades['outcome'] == 'EOD_EXIT'])
    
    win_rate = (len(winners) / total_trades * 100) if total_trades > 0 else 0
    avg_win = winners['pnl'].mean() if len(winners) > 0 else 0
    avg_loss = losers['pnl'].mean() if len(losers) > 0 else 0
    total_pnl = df_trades['pnl'].sum()
    
    print(f"SUMMARY:")
    print(f"  Total Signals Generated: {total_trades}")
    print(f"  Winners: {len(winners)} ({win_rate:.1f}%)")
    print(f"  Losers: {len(losers)} ({100-win_rate:.1f}%)")
    print()
    print(f"OUTCOMES:")
    print(f"  T1 Hit: {t1_hits} ({t1_hits/total_trades*100:.1f}%)")
    print(f"  T2 Hit: {t2_hits} ({t2_hits/total_trades*100:.1f}%)")
    print(f"  SL Hit: {sl_hits} ({sl_hits/total_trades*100:.1f}%)")
    print(f"  EOD Exit: {eod_exits} ({eod_exits/total_trades*100:.1f}%)")
    print()
    print(f"P&L:")
    print(f"  Avg Winner: +{avg_win:.2f}%")
    print(f"  Avg Loser: {avg_loss:.2f}%")
    print(f"  Total P&L: {total_pnl:+.2f}%")
    print()
    
    # Show by signal type
    print("BY SIGNAL TYPE:")
    for sig in ['LONG', 'SHORT']:
        sig_trades = df_trades[df_trades['signal'] == sig]
        if len(sig_trades) > 0:
            sig_winners = sig_trades[sig_trades['pnl'] > 0]
            sig_wr = len(sig_winners) / len(sig_trades) * 100
            sig_pnl = sig_trades['pnl'].sum()
            print(f"  {sig}: {len(sig_trades)} trades, {sig_wr:.1f}% win rate, {sig_pnl:+.2f}% P&L")
    
    print()
    print("="*70)
    print("TRADE DETAILS")
    print("="*70)
    print()
    print(f"{'Time':<8} {'Symbol':<12} {'Signal':<6} {'Entry':>10} {'ADX':>6} {'Outcome':<10} {'P&L':>8}")
    print("-"*70)
    
    for _, trade in df_trades.sort_values('time').iterrows():
        pnl_str = f"{trade['pnl']:+.2f}%"
        print(f"{trade['time']:<8} {trade['symbol']:<12} {trade['signal']:<6} {trade['entry']:>10.2f} {trade['adx']:>6.1f} {trade['outcome']:<10} {pnl_str:>8}")
    
    print()
    print("="*70)
    print("TOP 5 WINNERS")
    print("="*70)
    for _, trade in df_trades.nlargest(5, 'pnl').iterrows():
        print(f"  {trade['symbol']} {trade['signal']} at {trade['time']}: {trade['pnl']:+.2f}% ({trade['outcome']})")
    
    print()
    print("="*70)
    print("TOP 5 LOSERS")
    print("="*70)
    for _, trade in df_trades.nsmallest(5, 'pnl').iterrows():
        print(f"  {trade['symbol']} {trade['signal']} at {trade['time']}: {trade['pnl']:+.2f}% ({trade['outcome']})")

if __name__ == "__main__":
    main()
