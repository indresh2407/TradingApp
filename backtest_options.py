#!/usr/bin/env python3
"""
SIDDHI Options Strategy Backtest
=================================
Tests the Options strategy (BUY CALL / BUY PUT) for F&O stocks.

Measures:
- Direction accuracy
- Target hit rate
- P&L with larger ATR-based targets

Run: python3 backtest_options.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# F&O Stocks to test
FNO_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC", "SBIN",
    "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "TATAMOTORS", "MARUTI", "TITAN",
    "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "TATASTEEL", "JSWSTEEL",
    "NTPC", "POWERGRID", "M&M", "ADANIENT", "INDUSINDBK", "HINDALCO", "BAJAJ-AUTO",
    "DLF", "TATAPOWER", "VEDL", "SAIL", "GAIL", "MUTHOOTFIN", "PFC", "RECLTD"
]

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]

def calculate_vwap(high, low, close, volume):
    tp = (high + low + close) / 3
    vwap = (tp * volume).cumsum() / volume.cumsum()
    price = close.iloc[-1]
    v = vwap.iloc[-1]
    return {"vwap": v, "signal": "BULLISH" if price > v * 1.002 else "BEARISH" if price < v * 0.998 else "NEUTRAL"}

def calculate_supertrend(high, low, close, period=10, mult=3.0):
    hl2 = (high + low) / 2
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    upper = hl2 + mult * atr
    lower = hl2 - mult * atr
    
    direction = pd.Series(index=close.index, dtype=int)
    st = pd.Series(index=close.index, dtype=float)
    
    for i in range(period, len(close)):
        if close.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1] if i > period else 1
        st.iloc[i] = lower.iloc[i] if direction.iloc[i] == 1 else upper.iloc[i]
    
    d = direction.iloc[-1]
    cross = d != direction.iloc[-2] if len(direction) > 1 else False
    return {"value": st.iloc[-1], "signal": "BULLISH" if d == 1 else "BEARISH", "crossover": cross}

def calculate_bb(close, period=20, std=2.0):
    mid = close.rolling(period).mean()
    s = close.rolling(period).std()
    upper = mid + std * s
    lower = mid - std * s
    
    price = close.iloc[-1]
    pct_b = ((price - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])) * 100
    
    if pct_b > 100: sig = "OVERBOUGHT"
    elif pct_b < 0: sig = "OVERSOLD"
    elif pct_b > 80: sig = "BULLISH"
    elif pct_b < 20: sig = "BEARISH"
    else: sig = "NEUTRAL"
    
    return {"upper": upper.iloc[-1], "lower": lower.iloc[-1], "signal": sig, "squeeze": False}

def calculate_adx(high, low, close, di_len=7, adx_smooth=7):
    if len(close) < di_len + adx_smooth + 5:
        return {"adx": 0, "trend_direction": "NEUTRAL"}
    
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(di_len).mean()
    
    plus_dm = high.diff().where((high.diff() > -low.diff()) & (high.diff() > 0), 0)
    minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0)
    
    plus_di = 100 * plus_dm.rolling(di_len).mean() / atr
    minus_di = 100 * minus_dm.rolling(di_len).mean() / atr
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
    adx = dx.rolling(adx_smooth).mean()
    
    return {"adx": adx.iloc[-1], "trend_direction": "BULLISH" if plus_di.iloc[-1] > minus_di.iloc[-1] else "BEARISH"}

def calculate_roc(prices, period=10):
    if len(prices) < period + 5:
        return {"roc": 0, "signal": "NEUTRAL"}
    
    roc = ((prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]) * 100
    return {"roc": roc, "signal": "BULLISH" if roc > 2 else "BEARISH" if roc < -2 else "NEUTRAL"}


def analyze_options_signal(h5, h15, min_score=5):
    """Analyze for options signal - returns CALL, PUT, or None"""
    if h5.empty or len(h5) < 50 or h15.empty or len(h15) < 20:
        return None
    
    ltp = h5['Close'].iloc[-1]
    atr = calculate_atr(h5['High'], h5['Low'], h5['Close'])
    atr_pct = (atr / ltp) * 100
    
    # Original volatility filter (1.2% ATR)
    if atr_pct < 1.2:
        return None
    
    # Indicators
    vwap = calculate_vwap(h5['High'], h5['Low'], h5['Close'], h5['Volume'])
    st5 = calculate_supertrend(h5['High'], h5['Low'], h5['Close'])
    st15 = calculate_supertrend(h15['High'], h15['Low'], h15['Close'])
    bb = calculate_bb(h5['Close'])
    adx = calculate_adx(h5['High'], h5['Low'], h5['Close'])
    roc = calculate_roc(h5['Close'])
    
    # CALL score
    call_score = 0
    if vwap["signal"] == "BULLISH": call_score += 1
    if st5["signal"] == "BULLISH": 
        call_score += 1
        if st5["crossover"]: call_score += 2
    if st15["signal"] == "BULLISH":
        call_score += 1
        if st15["crossover"]: call_score += 2
    if roc["signal"] == "BULLISH": call_score += 1
    if adx["adx"] >= 25 and adx["trend_direction"] == "BULLISH": call_score += 2
    if bb["signal"] == "OVERSOLD": call_score += 1
    
    # PUT score
    put_score = 0
    if vwap["signal"] == "BEARISH": put_score += 1
    if st5["signal"] == "BEARISH":
        put_score += 1
        if st5["crossover"]: put_score += 2
    if st15["signal"] == "BEARISH":
        put_score += 1
        if st15["crossover"]: put_score += 2
    if roc["signal"] == "BEARISH": put_score += 1
    if adx["adx"] >= 25 and adx["trend_direction"] == "BEARISH": put_score += 2
    if bb["signal"] == "OVERBOUGHT": put_score += 1
    
    has_crossover = st5["crossover"] or st15["crossover"]
    
    if call_score >= min_score and call_score > put_score:
        # Larger targets for options (1.5x ATR)
        entry = ltp
        stoploss = max(st5["value"] * 0.995, entry - (atr * 2))
        target1 = entry + (atr * 1.5)
        target2 = entry + (atr * 2.5)
        
        return {
            "signal": "CALL",
            "entry": entry,
            "stoploss": stoploss,
            "target1": target1,
            "target2": target2,
            "score": call_score,
            "atr_pct": atr_pct,
            "crossover": has_crossover
        }
    
    elif put_score >= min_score and put_score > call_score:
        entry = ltp
        stoploss = min(st5["value"] * 1.005, entry + (atr * 2))
        target1 = entry - (atr * 1.5)
        target2 = entry - (atr * 2.5)
        
        return {
            "signal": "PUT",
            "entry": entry,
            "stoploss": stoploss,
            "target1": target1,
            "target2": target2,
            "score": put_score,
            "atr_pct": atr_pct,
            "crossover": has_crossover
        }
    
    return None


def check_direction(h5, sig, entry_idx, check_candles=12):
    """Check if direction was correct within 1 hour"""
    if not sig:
        return None
    
    entry = sig["entry"]
    future = h5.iloc[entry_idx:min(entry_idx + check_candles, len(h5))]
    
    if future.empty or len(future) < 2:
        return None
    
    max_high = future['High'].max()
    min_low = future['Low'].min()
    
    if sig["signal"] == "CALL":
        max_favorable = ((max_high - entry) / entry) * 100
        max_adverse = ((entry - min_low) / entry) * 100
        direction_correct = max_favorable >= 0.3  # 0.3% move in right direction
    else:
        max_favorable = ((entry - min_low) / entry) * 100
        max_adverse = ((max_high - entry) / entry) * 100
        direction_correct = max_favorable >= 0.3
    
    return {
        "direction_correct": direction_correct,
        "max_favorable": round(max_favorable, 2),
        "max_adverse": round(max_adverse, 2)
    }


def check_target_hit(h5, sig, entry_idx, max_candles=24):
    """Check if target or stoploss hit within 2 hours"""
    if not sig:
        return None
    
    entry = sig["entry"]
    sl = sig["stoploss"]
    t1 = sig["target1"]
    t2 = sig["target2"]
    
    future = h5.iloc[entry_idx:min(entry_idx + max_candles, len(h5))]
    
    if future.empty or len(future) < 2:
        return {"outcome": "NO_DATA", "pnl": 0}
    
    for i, (_, row) in enumerate(future.iterrows()):
        if sig["signal"] == "CALL":
            if row['Low'] <= sl:
                return {"outcome": "SL_HIT", "pnl": ((sl - entry) / entry) * 100, "mins": (i+1)*5}
            if row['High'] >= t2:
                return {"outcome": "T2_HIT", "pnl": ((t2 - entry) / entry) * 100, "mins": (i+1)*5}
            if row['High'] >= t1:
                return {"outcome": "T1_HIT", "pnl": ((t1 - entry) / entry) * 100, "mins": (i+1)*5}
        else:
            if row['High'] >= sl:
                return {"outcome": "SL_HIT", "pnl": ((entry - sl) / entry) * 100, "mins": (i+1)*5}
            if row['Low'] <= t2:
                return {"outcome": "T2_HIT", "pnl": ((entry - t2) / entry) * 100, "mins": (i+1)*5}
            if row['Low'] <= t1:
                return {"outcome": "T1_HIT", "pnl": ((entry - t1) / entry) * 100, "mins": (i+1)*5}
    
    # Expired
    final = future['Close'].iloc[-1]
    pnl = ((final - entry) / entry) * 100 if sig["signal"] == "CALL" else ((entry - final) / entry) * 100
    return {"outcome": "EXPIRED", "pnl": pnl, "mins": len(future)*5}


def run_backtest():
    print("\n" + "="*70)
    print("🎯 SIDDHI OPTIONS Strategy Backtest")
    print("="*70)
    print(f"📊 Testing: {len(FNO_STOCKS)} F&O stocks")
    print(f"📅 Period: Last 5 trading days")
    print(f"🎯 Strategy: BUY CALL / BUY PUT with 1.5x ATR targets")
    print(f"⏱️  Max Hold: 2 hours (24 candles)")
    print("="*70)
    
    all_trades = []
    direction_results = []
    stock_results = {}
    
    for symbol in FNO_STOCKS:
        print(f"\n📈 {symbol}...", end=" ")
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            h5 = ticker.history(period="7d", interval="5m")
            
            if h5.empty or len(h5) < 100:
                print("❌ No data")
                continue
            
            # Resample to 15m
            h15 = h5.resample('15min').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min',
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            
            if h5.index.tz is not None:
                dates = h5.index.tz_localize(None).date
            else:
                dates = h5.index.date
            
            unique_dates = pd.Series(dates).unique()[-5:]
            
            sym_trades = []
            sym_directions = []
            
            for date in unique_dates:
                day_mask = dates == date
                day_idx = np.where(day_mask)[0]
                
                if len(day_idx) < 60:
                    continue
                
                # Test at multiple times
                for offset in [15, 33, 51, 69]:  # 9:30, 11:00, 12:30, 14:00
                    idx = day_idx[0] + offset
                    if idx >= len(h5) - 24:
                        continue
                    
                    sig = analyze_options_signal(h5.iloc[:idx+1], h15[h15.index <= h5.index[idx]])
                    
                    if sig:
                        # Check direction
                        dir_result = check_direction(h5, sig, idx)
                        if dir_result:
                            direction_results.append({
                                "symbol": symbol,
                                "signal": sig["signal"],
                                "score": sig["score"],
                                **dir_result
                            })
                            sym_directions.append(dir_result)
                        
                        # Check target hit
                        target_result = check_target_hit(h5, sig, idx)
                        if target_result:
                            trade = {
                                "symbol": symbol,
                                "signal": sig["signal"],
                                "score": sig["score"],
                                "atr_pct": sig["atr_pct"],
                                "crossover": sig["crossover"],
                                **target_result
                            }
                            all_trades.append(trade)
                            sym_trades.append(trade)
            
            if sym_trades:
                wins = sum(1 for t in sym_trades if t["outcome"] in ["T1_HIT", "T2_HIT"])
                dir_correct = sum(1 for d in sym_directions if d["direction_correct"])
                win_rate = (wins / len(sym_trades)) * 100
                dir_rate = (dir_correct / len(sym_directions)) * 100 if sym_directions else 0
                
                stock_results[symbol] = {
                    "trades": len(sym_trades),
                    "win_rate": win_rate,
                    "dir_rate": dir_rate
                }
                
                print(f"✅ {len(sym_trades)} signals | Dir: {dir_rate:.0f}% | Target: {win_rate:.0f}%")
            else:
                print("⚪ No signals (low volatility or weak trend)")
                
        except Exception as e:
            print(f"❌ {e}")
    
    # ============== SUMMARY ==============
    print("\n" + "="*70)
    print("📊 OPTIONS STRATEGY BACKTEST RESULTS")
    print("="*70)
    
    if not all_trades:
        print("❌ No trades generated")
        return
    
    total = len(all_trades)
    t1_hits = sum(1 for t in all_trades if t["outcome"] == "T1_HIT")
    t2_hits = sum(1 for t in all_trades if t["outcome"] == "T2_HIT")
    sl_hits = sum(1 for t in all_trades if t["outcome"] == "SL_HIT")
    expired = sum(1 for t in all_trades if t["outcome"] == "EXPIRED")
    
    total_wins = t1_hits + t2_hits
    win_rate = (total_wins / total) * 100
    total_pnl = sum(t["pnl"] for t in all_trades)
    
    # Direction accuracy
    dir_total = len(direction_results)
    dir_correct = sum(1 for d in direction_results if d["direction_correct"])
    dir_accuracy = (dir_correct / dir_total) * 100 if dir_total > 0 else 0
    
    print(f"\n🎯 DIRECTION ACCURACY: {dir_accuracy:.1f}% ({dir_correct}/{dir_total})")
    print(f"   Avg Favorable Move: +{np.mean([d['max_favorable'] for d in direction_results]):.2f}%")
    print(f"   Avg Adverse Move:   -{np.mean([d['max_adverse'] for d in direction_results]):.2f}%")
    
    print(f"\n📈 TARGET HIT RATE: {win_rate:.1f}%")
    print(f"   Total Signals: {total}")
    print(f"   ✅ T1 Hit: {t1_hits}")
    print(f"   ✅ T2 Hit: {t2_hits}")
    print(f"   ❌ SL Hit: {sl_hits}")
    print(f"   ⏰ Expired: {expired}")
    print(f"   💰 Total P&L: {total_pnl:+.2f}%")
    
    # By signal type
    calls = [t for t in all_trades if t["signal"] == "CALL"]
    puts = [t for t in all_trades if t["signal"] == "PUT"]
    
    print(f"\n📊 BY SIGNAL TYPE:")
    if calls:
        call_wins = sum(1 for t in calls if t["outcome"] in ["T1_HIT", "T2_HIT"])
        call_wr = (call_wins / len(calls)) * 100
        call_pnl = sum(t["pnl"] for t in calls)
        print(f"   🟢 CALL: {len(calls)} signals | Win Rate: {call_wr:.1f}% | P&L: {call_pnl:+.2f}%")
    if puts:
        put_wins = sum(1 for t in puts if t["outcome"] in ["T1_HIT", "T2_HIT"])
        put_wr = (put_wins / len(puts)) * 100
        put_pnl = sum(t["pnl"] for t in puts)
        print(f"   🔴 PUT: {len(puts)} signals | Win Rate: {put_wr:.1f}% | P&L: {put_pnl:+.2f}%")
    
    # By score
    print(f"\n📊 BY SCORE:")
    for score in sorted(set(t["score"] for t in all_trades)):
        st = [t for t in all_trades if t["score"] == score]
        s_wins = sum(1 for t in st if t["outcome"] in ["T1_HIT", "T2_HIT"])
        s_wr = (s_wins / len(st)) * 100
        print(f"   Score {score}: {len(st)} signals | Win Rate: {s_wr:.1f}%")
    
    # Crossover vs non-crossover
    cross_trades = [t for t in all_trades if t["crossover"]]
    non_cross = [t for t in all_trades if not t["crossover"]]
    
    print(f"\n📊 CROSSOVER IMPACT:")
    if cross_trades:
        cross_wr = (sum(1 for t in cross_trades if t["outcome"] in ["T1_HIT", "T2_HIT"]) / len(cross_trades)) * 100
        print(f"   🔥 With Crossover: {len(cross_trades)} signals | Win Rate: {cross_wr:.1f}%")
    if non_cross:
        non_wr = (sum(1 for t in non_cross if t["outcome"] in ["T1_HIT", "T2_HIT"]) / len(non_cross)) * 100
        print(f"   ➖ No Crossover: {len(non_cross)} signals | Win Rate: {non_wr:.1f}%")
    
    # Top performers
    if stock_results:
        print(f"\n🏆 TOP 5 STOCKS:")
        sorted_stocks = sorted(stock_results.items(), key=lambda x: x[1]["win_rate"], reverse=True)[:5]
        for sym, stats in sorted_stocks:
            print(f"   {sym}: {stats['trades']} signals | Dir: {stats['dir_rate']:.0f}% | Target: {stats['win_rate']:.0f}%")
    
    # Avg time to target
    winning_trades = [t for t in all_trades if t["outcome"] in ["T1_HIT", "T2_HIT"]]
    if winning_trades:
        avg_time = np.mean([t["mins"] for t in winning_trades])
        print(f"\n⏱️  Avg time to hit target: {avg_time:.0f} minutes")
    
    print("\n" + "="*70)
    print("✅ Backtest Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_backtest()
