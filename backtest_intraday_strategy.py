#!/usr/bin/env python3
"""
SIDDHI - Intraday Strategy Backtester
Backtests the Multi-Timeframe (VWAP + Supertrend + Bollinger Bands) Strategy

Run this locally (not in sandbox) to test strategy accuracy:
    python backtest_intraday_strategy.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# ============== STOCK LISTS ==============
NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "BHARTIARTL", "INFY", "SBIN",
    "HINDUNILVR", "ITC", "LT", "KOTAKBANK", "BAJFINANCE", "AXISBANK", "ASIANPAINT",
    "MARUTI", "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "NTPC",
    "POWERGRID", "M&M", "ONGC", "JSWSTEEL", "TATAMOTORS", "ADANIENT", "ADANIPORTS",
    "COALINDIA", "BAJAJFINSV", "NESTLEIND", "TATASTEEL", "TECHM", "INDUSINDBK",
    "GRASIM", "HINDALCO", "DRREDDY", "DIVISLAB", "CIPLA", "BRITANNIA",
    "APOLLOHOSP", "EICHERMOT", "HEROMOTOCO", "BPCL", "TATACONSUM", "SBILIFE",
    "HDFCLIFE", "UPL", "BAJAJ-AUTO", "LTIM"
]

NIFTY_BANK = [
    "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK",
    "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB", "AUBANK", "IDBIBANK"
]


def get_yahoo_symbol(symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance format"""
    special_mappings = {
        "M&M": "M%26M.NS",
        "NIFTY50": "^NSEI",
        "NIFTYBANK": "^NSEBANK"
    }
    return special_mappings.get(symbol, f"{symbol}.NS")


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1] if not atr.empty else 0


def calculate_supertrend(data: pd.DataFrame, period: int = 10, multiplier: float = 3.0) -> Dict[str, Any]:
    """Calculate Supertrend indicator"""
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    atr = calculate_atr(high, low, close, period)
    hl2 = (high + low) / 2
    
    basic_upper = hl2.iloc[-1] + (multiplier * atr)
    basic_lower = hl2.iloc[-1] - (multiplier * atr)
    
    # Simplified trend determination
    close_vals = close.tail(10).values
    is_uptrend = close_vals[-1] > close_vals[-3] if len(close_vals) >= 3 else True
    
    if is_uptrend:
        return {
            "signal": "BULLISH",
            "value": basic_lower,
            "crossover": close.iloc[-2] < basic_lower if len(close) > 1 else False
        }
    else:
        return {
            "signal": "BEARISH", 
            "value": basic_upper,
            "crossover": close.iloc[-2] > basic_upper if len(close) > 1 else False
        }


def calculate_vwap(data: pd.DataFrame) -> Dict[str, Any]:
    """Calculate VWAP"""
    if 'Volume' not in data.columns or data['Volume'].sum() == 0:
        return {"vwap": data['Close'].iloc[-1], "signal": "NEUTRAL", "distance_pct": 0}
    
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    vwap = (typical_price * data['Volume']).sum() / data['Volume'].sum()
    
    current_price = data['Close'].iloc[-1]
    distance_pct = ((current_price - vwap) / vwap) * 100
    
    if distance_pct > 0.3:
        signal = "BULLISH"
    elif distance_pct < -0.3:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {"vwap": vwap, "signal": signal, "distance_pct": distance_pct}


def calculate_bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
    """Calculate Bollinger Bands"""
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper = sma + (std_dev * std)
    lower = sma - (std_dev * std)
    
    current = close.iloc[-1]
    upper_val = upper.iloc[-1]
    lower_val = lower.iloc[-1]
    middle_val = sma.iloc[-1]
    
    bandwidth = (upper_val - lower_val) / middle_val * 100 if middle_val > 0 else 0
    percent_b = (current - lower_val) / (upper_val - lower_val) * 100 if (upper_val - lower_val) > 0 else 50
    
    # Squeeze detection
    avg_bandwidth = ((upper - lower) / sma * 100).rolling(50).mean().iloc[-1]
    squeeze = bandwidth < (avg_bandwidth * 0.6) if pd.notna(avg_bandwidth) else False
    
    if percent_b < 15:
        signal = "OVERSOLD"
    elif percent_b > 85:
        signal = "OVERBOUGHT"
    elif current > middle_val:
        signal = "BULLISH"
    elif current < middle_val:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {
        "upper": upper_val,
        "middle": middle_val,
        "lower": lower_val,
        "signal": signal,
        "bandwidth": bandwidth,
        "percent_b": percent_b,
        "squeeze": squeeze
    }


def analyze_at_time(data_5m: pd.DataFrame, data_15m: pd.DataFrame, analysis_idx: int) -> Dict[str, Any]:
    """
    Analyze stock at a specific point in time using historical data
    Returns signal if confirmations >= 5
    """
    try:
        # Get data up to analysis point
        hist_5m = data_5m.iloc[:analysis_idx].copy()
        
        # Find corresponding 15m index (approx 3x fewer candles)
        idx_15m = min(analysis_idx // 3, len(data_15m) - 1)
        hist_15m = data_15m.iloc[:max(idx_15m, 30)].copy()
        
        if len(hist_5m) < 50 or len(hist_15m) < 20:
            return None
        
        ltp = hist_5m['Close'].iloc[-1]
        
        # ============== 5-MINUTE ANALYSIS ==============
        vwap_5m_data = calculate_vwap(hist_5m.tail(75))
        vwap_5m_signal = vwap_5m_data.get("signal", "NEUTRAL")
        
        st_5m_data = calculate_supertrend(hist_5m)
        st_5m_signal = st_5m_data.get("signal", "NEUTRAL")
        st_5m_crossover = st_5m_data.get("crossover", False)
        st_5m_value = st_5m_data.get("value", ltp)
        
        bb_5m_data = calculate_bollinger_bands(hist_5m['Close'])
        bb_5m_signal = bb_5m_data.get("signal", "NEUTRAL")
        bb_5m_upper = bb_5m_data.get("upper", ltp)
        bb_5m_lower = bb_5m_data.get("lower", ltp)
        
        # ============== 15-MINUTE ANALYSIS ==============
        vwap_15m_data = calculate_vwap(hist_15m.tail(30))
        vwap_15m_signal = vwap_15m_data.get("signal", "NEUTRAL")
        
        st_15m_data = calculate_supertrend(hist_15m)
        st_15m_signal = st_15m_data.get("signal", "NEUTRAL")
        st_15m_crossover = st_15m_data.get("crossover", False)
        
        bb_15m_data = calculate_bollinger_bands(hist_15m['Close'])
        bb_15m_signal = bb_15m_data.get("signal", "NEUTRAL")
        
        # RSI & Volume
        rsi_5m = calculate_rsi(hist_5m['Close'])
        avg_volume = hist_5m['Volume'].rolling(50).mean().iloc[-1]
        current_volume = hist_5m['Volume'].tail(5).mean()
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Day high/low from current session
        session_data = hist_5m.tail(75)
        day_high = session_data['High'].max()
        day_low = session_data['Low'].min()
        
        # ============== LONG CONFIRMATIONS ==============
        long_confirmations = 0
        if vwap_5m_signal == "BULLISH":
            long_confirmations += 1
        if st_5m_signal == "BULLISH":
            long_confirmations += 1
            if st_5m_crossover:
                long_confirmations += 1
        if bb_5m_signal in ["OVERSOLD", "BULLISH"]:
            long_confirmations += 1
        if vwap_15m_signal == "BULLISH":
            long_confirmations += 1
        if st_15m_signal == "BULLISH":
            long_confirmations += 1
            if st_15m_crossover:
                long_confirmations += 1
        if bb_15m_signal in ["OVERSOLD", "BULLISH"]:
            long_confirmations += 1
        if rsi_5m < 40:
            long_confirmations += 1
        if volume_ratio > 1.5:
            long_confirmations += 1
        
        # ============== SHORT CONFIRMATIONS ==============
        short_confirmations = 0
        if vwap_5m_signal == "BEARISH":
            short_confirmations += 1
        if st_5m_signal == "BEARISH":
            short_confirmations += 1
            if st_5m_crossover:
                short_confirmations += 1
        if bb_5m_signal in ["OVERBOUGHT", "BEARISH"]:
            short_confirmations += 1
        if vwap_15m_signal == "BEARISH":
            short_confirmations += 1
        if st_15m_signal == "BEARISH":
            short_confirmations += 1
            if st_15m_crossover:
                short_confirmations += 1
        if bb_15m_signal in ["OVERBOUGHT", "BEARISH"]:
            short_confirmations += 1
        if rsi_5m > 65:
            short_confirmations += 1
        if volume_ratio > 1.5:
            short_confirmations += 1
        
        # ============== GENERATE SIGNAL ==============
        min_confirmations = 5
        
        if long_confirmations >= min_confirmations and long_confirmations > short_confirmations:
            entry = ltp
            stoploss = max(bb_5m_lower * 0.998, st_5m_value * 0.995, day_low * 0.998)
            target1 = min(bb_5m_upper, day_high * 1.002)
            target2 = max(bb_5m_upper * 1.01, day_high * 1.005)
            
            if stoploss >= entry:
                stoploss = entry * 0.993
            if target1 <= entry:
                target1 = entry * 1.01
            if target2 <= target1:
                target2 = entry * 1.02
            
            return {
                "signal": "LONG",
                "entry": round(entry, 2),
                "stoploss": round(stoploss, 2),
                "target1": round(target1, 2),
                "target2": round(target2, 2),
                "confirmations": long_confirmations,
                "confidence": "HIGH" if long_confirmations >= 7 else "GOOD" if long_confirmations >= 6 else "MODERATE"
            }
        
        elif short_confirmations >= min_confirmations and short_confirmations > long_confirmations:
            entry = ltp
            stoploss = min(bb_5m_upper * 1.002, st_5m_value * 1.005, day_high * 1.002)
            target1 = max(bb_5m_lower, day_low * 0.998)
            target2 = min(bb_5m_lower * 0.99, day_low * 0.995)
            
            if stoploss <= entry:
                stoploss = entry * 1.007
            if target1 >= entry:
                target1 = entry * 0.99
            if target2 >= target1:
                target2 = entry * 0.98
            
            return {
                "signal": "SHORT",
                "entry": round(entry, 2),
                "stoploss": round(stoploss, 2),
                "target1": round(target1, 2),
                "target2": round(target2, 2),
                "confirmations": short_confirmations,
                "confidence": "HIGH" if short_confirmations >= 7 else "GOOD" if short_confirmations >= 6 else "MODERATE"
            }
        
        return None
        
    except Exception as e:
        return None


def check_outcome(data_5m: pd.DataFrame, signal: Dict, entry_idx: int) -> Dict[str, Any]:
    """
    Check if target or stoploss was hit after signal generation
    Returns outcome: TARGET1_HIT, TARGET2_HIT, STOPLOSS_HIT, BREAKEVEN, TIME_EXIT
    """
    try:
        # Look at data after the signal (rest of day, max ~75 candles = 6.25 hours)
        remaining_data = data_5m.iloc[entry_idx:entry_idx + 75]
        
        if len(remaining_data) < 5:
            return {"outcome": "INSUFFICIENT_DATA", "pnl_pct": 0}
        
        entry = signal["entry"]
        sl = signal["stoploss"]
        t1 = signal["target1"]
        t2 = signal["target2"]
        direction = signal["signal"]
        
        for i, row in remaining_data.iterrows():
            high = row['High']
            low = row['Low']
            
            if direction == "LONG":
                # Check stoploss first
                if low <= sl:
                    pnl = ((sl - entry) / entry) * 100
                    return {"outcome": "STOPLOSS_HIT", "pnl_pct": round(pnl, 2)}
                # Check target 2
                if high >= t2:
                    pnl = ((t2 - entry) / entry) * 100
                    return {"outcome": "TARGET2_HIT", "pnl_pct": round(pnl, 2)}
                # Check target 1
                if high >= t1:
                    pnl = ((t1 - entry) / entry) * 100
                    return {"outcome": "TARGET1_HIT", "pnl_pct": round(pnl, 2)}
            
            else:  # SHORT
                # Check stoploss first
                if high >= sl:
                    pnl = ((entry - sl) / entry) * 100
                    return {"outcome": "STOPLOSS_HIT", "pnl_pct": round(pnl, 2)}
                # Check target 2
                if low <= t2:
                    pnl = ((entry - t2) / entry) * 100
                    return {"outcome": "TARGET2_HIT", "pnl_pct": round(pnl, 2)}
                # Check target 1
                if low <= t1:
                    pnl = ((entry - t1) / entry) * 100
                    return {"outcome": "TARGET1_HIT", "pnl_pct": round(pnl, 2)}
        
        # Time exit - close at last price
        exit_price = remaining_data['Close'].iloc[-1]
        if direction == "LONG":
            pnl = ((exit_price - entry) / entry) * 100
        else:
            pnl = ((entry - exit_price) / entry) * 100
        
        return {"outcome": "TIME_EXIT", "pnl_pct": round(pnl, 2)}
        
    except Exception as e:
        return {"outcome": "ERROR", "pnl_pct": 0}


def backtest_stock(symbol: str, days_back: int = 10) -> List[Dict]:
    """Backtest a single stock over historical days"""
    results = []
    
    try:
        yahoo_symbol = get_yahoo_symbol(symbol)
        ticker = yf.Ticker(yahoo_symbol)
        
        # Get 5m data
        data_5m = ticker.history(period=f"{days_back + 5}d", interval="5m")
        # Get 15m data
        data_15m = ticker.history(period=f"{days_back + 5}d", interval="15m")
        
        if data_5m.empty or len(data_5m) < 100:
            return results
        
        # Analyze at different points (simulate 10:00, 11:00, 12:00, 1:00, 2:00 entries)
        # Each day has ~75 5m candles (9:15 to 3:30)
        # We'll check at candle 15, 30, 45, 60 of each day
        
        candles_per_day = 75
        total_days = len(data_5m) // candles_per_day
        
        for day in range(min(total_days - 1, days_back)):
            day_start = day * candles_per_day
            
            # Check at 4 different times during the day
            for offset in [15, 25, 35, 50]:  # ~10:30, 11:15, 12:00, 1:30
                analysis_idx = day_start + offset
                
                if analysis_idx >= len(data_5m) - 10:
                    continue
                
                signal = analyze_at_time(data_5m, data_15m, analysis_idx)
                
                if signal:
                    outcome = check_outcome(data_5m, signal, analysis_idx)
                    
                    results.append({
                        "symbol": symbol,
                        "signal": signal["signal"],
                        "entry": signal["entry"],
                        "stoploss": signal["stoploss"],
                        "target1": signal["target1"],
                        "target2": signal["target2"],
                        "confirmations": signal["confirmations"],
                        "confidence": signal["confidence"],
                        "outcome": outcome["outcome"],
                        "pnl_pct": outcome["pnl_pct"],
                        "day_offset": day
                    })
        
        return results
        
    except Exception as e:
        print(f"  Error backtesting {symbol}: {e}")
        return results


def run_backtest(stocks: List[str] = None, days: int = 10):
    """Run full backtest on stock list"""
    if stocks is None:
        stocks = NIFTY_50
    
    print("=" * 70)
    print("SIDDHI - MULTI-TIMEFRAME INTRADAY STRATEGY BACKTEST")
    print("=" * 70)
    print(f"\nStrategy: VWAP + Supertrend + Bollinger Bands (5m & 15m)")
    print(f"Stocks: {len(stocks)}")
    print(f"Days: {days}")
    print(f"Min Confirmations: 5")
    print("\n" + "-" * 70)
    print("Analyzing... (this may take a few minutes)")
    print("-" * 70)
    
    all_results = []
    stocks_with_signals = 0
    
    for i, symbol in enumerate(stocks):
        print(f"  [{i+1}/{len(stocks)}] {symbol}...", end=" ")
        results = backtest_stock(symbol, days)
        if results:
            all_results.extend(results)
            stocks_with_signals += 1
            print(f"{len(results)} signals")
        else:
            print("no signals")
    
    if not all_results:
        print("\n⚠️ No signals generated during the backtest period.")
        return
    
    # Convert to DataFrame for analysis
    df = pd.DataFrame(all_results)
    
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    
    # Overall Stats
    total_signals = len(df)
    wins = df[df['outcome'].isin(['TARGET1_HIT', 'TARGET2_HIT'])]
    losses = df[df['outcome'] == 'STOPLOSS_HIT']
    time_exits = df[df['outcome'] == 'TIME_EXIT']
    
    win_rate = len(wins) / total_signals * 100 if total_signals > 0 else 0
    
    print(f"\n📊 OVERALL PERFORMANCE")
    print(f"   Total Signals: {total_signals}")
    print(f"   Stocks with Signals: {stocks_with_signals}/{len(stocks)}")
    print(f"   ✅ Target 1 Hit: {len(df[df['outcome'] == 'TARGET1_HIT'])}")
    print(f"   🎯 Target 2 Hit: {len(df[df['outcome'] == 'TARGET2_HIT'])}")
    print(f"   ❌ Stoploss Hit: {len(losses)}")
    print(f"   ⏰ Time Exit: {len(time_exits)}")
    print(f"\n   🏆 WIN RATE: {win_rate:.1f}%")
    
    avg_pnl = df['pnl_pct'].mean()
    total_pnl = df['pnl_pct'].sum()
    print(f"   📈 Avg P&L per trade: {avg_pnl:.2f}%")
    print(f"   📈 Total P&L: {total_pnl:.2f}%")
    
    # By Direction
    print(f"\n📊 BY DIRECTION")
    for direction in ['LONG', 'SHORT']:
        dir_df = df[df['signal'] == direction]
        if len(dir_df) > 0:
            dir_wins = dir_df[dir_df['outcome'].isin(['TARGET1_HIT', 'TARGET2_HIT'])]
            dir_wr = len(dir_wins) / len(dir_df) * 100
            dir_pnl = dir_df['pnl_pct'].mean()
            print(f"   {direction}: {len(dir_df)} trades | Win Rate: {dir_wr:.1f}% | Avg P&L: {dir_pnl:.2f}%")
    
    # By Confidence
    print(f"\n📊 BY CONFIDENCE LEVEL")
    for conf in ['HIGH', 'GOOD', 'MODERATE']:
        conf_df = df[df['confidence'] == conf]
        if len(conf_df) > 0:
            conf_wins = conf_df[conf_df['outcome'].isin(['TARGET1_HIT', 'TARGET2_HIT'])]
            conf_wr = len(conf_wins) / len(conf_df) * 100
            conf_pnl = conf_df['pnl_pct'].mean()
            print(f"   {conf}: {len(conf_df)} trades | Win Rate: {conf_wr:.1f}% | Avg P&L: {conf_pnl:.2f}%")
    
    # By Confirmations
    print(f"\n📊 BY CONFIRMATIONS")
    for conf_count in sorted(df['confirmations'].unique()):
        conf_df = df[df['confirmations'] == conf_count]
        if len(conf_df) > 0:
            conf_wins = conf_df[conf_df['outcome'].isin(['TARGET1_HIT', 'TARGET2_HIT'])]
            conf_wr = len(conf_wins) / len(conf_df) * 100
            conf_pnl = conf_df['pnl_pct'].mean()
            print(f"   {conf_count} confirmations: {len(conf_df)} trades | Win Rate: {conf_wr:.1f}% | Avg P&L: {conf_pnl:.2f}%")
    
    # Top performers
    print(f"\n🏆 TOP 5 PERFORMERS")
    by_symbol = df.groupby('symbol').agg({
        'pnl_pct': ['sum', 'count', 'mean']
    }).round(2)
    by_symbol.columns = ['total_pnl', 'trades', 'avg_pnl']
    top5 = by_symbol.sort_values('total_pnl', ascending=False).head(5)
    for sym, row in top5.iterrows():
        print(f"   {sym}: {row['trades']:.0f} trades | Total P&L: {row['total_pnl']:.2f}% | Avg: {row['avg_pnl']:.2f}%")
    
    # Worst performers
    print(f"\n⚠️ WORST 5 PERFORMERS")
    bottom5 = by_symbol.sort_values('total_pnl', ascending=True).head(5)
    for sym, row in bottom5.iterrows():
        print(f"   {sym}: {row['trades']:.0f} trades | Total P&L: {row['total_pnl']:.2f}% | Avg: {row['avg_pnl']:.2f}%")
    
    # Profit Factor
    gross_profit = df[df['pnl_pct'] > 0]['pnl_pct'].sum()
    gross_loss = abs(df[df['pnl_pct'] < 0]['pnl_pct'].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    print(f"\n📈 RISK METRICS")
    print(f"   Gross Profit: {gross_profit:.2f}%")
    print(f"   Gross Loss: {gross_loss:.2f}%")
    print(f"   Profit Factor: {profit_factor:.2f}")
    print(f"   Max Win: {df['pnl_pct'].max():.2f}%")
    print(f"   Max Loss: {df['pnl_pct'].min():.2f}%")
    
    # Summary
    print("\n" + "=" * 70)
    if win_rate >= 60:
        print("✅ STRATEGY VERDICT: GOOD - Win rate above 60%")
    elif win_rate >= 50:
        print("⚠️ STRATEGY VERDICT: MODERATE - Win rate around 50%")
    else:
        print("❌ STRATEGY VERDICT: NEEDS IMPROVEMENT - Win rate below 50%")
    
    if profit_factor >= 1.5:
        print("✅ Profit Factor is healthy (>= 1.5)")
    elif profit_factor >= 1.0:
        print("⚠️ Profit Factor is marginal (1.0-1.5)")
    else:
        print("❌ Profit Factor is negative (< 1.0)")
    
    print("=" * 70)
    
    return df


def run_quick_test():
    """Quick test with fewer stocks"""
    test_stocks = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "SBIN", 
                   "ICICIBANK", "KOTAKBANK", "AXISBANK", "LT", "TATAMOTORS"]
    return run_backtest(test_stocks, days=5)


if __name__ == "__main__":
    print("\nSIDDHI Intraday Strategy Backtester")
    print("-" * 40)
    print("1. Quick Test (10 stocks, 5 days)")
    print("2. Full NIFTY 50 Test (50 stocks, 10 days)")
    print("3. BANK NIFTY Test (12 stocks, 10 days)")
    
    choice = input("\nSelect option (1/2/3): ").strip()
    
    if choice == "1":
        run_quick_test()
    elif choice == "2":
        run_backtest(NIFTY_50, days=10)
    elif choice == "3":
        run_backtest(NIFTY_BANK, days=10)
    else:
        print("Running quick test by default...")
        run_quick_test()
