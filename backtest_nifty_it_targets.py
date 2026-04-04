#!/usr/bin/env python3
"""
SIDDHI DayTrade - NIFTY IT Target Hit Rate
===========================================
Tests TARGET HIT RATE for NIFTY IT stocks.
Compares OLD (BB-based) vs NEW (ATR-based) targets.

Run: python3 backtest_nifty_it_targets.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# NIFTY IT stocks
NIFTY_IT = [
    "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM",
    "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "LTTS"
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
    
    return {"upper": upper.iloc[-1], "lower": lower.iloc[-1], "middle": mid.iloc[-1], "signal": sig}

def calculate_adx(high, low, close, di_len=7, adx_smooth=7):
    if len(close) < di_len + adx_smooth + 5:
        return {"adx": 0, "trend_direction": "NEUTRAL", "weakening": False}
    
    tr = pd.concat([high - low, abs(high - close.shift(1)), abs(low - close.shift(1))], axis=1).max(axis=1)
    atr = tr.rolling(di_len).mean()
    
    plus_dm = high.diff().where((high.diff() > -low.diff()) & (high.diff() > 0), 0)
    minus_dm = (-low.diff()).where((-low.diff() > high.diff()) & (-low.diff() > 0), 0)
    
    plus_di = 100 * plus_dm.rolling(di_len).mean() / atr
    minus_di = 100 * minus_dm.rolling(di_len).mean() / atr
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
    adx = dx.rolling(adx_smooth).mean()
    
    curr = adx.iloc[-1]
    prev = adx.iloc[-2] if len(adx) > 1 else curr
    
    return {"adx": curr, "trend_direction": "BULLISH" if plus_di.iloc[-1] > minus_di.iloc[-1] else "BEARISH", 
            "weakening": curr < prev and curr > 20}

def calculate_roc(prices, period=10):
    if len(prices) < period + 5:
        return {"roc": 0, "signal": "NEUTRAL", "bearish_div": False, "bullish_div": False, "weakening": False}
    
    roc = ((prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]) * 100
    prev_roc = ((prices.iloc[-2] - prices.iloc[-period-1]) / prices.iloc[-period-1]) * 100
    
    bear_div = prices.iloc[-1] > prices.iloc[-5:-1].max() and roc < prev_roc and roc > 0
    bull_div = prices.iloc[-1] < prices.iloc[-5:-1].min() and roc > prev_roc and roc < 0
    
    return {"roc": roc, "signal": "BULLISH" if roc > 2 else "BEARISH" if roc < -2 else "NEUTRAL", 
            "bearish_div": bear_div, "bullish_div": bull_div, "weakening": abs(roc) < abs(prev_roc)}

def analyze_signal_with_targets(h5, h10, min_conf=4):
    if h5.empty or len(h5) < 50 or h10.empty or len(h10) < 20:
        return None
    
    ltp = h5['Close'].iloc[-1]
    atr = calculate_atr(h5['High'], h5['Low'], h5['Close'])
    
    today_data = h5.tail(75)
    day_high = today_data['High'].max()
    day_low = today_data['Low'].min()
    
    vwap5 = calculate_vwap(h5['High'], h5['Low'], h5['Close'], h5['Volume'])
    st5 = calculate_supertrend(h5['High'], h5['Low'], h5['Close'])
    bb5 = calculate_bb(h5['Close'])
    
    vwap10 = calculate_vwap(h10['High'], h10['Low'], h10['Close'], h10['Volume'])
    st10 = calculate_supertrend(h10['High'], h10['Low'], h10['Close'])
    bb10 = calculate_bb(h10['Close'])
    
    adx = calculate_adx(h5['High'], h5['Low'], h5['Close'])
    roc = calculate_roc(h5['Close'])
    
    # LONG
    lc = 0
    if vwap5["signal"] == "BULLISH": lc += 1
    if st5["signal"] == "BULLISH": lc += 1; lc += 1 if st5["crossover"] else 0
    if bb5["signal"] in ["OVERSOLD", "BULLISH"]: lc += 1
    if vwap10["signal"] == "BULLISH": lc += 1
    if st10["signal"] == "BULLISH": lc += 1; lc += 1 if st10["crossover"] else 0
    if bb10["signal"] in ["OVERSOLD", "BULLISH"]: lc += 1
    if adx["adx"] >= 25 and adx["trend_direction"] == "BULLISH": lc += 1
    if roc["signal"] == "BULLISH" and not roc["weakening"]: lc += 1
    if roc["bullish_div"]: lc += 2
    if adx["weakening"] and adx["trend_direction"] == "BULLISH": lc -= 1
    if roc["bearish_div"]: lc -= 2
    
    # SHORT
    sc = 0
    if vwap5["signal"] == "BEARISH": sc += 1
    if st5["signal"] == "BEARISH": sc += 1; sc += 1 if st5["crossover"] else 0
    if bb5["signal"] in ["OVERBOUGHT", "BEARISH"]: sc += 1
    if vwap10["signal"] == "BEARISH": sc += 1
    if st10["signal"] == "BEARISH": sc += 1; sc += 1 if st10["crossover"] else 0
    if bb10["signal"] in ["OVERBOUGHT", "BEARISH"]: sc += 1
    if adx["adx"] >= 25 and adx["trend_direction"] == "BEARISH": sc += 1
    if roc["signal"] == "BEARISH" and not roc["weakening"]: sc += 1
    if roc["bearish_div"]: sc += 2
    if adx["weakening"] and adx["trend_direction"] == "BEARISH": sc -= 1
    if roc["bullish_div"]: sc -= 2
    
    has_crossover = st5["crossover"] or st10["crossover"]
    
    if lc >= min_conf and lc > sc:
        # OLD targets (BB-based)
        old_sl = max(bb5["lower"] * 0.998, st5["value"] * 0.995, day_low * 0.998)
        old_t1 = min(bb5["upper"], day_high * 1.002)
        
        # NEW targets (ATR-based)
        new_sl = max(ltp - (atr * 1.5), st5["value"] * 0.997, day_low * 0.998)
        if has_crossover:
            new_t1 = ltp + (atr * 1.2)
        else:
            new_t1 = ltp + (atr * 1.0)
        
        return {
            "signal": "LONG", "confirmations": lc, "entry": ltp, "atr": atr, "crossover": has_crossover,
            "old_sl": old_sl, "old_t1": old_t1,
            "new_sl": new_sl, "new_t1": new_t1
        }
    
    if sc >= min_conf and sc > lc:
        # OLD targets
        old_sl = min(bb5["upper"] * 1.002, st5["value"] * 1.005, day_high * 1.002)
        old_t1 = max(bb5["lower"], day_low * 0.998)
        
        # NEW targets
        new_sl = min(ltp + (atr * 1.5), st5["value"] * 1.003, day_high * 1.002)
        if has_crossover:
            new_t1 = ltp - (atr * 1.2)
        else:
            new_t1 = ltp - (atr * 1.0)
        
        return {
            "signal": "SHORT", "confirmations": sc, "entry": ltp, "atr": atr, "crossover": has_crossover,
            "old_sl": old_sl, "old_t1": old_t1,
            "new_sl": new_sl, "new_t1": new_t1
        }
    
    return None

def check_outcome(h5, sig, entry_idx, sl, t1, max_candles=24):
    """Check if target or stoploss hit within max_candles (24 = 2 hours)"""
    entry = sig["entry"]
    future = h5.iloc[entry_idx:min(entry_idx + max_candles, len(h5))]
    
    if future.empty or len(future) < 2:
        return {"outcome": "NO_DATA", "pnl": 0}
    
    for i, (_, row) in enumerate(future.iterrows()):
        if sig["signal"] == "LONG":
            if row['Low'] <= sl:
                return {"outcome": "LOSS", "pnl": ((sl - entry) / entry) * 100, "candles": i+1, "mins": (i+1)*5}
            if row['High'] >= t1:
                return {"outcome": "WIN", "pnl": ((t1 - entry) / entry) * 100, "candles": i+1, "mins": (i+1)*5}
        else:
            if row['High'] >= sl:
                return {"outcome": "LOSS", "pnl": ((entry - sl) / entry) * 100, "candles": i+1, "mins": (i+1)*5}
            if row['Low'] <= t1:
                return {"outcome": "WIN", "pnl": ((entry - t1) / entry) * 100, "candles": i+1, "mins": (i+1)*5}
    
    # Expired - check final close
    final = future['Close'].iloc[-1]
    pnl = ((final - entry) / entry) * 100 if sig["signal"] == "LONG" else ((entry - final) / entry) * 100
    return {"outcome": "EXPIRED", "pnl": pnl, "candles": len(future), "mins": len(future)*5}

def run_backtest():
    print("\n" + "="*70)
    print("🎯 NIFTY IT - TARGET HIT RATE Backtest")
    print("="*70)
    print(f"📊 Stocks: {', '.join(NIFTY_IT)}")
    print(f"⏱️  Max Hold: 2 hours (24 candles on 5-min)")
    print(f"\n📐 Comparing:")
    print(f"   OLD: BB-based targets (often 1.5-2% away)")
    print(f"   NEW: ATR-based targets (1x ATR, ~0.8-1.2%)")
    print("="*70)
    
    old_trades = []
    new_trades = []
    stock_results = {}
    
    for symbol in NIFTY_IT:
        print(f"\n📈 {symbol}...", end=" ")
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            h5 = ticker.history(period="5d", interval="5m")
            
            if h5.empty or len(h5) < 100:
                print("❌ No data")
                continue
            
            h10 = h5.resample('10min').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            
            if h5.index.tz is not None:
                dates = h5.index.tz_localize(None).date
            else:
                dates = h5.index.date
            
            unique_dates = pd.Series(dates).unique()[-3:]  # Last 3 days
            
            sym_old = []
            sym_new = []
            
            for date in unique_dates:
                day_mask = dates == date
                day_idx = np.where(day_mask)[0]
                
                if len(day_idx) < 60:
                    continue
                
                for offset in [15, 27, 39, 51, 63]:  # 9:30, 10:15, 11:00, 11:45, 12:30
                    idx = day_idx[0] + offset
                    if idx >= len(h5) - 24:
                        continue
                    
                    sig = analyze_signal_with_targets(h5.iloc[:idx+1], h10[h10.index <= h5.index[idx]])
                    
                    if sig:
                        # Test OLD targets
                        old_out = check_outcome(h5, sig, idx, sig["old_sl"], sig["old_t1"])
                        old_trades.append({
                            "symbol": symbol, "signal": sig["signal"], "conf": sig["confirmations"],
                            "outcome": old_out["outcome"], "pnl": old_out["pnl"],
                            "sl_dist": abs(sig["entry"] - sig["old_sl"]) / sig["entry"] * 100,
                            "t1_dist": abs(sig["old_t1"] - sig["entry"]) / sig["entry"] * 100
                        })
                        sym_old.append(old_out)
                        
                        # Test NEW targets
                        new_out = check_outcome(h5, sig, idx, sig["new_sl"], sig["new_t1"])
                        new_trades.append({
                            "symbol": symbol, "signal": sig["signal"], "conf": sig["confirmations"],
                            "outcome": new_out["outcome"], "pnl": new_out["pnl"],
                            "sl_dist": abs(sig["entry"] - sig["new_sl"]) / sig["entry"] * 100,
                            "t1_dist": abs(sig["new_t1"] - sig["entry"]) / sig["entry"] * 100
                        })
                        sym_new.append(new_out)
            
            if sym_old:
                old_wins = sum(1 for t in sym_old if t["outcome"] == "WIN")
                new_wins = sum(1 for t in sym_new if t["outcome"] == "WIN")
                old_wr = (old_wins / len(sym_old)) * 100
                new_wr = (new_wins / len(sym_new)) * 100
                
                stock_results[symbol] = {"old_wr": old_wr, "new_wr": new_wr, "trades": len(sym_old)}
                
                change = "📈" if new_wr > old_wr else "📉" if new_wr < old_wr else "➖"
                print(f"✅ {len(sym_old)} signals | OLD: {old_wr:.0f}% | NEW: {new_wr:.0f}% {change}")
            else:
                print("⚪ No signals")
                
        except Exception as e:
            print(f"❌ {e}")
    
    # ============== SUMMARY ==============
    print("\n" + "="*70)
    print("📊 NIFTY IT - TARGET HIT RATE COMPARISON")
    print("="*70)
    
    if not old_trades:
        print("❌ No trades generated")
        return
    
    # Calculate stats
    old_total = len(old_trades)
    old_wins = sum(1 for t in old_trades if t["outcome"] == "WIN")
    old_losses = sum(1 for t in old_trades if t["outcome"] == "LOSS")
    old_expired = sum(1 for t in old_trades if t["outcome"] == "EXPIRED")
    old_wr = (old_wins / old_total) * 100
    old_pnl = sum(t["pnl"] for t in old_trades)
    old_avg_t1 = np.mean([t["t1_dist"] for t in old_trades])
    old_avg_sl = np.mean([t["sl_dist"] for t in old_trades])
    
    new_total = len(new_trades)
    new_wins = sum(1 for t in new_trades if t["outcome"] == "WIN")
    new_losses = sum(1 for t in new_trades if t["outcome"] == "LOSS")
    new_expired = sum(1 for t in new_trades if t["outcome"] == "EXPIRED")
    new_wr = (new_wins / new_total) * 100
    new_pnl = sum(t["pnl"] for t in new_trades)
    new_avg_t1 = np.mean([t["t1_dist"] for t in new_trades])
    new_avg_sl = np.mean([t["sl_dist"] for t in new_trades])
    
    print(f"\n{'Metric':<25} {'OLD (BB)':<18} {'NEW (ATR)':<18} {'Diff':<15}")
    print("-" * 76)
    print(f"{'Total Signals':<25} {old_total:<18}")
    print(f"{'Avg Target Distance':<25} {old_avg_t1:.2f}%{'':<12} {new_avg_t1:.2f}%{'':<12} {new_avg_t1 - old_avg_t1:+.2f}%")
    print(f"{'Avg Stoploss Distance':<25} {old_avg_sl:.2f}%{'':<12} {new_avg_sl:.2f}%{'':<12} {new_avg_sl - old_avg_sl:+.2f}%")
    print("-" * 76)
    print(f"{'✅ WINS (Target Hit)':<25} {old_wins:<18} {new_wins:<18} {'+' if new_wins > old_wins else ''}{new_wins - old_wins}")
    print(f"{'❌ LOSSES (SL Hit)':<25} {old_losses:<18} {new_losses:<18} {'+' if new_losses > old_losses else ''}{new_losses - old_losses}")
    print(f"{'⏰ EXPIRED':<25} {old_expired:<18} {new_expired:<18} {'+' if new_expired > old_expired else ''}{new_expired - old_expired}")
    print("-" * 76)
    print(f"{'🎯 TARGET HIT RATE':<25} {old_wr:.1f}%{'':<13} {new_wr:.1f}%{'':<13} {'+' if new_wr > old_wr else ''}{new_wr - old_wr:.1f}%")
    print(f"{'💰 Total P&L':<25} {old_pnl:+.2f}%{'':<11} {new_pnl:+.2f}%{'':<11} {'+' if new_pnl > old_pnl else ''}{new_pnl - old_pnl:.2f}%")
    
    # Per stock breakdown
    print(f"\n📊 BY STOCK:")
    print(f"{'Stock':<12} {'OLD WR':<12} {'NEW WR':<12} {'Change':<12}")
    print("-" * 48)
    for sym in NIFTY_IT:
        if sym in stock_results:
            r = stock_results[sym]
            change = r["new_wr"] - r["old_wr"]
            icon = "📈" if change > 0 else "📉" if change < 0 else "➖"
            print(f"{sym:<12} {r['old_wr']:.0f}%{'':<8} {r['new_wr']:.0f}%{'':<8} {change:+.0f}% {icon}")
    
    # Verdict
    print("\n" + "="*70)
    improvement = new_wr - old_wr
    if improvement > 5:
        print(f"✅ NEW METHOD SIGNIFICANTLY BETTER! +{improvement:.1f}% hit rate")
    elif improvement > 0:
        print(f"✅ NEW METHOD BETTER by +{improvement:.1f}% hit rate")
    elif improvement > -5:
        print(f"➖ SIMILAR PERFORMANCE ({improvement:+.1f}% difference)")
    else:
        print(f"⚠️ OLD METHOD was better by {-improvement:.1f}%")
    
    print("="*70 + "\n")

if __name__ == "__main__":
    run_backtest()
