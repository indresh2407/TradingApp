#!/usr/bin/env python3
"""
Test Tomorrow's Intraday Strategy
Run this locally to check if the strategy generates signals
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

# Test stocks (including IDBI which moved big today)
TEST_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN",
    "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "AXISBANK", "HINDUNILVR",
    "BAJFINANCE", "MARUTI", "TATAMOTORS", "SUNPHARMA", "TITAN", "WIPRO",
    "IDBI", "PNB", "BANKBARODA", "CANBK", "FEDERALBNK", "IDFCFIRSTB"  # PSU banks
]

def get_yahoo_symbol(symbol):
    if symbol == "M&M":
        return "M%26M.NS"
    return f"{symbol}.NS"

def calculate_atr(high, low, close, period=10):
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean().iloc[-1]

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

def calculate_supertrend(data, period=10, multiplier=3.0):
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    atr = calculate_atr(high, low, close, period)
    hl2 = (high + low) / 2
    
    basic_upper = hl2.iloc[-1] + (multiplier * atr)
    basic_lower = hl2.iloc[-1] - (multiplier * atr)
    
    close_vals = close.tail(10).values
    is_uptrend = close_vals[-1] > close_vals[-3] if len(close_vals) >= 3 else True
    
    if is_uptrend:
        return {"signal": "BULLISH", "crossover": close.iloc[-2] < basic_lower if len(close) > 1 else False}
    else:
        return {"signal": "BEARISH", "crossover": close.iloc[-2] > basic_upper if len(close) > 1 else False}

def analyze_stock_for_tomorrow(symbol):
    """Analyze a single stock for tomorrow's intraday potential - IMPROVED strategy"""
    try:
        yahoo_symbol = get_yahoo_symbol(symbol)
        ticker = yf.Ticker(yahoo_symbol)
        
        # Get daily data
        hist = ticker.history(period="1mo", interval="1d")
        
        if hist.empty or len(hist) < 10:
            return None
        
        # Today's values (most recent day)
        ltp = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        today_open = hist['Open'].iloc[-1]
        today_high = hist['High'].iloc[-1]
        today_low = hist['Low'].iloc[-1]
        today_volume = hist['Volume'].iloc[-1]
        
        change_pct = ((ltp - prev_close) / prev_close) * 100
        
        # Closing strength
        day_range = today_high - today_low if today_high > today_low else 0.01
        close_position = (ltp - today_low) / day_range
        
        strong_close = close_position > 0.75
        weak_close = close_position < 0.25
        
        # Candle type
        positive_candle = ltp > today_open
        negative_candle = ltp < today_open
        
        # ATR
        atr = calculate_atr(hist['High'], hist['Low'], hist['Close'], period=10)
        atr_pct = (atr / ltp) * 100
        
        # Volume
        avg_volume = hist['Volume'].tail(20).mean()
        volume_ratio = today_volume / avg_volume if avg_volume > 0 else 1
        volume_surge = volume_ratio > 1.5
        
        # Volume building (accumulation)
        recent_vol = hist['Volume'].tail(3).mean()
        prev_vol = hist['Volume'].tail(6).head(3).mean()
        volume_building = recent_vol > prev_vol * 1.2
        
        # Gap potential
        gap_up_potential = strong_close and volume_surge and change_pct > 0.3
        gap_down_potential = weak_close and volume_surge and change_pct < -0.3
        
        # Supertrend
        st = calculate_supertrend(hist)
        st_signal = st.get("signal", "NEUTRAL")
        st_crossover = st.get("crossover", False)
        
        # RSI
        rsi = calculate_rsi(hist['Close'])
        rsi_oversold = rsi < 35
        rsi_overbought = rsi > 65
        
        # Near week high/low
        week_high = hist['High'].tail(5).max()
        week_low = hist['Low'].tail(5).min()
        near_week_high = (week_high - ltp) / ltp * 100 < 1.5
        near_week_low = (ltp - week_low) / ltp * 100 < 1.5
        
        # Support/Resistance
        recent_low = hist['Low'].tail(10).min()
        recent_high = hist['High'].tail(10).max()
        at_support = (ltp - recent_low) / ltp * 100 < 2
        at_resistance = (recent_high - ltp) / ltp * 100 < 2
        
        # Consolidation
        recent_5d_range = (hist['High'].tail(5).max() - hist['Low'].tail(5).min()) / ltp * 100
        avg_daily_range = ((hist['High'] - hist['Low']) / hist['Close']).tail(20).mean() * 100
        is_consolidating = recent_5d_range < avg_daily_range * 1.5
        
        # Moving average
        sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
        above_sma = ltp > sma_20
        below_sma = ltp < sma_20
        
        # Breaking out of range
        prev_4d_high = hist['High'].tail(5).head(4).max()
        prev_4d_low = hist['Low'].tail(5).head(4).min()
        breaking_up = ltp > prev_4d_high
        breaking_down = ltp < prev_4d_low
        
        high_volatility = atr_pct > 2.0
        
        # === IMPROVED SCORING ===
        long_score = 0
        short_score = 0
        long_signals = []
        short_signals = []
        
        # LONG - Momentum continuation
        if strong_close:
            long_score += 20
            long_signals.append("Strong Close")
        if gap_up_potential:
            long_score += 15
            long_signals.append("Gap Up")
        
        # LONG - Trend alignment
        if st_signal == "BULLISH":
            long_score += 15
            long_signals.append("ST+")
        if st_crossover and st_signal == "BULLISH":
            long_score += 15
            long_signals.append("Fresh ST Cross")
        if above_sma:
            long_score += 10
            long_signals.append(">SMA20")
        
        # LONG - Breakout patterns
        if breaking_up:
            long_score += 20
            long_signals.append("BREAKING OUT!")
        if near_week_high and volume_surge:
            long_score += 15
            long_signals.append("Breakout+Vol")
        if is_consolidating and positive_candle:
            long_score += 15
            long_signals.append("Consolidation")
        
        # LONG - Reversal/Bounce patterns
        if at_support and positive_candle:
            long_score += 20
            long_signals.append("Support Bounce")
        if rsi_oversold and positive_candle:
            long_score += 15
            long_signals.append(f"RSI {rsi:.0f}")
        
        # LONG - Volume confirmation
        if volume_surge:
            long_score += 10
            long_signals.append(f"Vol {volume_ratio:.1f}x")
        if volume_building:
            long_score += 10
            long_signals.append("Accumulation")
        
        # LONG - Volatility & Momentum
        if high_volatility:
            long_score += 10
            long_signals.append(f"ATR {atr_pct:.1f}%")
        if change_pct > 0.5:
            long_score += 10
            long_signals.append(f"+{change_pct:.1f}%")
        if change_pct > 2:
            long_score += 10  # Extra for big moves
        
        # SHORT - Momentum continuation
        if weak_close:
            short_score += 20
            short_signals.append("Weak Close")
        if gap_down_potential:
            short_score += 15
            short_signals.append("Gap Down")
        
        # SHORT - Trend alignment
        if st_signal == "BEARISH":
            short_score += 15
            short_signals.append("ST-")
        if st_crossover and st_signal == "BEARISH":
            short_score += 15
            short_signals.append("Fresh ST Cross")
        if below_sma:
            short_score += 10
            short_signals.append("<SMA20")
        
        # SHORT - Breakdown patterns
        if breaking_down:
            short_score += 20
            short_signals.append("BREAKING DOWN!")
        if near_week_low and volume_surge:
            short_score += 15
            short_signals.append("Breakdown+Vol")
        if is_consolidating and negative_candle:
            short_score += 15
            short_signals.append("Consolidation")
        
        # SHORT - Reversal patterns
        if at_resistance and negative_candle:
            short_score += 20
            short_signals.append("Resistance Reject")
        if rsi_overbought and negative_candle:
            short_score += 15
            short_signals.append(f"RSI {rsi:.0f}")
        
        # SHORT - Volume confirmation
        if volume_surge:
            short_score += 10
            short_signals.append(f"Vol {volume_ratio:.1f}x")
        if volume_building and change_pct < 0:
            short_score += 10
            short_signals.append("Distribution")
        
        # SHORT - Volatility & Momentum
        if high_volatility:
            short_score += 10
            short_signals.append(f"ATR {atr_pct:.1f}%")
        if change_pct < -0.5:
            short_score += 10
            short_signals.append(f"{change_pct:.1f}%")
        if change_pct < -2:
            short_score += 10  # Extra for big moves
        
        return {
            "symbol": symbol,
            "ltp": round(ltp, 2),
            "change_pct": round(change_pct, 2),
            "close_position": round(close_position * 100, 0),
            "volume_ratio": round(volume_ratio, 1),
            "atr_pct": round(atr_pct, 2),
            "rsi": round(rsi, 1),
            "st_signal": st_signal,
            "long_score": long_score,
            "short_score": short_score,
            "long_signals": long_signals,
            "short_signals": short_signals,
            "direction": "LONG" if long_score > short_score else "SHORT" if short_score > long_score else "NEUTRAL"
        }
        
    except Exception as e:
        print(f"  Error analyzing {symbol}: {e}")
        return None

def run_test():
    print("=" * 70)
    print("TOMORROW'S INTRADAY STRATEGY - TEST")
    print("=" * 70)
    print(f"Testing {len(TEST_STOCKS)} stocks...")
    print()
    
    results = []
    
    for symbol in TEST_STOCKS:
        print(f"  Analyzing {symbol}...", end=" ")
        result = analyze_stock_for_tomorrow(symbol)
        if result:
            results.append(result)
            print(f"✓ L:{result['long_score']} S:{result['short_score']}")
        else:
            print("✗ No data")
    
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # Sort by score
    long_candidates = sorted([r for r in results if r['long_score'] > r['short_score']], 
                            key=lambda x: x['long_score'], reverse=True)
    short_candidates = sorted([r for r in results if r['short_score'] > r['long_score']], 
                             key=lambda x: x['short_score'], reverse=True)
    
    print(f"\nTotal stocks analyzed: {len(results)}")
    print(f"Stocks with LONG bias: {len(long_candidates)}")
    print(f"Stocks with SHORT bias: {len(short_candidates)}")
    
    # Show all stocks with scores
    print("\n" + "-" * 70)
    print("ALL STOCKS BY SCORE:")
    print("-" * 70)
    print(f"{'Symbol':<12} {'LTP':>10} {'Change':>8} {'Close%':>7} {'Vol':>5} {'ATR%':>6} {'ST':>8} {'L-Score':>8} {'S-Score':>8}")
    print("-" * 70)
    
    for r in sorted(results, key=lambda x: max(x['long_score'], x['short_score']), reverse=True):
        print(f"{r['symbol']:<12} {r['ltp']:>10.2f} {r['change_pct']:>+7.1f}% {r['close_position']:>6.0f}% {r['volume_ratio']:>5.1f} {r['atr_pct']:>5.1f}% {r['st_signal']:>8} {r['long_score']:>8} {r['short_score']:>8}")
    
    # LONG signals (score >= 15)
    print("\n" + "=" * 70)
    print("🟢 LONG SIGNALS (Score >= 15):")
    print("=" * 70)
    
    long_filtered = [r for r in long_candidates if r['long_score'] >= 15]
    if long_filtered:
        for r in long_filtered[:6]:
            print(f"\n{r['symbol']} - Score: {r['long_score']}")
            print(f"  LTP: ₹{r['ltp']:,.2f} | Change: {r['change_pct']:+.1f}% | Close: {r['close_position']:.0f}%")
            print(f"  ATR: {r['atr_pct']:.1f}% | Vol: {r['volume_ratio']:.1f}x | RSI: {r['rsi']:.0f}")
            print(f"  Signals: {', '.join(r['long_signals'][:4])}")
    else:
        print("  No stocks meet threshold (Score >= 15)")
        print("\n  Top 3 by long score (even if below threshold):")
        for r in long_candidates[:3]:
            print(f"    {r['symbol']}: Score {r['long_score']} - {', '.join(r['long_signals'][:3])}")
    
    # SHORT signals (score >= 15)
    print("\n" + "=" * 70)
    print("🔴 SHORT SIGNALS (Score >= 15):")
    print("=" * 70)
    
    short_filtered = [r for r in short_candidates if r['short_score'] >= 15]
    if short_filtered:
        for r in short_filtered[:6]:
            print(f"\n{r['symbol']} - Score: {r['short_score']}")
            print(f"  LTP: ₹{r['ltp']:,.2f} | Change: {r['change_pct']:+.1f}% | Close: {r['close_position']:.0f}%")
            print(f"  ATR: {r['atr_pct']:.1f}% | Vol: {r['volume_ratio']:.1f}x | RSI: {r['rsi']:.0f}")
            print(f"  Signals: {', '.join(r['short_signals'][:4])}")
    else:
        print("  No stocks meet threshold (Score >= 15)")
        print("\n  Top 3 by short score (even if below threshold):")
        for r in short_candidates[:3]:
            print(f"    {r['symbol']}: Score {r['short_score']} - {', '.join(r['short_signals'][:3])}")
    
    print("\n" + "=" * 70)
    print("DIAGNOSIS:")
    print("=" * 70)
    
    if not long_filtered and not short_filtered:
        print("⚠️  No signals generated!")
        print("\nPossible reasons:")
        print("  1. Market was flat today (no strong closes)")
        print("  2. Low volume day")
        print("  3. Stocks not near extremes (week high/low)")
        print("\nTop scoring factors across all stocks:")
        
        # Check what signals are being triggered
        all_long_signals = []
        all_short_signals = []
        for r in results:
            all_long_signals.extend(r['long_signals'])
            all_short_signals.extend(r['short_signals'])
        
        from collections import Counter
        long_counts = Counter(all_long_signals)
        short_counts = Counter(all_short_signals)
        
        print("\n  LONG triggers:")
        for signal, count in long_counts.most_common(5):
            print(f"    {signal}: {count} stocks")
        
        print("\n  SHORT triggers:")
        for signal, count in short_counts.most_common(5):
            print(f"    {signal}: {count} stocks")
    else:
        print(f"✅ Found {len(long_filtered)} LONG and {len(short_filtered)} SHORT signals!")
    
    print("=" * 70)

if __name__ == "__main__":
    run_test()
