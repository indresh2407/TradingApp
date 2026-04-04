#!/usr/bin/env python3
"""
SIDDHI DayTrade - NIFTY 100 Direction Accuracy
===============================================
Tests directional accuracy for NIFTY 100 stocks.

Run: python3 backtest_nifty100_direction.py
"""

import yfinance as yf
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# NIFTY 100 stocks
NIFTY_100 = [
    # NIFTY 50
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR", "SBIN", 
    "BHARTIARTL", "KOTAKBANK", "ITC", "LT", "AXISBANK", "ASIANPAINT", "MARUTI",
    "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO", "BAJFINANCE",
    "NESTLEIND", "TATAMOTORS", "ONGC", "NTPC", "POWERGRID", "M&M", "JSWSTEEL",
    "TATASTEEL", "ADANIENT", "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "TECHM",
    "HDFCLIFE", "SBILIFE", "GRASIM", "DIVISLAB", "DRREDDY", "CIPLA", "BRITANNIA",
    "APOLLOHOSP", "EICHERMOT", "INDUSINDBK", "HINDALCO", "BPCL", "TATACONSUM",
    "HEROMOTOCO", "UPL", "BAJAJ-AUTO", "VEDL",
    # NIFTY NEXT 50
    "GODREJCP", "DABUR", "PIDILITIND", "HAVELLS", "SIEMENS", "BOSCHLTD",
    "COLPAL", "MARICO", "BERGEPAINT", "PAGEIND", "MCDOWELL-N", "INDIGO",
    "BANDHANBNK", "NAUKRI", "ICICIPRULI", "GAIL", "DLF", "PETRONET",
    "LUPIN", "AUROPHARMA", "BIOCON", "TORNTPHARM", "CADILAHC", "PEL",
    "AMBUJACEM", "ACC", "SHREECEM", "DALBHARAT", "MUTHOOTFIN", "CHOLAFIN",
    "BAJAJHLDNG", "SRTRANSFIN", "PFC", "RECLTD", "IRCTC", "TATAPOWER",
    "ADANIGREEN", "ADANITRANS", "INDUSTOWER", "ICICIGI", "SBICARD",
    "PIIND", "ALKEM", "LALPATHLAB", "OFSS", "LTTS", "MPHASIS", "COFORGE"
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
    
    return {"upper": upper.iloc[-1], "lower": lower.iloc[-1], "signal": sig}

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

def analyze_signal(h5, h10, min_conf=4):
    if h5.empty or len(h5) < 50 or h10.empty or len(h10) < 20:
        return None
    
    ltp = h5['Close'].iloc[-1]
    
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
    
    if lc >= min_conf and lc > sc:
        return {"signal": "LONG", "confirmations": lc, "entry": ltp}
    if sc >= min_conf and sc > lc:
        return {"signal": "SHORT", "confirmations": sc, "entry": ltp}
    return None

def check_direction(h5, sig, entry_idx, check_candles=12):
    if not sig:
        return None
    
    entry = sig["entry"]
    future = h5.iloc[entry_idx:min(entry_idx + check_candles, len(h5))]
    
    if future.empty or len(future) < 2:
        return None
    
    max_high = future['High'].max()
    min_low = future['Low'].min()
    close_final = future['Close'].iloc[-1]
    
    if sig["signal"] == "LONG":
        max_favorable = ((max_high - entry) / entry) * 100
        max_adverse = ((entry - min_low) / entry) * 100
        final_pnl = ((close_final - entry) / entry) * 100
        direction_correct = max_favorable >= 0.1
    else:
        max_favorable = ((entry - min_low) / entry) * 100
        max_adverse = ((max_high - entry) / entry) * 100
        final_pnl = ((entry - close_final) / entry) * 100
        direction_correct = max_favorable >= 0.1
    
    return {
        "direction_correct": direction_correct,
        "strong_move": max_favorable > max_adverse,
        "max_favorable": round(max_favorable, 2),
        "max_adverse": round(max_adverse, 2),
        "final_pnl": round(final_pnl, 2)
    }

def run_backtest():
    print("\n" + "="*70)
    print("🎯 NIFTY 100 - Direction Accuracy Backtest")
    print("="*70)
    print(f"📊 Testing: {len(NIFTY_100)} stocks")
    print(f"⏱️  Check Window: 1 hour (12 candles on 5-min)")
    print(f"📅 Period: Last 3 trading days")
    print("="*70)
    
    all_trades = []
    sector_results = {
        "BANKING": [], "IT": [], "AUTO": [], "PHARMA": [], "FMCG": [],
        "METAL": [], "ENERGY": [], "INFRA": [], "OTHERS": []
    }
    
    # Sector mapping
    sector_map = {
        "HDFCBANK": "BANKING", "ICICIBANK": "BANKING", "SBIN": "BANKING", "KOTAKBANK": "BANKING",
        "AXISBANK": "BANKING", "INDUSINDBK": "BANKING", "BANDHANBNK": "BANKING", "PNB": "BANKING",
        "TCS": "IT", "INFY": "IT", "HCLTECH": "IT", "WIPRO": "IT", "TECHM": "IT",
        "LTTS": "IT", "MPHASIS": "IT", "COFORGE": "IT", "NAUKRI": "IT", "OFSS": "IT",
        "TATAMOTORS": "AUTO", "MARUTI": "AUTO", "M&M": "AUTO", "BAJAJ-AUTO": "AUTO",
        "HEROMOTOCO": "AUTO", "EICHERMOT": "AUTO",
        "SUNPHARMA": "PHARMA", "DRREDDY": "PHARMA", "CIPLA": "PHARMA", "DIVISLAB": "PHARMA",
        "LUPIN": "PHARMA", "AUROPHARMA": "PHARMA", "BIOCON": "PHARMA", "TORNTPHARM": "PHARMA",
        "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG", "BRITANNIA": "FMCG",
        "DABUR": "FMCG", "MARICO": "FMCG", "COLPAL": "FMCG", "GODREJCP": "FMCG",
        "TATASTEEL": "METAL", "JSWSTEEL": "METAL", "HINDALCO": "METAL", "VEDL": "METAL",
        "COALINDIA": "METAL",
        "RELIANCE": "ENERGY", "ONGC": "ENERGY", "BPCL": "ENERGY", "GAIL": "ENERGY",
        "PETRONET": "ENERGY", "POWERGRID": "ENERGY", "NTPC": "ENERGY", "TATAPOWER": "ENERGY",
        "LT": "INFRA", "ADANIENT": "INFRA", "ADANIPORTS": "INFRA", "DLF": "INFRA",
        "ULTRACEMCO": "INFRA", "GRASIM": "INFRA", "AMBUJACEM": "INFRA", "ACC": "INFRA"
    }
    
    processed = 0
    
    for symbol in NIFTY_100:
        processed += 1
        print(f"\r📈 Processing {processed}/{len(NIFTY_100)}: {symbol}...", end="", flush=True)
        
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            h5 = ticker.history(period="5d", interval="5m")
            
            if h5.empty or len(h5) < 100:
                continue
            
            h10 = h5.resample('10min').agg({
                'Open': 'first', 'High': 'max', 'Low': 'min', 
                'Close': 'last', 'Volume': 'sum'
            }).dropna()
            
            if h5.index.tz is not None:
                dates = h5.index.tz_localize(None).date
            else:
                dates = h5.index.date
            
            unique_dates = pd.Series(dates).unique()[-3:]
            
            for date in unique_dates:
                day_mask = dates == date
                day_idx = np.where(day_mask)[0]
                
                if len(day_idx) < 50:
                    continue
                
                for offset in [15, 33, 51]:  # 9:30, 11:00, 12:30
                    idx = day_idx[0] + offset
                    if idx >= len(h5) - 12:
                        continue
                    
                    sig = analyze_signal(h5.iloc[:idx+1], h10[h10.index <= h5.index[idx]])
                    
                    if sig:
                        out = check_direction(h5, sig, idx)
                        if out:
                            trade = {
                                "symbol": symbol,
                                "signal": sig["signal"],
                                "conf": sig["confirmations"],
                                **out
                            }
                            all_trades.append(trade)
                            
                            sector = sector_map.get(symbol, "OTHERS")
                            sector_results[sector].append(trade)
                
        except Exception as e:
            continue
    
    print("\n")
    
    # ============== SUMMARY ==============
    print("="*70)
    print("📊 NIFTY 100 - DIRECTION ACCURACY RESULTS")
    print("="*70)
    
    if not all_trades:
        print("❌ No trades generated")
        return
    
    total = len(all_trades)
    correct = sum(1 for t in all_trades if t["direction_correct"])
    strong = sum(1 for t in all_trades if t["strong_move"])
    
    accuracy = (correct / total) * 100
    strong_rate = (strong / total) * 100
    
    avg_favorable = np.mean([t["max_favorable"] for t in all_trades])
    avg_adverse = np.mean([t["max_adverse"] for t in all_trades])
    avg_pnl = np.mean([t["final_pnl"] for t in all_trades])
    
    print(f"\n🎯 OVERALL DIRECTION ACCURACY: {accuracy:.1f}%")
    print(f"   Total Signals: {total}")
    print(f"   ✅ Correct Direction: {correct} ({accuracy:.1f}%)")
    print(f"   💪 Strong Moves: {strong} ({strong_rate:.1f}%)")
    
    print(f"\n📈 MOVE ANALYSIS:")
    print(f"   Avg Favorable Move: +{avg_favorable:.2f}%")
    print(f"   Avg Adverse Move:   -{avg_adverse:.2f}%")
    print(f"   Avg Final P&L (1hr): {avg_pnl:+.2f}%")
    
    # By direction
    longs = [t for t in all_trades if t["signal"] == "LONG"]
    shorts = [t for t in all_trades if t["signal"] == "SHORT"]
    
    print(f"\n📊 BY SIGNAL TYPE:")
    if longs:
        long_acc = (sum(1 for t in longs if t["direction_correct"]) / len(longs)) * 100
        long_fav = np.mean([t["max_favorable"] for t in longs])
        print(f"   🟢 LONG:  {len(longs)} signals | Accuracy: {long_acc:.1f}% | Avg Move: +{long_fav:.2f}%")
    if shorts:
        short_acc = (sum(1 for t in shorts if t["direction_correct"]) / len(shorts)) * 100
        short_fav = np.mean([t["max_favorable"] for t in shorts])
        print(f"   🔴 SHORT: {len(shorts)} signals | Accuracy: {short_acc:.1f}% | Avg Move: +{short_fav:.2f}%")
    
    # By sector
    print(f"\n📊 BY SECTOR:")
    print(f"{'Sector':<12} {'Signals':<10} {'Accuracy':<12} {'Avg Move':<12}")
    print("-" * 46)
    
    sector_order = ["BANKING", "IT", "AUTO", "PHARMA", "FMCG", "METAL", "ENERGY", "INFRA", "OTHERS"]
    for sector in sector_order:
        trades = sector_results[sector]
        if trades:
            s_correct = sum(1 for t in trades if t["direction_correct"])
            s_acc = (s_correct / len(trades)) * 100
            s_fav = np.mean([t["max_favorable"] for t in trades])
            icon = "🟢" if s_acc >= 60 else "🟡" if s_acc >= 50 else "🔴"
            print(f"{sector:<12} {len(trades):<10} {s_acc:.0f}% {icon:<8} +{s_fav:.2f}%")
    
    # By confirmations
    print(f"\n📊 BY CONFIRMATION COUNT:")
    for c in sorted(set(t["conf"] for t in all_trades)):
        ct = [t for t in all_trades if t["conf"] == c]
        c_correct = sum(1 for t in ct if t["direction_correct"])
        c_acc = (c_correct / len(ct)) * 100
        print(f"   {c} confirmations: {len(ct)} signals | Accuracy: {c_acc:.1f}%")
    
    # Top performers
    print(f"\n🏆 TOP 10 STOCKS (by accuracy):")
    stock_acc = {}
    for sym in set(t["symbol"] for t in all_trades):
        st = [t for t in all_trades if t["symbol"] == sym]
        if len(st) >= 2:
            stock_acc[sym] = (sum(1 for t in st if t["direction_correct"]) / len(st)) * 100
    
    sorted_stocks = sorted(stock_acc.items(), key=lambda x: x[1], reverse=True)[:10]
    for sym, acc in sorted_stocks:
        print(f"   {sym}: {acc:.0f}%")
    
    print("\n" + "="*70)
    print("✅ Backtest Complete!")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_backtest()
