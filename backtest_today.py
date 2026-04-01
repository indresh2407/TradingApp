#!/usr/bin/env python3
"""
Backtest Today's Predictions
Simulates what our strategy would have predicted during today's trading session
and checks if those predictions were successful.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Stock lists to analyze
NIFTY_50_STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL",
    "HINDUNILVR", "ITC", "KOTAKBANK", "LT", "AXISBANK", "MARUTI", "WIPRO",
    "HCLTECH", "ASIANPAINT", "BAJFINANCE", "TITAN", "SUNPHARMA", "TATAMOTORS",
    "ONGC", "NTPC", "POWERGRID", "COALINDIA", "BPCL", "GRASIM", "ULTRACEMCO",
    "JSWSTEEL", "TATASTEEL", "HINDALCO"
]

def get_yahoo_symbol(symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance symbol"""
    return f"{symbol}.NS"

def calculate_rsi(close: pd.Series, period: int = 14) -> float:
    """Calculate RSI"""
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series, 
                         period: int = 10, multiplier: float = 3.0) -> str:
    """Calculate Supertrend signal"""
    try:
        hl2 = (high + low) / 2
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        upper_band = hl2 + (multiplier * atr)
        lower_band = hl2 - (multiplier * atr)
        
        if close.iloc[-1] > upper_band.iloc[-2]:
            return "BULLISH"
        elif close.iloc[-1] < lower_band.iloc[-2]:
            return "BEARISH"
        return "NEUTRAL"
    except:
        return "NEUTRAL"

def analyze_stock_at_time(symbol: str, hist: pd.DataFrame, time_idx: int) -> Dict:
    """Analyze a stock at a specific point in time"""
    if time_idx < 20 or time_idx >= len(hist):
        return None
    
    # Get data up to this point in time
    data = hist.iloc[:time_idx+1].copy()
    
    ltp = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[-2]
    change_pct = ((ltp - prev_close) / prev_close) * 100
    
    # Today's OHLC up to this point
    today_data = data.tail(min(len(data), 75))  # ~6 hours of 5-min data
    today_high = today_data['High'].max()
    today_low = today_data['Low'].min()
    
    # RSI
    rsi = calculate_rsi(data['Close'])
    
    # Supertrend
    supertrend = calculate_supertrend(data['High'], data['Low'], data['Close'])
    
    # Volume analysis
    avg_volume = data['Volume'].tail(20).mean()
    current_volume = data['Volume'].iloc[-1]
    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
    
    # VWAP
    typical_price = (data['High'] + data['Low'] + data['Close']) / 3
    vwap = (typical_price * data['Volume']).sum() / data['Volume'].sum()
    vwap_signal = "BULLISH" if ltp > vwap else "BEARISH"
    
    # Calculate signal
    long_score = 0
    short_score = 0
    
    if supertrend == "BULLISH":
        long_score += 30
    elif supertrend == "BEARISH":
        short_score += 30
    
    if vwap_signal == "BULLISH":
        long_score += 20
    else:
        short_score += 20
    
    if rsi < 40:
        long_score += 15
    elif rsi > 60:
        short_score += 15
    
    if change_pct > 0.3:
        long_score += 10
    elif change_pct < -0.3:
        short_score += 10
    
    if volume_ratio > 1.5:
        if change_pct > 0:
            long_score += 10
        else:
            short_score += 10
    
    # Determine signal
    if long_score > short_score and long_score >= 40:
        signal = "LONG"
        entry = ltp
        stoploss = round(ltp * 0.993, 2)
        target1 = round(ltp * 1.01, 2)  # 1% target
        target2 = round(ltp * 1.015, 2)  # 1.5% target
    elif short_score > long_score and short_score >= 40:
        signal = "SHORT"
        entry = ltp
        stoploss = round(ltp * 1.007, 2)
        target1 = round(ltp * 0.99, 2)
        target2 = round(ltp * 0.985, 2)
    else:
        return None
    
    return {
        "symbol": symbol,
        "signal": signal,
        "entry": entry,
        "stoploss": stoploss,
        "target1": target1,
        "target2": target2,
        "rsi": round(rsi, 1),
        "supertrend": supertrend,
        "vwap_signal": vwap_signal,
        "volume_ratio": round(volume_ratio, 1),
        "time_idx": time_idx,
        "long_score": long_score,
        "short_score": short_score
    }

def check_prediction_outcome(prediction: Dict, future_data: pd.DataFrame) -> Dict:
    """Check if a prediction hit target or stoploss"""
    if future_data.empty or len(future_data) < 2:
        return {"outcome": "NO_DATA", "max_profit_pct": 0, "max_loss_pct": 0}
    
    entry = prediction["entry"]
    target1 = prediction["target1"]
    stoploss = prediction["stoploss"]
    signal = prediction["signal"]
    
    target_hit = False
    stoploss_hit = False
    max_favorable = 0
    max_adverse = 0
    
    for i in range(len(future_data)):
        high = future_data['High'].iloc[i]
        low = future_data['Low'].iloc[i]
        
        if signal == "LONG":
            # Check if target hit
            if high >= target1:
                target_hit = True
                break
            # Check if stoploss hit
            if low <= stoploss:
                stoploss_hit = True
                break
            # Track max profit/loss
            max_favorable = max(max_favorable, (high - entry) / entry * 100)
            max_adverse = max(max_adverse, (entry - low) / entry * 100)
        else:  # SHORT
            # Check if target hit
            if low <= target1:
                target_hit = True
                break
            # Check if stoploss hit
            if high >= stoploss:
                stoploss_hit = True
                break
            # Track max profit/loss
            max_favorable = max(max_favorable, (entry - low) / entry * 100)
            max_adverse = max(max_adverse, (high - entry) / entry * 100)
    
    if target_hit:
        outcome = "WIN"
    elif stoploss_hit:
        outcome = "LOSS"
    else:
        # Check final price
        final_price = future_data['Close'].iloc[-1]
        if signal == "LONG":
            if final_price > entry:
                outcome = "PARTIAL_WIN"
            else:
                outcome = "PARTIAL_LOSS"
        else:
            if final_price < entry:
                outcome = "PARTIAL_WIN"
            else:
                outcome = "PARTIAL_LOSS"
    
    return {
        "outcome": outcome,
        "max_profit_pct": round(max_favorable, 2),
        "max_loss_pct": round(max_adverse, 2),
        "target_hit": target_hit,
        "stoploss_hit": stoploss_hit
    }

def run_backtest():
    """Run backtest for today's predictions"""
    print("=" * 70)
    print("BACKTEST: Today's Predictions Analysis")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    print("=" * 70)
    
    all_predictions = []
    
    # Analyze each stock
    for symbol in NIFTY_50_STOCKS[:20]:  # Top 20 stocks
        try:
            yahoo_symbol = get_yahoo_symbol(symbol)
            ticker = yf.Ticker(yahoo_symbol)
            
            # Get 5-minute data for today and yesterday
            hist = ticker.history(period="2d", interval="5m")
            
            if hist.empty or len(hist) < 50:
                continue
            
            # Filter to today's data only
            today = datetime.now().date()
            if hist.index.tz is not None:
                hist.index = hist.index.tz_convert('Asia/Kolkata')
            
            today_mask = hist.index.date == today
            today_data = hist[today_mask]
            
            if len(today_data) < 20:
                print(f"{symbol}: Insufficient data ({len(today_data)} candles)")
                continue
            
            # Simulate predictions at different times
            # 10:00 AM, 11:00 AM, 12:00 PM, 1:00 PM, 2:00 PM
            check_times = [12, 24, 36, 48, 60]  # Candle indices (~10, 11, 12, 1, 2 PM)
            
            for time_idx in check_times:
                if time_idx >= len(today_data) - 12:  # Need at least 1 hour of future data
                    continue
                
                prediction = analyze_stock_at_time(symbol, hist, len(hist) - len(today_data) + time_idx)
                
                if prediction:
                    # Get future data (next 1-2 hours)
                    future_start = len(hist) - len(today_data) + time_idx + 1
                    future_end = min(future_start + 24, len(hist))  # ~2 hours
                    future_data = hist.iloc[future_start:future_end]
                    
                    # Check outcome
                    result = check_prediction_outcome(prediction, future_data)
                    prediction.update(result)
                    prediction["check_time"] = today_data.index[time_idx].strftime("%H:%M") if time_idx < len(today_data) else "N/A"
                    
                    all_predictions.append(prediction)
                    
        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            continue
    
    if not all_predictions:
        print("\nNo predictions generated. Market may be closed or no clear signals.")
        return
    
    # Analyze results
    print(f"\n{'='*70}")
    print("PREDICTION RESULTS")
    print(f"{'='*70}")
    
    wins = [p for p in all_predictions if p["outcome"] == "WIN"]
    losses = [p for p in all_predictions if p["outcome"] == "LOSS"]
    partial_wins = [p for p in all_predictions if p["outcome"] == "PARTIAL_WIN"]
    partial_losses = [p for p in all_predictions if p["outcome"] == "PARTIAL_LOSS"]
    
    total = len(all_predictions)
    win_rate = (len(wins) / total * 100) if total > 0 else 0
    success_rate = ((len(wins) + len(partial_wins)) / total * 100) if total > 0 else 0
    
    print(f"\n📊 SUMMARY")
    print(f"   Total Predictions: {total}")
    print(f"   ✅ Wins (Target Hit): {len(wins)}")
    print(f"   ❌ Losses (SL Hit): {len(losses)}")
    print(f"   📈 Partial Wins: {len(partial_wins)}")
    print(f"   📉 Partial Losses: {len(partial_losses)}")
    print(f"\n   🎯 Win Rate (Target Hit): {win_rate:.1f}%")
    print(f"   📈 Success Rate (Win + Partial Win): {success_rate:.1f}%")
    
    # Breakdown by signal type
    long_preds = [p for p in all_predictions if p["signal"] == "LONG"]
    short_preds = [p for p in all_predictions if p["signal"] == "SHORT"]
    
    long_wins = len([p for p in long_preds if p["outcome"] in ["WIN", "PARTIAL_WIN"]])
    short_wins = len([p for p in short_preds if p["outcome"] in ["WIN", "PARTIAL_WIN"]])
    
    print(f"\n📊 BY SIGNAL TYPE")
    print(f"   LONG Predictions: {len(long_preds)} (Success: {long_wins}/{len(long_preds)})")
    print(f"   SHORT Predictions: {len(short_preds)} (Success: {short_wins}/{len(short_preds)})")
    
    # Top performers and worst performers
    print(f"\n✅ TOP WINNING PREDICTIONS:")
    for p in sorted(wins, key=lambda x: x["max_profit_pct"], reverse=True)[:5]:
        print(f"   {p['symbol']} {p['signal']} @ {p['check_time']} - Max Profit: +{p['max_profit_pct']:.2f}%")
    
    print(f"\n❌ LOSING PREDICTIONS:")
    for p in losses[:5]:
        print(f"   {p['symbol']} {p['signal']} @ {p['check_time']} - Max Loss: -{p['max_loss_pct']:.2f}%")
    
    # Detailed breakdown
    print(f"\n{'='*70}")
    print("DETAILED PREDICTIONS")
    print(f"{'='*70}")
    print(f"{'Symbol':<12} {'Signal':<6} {'Time':<6} {'Entry':>10} {'Target':>10} {'SL':>10} {'Outcome':<12} {'Max P/L':>10}")
    print("-" * 80)
    
    for p in sorted(all_predictions, key=lambda x: x["symbol"]):
        outcome_emoji = "✅" if p["outcome"] == "WIN" else "❌" if p["outcome"] == "LOSS" else "📊"
        max_pl = f"+{p['max_profit_pct']:.1f}%" if p["outcome"] in ["WIN", "PARTIAL_WIN"] else f"-{p['max_loss_pct']:.1f}%"
        print(f"{p['symbol']:<12} {p['signal']:<6} {p['check_time']:<6} {p['entry']:>10.2f} {p['target1']:>10.2f} {p['stoploss']:>10.2f} {outcome_emoji} {p['outcome']:<10} {max_pl:>10}")
    
    print(f"\n{'='*70}")
    print("STRATEGY INSIGHTS")
    print(f"{'='*70}")
    
    # Supertrend analysis
    st_bullish_preds = [p for p in all_predictions if p["supertrend"] == "BULLISH"]
    st_bearish_preds = [p for p in all_predictions if p["supertrend"] == "BEARISH"]
    
    st_bullish_wins = len([p for p in st_bullish_preds if p["outcome"] in ["WIN", "PARTIAL_WIN"]])
    st_bearish_wins = len([p for p in st_bearish_preds if p["outcome"] in ["WIN", "PARTIAL_WIN"]])
    
    print(f"\n📈 Supertrend Analysis:")
    if st_bullish_preds:
        print(f"   BULLISH Supertrend: {st_bullish_wins}/{len(st_bullish_preds)} successful ({st_bullish_wins/len(st_bullish_preds)*100:.1f}%)")
    if st_bearish_preds:
        print(f"   BEARISH Supertrend: {st_bearish_wins}/{len(st_bearish_preds)} successful ({st_bearish_wins/len(st_bearish_preds)*100:.1f}%)")
    
    # Time analysis
    print(f"\n⏰ Time Analysis:")
    times = set(p["check_time"] for p in all_predictions)
    for t in sorted(times):
        time_preds = [p for p in all_predictions if p["check_time"] == t]
        time_wins = len([p for p in time_preds if p["outcome"] in ["WIN", "PARTIAL_WIN"]])
        print(f"   {t}: {time_wins}/{len(time_preds)} successful")
    
    return all_predictions

if __name__ == "__main__":
    run_backtest()
