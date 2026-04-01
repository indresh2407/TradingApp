"""
Long-Term Strategy Backtester
Tests the long-term investment strategy by going back in time and checking outcomes
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import warnings
warnings.filterwarnings('ignore')

# Stock lists for testing
NIFTY_50 = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
    "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "ULTRACEMCO",
    "TATAMOTORS", "NTPC", "POWERGRID", "M&M", "ONGC",
    "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS", "COALINDIA",
    "BAJAJFINSV", "TECHM", "NESTLEIND", "GRASIM", "DIVISLAB",
    "DRREDDY", "CIPLA", "BRITANNIA", "APOLLOHOSP", "EICHERMOT",
    "HEROMOTOCO", "INDUSINDBK", "HINDALCO", "BPCL", "TATACONSUM"
]


def get_yahoo_symbol(nse_symbol: str) -> str:
    return f"{nse_symbol.upper()}.NS"


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50


def analyze_stock_at_date(symbol: str, analysis_date: datetime, holding_period_days: int) -> Dict[str, Any]:
    """
    Analyze a stock as if we were on analysis_date, then check what actually happened
    """
    try:
        yahoo_symbol = get_yahoo_symbol(symbol)
        ticker = yf.Ticker(yahoo_symbol)
        
        # Get data from before analysis_date (for indicators) to after (for outcome)
        start_date = analysis_date - timedelta(days=400)  # Need history for 200 SMA
        end_date = analysis_date + timedelta(days=holding_period_days + 10)
        
        hist = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if hist.empty or len(hist) < 250:
            return None
        
        # Find the index closest to analysis_date
        hist.index = hist.index.tz_localize(None)
        analysis_idx = hist.index.get_indexer([analysis_date], method='nearest')[0]
        
        if analysis_idx < 200 or analysis_idx >= len(hist) - holding_period_days:
            return None
        
        # Data available on analysis_date
        hist_at_date = hist.iloc[:analysis_idx + 1]
        
        # Current price on analysis date
        entry_price = hist_at_date['Close'].iloc[-1]
        
        # Calculate indicators as of analysis_date
        sma_50 = hist_at_date['Close'].rolling(50).mean().iloc[-1]
        sma_200 = hist_at_date['Close'].rolling(200).mean().iloc[-1]
        rsi = calculate_rsi(hist_at_date['Close'], period=14)
        
        # Performance in the period before analysis
        if len(hist_at_date) > 60:
            past_3m_return = ((entry_price - hist_at_date['Close'].iloc[-60]) / hist_at_date['Close'].iloc[-60]) * 100
        else:
            past_3m_return = 0
        
        # MA signals
        above_50_sma = entry_price > sma_50
        above_200_sma = entry_price > sma_200
        golden_cross = sma_50 > sma_200
        
        # Volume
        avg_volume = hist_at_date['Volume'].rolling(50).mean().iloc[-1]
        recent_volume = hist_at_date['Volume'].tail(10).mean()
        volume_trend = recent_volume / avg_volume if avg_volume > 0 else 1
        
        # 52-week high/low
        high_52w = hist_at_date['High'].tail(252).max()
        low_52w = hist_at_date['Low'].tail(252).min()
        dist_from_52w_high = ((high_52w - entry_price) / high_52w) * 100
        
        # === SCORING (same as strategy) ===
        bullish_score = 0
        bearish_score = 0
        
        # Bullish
        if golden_cross:
            bullish_score += 20
        if above_200_sma:
            bullish_score += 15
        if above_50_sma:
            bullish_score += 10
        if past_3m_return > 10:
            bullish_score += 15
        elif past_3m_return > 0:
            bullish_score += 5
        if rsi < 40:
            bullish_score += 10
        elif 40 <= rsi <= 60:
            bullish_score += 5
        if volume_trend > 1.3:
            bullish_score += 8
        if dist_from_52w_high < 5:
            bullish_score += 15
        
        # Bearish
        if not golden_cross:
            bearish_score += 20
        if not above_200_sma:
            bearish_score += 15
        if not above_50_sma:
            bearish_score += 10
        if past_3m_return < -10:
            bearish_score += 15
        elif past_3m_return < 0:
            bearish_score += 5
        if rsi > 75:
            bearish_score += 12
        if dist_from_52w_high > 20:
            bearish_score += 10
        
        # Determine signal
        if bullish_score >= 35 and bullish_score > bearish_score:
            signal = "BUY"
            score = bullish_score
        elif bearish_score >= 35 and bearish_score > bullish_score:
            signal = "AVOID"
            score = bearish_score
        else:
            signal = "NEUTRAL"
            score = max(bullish_score, bearish_score)
        
        # === CHECK ACTUAL OUTCOME ===
        # What happened after holding_period_days?
        future_data = hist.iloc[analysis_idx + 1 : analysis_idx + 1 + holding_period_days]
        
        if len(future_data) < holding_period_days * 0.8:  # Need at least 80% of days
            return None
        
        exit_price = future_data['Close'].iloc[-1]
        max_price = future_data['High'].max()
        min_price = future_data['Low'].min()
        
        actual_return = ((exit_price - entry_price) / entry_price) * 100
        max_gain = ((max_price - entry_price) / entry_price) * 100
        max_drawdown = ((entry_price - min_price) / entry_price) * 100
        
        # Calculate targets (same as strategy)
        if signal == "BUY":
            if holding_period_days >= 365:
                target_pct = 20
            elif holding_period_days >= 180:
                target_pct = 12
            else:
                target_pct = 8
            stoploss_pct = 10
        else:
            target_pct = 0
            stoploss_pct = 0
        
        # Determine outcome
        if signal == "BUY":
            if actual_return >= target_pct:
                outcome = "TARGET_HIT"
            elif actual_return > 0:
                outcome = "PARTIAL_WIN"
            elif actual_return > -stoploss_pct:
                outcome = "SMALL_LOSS"
            else:
                outcome = "STOPLOSS_HIT"
        elif signal == "AVOID":
            if actual_return < -5:
                outcome = "CORRECT_AVOID"  # Good we avoided
            elif actual_return < 0:
                outcome = "PARTIAL_CORRECT"
            else:
                outcome = "MISSED_GAIN"  # Stock went up, we missed
        else:
            outcome = "NEUTRAL"
        
        return {
            "symbol": symbol,
            "analysis_date": analysis_date.strftime("%Y-%m-%d"),
            "signal": signal,
            "score": score,
            "entry_price": round(entry_price, 2),
            "exit_price": round(exit_price, 2),
            "actual_return": round(actual_return, 2),
            "max_gain": round(max_gain, 2),
            "max_drawdown": round(max_drawdown, 2),
            "target_pct": target_pct,
            "outcome": outcome,
            "golden_cross": golden_cross,
            "above_200_sma": above_200_sma,
            "rsi": round(rsi, 1),
            "past_3m_return": round(past_3m_return, 2)
        }
        
    except Exception as e:
        return None


def backtest_long_term_strategy(
    stocks: List[str],
    analysis_date: datetime,
    holding_period: str = "6 Months"
) -> Dict[str, Any]:
    """
    Backtest the long-term strategy
    """
    period_days = {
        "1 Month": 22,
        "3 Months": 66,
        "6 Months": 132,
        "1 Year": 252
    }
    
    holding_days = period_days.get(holding_period, 132)
    
    print(f"\n{'='*60}")
    print(f"LONG-TERM STRATEGY BACKTEST")
    print(f"{'='*60}")
    print(f"Analysis Date: {analysis_date.strftime('%Y-%m-%d')}")
    print(f"Holding Period: {holding_period} ({holding_days} trading days)")
    print(f"Stocks: {len(stocks)}")
    print(f"{'='*60}\n")
    
    results = []
    buy_signals = []
    avoid_signals = []
    
    for i, symbol in enumerate(stocks):
        print(f"Analyzing {symbol}... ({i+1}/{len(stocks)})", end="\r")
        result = analyze_stock_at_date(symbol, analysis_date, holding_days)
        if result:
            results.append(result)
            if result["signal"] == "BUY":
                buy_signals.append(result)
            elif result["signal"] == "AVOID":
                avoid_signals.append(result)
    
    print(f"\nAnalyzed {len(results)} stocks successfully\n")
    
    # === BUY SIGNALS ANALYSIS ===
    print(f"\n{'='*60}")
    print(f"BUY SIGNALS ANALYSIS ({len(buy_signals)} stocks)")
    print(f"{'='*60}")
    
    if buy_signals:
        target_hit = [r for r in buy_signals if r["outcome"] == "TARGET_HIT"]
        partial_win = [r for r in buy_signals if r["outcome"] == "PARTIAL_WIN"]
        small_loss = [r for r in buy_signals if r["outcome"] == "SMALL_LOSS"]
        stoploss_hit = [r for r in buy_signals if r["outcome"] == "STOPLOSS_HIT"]
        
        winners = target_hit + partial_win
        losers = small_loss + stoploss_hit
        
        win_rate = len(winners) / len(buy_signals) * 100 if buy_signals else 0
        avg_return = sum(r["actual_return"] for r in buy_signals) / len(buy_signals)
        avg_winner = sum(r["actual_return"] for r in winners) / len(winners) if winners else 0
        avg_loser = sum(r["actual_return"] for r in losers) / len(losers) if losers else 0
        
        print(f"\nWIN RATE: {win_rate:.1f}%")
        print(f"  - Target Hit: {len(target_hit)} ({len(target_hit)/len(buy_signals)*100:.1f}%)")
        print(f"  - Partial Win: {len(partial_win)} ({len(partial_win)/len(buy_signals)*100:.1f}%)")
        print(f"  - Small Loss: {len(small_loss)} ({len(small_loss)/len(buy_signals)*100:.1f}%)")
        print(f"  - Stoploss Hit: {len(stoploss_hit)} ({len(stoploss_hit)/len(buy_signals)*100:.1f}%)")
        print(f"\nAVERAGE RETURNS:")
        print(f"  - All BUY signals: {avg_return:+.2f}%")
        print(f"  - Winners only: {avg_winner:+.2f}%")
        print(f"  - Losers only: {avg_loser:+.2f}%")
        
        # Top performers
        buy_signals.sort(key=lambda x: x["actual_return"], reverse=True)
        print(f"\nTOP 5 PERFORMERS:")
        for r in buy_signals[:5]:
            print(f"  {r['symbol']}: {r['actual_return']:+.1f}% (Entry: ₹{r['entry_price']}, Exit: ₹{r['exit_price']})")
        
        print(f"\nWORST 5 PERFORMERS:")
        for r in buy_signals[-5:]:
            print(f"  {r['symbol']}: {r['actual_return']:+.1f}% (Entry: ₹{r['entry_price']}, Exit: ₹{r['exit_price']})")
    else:
        print("No BUY signals generated")
    
    # === AVOID SIGNALS ANALYSIS ===
    print(f"\n{'='*60}")
    print(f"AVOID SIGNALS ANALYSIS ({len(avoid_signals)} stocks)")
    print(f"{'='*60}")
    
    if avoid_signals:
        correct_avoid = [r for r in avoid_signals if r["outcome"] == "CORRECT_AVOID"]
        partial_correct = [r for r in avoid_signals if r["outcome"] == "PARTIAL_CORRECT"]
        missed_gain = [r for r in avoid_signals if r["outcome"] == "MISSED_GAIN"]
        
        correct = correct_avoid + partial_correct
        accuracy = len(correct) / len(avoid_signals) * 100 if avoid_signals else 0
        avg_decline = sum(r["actual_return"] for r in avoid_signals) / len(avoid_signals)
        
        print(f"\nACCURACY: {accuracy:.1f}%")
        print(f"  - Correct Avoid (fell >5%): {len(correct_avoid)} ({len(correct_avoid)/len(avoid_signals)*100:.1f}%)")
        print(f"  - Partial Correct (fell 0-5%): {len(partial_correct)} ({len(partial_correct)/len(avoid_signals)*100:.1f}%)")
        print(f"  - Missed Gain (went up): {len(missed_gain)} ({len(missed_gain)/len(avoid_signals)*100:.1f}%)")
        print(f"\nAVERAGE RETURN of avoided stocks: {avg_decline:+.2f}%")
        
        # Worst decliners (we correctly avoided)
        avoid_signals.sort(key=lambda x: x["actual_return"])
        print(f"\nCORRECTLY AVOIDED (biggest falls):")
        for r in avoid_signals[:5]:
            print(f"  {r['symbol']}: {r['actual_return']:+.1f}% (Good we avoided!)")
        
        print(f"\nMISSED OPPORTUNITIES (went up):")
        for r in [r for r in avoid_signals if r["actual_return"] > 5][:5]:
            print(f"  {r['symbol']}: {r['actual_return']:+.1f}% (Missed gain)")
    else:
        print("No AVOID signals generated")
    
    # === OVERALL SUMMARY ===
    print(f"\n{'='*60}")
    print(f"OVERALL STRATEGY SUMMARY")
    print(f"{'='*60}")
    
    if buy_signals:
        buy_win_rate = len([r for r in buy_signals if r["actual_return"] > 0]) / len(buy_signals) * 100
        buy_avg_return = sum(r["actual_return"] for r in buy_signals) / len(buy_signals)
    else:
        buy_win_rate = 0
        buy_avg_return = 0
    
    if avoid_signals:
        avoid_accuracy = len([r for r in avoid_signals if r["actual_return"] < 0]) / len(avoid_signals) * 100
        avoid_avg_return = sum(r["actual_return"] for r in avoid_signals) / len(avoid_signals)
    else:
        avoid_accuracy = 0
        avoid_avg_return = 0
    
    print(f"\nBUY Signals:")
    print(f"  - Count: {len(buy_signals)}")
    print(f"  - Win Rate (made profit): {buy_win_rate:.1f}%")
    print(f"  - Average Return: {buy_avg_return:+.2f}%")
    
    print(f"\nAVOID Signals:")
    print(f"  - Count: {len(avoid_signals)}")
    print(f"  - Accuracy (correctly avoided): {avoid_accuracy:.1f}%")
    print(f"  - Avg Return of Avoided: {avoid_avg_return:+.2f}%")
    
    # Calculate what would happen if we invested equally in all BUY signals
    if buy_signals:
        portfolio_return = buy_avg_return
        print(f"\n📈 PORTFOLIO PERFORMANCE (equal weight in all BUY signals):")
        print(f"  - Return: {portfolio_return:+.2f}%")
        print(f"  - If invested ₹10,000 in each: ₹{len(buy_signals)*10000:,} → ₹{len(buy_signals)*10000*(1+portfolio_return/100):,.0f}")
        print(f"  - Total Profit/Loss: ₹{len(buy_signals)*10000*portfolio_return/100:,.0f}")
    
    return {
        "analysis_date": analysis_date.strftime("%Y-%m-%d"),
        "holding_period": holding_period,
        "total_stocks": len(results),
        "buy_signals": len(buy_signals),
        "avoid_signals": len(avoid_signals),
        "buy_win_rate": buy_win_rate,
        "buy_avg_return": buy_avg_return,
        "avoid_accuracy": avoid_accuracy,
        "avoid_avg_return": avoid_avg_return,
        "results": results
    }


def run_multiple_backtests():
    """Run backtests for multiple time periods"""
    
    print("\n" + "="*70)
    print("LONG-TERM STRATEGY - MULTIPLE PERIOD BACKTEST")
    print("="*70)
    
    # Test different starting dates
    test_dates = [
        (datetime(2024, 1, 2), "6 Months"),   # Jan 2024, check 6 months later
        (datetime(2024, 4, 1), "3 Months"),   # Apr 2024, check 3 months later
        (datetime(2023, 10, 1), "6 Months"),  # Oct 2023, check 6 months later
        (datetime(2023, 7, 1), "1 Year"),     # Jul 2023, check 1 year later
    ]
    
    all_results = []
    
    for analysis_date, period in test_dates:
        print(f"\n\n{'#'*70}")
        print(f"# BACKTEST: {analysis_date.strftime('%B %Y')} - {period} holding")
        print(f"{'#'*70}")
        
        result = backtest_long_term_strategy(
            stocks=NIFTY_50[:30],  # Top 30 for faster testing
            analysis_date=analysis_date,
            holding_period=period
        )
        all_results.append(result)
    
    # Final Summary
    print("\n\n" + "="*70)
    print("FINAL SUMMARY - ALL BACKTESTS")
    print("="*70)
    
    print(f"\n{'Date':<15} {'Period':<12} {'BUY Win%':<12} {'BUY Avg%':<12} {'AVOID Acc%':<12}")
    print("-"*65)
    
    total_buy_win = 0
    total_buy_return = 0
    total_avoid_acc = 0
    count = 0
    
    for r in all_results:
        print(f"{r['analysis_date']:<15} {r['holding_period']:<12} {r['buy_win_rate']:<12.1f} {r['buy_avg_return']:<+12.2f} {r['avoid_accuracy']:<12.1f}")
        total_buy_win += r['buy_win_rate']
        total_buy_return += r['buy_avg_return']
        total_avoid_acc += r['avoid_accuracy']
        count += 1
    
    print("-"*65)
    print(f"{'AVERAGE':<15} {'':<12} {total_buy_win/count:<12.1f} {total_buy_return/count:<+12.2f} {total_avoid_acc/count:<12.1f}")
    
    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    avg_win = total_buy_win / count
    avg_return = total_buy_return / count
    avg_avoid = total_avoid_acc / count
    
    print(f"\n📊 BUY Signal Performance:")
    print(f"   - Average Win Rate: {avg_win:.1f}%")
    print(f"   - Average Return: {avg_return:+.2f}%")
    if avg_win >= 60:
        print(f"   ✅ Strategy is PROFITABLE")
    elif avg_win >= 50:
        print(f"   ⚠️ Strategy is MARGINALLY profitable")
    else:
        print(f"   ❌ Strategy needs improvement")
    
    print(f"\n📊 AVOID Signal Performance:")
    print(f"   - Average Accuracy: {avg_avoid:.1f}%")
    if avg_avoid >= 60:
        print(f"   ✅ AVOID signals are accurate")
    else:
        print(f"   ⚠️ AVOID signals need improvement")


if __name__ == "__main__":
    print("\nChoose backtest option:")
    print("1. Single period backtest")
    print("2. Multiple period backtest")
    
    choice = input("\nEnter choice (1 or 2): ").strip()
    
    if choice == "2":
        run_multiple_backtests()
    else:
        # Default: 6 months ago
        analysis_date = datetime.now() - timedelta(days=180)
        backtest_long_term_strategy(
            stocks=NIFTY_50,
            analysis_date=analysis_date,
            holding_period="6 Months"
        )
