"""
Stock Analyzer
Analyzes stocks and provides trading tips for intraday
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger


# Stock lists by index/sector
STOCK_LISTS = {
    "NIFTY 50": [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
        "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
        "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
        "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "ULTRACEMCO",
        "TATAMOTORS", "NTPC", "POWERGRID", "M&M", "ONGC",
        "JSWSTEEL", "TATASTEEL", "ADANIENT", "ADANIPORTS", "COALINDIA",
        "BAJAJFINSV", "TECHM", "NESTLEIND", "GRASIM", "DIVISLAB",
        "DRREDDY", "CIPLA", "BRITANNIA", "APOLLOHOSP", "EICHERMOT",
        "HEROMOTOCO", "INDUSINDBK", "HINDALCO", "BPCL", "TATACONSUM",
        "SBILIFE", "HDFCLIFE", "BAJAJ-AUTO", "UPL", "LTIM"
    ],
    "NIFTY 100": [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY",
        "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
        "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
        "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "ULTRACEMCO",
        "TATAMOTORS", "NTPC", "POWERGRID", "M&M", "ONGC",
        "PIDILITIND", "DABUR", "HAVELLS", "SIEMENS", "GODREJCP",
        "BERGEPAINT", "ICICIPRULI", "MARICO", "COLPAL", "PGHH",
        "INDIGO", "DLF", "NAUKRI", "MUTHOOTFIN", "BANDHANBNK",
        "TATAPOWER", "TORNTPHARM", "LUPIN", "BIOCON", "AUROPHARMA"
    ],
    "NIFTY BANK": [
        "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK",
        "INDUSINDBK", "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB",
        "BANKBARODA", "AUBANK", "IDBI", "CANBK", "UNIONBANK", "IOB"
    ],
    "NIFTY IT": [
        "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM",
        "LTIM", "MPHASIS", "COFORGE", "PERSISTENT", "LTTS"
    ],
    "NIFTY AUTO": [
        "TATAMOTORS", "M&M", "MARUTI", "BAJAJ-AUTO", "HEROMOTOCO",
        "EICHERMOT", "TVSMOTOR", "ASHOKLEY", "BHARATFORG", "MRF",
        "BALKRISIND", "BOSCHLTD", "MOTHERSON", "EXIDEIND"
    ],
    "NIFTY PHARMA": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP",
        "LUPIN", "AUROPHARMA", "BIOCON", "TORNTPHARM", "ALKEM",
        "IPCALAB", "GLAND", "LAURUSLABS", "ZYDUSLIFE"
    ],
    "NIFTY METAL": [
        "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "COALINDIA",
        "NMDC", "SAIL", "JINDALSTEL", "NATIONALUM", "MOIL"
    ],
    "NIFTY ENERGY": [
        "RELIANCE", "ONGC", "NTPC", "POWERGRID", "BPCL",
        "IOC", "GAIL", "ADANIGREEN", "TATAPOWER", "ADANIENSOL"
    ],
    # F&O Stocks - Most liquid stocks with options trading
    "FNO_STOCKS": [
        # NIFTY 50 F&O (Most Liquid)
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC", "SBIN",
        "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
        "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "ULTRACEMCO", "TATAMOTORS",
        "NTPC", "POWERGRID", "M&M", "ONGC", "JSWSTEEL", "TATASTEEL", "ADANIENT",
        "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "TECHM", "NESTLEIND", "GRASIM",
        "DIVISLAB", "DRREDDY", "CIPLA", "BRITANNIA", "APOLLOHOSP", "EICHERMOT",
        "HEROMOTOCO", "INDUSINDBK", "HINDALCO", "BPCL", "TATACONSUM", "SBILIFE",
        "HDFCLIFE", "BAJAJ-AUTO", "LTIM",
        # Bank Nifty F&O
        "BANDHANBNK", "FEDERALBNK", "IDFCFIRSTB", "PNB", "BANKBARODA", "AUBANK",
        # Other Popular F&O
        "DLF", "TATAPOWER", "ZOMATO", "VEDL", "SAIL", "NMDC", "JINDALSTEL",
        "IRCTC", "HAL", "BEL", "BHEL", "GAIL", "IOC", "PETRONET",
        "PIDILITIND", "HAVELLS", "VOLTAS", "GODREJCP", "DABUR", "MARICO",
        "LUPIN", "AUROPHARMA", "BIOCON", "ALKEM", "TORNTPHARM",
        "MUTHOOTFIN", "CHOLAFIN", "SHRIRAMFIN", "M&MFIN", "PFC", "RECLTD",
        "MPHASIS", "COFORGE", "PERSISTENT", "LTTS", "TATAELXSI",
        "MRF", "BALKRISIND", "BOSCHLTD", "MOTHERSON", "EXIDEIND",
        "AMBUJACEM", "ACC", "SHREECEM", "RAMCOCEM"
    ],
    # FULL MARKET SCAN - 500+ stocks across all sectors (price > ₹20)
    "FULL MARKET": [
        # Large Caps (NIFTY 50)
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "HINDUNILVR", "ITC", "SBIN", 
        "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "TITAN",
        "BAJFINANCE", "HCLTECH", "WIPRO", "SUNPHARMA", "ULTRACEMCO", "TATAMOTORS", 
        "NTPC", "POWERGRID", "M&M", "ONGC", "JSWSTEEL", "TATASTEEL", "ADANIENT",
        "ADANIPORTS", "COALINDIA", "BAJAJFINSV", "TECHM", "NESTLEIND", "GRASIM",
        "DIVISLAB", "DRREDDY", "CIPLA", "BRITANNIA", "APOLLOHOSP", "EICHERMOT",
        "HEROMOTOCO", "INDUSINDBK", "HINDALCO", "BPCL", "TATACONSUM", "SBILIFE",
        "HDFCLIFE", "BAJAJ-AUTO", "UPL", "LTIM",
        # Mid Caps
        "PIDILITIND", "DABUR", "HAVELLS", "SIEMENS", "GODREJCP", "BERGEPAINT",
        "ICICIPRULI", "MARICO", "COLPAL", "INDIGO", "DLF", "NAUKRI", "MUTHOOTFIN",
        "BANDHANBNK", "TATAPOWER", "TORNTPHARM", "LUPIN", "BIOCON", "AUROPHARMA",
        "SBICARD", "ASTRAL", "VOLTAS", "ESCORTS", "LICHSGFIN", "JUBLFOOD",
        "PAGEIND", "MFSL", "OBEROIRLTY", "GODREJPROP", "BHARATFORG", "ACC",
        "AMBUJACEM", "SHREECEM", "RAMCOCEM", "DALBHARAT", "JKCEMENT", "STARCEMENT",
        # Banking & Finance
        "PNB", "BANKBARODA", "CANBK", "UNIONBANK", "IOB", "IDBI", "CENTRALBK",
        "MAHABANK", "INDIANB", "UCOBANK", "J&KBANK", "KTKBANK", "DCBBANK",
        "RBLBANK", "UJJIVANSFB", "EQUITASBNK", "AUBANK", "CUB", "KARURVYSYA",
        "FEDERALBNK", "IDFCFIRSTB", "YESBANK", "MANAPPURAM", "IIFL", "CHOLAFIN",
        "BAJAJHLDNG", "LICHSGFIN", "CANFINHOME", "HOMEFIRST", "AAVAS", "APTUS",
        "SHRIRAMFIN", "SUNDARMFIN", "M&MFIN", "PNBHOUSING", "IBULHSGFIN",
        # IT & Tech
        "MPHASIS", "COFORGE", "PERSISTENT", "LTTS", "MINDTREE", "NIITLTD",
        "HAPPSTMNDS", "ROUTE", "TANLA", "MASTEK", "SONATSOFTW", "TATAELXSI",
        "KPITTECH", "CYIENT", "ZENSAR", "BIRLASOFT", "NEWGEN", "INTELLECT",
        "LATENTVIEW", "DATAPATTNS", "MAPMY", "ZOMATO", "NYKAA", "PAYTM",
        "POLICYBZR", "DELHIVERY", "CARTRADE",
        # Pharma & Healthcare
        "ALKEM", "IPCALAB", "GLAND", "LAURUSLABS", "ZYDUSLIFE", "GLENMARK",
        "NATCOPHARM", "GRANULES", "LALPATHLAB", "METROPOLIS", "THYROCARE",
        "MAXHEALTH", "FORTIS", "NARAYANA", "SYNGENE", "ABBOTINDIA", "PFIZER",
        "GLAXO", "SANOFI", "ASTRAZEN", "JBCHEPHARM", "SOLARA", "SUVEN",
        "STRIDES", "ERIS", "AJANTPHARM", "CAPLIPOINT", "AARTIIND",
        # Auto & Auto Ancillary
        "TVSMOTOR", "ASHOKLEY", "MRF", "BALKRISIND", "BOSCHLTD", "MOTHERSON",
        "EXIDEIND", "AMARAJABAT", "APOLLOTYRE", "CEAT", "JKTYRE", "SWARAJENG",
        "SCHAEFFLER", "SUNDRMFAST", "ENDURANCE", "SUPRAJIT", "MAHINDCIE",
        "CRAFTSMAN", "LUMAXTECH", "MINDA", "VARROC", "UNOMINDA",
        # Metal & Mining
        "VEDL", "NMDC", "SAIL", "JINDALSTEL", "NATIONALUM", "MOIL", "GMRINFRA",
        "JSL", "RATNAMANI", "WELCORP", "SARDAEN", "GPPL", "KIOCL", "FCSSOFT",
        # Oil & Gas
        "IOC", "GAIL", "PETRONET", "HINDPETRO", "MRPL", "CHENNPETRO", "GSPL",
        "IGL", "MGL", "GUJGASLTD", "ATGL", "AEGISCHEM", "DEEPAKFERT", "GNFC",
        # Power & Utilities
        "ADANIGREEN", "TATAPOWER", "ADANIENSOL", "NHPC", "SJVN", "TORNTPOWER",
        "CESC", "JSWENERGY", "NLCINDIA", "RPOWER", "GIPCL", "JPPOWER",
        "HUDCO", "IRFC", "PFC", "RECLTD", "IREDA",
        # Infrastructure & Construction
        "IRB", "ASHOKA", "KNRCON", "PNC", "HCC", "NCC", "JKIL", "GPIL",
        "AHLUCONT", "CAPACITE", "JMCPROJECT", "KOLTEPATIL", "PRESTIGE",
        "BRIGADE", "SOBHA", "SUNTECK", "MAHLIFE", "PURVA", "LODHA", "SIGNATURE",
        # Cement
        "JKLAKSHMI", "HERITAGEFOOD", "HEIDELBERG", "SAGCEM", "PRISMJONN",
        # FMCG & Consumer
        "TATACONSUM", "MARICO", "EMAMILTD", "JYOTHYLAB", "ZYDUSWELL", "VGUARD",
        "SYMPHONY", "BLUESTARCO", "CROMPTON", "HAVELLS", "POLYCAB", "KEI",
        "RAJESHEXPO", "VAIBHAVGBL", "VBL", "RADICO", "GLOBUSSPR", "VENKEYS",
        # Textiles & Apparel
        "PAGEIND", "ARVIND", "RAYMOND", "SIYARAM", "GOKALDAS", "KPRMILL",
        "VARDHACRLC", "TRIDENT", "WELSPUNIND", "HIMATSEIDE", "NITIRAJ",
        # Chemicals & Fertilizers
        "PIIND", "ATUL", "NAVINFLUOR", "SRF", "DEEPAKNTR", "FINEORG",
        "CLEAN", "GALAXY", "AARTI", "VINATI", "LXCHEM", "TATACHEM",
        "CHEMPLASTS", "ROSSARI", "ACRYSIL", "ALKYLAMINE", "ANURAS", "BALRAMCHIN",
        # Real Estate
        "PHOENIX", "MAHINDRA", "RUSTOMJEE", "RAYMOND", "MAHINDRACIE",
        # Retail & E-commerce
        "TRENT", "SHOPERSTOP", "VMART", "ABFRL", "MANYAVAR", "CAMPUS",
        "METROBRAND", "DEVYANI", "SAPPHIRE", "WESTLIFE", "JUBLFOOD", "BURGERKING",
        # Telecom & Media
        "BHARTIARTL", "IDEA", "TTML", "HATHWAY", "DEN", "NAZARA", "NETWEB",
        "SUNTV", "TV18BRDCST", "NETWORK18", "ZEEL", "PVRINOX", "INOXLEISUR",
        # Logistics & Transport
        "BLUEDART", "MAHSEAMLES", "CONCOR", "GATEWAY", "AEGISLOG", "TCI",
        "VRL", "MAHLOG", "ALLCARGO", "GESHIP", "SCI", "SHREYAS", "GRINFRA",
        # Hotels & Tourism
        "INDHOTEL", "LEMONTRE", "CHALET", "EIH", "EIHOTEL", "THOTEL",
        "TAJGVK", "MAHINDHOLIDAY", "THOMASCOOK",
        # Agriculture & Sugar
        "UPL", "PIIND", "RALLIS", "BAYER", "DHANUKA", "SHARDACROP",
        "BALRAMCHIN", "RENUKA", "DWARIKESH", "TRIVENI", "BAJAJHIND", "AVANTIFEED",
        # Capital Goods & Engineering
        "ABB", "HONAUT", "SIEMENS", "CGPOWER", "CUMMINSIND", "THERMAX",
        "GRINDWELL", "CARBORUNIV", "ELGIEQUIP", "ATFL", "TIINDIA", "BEL",
        "BHEL", "BEML", "HAL", "BDL", "COCHINSHIP", "GRSE", "MAZAGON", "MIDHANI",
        # Insurance
        "ICICIGI", "ICICIPRULI", "HDFCLIFE", "SBILIFE", "LICI", "STARHEALTH",
        "NIACL", "GICRE", "MAXLIFE",
        # Diversified
        "IEX", "BSE", "MCX", "CAMS", "KFINTECH", "CDSL", "ANGEL", "IIFLSEC",
        "MOTILALOFS", "JMFINANCIL", "GEOJITFSL", "CENTRUM",
        # Small Caps with high volatility potential
        "IRCTC", "RVNL", "IRCON", "RAILTEL", "RITES", "NBCC", "MOIL",
        "NFL", "RCF", "FACT", "GSFC", "GNFC", "GMDCLTD", "GMDC",
        "NATIONALUM", "HINDZINC", "HZL", "APLAPOLLO", "JSWHL", "JSWINFRA",
        "JIOFIN", "JIOFINSERV", "JIOMONEY", "BAJAJHLDNG", "BAJAJCON",
        "MAHSCOOTER", "MAHSEAMLES", "MAHLOG", "VSTIND", "GODFRYPHLP",
        "WHIRLPOOL", "TTKPRESTIG", "KAJARIACER", "CENTURYTEX", "WOCKPHARMA"
    ]
}

# Default stocks for analysis
ANALYSIS_STOCKS = STOCK_LISTS["NIFTY 50"][:20]  # Top 20 from NIFTY 50


def get_stocks_for_index(index_name: str) -> List[str]:
    """Get stock list for a given index"""
    return STOCK_LISTS.get(index_name, ANALYSIS_STOCKS)


def get_yahoo_symbol(nse_symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance symbol"""
    return f"{nse_symbol.upper()}.NS"


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI - returns last value"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi.iloc[-1] if not rsi.empty else 50


def calculate_rsi_series(prices: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI - returns full series"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_momentum(prices: pd.Series, period: int = 10) -> float:
    """Calculate price momentum percentage"""
    if len(prices) < period:
        return 0
    return ((prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]) * 100


def calculate_roc(prices: pd.Series, period: int = 10) -> Dict[str, Any]:
    """
    Calculate Rate of Change (ROC) - measures momentum/speed of price movement
    
    Returns:
        Dict with ROC value, signal, and divergence detection
    """
    if len(prices) < period + 5:
        return {"roc": 0, "signal": "NEUTRAL", "divergence": False, "weakening": False}
    
    # ROC = ((Current Price - Price n periods ago) / Price n periods ago) * 100
    roc = ((prices.iloc[-1] - prices.iloc[-period]) / prices.iloc[-period]) * 100
    prev_roc = ((prices.iloc[-2] - prices.iloc[-period-1]) / prices.iloc[-period-1]) * 100
    
    # Check for divergence (price making new highs but ROC making lower highs)
    price_higher = prices.iloc[-1] > prices.iloc[-5:-1].max()
    roc_lower = roc < prev_roc
    bearish_divergence = price_higher and roc_lower and roc > 0
    
    # Check for bullish divergence (price making new lows but ROC making higher lows)
    price_lower = prices.iloc[-1] < prices.iloc[-5:-1].min()
    roc_higher = roc > prev_roc
    bullish_divergence = price_lower and roc_higher and roc < 0
    
    # Momentum weakening
    weakening = abs(roc) < abs(prev_roc)
    
    if roc > 2:
        signal = "BULLISH"
    elif roc < -2:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {
        "roc": round(roc, 2),
        "prev_roc": round(prev_roc, 2),
        "signal": signal,
        "bearish_divergence": bearish_divergence,
        "bullish_divergence": bullish_divergence,
        "weakening": weakening
    }


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, 
                  di_length: int = 10, adx_smoothing: int = 10) -> Dict[str, Any]:
    """
    Calculate ADX (Average Directional Index) - measures trend strength
    
    Parameters:
        di_length: Period for DI calculation (default 7 for faster response)
        adx_smoothing: Period for ADX smoothing (default 7 for faster response)
    
    ADX > 25 = Strong trend
    ADX < 20 = Weak/No trend
    ADX falling = Trend weakening (prepare for reversal)
    
    Returns:
        Dict with ADX value, trend strength, and direction
    """
    if len(close) < di_length + adx_smoothing + 5:
        return {
            "adx": 0, "trend_strength": "WEAK", "weakening": False, 
            "plus_di": 0, "minus_di": 0, "prev_plus_di": 0, "prev_minus_di": 0,
            "di_gap": 0, "prev_di_gap": 0, "di_gap_change": 0,
            "di_gap_narrowing": False, "di_gap_widening": False,
            "rising": False, "flat": True, "no_trend": True,
            "adx_change": 0, "prev_adx": 0, "trend_direction": "NEUTRAL"
        }
    
    # Calculate True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=di_length).mean()
    
    # Calculate +DM and -DM
    plus_dm = high.diff()
    minus_dm = -low.diff()
    
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
    
    # Smooth the DMs using DI length
    plus_dm_smooth = plus_dm.rolling(window=di_length).mean()
    minus_dm_smooth = minus_dm.rolling(window=di_length).mean()
    
    # Calculate +DI and -DI
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)
    
    # Calculate DX and ADX (smoothed with adx_smoothing period)
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 0.0001)
    adx = dx.rolling(window=adx_smoothing).mean()
    
    current_adx = adx.iloc[-1] if not adx.empty else 0
    prev_adx = adx.iloc[-2] if len(adx) > 1 else current_adx
    
    # Determine trend strength
    if current_adx >= 40:
        trend_strength = "VERY_STRONG"
    elif current_adx >= 25:
        trend_strength = "STRONG"
    elif current_adx >= 20:
        trend_strength = "MODERATE"
    else:
        trend_strength = "WEAK"
    
    # ADX direction - CRITICAL for signal quality
    adx_change = current_adx - prev_adx
    
    # ADX rising = trend strengthening (GOOD for entry)
    rising = adx_change > 0.5  # ADX increasing by more than 0.5
    
    # ADX falling = trend weakening (BAD for entry)
    weakening = adx_change < -0.5 and current_adx > 15  # ADX decreasing
    
    # ADX flat = no momentum in trend (CAUTION)
    flat = abs(adx_change) <= 0.5
    
    # No trend at all - ADX too low
    no_trend = current_adx < 20
    
    # Get current and previous DI values for gap analysis
    current_plus_di = plus_di.iloc[-1] if not plus_di.empty else 0
    current_minus_di = minus_di.iloc[-1] if not minus_di.empty else 0
    prev_plus_di = plus_di.iloc[-2] if len(plus_di) > 1 else current_plus_di
    prev_minus_di = minus_di.iloc[-2] if len(minus_di) > 1 else current_minus_di
    
    # Calculate DI gap (difference between dominant and non-dominant DI)
    # For bearish: -DI should be > +DI, gap = -DI minus +DI
    # For bullish: +DI should be > -DI, gap = +DI minus -DI
    current_di_gap = abs(current_plus_di - current_minus_di)
    prev_di_gap = abs(prev_plus_di - prev_minus_di)
    di_gap_change = current_di_gap - prev_di_gap
    di_gap_narrowing = di_gap_change < -1.0  # Gap shrinking by more than 1 point
    di_gap_widening = di_gap_change > 1.0   # Gap growing by more than 1 point
    
    return {
        "adx": round(current_adx, 1),
        "prev_adx": round(prev_adx, 1),
        "adx_change": round(adx_change, 1),
        "trend_strength": trend_strength,
        "rising": rising,
        "weakening": weakening,
        "flat": flat,
        "no_trend": no_trend,
        "plus_di": round(current_plus_di, 1),
        "minus_di": round(current_minus_di, 1),
        "prev_plus_di": round(prev_plus_di, 1),
        "prev_minus_di": round(prev_minus_di, 1),
        "di_gap": round(current_di_gap, 1),
        "prev_di_gap": round(prev_di_gap, 1),
        "di_gap_change": round(di_gap_change, 1),
        "di_gap_narrowing": di_gap_narrowing,
        "di_gap_widening": di_gap_widening,
        "trend_direction": "BULLISH" if current_plus_di > current_minus_di else "BEARISH"
    }


def calculate_bb_advanced(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
    """
    Advanced Bollinger Band analysis with Squeeze and Walk detection
    
    - Squeeze: Bands narrowing (volatility compression, breakout coming)
    - Walk: Price hugging outer band (strong trend)
    - Curl: Price failing to touch outer band and curling toward middle (reversal sign)
    
    Returns:
        Dict with BB values and advanced signals
    """
    if len(close) < period + 5:
        return {
            "middle": close.iloc[-1], "upper": close.iloc[-1], "lower": close.iloc[-1],
            "squeeze": False, "walking_upper": False, "walking_lower": False,
            "curling_down": False, "curling_up": False, "percent_b": 50
        }
    
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    
    current_price = close.iloc[-1]
    prev_price = close.iloc[-2]
    
    current_middle = middle.iloc[-1]
    current_upper = upper.iloc[-1]
    current_lower = lower.iloc[-1]
    
    # Bandwidth for squeeze detection
    bandwidth = (current_upper - current_lower) / current_middle * 100
    prev_bandwidth = (upper.iloc[-5] - lower.iloc[-5]) / middle.iloc[-5] * 100 if len(upper) > 5 else bandwidth
    
    # Squeeze: bandwidth contracting (volatility compression)
    squeeze = bandwidth < prev_bandwidth * 0.8
    
    # Percent B: where price is within the bands (0 = lower, 100 = upper)
    percent_b = ((current_price - current_lower) / (current_upper - current_lower)) * 100 if (current_upper - current_lower) > 0 else 50
    prev_percent_b = ((prev_price - lower.iloc[-2]) / (upper.iloc[-2] - lower.iloc[-2])) * 100 if len(upper) > 1 else 50
    
    # Walking the bands (price staying near outer bands in strong trend)
    walking_upper = percent_b > 80 and close.tail(3).min() > middle.iloc[-3:].max()
    walking_lower = percent_b < 20 and close.tail(3).max() < middle.iloc[-3:].min()
    
    # Curling: Price failing to touch outer band and moving toward middle
    # Curling down: Was near upper band, now moving toward middle
    curling_down = prev_percent_b > 70 and percent_b < prev_percent_b and percent_b < 70
    # Curling up: Was near lower band, now moving toward middle
    curling_up = prev_percent_b < 30 and percent_b > prev_percent_b and percent_b > 30
    
    # Signal based on position
    if percent_b > 100:
        signal = "OVERBOUGHT"
    elif percent_b < 0:
        signal = "OVERSOLD"
    elif percent_b > 80:
        signal = "BULLISH"
    elif percent_b < 20:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {
        "middle": round(current_middle, 2),
        "upper": round(current_upper, 2),
        "lower": round(current_lower, 2),
        "bandwidth": round(bandwidth, 2),
        "percent_b": round(percent_b, 1),
        "signal": signal,
        "squeeze": squeeze,
        "walking_upper": walking_upper,
        "walking_lower": walking_lower,
        "curling_down": curling_down,
        "curling_up": curling_up
    }


def calculate_vwap_distance(high: pd.Series, low: pd.Series, close: pd.Series, 
                            volume: pd.Series) -> Dict[str, Any]:
    """
    Calculate VWAP with Standard Deviation Bands (Rubber Band Effect)
    
    Price at 2nd or 3rd StdDev from VWAP = overextended, likely to snap back
    
    Returns:
        Dict with VWAP, distance, and overextension signals
    """
    if len(close) < 20:
        return {
            "vwap": close.iloc[-1], "distance_pct": 0, "overextended_up": False,
            "overextended_down": False, "band_1_upper": close.iloc[-1], "band_2_upper": close.iloc[-1]
        }
    
    typical_price = (high + low + close) / 3
    cumulative_tp_vol = (typical_price * volume).cumsum()
    cumulative_vol = volume.cumsum()
    vwap = cumulative_tp_vol / cumulative_vol
    
    current_vwap = vwap.iloc[-1]
    current_price = close.iloc[-1]
    
    # Calculate VWAP Standard Deviation
    squared_diff = ((typical_price - vwap) ** 2 * volume).cumsum()
    variance = squared_diff / cumulative_vol
    vwap_std = variance ** 0.5
    current_std = vwap_std.iloc[-1]
    
    # VWAP Bands
    band_1_upper = current_vwap + current_std
    band_1_lower = current_vwap - current_std
    band_2_upper = current_vwap + 2 * current_std
    band_2_lower = current_vwap - 2 * current_std
    band_3_upper = current_vwap + 3 * current_std
    band_3_lower = current_vwap - 3 * current_std
    
    # Distance from VWAP as percentage
    distance_pct = ((current_price - current_vwap) / current_vwap) * 100
    
    # Overextension detection (rubber band effect)
    overextended_up = current_price >= band_2_upper
    overextended_down = current_price <= band_2_lower
    extreme_up = current_price >= band_3_upper
    extreme_down = current_price <= band_3_lower
    
    # Signal
    if extreme_up:
        signal = "EXTREME_OVERBOUGHT"
    elif extreme_down:
        signal = "EXTREME_OVERSOLD"
    elif overextended_up:
        signal = "OVERBOUGHT"
    elif overextended_down:
        signal = "OVERSOLD"
    elif current_price > band_1_upper:
        signal = "BULLISH"
    elif current_price < band_1_lower:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    return {
        "vwap": round(current_vwap, 2),
        "distance_pct": round(distance_pct, 2),
        "band_1_upper": round(band_1_upper, 2),
        "band_1_lower": round(band_1_lower, 2),
        "band_2_upper": round(band_2_upper, 2),
        "band_2_lower": round(band_2_lower, 2),
        "overextended_up": overextended_up,
        "overextended_down": overextended_down,
        "extreme_up": extreme_up,
        "extreme_down": extreme_down,
        "signal": signal
    }


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    """Calculate Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr.iloc[-1] if not atr.empty else 0


def calculate_volatility(hist: pd.DataFrame, period: int = 20) -> Dict[str, Any]:
    """
    Calculate comprehensive volatility metrics for a stock
    
    Returns:
        Dict with:
        - atr_pct: ATR as percentage of price
        - daily_range_pct: Average daily range as percentage
        - volatility_score: 0-100 score (higher = more volatile)
        - volatility_rank: "HIGH", "MEDIUM", "LOW"
        - historical_vol: Standard deviation of returns (annualized)
        - is_volatile: True if stock is considered highly volatile
    """
    if hist.empty or len(hist) < period:
        return {
            "atr_pct": 0,
            "daily_range_pct": 0,
            "volatility_score": 0,
            "volatility_rank": "LOW",
            "historical_vol": 0,
            "is_volatile": False,
            "volatility_percentile": 0
        }
    
    close = hist['Close']
    high = hist['High']
    low = hist['Low']
    ltp = close.iloc[-1]
    
    # 1. ATR as percentage of price
    atr = calculate_atr(high, low, close, period=min(14, len(hist)-1))
    atr_pct = (atr / ltp) * 100 if ltp > 0 else 0
    
    # 2. Average Daily Range (High - Low) as percentage
    daily_ranges = ((high - low) / close) * 100
    avg_daily_range_pct = daily_ranges.tail(period).mean()
    
    # 3. Historical Volatility (Standard Deviation of returns, annualized)
    returns = close.pct_change().dropna()
    if len(returns) > 5:
        daily_std = returns.tail(period).std()
        historical_vol = daily_std * (252 ** 0.5) * 100  # Annualized
    else:
        historical_vol = 0
    
    # 4. Recent vs Historical volatility (is it expanding?)
    recent_vol = returns.tail(5).std() if len(returns) >= 5 else 0
    avg_vol = returns.tail(20).std() if len(returns) >= 20 else recent_vol
    vol_expansion = recent_vol > avg_vol * 1.2  # Recent vol 20% higher than average
    
    # 5. Intraday volatility (for 5-min data)
    if len(hist) > 50:
        intraday_ranges = ((hist['High'].tail(50) - hist['Low'].tail(50)) / hist['Close'].tail(50)) * 100
        intraday_vol = intraday_ranges.mean()
    else:
        intraday_vol = avg_daily_range_pct
    
    # === VOLATILITY SCORE (0-100) ===
    # Higher score = more volatile = better for intraday
    score = 0
    
    # ATR contribution (0-30 points)
    # ATR > 2% = very volatile, ATR < 0.5% = low volatility
    if atr_pct >= 3:
        score += 30
    elif atr_pct >= 2:
        score += 25
    elif atr_pct >= 1.5:
        score += 20
    elif atr_pct >= 1:
        score += 15
    elif atr_pct >= 0.7:
        score += 10
    else:
        score += 5
    
    # Daily Range contribution (0-30 points)
    if avg_daily_range_pct >= 4:
        score += 30
    elif avg_daily_range_pct >= 3:
        score += 25
    elif avg_daily_range_pct >= 2:
        score += 20
    elif avg_daily_range_pct >= 1.5:
        score += 15
    elif avg_daily_range_pct >= 1:
        score += 10
    else:
        score += 5
    
    # Historical volatility contribution (0-25 points)
    if historical_vol >= 50:
        score += 25
    elif historical_vol >= 40:
        score += 20
    elif historical_vol >= 30:
        score += 15
    elif historical_vol >= 20:
        score += 10
    else:
        score += 5
    
    # Volatility expansion bonus (0-15 points)
    if vol_expansion:
        score += 15
    
    # Determine rank
    if score >= 70:
        rank = "HIGH"
        is_volatile = True
    elif score >= 45:
        rank = "MEDIUM"
        is_volatile = True
    else:
        rank = "LOW"
        is_volatile = False
    
    return {
        "atr_pct": round(atr_pct, 2),
        "daily_range_pct": round(avg_daily_range_pct, 2),
        "volatility_score": score,
        "volatility_rank": rank,
        "historical_vol": round(historical_vol, 1),
        "is_volatile": is_volatile,
        "vol_expansion": vol_expansion,
        "intraday_vol": round(intraday_vol, 2)
    }


def calculate_support_resistance(hist: pd.DataFrame) -> Tuple[float, float]:
    """Calculate recent support and resistance levels"""
    recent = hist.tail(10)
    support = recent['Low'].min()
    resistance = recent['High'].max()
    return support, resistance


def get_market_time_context() -> Dict[str, Any]:
    """
    Get market time context for intraday trading
    
    Indian Market Hours: 9:15 AM - 3:30 PM
    Intraday Square-off: 3:15-3:20 PM
    
    Returns:
        Dict with time info, target multiplier, and warnings
    """
    now = datetime.now()
    current_hour = now.hour
    current_minute = now.minute
    current_time_mins = current_hour * 60 + current_minute  # Minutes since midnight
    
    market_open = 9 * 60 + 15   # 9:15 AM = 555 mins
    market_close = 15 * 60 + 30  # 3:30 PM = 930 mins
    squareoff_time = 15 * 60 + 15  # 3:15 PM = 915 mins
    
    # Calculate time remaining until square-off
    time_to_squareoff = squareoff_time - current_time_mins
    time_to_close = market_close - current_time_mins
    
    # Determine trading phase
    if current_time_mins < market_open:
        phase = "PRE_MARKET"
        can_trade = False
        target_multiplier = 1.0
        warning = "Market not yet open"
    elif current_time_mins >= squareoff_time:
        phase = "SQUARE_OFF"
        can_trade = False
        target_multiplier = 0
        warning = "⚠️ Square-off time! Close all intraday positions"
    elif current_time_mins >= 15 * 60:  # After 3:00 PM
        phase = "CLOSING"
        can_trade = False
        target_multiplier = 0.3
        warning = "⚠️ Market closing soon - no new positions"
    elif current_time_mins >= 14 * 60 + 30:  # After 2:30 PM
        phase = "LATE"
        can_trade = True
        target_multiplier = 0.5  # Reduce targets by 50%
        warning = "⏰ Less than 1 hour to square-off - scalp only"
    elif current_time_mins >= 14 * 60:  # After 2:00 PM
        phase = "AFTERNOON_LATE"
        can_trade = True
        target_multiplier = 0.7  # Reduce targets by 30%
        warning = "Reduced targets - market closing in ~1.5 hours"
    elif current_time_mins >= 12 * 60:  # After 12:00 PM
        phase = "AFTERNOON"
        can_trade = True
        target_multiplier = 0.9
        warning = None
    elif current_time_mins >= 10 * 60:  # After 10:00 AM (best trading time)
        phase = "PRIME"
        can_trade = True
        target_multiplier = 1.0
        warning = None
    else:  # 9:15 - 10:00 AM
        phase = "OPENING"
        can_trade = True
        target_multiplier = 0.8  # Slightly reduced due to opening volatility
        warning = "Opening hour - expect volatility"
    
    return {
        "current_time": now.strftime("%H:%M"),
        "phase": phase,
        "can_trade": can_trade,
        "target_multiplier": target_multiplier,
        "time_to_squareoff_mins": max(0, time_to_squareoff),
        "time_to_close_mins": max(0, time_to_close),
        "warning": warning,
        "is_market_hours": market_open <= current_time_mins < market_close
    }


def calculate_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> Dict[str, Any]:
    """
    Calculate VWAP (Volume Weighted Average Price) for intraday trading
    
    VWAP = Cumulative(Typical Price * Volume) / Cumulative(Volume)
    Typical Price = (High + Low + Close) / 3
    
    Returns:
        Dict with vwap value, signal, and distance from current price
    """
    try:
        # Calculate typical price
        typical_price = (high + low + close) / 3
        
        # Calculate VWAP (cumulative)
        cumulative_tp_vol = (typical_price * volume).cumsum()
        cumulative_vol = volume.cumsum()
        
        vwap = cumulative_tp_vol / cumulative_vol
        
        # Get current values
        current_vwap = vwap.iloc[-1] if not vwap.empty else close.iloc[-1]
        current_price = close.iloc[-1]
        
        # Calculate distance from VWAP
        vwap_distance = ((current_price - current_vwap) / current_vwap) * 100
        
        # Determine signal
        # Price above VWAP = Bullish (buyers paying more than average)
        # Price below VWAP = Bearish (sellers in control)
        if current_price > current_vwap * 1.002:  # 0.2% above
            signal = "BULLISH"
            strength = min(3, int(abs(vwap_distance) / 0.3))  # 1-3 strength
        elif current_price < current_vwap * 0.998:  # 0.2% below
            signal = "BEARISH"
            strength = min(3, int(abs(vwap_distance) / 0.3))
        else:
            signal = "NEUTRAL"
            strength = 0
        
        # Check if price just crossed VWAP (potential entry signal)
        prev_price = close.iloc[-2] if len(close) > 1 else current_price
        prev_vwap = vwap.iloc[-2] if len(vwap) > 1 else current_vwap
        
        crossed_above = (prev_price <= prev_vwap) and (current_price > current_vwap)
        crossed_below = (prev_price >= prev_vwap) and (current_price < current_vwap)
        
        return {
            "vwap": round(current_vwap, 2),
            "signal": signal,
            "strength": strength,
            "distance_pct": round(vwap_distance, 2),
            "crossed_above": crossed_above,
            "crossed_below": crossed_below,
            "is_bullish": signal == "BULLISH"
        }
    except Exception as e:
        logger.error(f"VWAP calculation error: {e}")
        return {
            "vwap": 0,
            "signal": "NEUTRAL",
            "strength": 0,
            "distance_pct": 0,
            "crossed_above": False,
            "crossed_below": False,
            "is_bullish": False
        }


def calculate_supertrend(high: pd.Series, low: pd.Series, close: pd.Series, 
                         period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series, str]:
    """
    Calculate Supertrend Indicator
    
    Args:
        high: High prices series
        low: Low prices series
        close: Close prices series
        period: ATR period (default 10)
        multiplier: ATR multiplier (default 3.0)
    
    Returns:
        Tuple of (supertrend_line, direction_series, current_signal)
        direction: 1 = Bullish (price above supertrend), -1 = Bearish (price below)
        current_signal: "BULLISH" or "BEARISH"
    """
    # Calculate ATR
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    # Calculate basic upper and lower bands
    hl2 = (high + low) / 2
    basic_upper = hl2 + (multiplier * atr)
    basic_lower = hl2 - (multiplier * atr)
    
    # Initialize final bands
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    supertrend = pd.Series(index=close.index, dtype=float)
    direction = pd.Series(index=close.index, dtype=int)
    
    # Calculate final bands and supertrend
    for i in range(period, len(close)):
        # Final Upper Band
        if basic_upper.iloc[i] < final_upper.iloc[i-1] or close.iloc[i-1] > final_upper.iloc[i-1]:
            final_upper.iloc[i] = basic_upper.iloc[i]
        else:
            final_upper.iloc[i] = final_upper.iloc[i-1]
        
        # Final Lower Band
        if basic_lower.iloc[i] > final_lower.iloc[i-1] or close.iloc[i-1] < final_lower.iloc[i-1]:
            final_lower.iloc[i] = basic_lower.iloc[i]
        else:
            final_lower.iloc[i] = final_lower.iloc[i-1]
        
        # Supertrend
        if i == period:
            # Initialize
            if close.iloc[i] <= final_upper.iloc[i]:
                supertrend.iloc[i] = final_upper.iloc[i]
                direction.iloc[i] = -1  # Bearish
            else:
                supertrend.iloc[i] = final_lower.iloc[i]
                direction.iloc[i] = 1  # Bullish
        else:
            # Check for trend change
            if supertrend.iloc[i-1] == final_upper.iloc[i-1]:
                # Was bearish
                if close.iloc[i] > final_upper.iloc[i]:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1  # Turned bullish
                else:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1  # Still bearish
            else:
                # Was bullish
                if close.iloc[i] < final_lower.iloc[i]:
                    supertrend.iloc[i] = final_upper.iloc[i]
                    direction.iloc[i] = -1  # Turned bearish
                else:
                    supertrend.iloc[i] = final_lower.iloc[i]
                    direction.iloc[i] = 1  # Still bullish
    
    # Get current signal
    current_direction = direction.iloc[-1] if not direction.empty else 0
    current_signal = "BULLISH" if current_direction == 1 else "BEARISH"
    
    # Check for recent crossover (signal change)
    prev_direction = direction.iloc[-2] if len(direction) > 1 else current_direction
    signal_change = current_direction != prev_direction
    
    return supertrend, direction, current_signal, signal_change


def calculate_supertrend_simple(high: pd.Series, low: pd.Series, close: pd.Series,
                                  period: int = 10, multiplier: float = 3.0) -> Dict[str, Any]:
    """
    Simplified Supertrend calculation returning key values
    
    Returns dict with:
    - signal: "BULLISH" or "BEARISH"
    - value: Current supertrend value
    - crossover: True if signal just changed
    - distance_pct: Distance from price to supertrend line (%)
    """
    try:
        supertrend, direction, signal, crossover = calculate_supertrend(high, low, close, period, multiplier)
        
        st_value = supertrend.iloc[-1] if not supertrend.empty else close.iloc[-1]
        current_price = close.iloc[-1]
        distance_pct = ((current_price - st_value) / st_value) * 100 if st_value > 0 else 0
        
        return {
            "signal": signal,
            "value": round(st_value, 2),
            "crossover": crossover,
            "distance_pct": round(distance_pct, 2),
            "is_bullish": signal == "BULLISH"
        }
    except Exception as e:
        logger.error(f"Supertrend calculation error: {e}")
        return {
            "signal": "NEUTRAL",
            "value": 0,
            "crossover": False,
            "distance_pct": 0,
            "is_bullish": False
        }


def analyze_gap(open_price: float, prev_close: float, current_price: float, prev_high: float, prev_low: float) -> Dict[str, Any]:
    """
    Analyze gap at market open
    
    Returns:
        gap_pct: Gap percentage
        gap_type: "GAP_UP", "GAP_DOWN", or "NO_GAP"
        gap_status: "FILLING", "HOLDING", or "EXTENDING"
        intraday_bias: Suggested trading direction based on gap
    """
    gap_pct = ((open_price - prev_close) / prev_close) * 100
    
    # Determine gap type (>0.3% considered a gap)
    if gap_pct > 0.3:
        gap_type = "GAP_UP"
    elif gap_pct < -0.3:
        gap_type = "GAP_DOWN"
    else:
        gap_type = "NO_GAP"
    
    # Determine if gap is filling, holding, or extending
    if gap_type == "GAP_UP":
        if current_price < open_price and current_price <= prev_close:
            gap_status = "FILLED"  # Gap completely filled
        elif current_price < open_price:
            gap_status = "FILLING"  # Gap partially filling
        elif current_price > open_price:
            gap_status = "EXTENDING"  # Gap extending higher
        else:
            gap_status = "HOLDING"  # Gap holding
    elif gap_type == "GAP_DOWN":
        if current_price > open_price and current_price >= prev_close:
            gap_status = "FILLED"  # Gap completely filled
        elif current_price > open_price:
            gap_status = "FILLING"  # Gap partially filling
        elif current_price < open_price:
            gap_status = "EXTENDING"  # Gap extending lower
        else:
            gap_status = "HOLDING"  # Gap holding
    else:
        gap_status = "NO_GAP"
    
    # Determine intraday bias based on gap behavior
    intraday_bias = "NEUTRAL"
    bias_reason = ""
    
    if gap_type == "GAP_UP":
        if gap_status == "EXTENDING":
            intraday_bias = "LONG"
            bias_reason = f"Gap Up +{gap_pct:.1f}% extending"
        elif gap_status == "FILLING" or gap_status == "FILLED":
            intraday_bias = "SHORT"
            bias_reason = f"Gap Up +{gap_pct:.1f}% filling (weak)"
        else:
            intraday_bias = "LONG"
            bias_reason = f"Gap Up +{gap_pct:.1f}% holding"
    elif gap_type == "GAP_DOWN":
        if gap_status == "EXTENDING":
            intraday_bias = "SHORT"
            bias_reason = f"Gap Down {gap_pct:.1f}% extending"
        elif gap_status == "FILLING" or gap_status == "FILLED":
            intraday_bias = "LONG"
            bias_reason = f"Gap Down {gap_pct:.1f}% filling (recovery)"
        else:
            intraday_bias = "SHORT"
            bias_reason = f"Gap Down {gap_pct:.1f}% holding"
    
    return {
        "gap_pct": round(gap_pct, 2),
        "gap_type": gap_type,
        "gap_status": gap_status,
        "intraday_bias": intraday_bias,
        "bias_reason": bias_reason
    }


def analyze_stock(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Analyze a single stock for trading signals
    
    TIME-AWARE: Adjusts targets based on time remaining until 3:15 PM square-off
    
    Returns dict with:
    - symbol, ltp, change_pct
    - rsi, momentum
    - signal: LONG, SHORT, or NEUTRAL
    - strength: 1-5 (5 being strongest)
    - reason: explanation
    - entry, stoploss, target1, target2
    - gap analysis for intraday
    - time_context for market timing
    - data_status: "LIVE", "STALE", or "ERROR" - indicates data freshness
    - data_error: error message if data fetch failed
    - data_timestamp: when data was fetched
    """
    from datetime import datetime
    
    # Get market time context
    time_context = get_market_time_context()
    target_multiplier = time_context["target_multiplier"]
    
    try:
        yahoo_symbol = get_yahoo_symbol(symbol)
        ticker = yf.Ticker(yahoo_symbol)
        
        # Get DAILY data for RSI, MAs, support/resistance
        hist_daily = ticker.history(period="1mo", interval="1d")
        
        if hist_daily.empty or len(hist_daily) < 14:
            logger.warning(f"No daily data for {symbol} - may be rate limited or delisted")
            return {
                "symbol": symbol,
                "data_status": "ERROR",
                "data_error": "No data available - API rate limited or symbol invalid",
                "data_timestamp": datetime.now().isoformat(),
                "signal": "ERROR",
                "ltp": 0
            }
        
        # Get INTRADAY data (5-min) for Supertrend - matches what traders see on charts
        hist_intraday = ticker.history(period="5d", interval="5m")
        
        # Use daily data for basic price info
        hist = hist_daily
        
        # Current price info
        ltp = hist['Close'].iloc[-1]
        prev_close = hist['Close'].iloc[-2]
        change_pct = ((ltp - prev_close) / prev_close) * 100
        
        # Today's OHLC
        today_open = hist['Open'].iloc[-1]
        today_high = hist['High'].iloc[-1]
        today_low = hist['Low'].iloc[-1]
        
        # Previous day's high/low
        prev_high = hist['High'].iloc[-2]
        prev_low = hist['Low'].iloc[-2]
        
        # Gap Analysis
        gap_analysis = analyze_gap(today_open, prev_close, ltp, prev_high, prev_low)
        
        # Calculate indicators on DAILY data
        rsi = calculate_rsi(hist['Close'])
        momentum = calculate_momentum(hist['Close'], 5)
        
        # Moving averages on DAILY data
        sma_5 = hist['Close'].rolling(5).mean().iloc[-1]
        sma_20 = hist['Close'].rolling(20).mean().iloc[-1]
        
        # ATR for stop-loss calculation
        atr = calculate_atr(hist['High'], hist['Low'], hist['Close'])
        
        # VOLATILITY ANALYSIS - Key for intraday stock selection
        volatility = calculate_volatility(hist)
        
        # Support and resistance from DAILY data
        support, resistance = calculate_support_resistance(hist)
        
        # Volume analysis
        avg_volume = hist['Volume'].rolling(10).mean().iloc[-1]
        current_volume = hist['Volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # SUPERTREND INDICATOR - Using INTRADAY 5-MIN data for real-time signals
        # This matches what traders see on their 5-minute charts!
        if not hist_intraday.empty and len(hist_intraday) >= 20:
            supertrend = calculate_supertrend_simple(
                hist_intraday['High'], 
                hist_intraday['Low'], 
                hist_intraday['Close'],
                period=10,      # 10 candles = 50 minutes of data
                multiplier=3.0
            )
            # Update LTP from intraday for more accurate current price
            ltp = hist_intraday['Close'].iloc[-1]
            today_high = max(today_high, hist_intraday['High'].max())
            today_low = min(today_low, hist_intraday['Low'].min())
        else:
            # Fallback to daily if intraday not available
            supertrend = calculate_supertrend_simple(hist['High'], hist['Low'], hist['Close'])
        
        st_signal = supertrend["signal"]
        st_crossover = supertrend["crossover"]
        st_value = supertrend["value"]
        st_distance = supertrend["distance_pct"]
        
        # VWAP INDICATOR - Essential for intraday trading
        # Use intraday data for accurate VWAP
        if not hist_intraday.empty and len(hist_intraday) >= 10:
            vwap_data = calculate_vwap(
                hist_intraday['High'],
                hist_intraday['Low'],
                hist_intraday['Close'],
                hist_intraday['Volume']
            )
        else:
            # Fallback to daily
            vwap_data = calculate_vwap(hist['High'], hist['Low'], hist['Close'], hist['Volume'])
        
        vwap = vwap_data["vwap"]
        vwap_signal = vwap_data["signal"]
        vwap_distance = vwap_data["distance_pct"]
        vwap_crossed_above = vwap_data["crossed_above"]
        vwap_crossed_below = vwap_data["crossed_below"]
        
        # ADX - Trend Strength (CRITICAL for filtering weak signals)
        if not hist_intraday.empty and len(hist_intraday) >= 20:
            adx_data = calculate_adx(
                hist_intraday['High'],
                hist_intraday['Low'],
                hist_intraday['Close'],
                di_length=10,
                adx_smoothing=10
            )
        else:
            adx_data = calculate_adx(hist['High'], hist['Low'], hist['Close'])
        
        adx_value = adx_data.get("adx", 0)
        adx_direction = adx_data.get("trend_direction", "NEUTRAL")
        adx_rising = adx_data.get("rising", False)
        adx_weakening = adx_data.get("weakening", False)
        adx_flat = adx_data.get("flat", False)
        adx_no_trend = adx_data.get("no_trend", False)
        adx_change = adx_data.get("adx_change", 0)
        plus_di = adx_data.get("plus_di", 0)
        minus_di = adx_data.get("minus_di", 0)
        
        # Determine signal
        signal = "NEUTRAL"
        strength = 0
        reasons = []
        
        # IMPROVED STRATEGY - Multiple confirmations required
        
        # === TREND DETECTION ===
        # Strong uptrend: Price > SMA5 > SMA20, and SMA5 rising
        sma_5_prev = hist['Close'].rolling(5).mean().iloc[-2]
        sma_20_prev = hist['Close'].rolling(20).mean().iloc[-2]
        
        uptrend = (ltp > sma_5 > sma_20) and (sma_5 > sma_5_prev)
        downtrend = (ltp < sma_5 < sma_20) and (sma_5 < sma_5_prev)
        
        # === PULLBACK DETECTION ===
        # In uptrend, look for pullback to buy (RSI dipped then recovering)
        rsi_series = calculate_rsi_series(hist['Close'])
        rsi_prev = rsi_series.iloc[-2] if len(rsi_series) > 1 else rsi
        rsi_prev2 = rsi_series.iloc[-3] if len(rsi_series) > 2 else rsi_prev
        
        rsi_recovering = (rsi > rsi_prev) and (rsi_prev <= rsi_prev2)  # V-shape recovery
        rsi_declining = (rsi < rsi_prev) and (rsi_prev >= rsi_prev2)  # Inverted V
        
        # === LONG CONDITIONS (Need 3+ confirmations) ===
        long_score = 0
        
        # 1. SUPERTREND confirmation (weight: 4) - STRONGEST SIGNAL
        if st_signal == "BULLISH":
            long_score += 3
            if st_crossover:
                long_score += 2  # Fresh crossover is even stronger
                reasons.append("🔥 Supertrend BUY signal!")
            else:
                reasons.append(f"📈 Supertrend Bullish (+{st_distance:.1f}%)")
        
        # 2. VWAP confirmation (weight: 3) - Price above VWAP = buyers in control
        if vwap_signal == "BULLISH":
            long_score += 2
            if vwap_crossed_above:
                long_score += 2  # Just crossed above VWAP - strong buy signal
                reasons.append("🔥 Price crossed ABOVE VWAP!")
            else:
                reasons.append(f"📊 Above VWAP (+{vwap_distance:.1f}%)")
        
        # 2. Trend confirmation (weight: 3)
        if uptrend:
            long_score += 3
            reasons.append("Strong uptrend")
        elif ltp > sma_20:
            long_score += 1
        
        # 3. RSI pullback in uptrend (weight: 2) - HIGH WIN RATE SETUP
        if uptrend and rsi < 45 and rsi_recovering:
            long_score += 3
            reasons.append(f"RSI pullback recovery ({rsi:.0f})")
        elif rsi < 30 and rsi_recovering:
            long_score += 2
            reasons.append(f"RSI oversold bounce ({rsi:.0f})")
        
        # 4. Price near support (weight: 2)
        if ltp <= support * 1.02 and ltp > support:
            long_score += 2
            reasons.append("Near support level")
        
        # 5. Volume confirmation (weight: 1)
        if volume_ratio > 1.3 and change_pct > 0.5:
            long_score += 1
            reasons.append(f"Volume surge {volume_ratio:.1f}x")
        
        # 6. Positive momentum (weight: 1)
        if momentum > 1.5:
            long_score += 1
        
        # 7. ADX - Trend Strength Confirmation (CRITICAL)
        if adx_value >= 25 and adx_direction == "BULLISH" and plus_di > minus_di:
            if adx_rising:
                long_score += 3  # Strong bonus for rising ADX
                reasons.append(f"🔥 ADX Rising ({adx_value:.0f})")
            elif not adx_flat and not adx_weakening:
                long_score += 1
                reasons.append(f"ADX Strong ({adx_value:.0f})")
        
        # ADX WARNINGS - Reduce score for weak/falling ADX
        if adx_weakening and adx_direction == "BULLISH":
            long_score -= 2
            reasons.append(f"⚠️ ADX Falling ({adx_change:+.1f})")
        if adx_flat and adx_value >= 20:
            long_score -= 1
            reasons.append("⚠️ ADX Flat")
        if adx_no_trend:
            long_score -= 2
            reasons.append(f"⛔ No Trend (ADX {adx_value:.0f})")
        
        # === SHORT CONDITIONS (Need 3+ confirmations) ===
        short_score = 0
        
        # 1. SUPERTREND confirmation (weight: 4) - STRONGEST SIGNAL
        if st_signal == "BEARISH":
            short_score += 3
            if st_crossover:
                short_score += 2  # Fresh crossover is even stronger
                reasons.append("🔥 Supertrend SELL signal!")
            else:
                reasons.append(f"📉 Supertrend Bearish ({st_distance:.1f}%)")
        
        # 2. VWAP confirmation (weight: 3) - Price below VWAP = sellers in control
        if vwap_signal == "BEARISH":
            short_score += 2
            if vwap_crossed_below:
                short_score += 2  # Just crossed below VWAP - strong sell signal
                reasons.append("🔥 Price crossed BELOW VWAP!")
            else:
                reasons.append(f"📊 Below VWAP ({vwap_distance:.1f}%)")
        
        # 2. Trend confirmation (weight: 3)
        if downtrend:
            short_score += 3
            reasons.append("Strong downtrend")
        elif ltp < sma_20:
            short_score += 1
        
        # 3. RSI rally in downtrend (weight: 2) - HIGH WIN RATE SETUP
        if downtrend and rsi > 55 and rsi_declining:
            short_score += 3
            reasons.append(f"RSI rally failing ({rsi:.0f})")
        elif rsi > 70 and rsi_declining:
            short_score += 2
            reasons.append(f"RSI overbought reversal ({rsi:.0f})")
        
        # 4. Price near resistance (weight: 2)
        if ltp >= resistance * 0.98 and ltp < resistance:
            short_score += 2
            reasons.append("Near resistance level")
        
        # 5. Volume confirmation (weight: 1)
        if volume_ratio > 1.3 and change_pct < -0.5:
            short_score += 1
            reasons.append(f"Selling volume {volume_ratio:.1f}x")
        
        # 6. Negative momentum (weight: 1)
        if momentum < -1.5:
            short_score += 1
        
        # 7. ADX - Trend Strength Confirmation (CRITICAL)
        if adx_value >= 25 and adx_direction == "BEARISH" and minus_di > plus_di:
            if adx_rising:
                short_score += 3  # Strong bonus for rising ADX
                reasons.append(f"🔥 ADX Rising ({adx_value:.0f})")
            elif not adx_flat and not adx_weakening:
                short_score += 1
                reasons.append(f"ADX Strong ({adx_value:.0f})")
        
        # ADX WARNINGS - Reduce score for weak/falling ADX
        if adx_weakening and adx_direction == "BEARISH":
            short_score -= 2
            reasons.append(f"⚠️ ADX Falling ({adx_change:+.1f})")
        if adx_flat and adx_value >= 20:
            short_score -= 1
            reasons.append("⚠️ ADX Flat")
        if adx_no_trend:
            short_score -= 2
            reasons.append(f"⛔ No Trend (ADX {adx_value:.0f})")
        
        # Include gap analysis in scoring
        if gap_analysis["intraday_bias"] == "LONG":
            long_score += 2
            if gap_analysis["bias_reason"]:
                reasons.append(gap_analysis["bias_reason"])
        elif gap_analysis["intraday_bias"] == "SHORT":
            short_score += 2
            if gap_analysis["bias_reason"]:
                reasons.append(gap_analysis["bias_reason"])
        
        # ============== HARD ADX FILTER ==============
        # Block signals when ADX is weak/falling - prevents false signals
        adx_blocks_long = False
        adx_blocks_short = False
        
        if adx_no_trend:
            # ADX < 20 = No trend at all
            adx_blocks_long = True
            adx_blocks_short = True
            reasons.append(f"⛔ BLOCKED: No Trend (ADX {adx_value:.0f} < 20)")
        elif adx_weakening:
            # ADX is falling = trend is weakening
            if adx_direction == "BULLISH":
                adx_blocks_long = True
                reasons.append(f"⛔ BLOCKED: ADX Falling ({adx_change:+.1f})")
            else:
                adx_blocks_short = True
                reasons.append(f"⛔ BLOCKED: ADX Falling ({adx_change:+.1f})")
        elif adx_flat and adx_value < 25:
            # ADX is flat AND below 25 = weak trend
            adx_blocks_long = True
            adx_blocks_short = True
            reasons.append(f"⛔ BLOCKED: ADX Flat & Weak ({adx_value:.0f})")
        
        # Determine final signal
        # STRICTER RULES: Require BOTH Supertrend AND VWAP to align
        st_vwap_aligned_long = (st_signal == "BULLISH") and (vwap_signal == "BULLISH")
        st_vwap_aligned_short = (st_signal == "BEARISH") and (vwap_signal == "BEARISH")
        
        # Calculate confidence level
        if st_vwap_aligned_long:
            confidence = "HIGH"
            min_score_required = 5  # Lower threshold when aligned
        elif st_vwap_aligned_short:
            confidence = "HIGH"
            min_score_required = 5
        elif st_signal == "BULLISH" or vwap_signal == "BULLISH":
            confidence = "MEDIUM"
            min_score_required = 6  # Higher threshold when not fully aligned
        elif st_signal == "BEARISH" or vwap_signal == "BEARISH":
            confidence = "MEDIUM"
            min_score_required = 6
        else:
            confidence = "LOW"
            min_score_required = 8  # Very high threshold for neutral indicators
        
        # STRICT: Only give LONG signal if ST and VWAP both support it AND ADX doesn't block
        if long_score >= min_score_required and long_score > short_score and not adx_blocks_long:
            if st_vwap_aligned_long:
                signal = "LONG"
                strength = min(5, int(long_score / 2))
                reasons.insert(0, "✅ ST+VWAP aligned")
            elif st_signal == "BULLISH" and vwap_signal != "BEARISH":
                signal = "LONG"
                strength = min(4, int(long_score / 2))
                reasons.insert(0, "⚠️ ST bullish, VWAP neutral")
            elif long_score >= 8:  # Very strong other signals
                signal = "LONG"
                strength = min(3, int(long_score / 3))
                reasons.insert(0, "⚠️ Weak - indicators not aligned")
            else:
                signal = "NEUTRAL"
                strength = 0
                reasons = ["❌ ST/VWAP not aligned - AVOID"]
        elif short_score >= min_score_required and short_score > long_score and not adx_blocks_short:
            if st_vwap_aligned_short:
                signal = "SHORT"
                strength = min(5, int(short_score / 2))
                reasons.insert(0, "✅ ST+VWAP aligned")
            elif st_signal == "BEARISH" and vwap_signal != "BULLISH":
                signal = "SHORT"
                strength = min(4, int(short_score / 2))
                reasons.insert(0, "⚠️ ST bearish, VWAP neutral")
            elif short_score >= 8:  # Very strong other signals
                signal = "SHORT"
                strength = min(3, int(short_score / 3))
                reasons.insert(0, "⚠️ Weak - indicators not aligned")
            else:
                signal = "NEUTRAL"
                strength = 0
                reasons = ["❌ ST/VWAP not aligned - AVOID"]
        else:
            signal = "NEUTRAL"
            strength = 0
            reasons = ["No clear signal - WAIT"]
        
        # Calculate Entry, Stop-loss, and Targets for INTRADAY
        # CRITICAL: For LONG - SL must be BELOW entry, Target ABOVE entry
        #           For SHORT - SL must be ABOVE entry, Target BELOW entry
        # TIME-AWARE: Reduce targets late in day based on target_multiplier
        
        # Calculate IDEAL ENTRY (not just current price)
        # For LONG: Find support level to buy at
        # For SHORT: Find resistance level to sell at
        
        entry_type = "LTP"
        current_price = round(ltp, 2)
        
        if signal == "LONG" or long_score > short_score:
            # LONG: Calculate ideal BUY entry (support levels)
            entry_options = []
            
            # Option 1: VWAP level (if price is above VWAP)
            if ltp > vwap:
                entry_options.append(("VWAP", round(vwap, 2)))
            
            # Option 2: Supertrend support (if ST is below price)
            if st_value < ltp:
                entry_options.append(("ST Support", round(st_value, 2)))
            
            # Option 3: Day's low + small buffer (strong support)
            day_low_entry = round(today_low * 1.003, 2)
            if day_low_entry < ltp:
                entry_options.append(("Day Low", day_low_entry))
            
            # Option 4: SMA5 support
            if sma_5 < ltp:
                entry_options.append(("SMA5", round(sma_5, 2)))
            
            # Choose the HIGHEST entry level below LTP (closest realistic entry)
            valid_entries = [(t, p) for t, p in entry_options if p < ltp and p > ltp * 0.97]
            
            if valid_entries:
                valid_entries.sort(key=lambda x: x[1], reverse=True)
                entry_type, entry = valid_entries[0]
            else:
                # No good support - use 0.3% below LTP
                entry = round(ltp * 0.997, 2)
                entry_type = "Limit"
        
        elif signal == "SHORT" or short_score > long_score:
            # SHORT: Calculate ideal SELL entry (resistance levels)
            entry_options = []
            
            # Option 1: VWAP level (if price is below VWAP)
            if ltp < vwap:
                entry_options.append(("VWAP", round(vwap, 2)))
            
            # Option 2: Supertrend resistance (if ST is above price)
            if st_value > ltp:
                entry_options.append(("ST Resist", round(st_value, 2)))
            
            # Option 3: Day's high - small buffer (strong resistance)
            day_high_entry = round(today_high * 0.997, 2)
            if day_high_entry > ltp:
                entry_options.append(("Day High", day_high_entry))
            
            # Option 4: SMA5 resistance
            if sma_5 > ltp:
                entry_options.append(("SMA5", round(sma_5, 2)))
            
            # Choose the LOWEST entry level above LTP (closest realistic entry)
            valid_entries = [(t, p) for t, p in entry_options if p > ltp and p < ltp * 1.03]
            
            if valid_entries:
                valid_entries.sort(key=lambda x: x[1])
                entry_type, entry = valid_entries[0]
            else:
                # No good resistance - use 0.3% above LTP
                entry = round(ltp * 1.003, 2)
                entry_type = "Limit"
        else:
            entry = current_price
            entry_type = "LTP"
        
        if signal == "LONG" or long_score > short_score:
            # LONG TRADE: Buy now, expect price to GO UP
            # Stop Loss = BELOW entry (exit if price falls)
            # Target = ABOVE entry (profit when price rises)
            
            # Stop loss: 0.5-1% BELOW entry (SL doesn't change with time)
            stoploss = round(ltp * 0.993, 2)  # 0.7% below
            
            # Ensure stop loss is ALWAYS below entry
            if stoploss >= entry:
                stoploss = round(entry - (entry * 0.007), 2)
            
            # Calculate risk and base targets
            risk = entry - stoploss
            base_target1 = entry + (risk * 1.5)  # 1:1.5 RR
            base_target2 = entry + (risk * 2.5)  # 1:2.5 RR
            
            # Apply time multiplier (reduce targets late in day)
            target1 = round(entry + (base_target1 - entry) * target_multiplier, 2)
            target2 = round(entry + (base_target2 - entry) * target_multiplier, 2)
            
            # Validate: targets must be ABOVE entry for LONG
            if target1 <= entry:
                target1 = round(entry * (1 + 0.01 * target_multiplier), 2)
            if target2 <= target1:
                target2 = round(entry * (1 + 0.02 * target_multiplier), 2)
                
        else:
            # SHORT TRADE: Sell now, expect price to GO DOWN
            # Stop Loss = ABOVE entry (exit if price rises)
            # Target = BELOW entry (profit when price falls)
            
            # Stop loss: 0.5-1% ABOVE entry (SL doesn't change with time)
            stoploss = round(ltp * 1.007, 2)  # 0.7% above
            
            # Ensure stop loss is ALWAYS above entry
            if stoploss <= entry:
                stoploss = round(entry + (entry * 0.007), 2)
            
            # Calculate risk and base targets
            risk = stoploss - entry
            base_target1 = entry - (risk * 1.5)  # 1:1.5 RR
            base_target2 = entry - (risk * 2.5)  # 1:2.5 RR
            
            # Apply time multiplier (reduce targets late in day)
            target1 = round(entry - (entry - base_target1) * target_multiplier, 2)
            target2 = round(entry - (entry - base_target2) * target_multiplier, 2)
            
            # Validate: targets must be BELOW entry for SHORT
            if target1 >= entry:
                target1 = round(entry * (1 - 0.01 * target_multiplier), 2)
            if target2 >= target1:
                target2 = round(entry * (1 - 0.02 * target_multiplier), 2)
        
        # Calculate risk-reward ratio
        risk_amount = abs(entry - stoploss)
        reward_amount = abs(target1 - entry)
        risk_reward = round(reward_amount / risk_amount, 1) if risk_amount > 0 else 0
        
        # Calculate intraday range position (where is price in today's range?)
        day_range = today_high - today_low if today_high > today_low else 1
        range_position = (ltp - today_low) / day_range  # 0 = day low, 1 = day high
        
        # Forward-looking intraday outlook - TIME-AWARE
        time_remaining = time_context["time_to_squareoff_mins"]
        time_warning = None
        
        # Add time warning if late in day
        if not time_context["can_trade"]:
            time_warning = "⛔ Market closing - no new positions"
            outlook = "⛔ Market closing soon - AVOID new trades"
        elif time_remaining < 30:
            time_warning = f"⚠️ SCALP ONLY ({time_remaining}m to square-off)"
            if signal == "LONG":
                outlook = f"⚠️ Quick scalp to ₹{target1:,.0f} only ({time_remaining}m left)"
            elif signal == "SHORT":
                outlook = f"⚠️ Quick scalp to ₹{target1:,.0f} only ({time_remaining}m left)"
            else:
                outlook = f"⚠️ Too late for new positions ({time_remaining}m left)"
        elif time_remaining < 60:
            time_warning = f"⏰ Limited time ({time_remaining}m to square-off)"
            if signal == "LONG":
                outlook = f"Quick trade - target ₹{target1:,.0f} ({time_remaining}m left)"
            elif signal == "SHORT":
                outlook = f"Quick trade - target ₹{target1:,.0f} ({time_remaining}m left)"
            else:
                outlook = "No clear direction - wait for better setup"
        else:
            # Normal outlook when plenty of time
            if signal == "LONG":
                if range_position < 0.3:
                    outlook = f"Near day low - expect bounce to ₹{target1:,.0f}"
                elif range_position > 0.7:
                    outlook = f"Near day high - wait for pullback, then target ₹{target2:,.0f}"
                else:
                    outlook = f"Bullish - targeting ₹{target1:,.0f} to ₹{target2:,.0f}"
            elif signal == "SHORT":
                if range_position > 0.7:
                    outlook = f"Near day high - expect fall to ₹{target1:,.0f}"
                elif range_position < 0.3:
                    outlook = f"Near day low - wait for pullback, then target ₹{target2:,.0f}"
                else:
                    outlook = f"Bearish - targeting ₹{target1:,.0f} to ₹{target2:,.0f}"
            else:
                outlook = "No clear direction - wait for better setup"
        
        return {
            "symbol": symbol,
            "ltp": ltp,
            "change_pct": change_pct,
            "today_open": today_open,
            "today_high": today_high,
            "today_low": today_low,
            "prev_close": prev_close,
            "rsi": rsi,
            "momentum": momentum,
            "sma_5": sma_5,
            "sma_20": sma_20,
            "atr": atr,
            "support": support,
            "resistance": resistance,
            "volume_ratio": volume_ratio,
            "signal": signal,
            "strength": strength,
            "confidence": confidence,
            "st_vwap_aligned": st_vwap_aligned_long if signal == "LONG" else st_vwap_aligned_short if signal == "SHORT" else False,
            "reason": " | ".join(reasons[:3]) if reasons else "Mixed signals",
            # Gap Analysis
            "gap_pct": gap_analysis["gap_pct"],
            "gap_type": gap_analysis["gap_type"],
            "gap_status": gap_analysis["gap_status"],
            # SUPERTREND
            "supertrend": st_signal,
            "supertrend_value": st_value,
            "supertrend_crossover": st_crossover,
            "supertrend_distance": st_distance,
            # VWAP
            "vwap": vwap,
            "vwap_signal": vwap_signal,
            "vwap_distance": vwap_distance,
            "vwap_crossed_above": vwap_crossed_above,
            "vwap_crossed_below": vwap_crossed_below,
            # ADX - Trend Strength
            "adx": adx_value,
            "adx_direction": adx_direction,
            "adx_rising": adx_rising,
            "adx_weakening": adx_weakening,
            "adx_flat": adx_flat,
            "adx_no_trend": adx_no_trend,
            "adx_change": adx_change,
            "plus_di": plus_di,
            "minus_di": minus_di,
            # Forward-looking
            "outlook": outlook,
            "range_position": round(range_position * 100),  # 0-100%
            # Trading levels
            "entry": entry,
            "entry_type": entry_type,
            "current_price": current_price,
            "stoploss": stoploss,
            "target1": target1,
            "target2": target2,
            "risk_reward": risk_reward,
            # Time Context
            "time_phase": time_context["phase"],
            "time_warning": time_warning,
            "mins_to_squareoff": time_remaining,
            "can_trade": time_context["can_trade"],
            "target_multiplier": target_multiplier,
            # VOLATILITY METRICS
            "volatility_score": volatility["volatility_score"],
            "volatility_rank": volatility["volatility_rank"],
            "atr_pct": volatility["atr_pct"],
            "daily_range_pct": volatility["daily_range_pct"],
            "historical_vol": volatility["historical_vol"],
            "is_volatile": volatility["is_volatile"],
            "vol_expansion": volatility.get("vol_expansion", False),
            # DATA FRESHNESS - Critical for avoiding stale signal trades
            "data_status": "LIVE",
            "data_error": None,
            "data_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze {symbol}: {e}")
        error_msg = str(e)
        # Check for rate limiting
        if "Too Many Requests" in error_msg or "rate" in error_msg.lower():
            error_type = "RATE_LIMITED"
            error_msg = "API rate limited - data may be stale. Wait 1-2 minutes."
        else:
            error_type = "ERROR"
        
        return {
            "symbol": symbol,
            "data_status": error_type,
            "data_error": error_msg,
            "data_timestamp": datetime.now().isoformat(),
            "signal": "ERROR",
            "ltp": 0
        }


def get_trading_tips(num_each: int = 2, index_name: str = "NIFTY 50") -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Get top trading tips - always returns top stocks for long and short
    Each stock appears in only ONE list based on its dominant signal
    
    TIME-AWARE: Adjusts targets based on time remaining until 3:15 PM square-off
    
    Args:
        num_each: Number of tips for each direction (LONG/SHORT)
        index_name: Index to analyze (NIFTY 50, NIFTY BANK, NIFTY IT, etc.)
    
    Returns:
        Tuple of (long_tips, short_tips, time_context)
    """
    # Get market time context - critical for intraday!
    time_context = get_market_time_context()
    target_multiplier = time_context["target_multiplier"]
    
    # Check if we should even provide tips
    if not time_context["can_trade"]:
        logger.warning(f"Market phase: {time_context['phase']} - {time_context['warning']}")
        return [], [], time_context
    
    # Get stocks for the selected index
    stocks_to_analyze = get_stocks_for_index(index_name)
    
    # For FULL MARKET scan, show progress
    is_full_scan = index_name == "FULL MARKET"
    min_price = 20 if is_full_scan else 0  # Filter stocks with price > ₹20 for full scan
    
    all_analysis = []
    analyzed_count = 0
    skipped_low_price = 0
    
    for symbol in stocks_to_analyze:
        result = analyze_stock(symbol)
        analyzed_count += 1
        
        if result:
            # Filter by minimum price (for FULL MARKET scan)
            if result.get("ltp", 0) >= min_price:
                all_analysis.append(result)
            else:
                skipped_low_price += 1
    
    if is_full_scan:
        logger.info(f"FULL MARKET scan: Analyzed {analyzed_count} stocks, {len(all_analysis)} passed (skipped {skipped_low_price} with price < ₹{min_price})")
    
    if not all_analysis:
        return [], [], time_context
    
    # Calculate long and short scores for ALL stocks
    # PRIORITY: Stocks that are ACTIVELY MOVING (not sleeping)
    for stock in all_analysis:
        # Activity score - how actively is this stock moving?
        # High volume + big change today = active stock
        volume_activity = min(stock["volume_ratio"], 3) * 10  # Max 30 points for 3x volume
        price_activity = min(abs(stock["change_pct"]), 3) * 10  # Max 30 points for 3% move
        
        # Is stock near day high or day low? (ready to breakout)
        day_range = stock["today_high"] - stock["today_low"]
        if day_range > 0:
            range_position = (stock["ltp"] - stock["today_low"]) / day_range
        else:
            range_position = 0.5
        
        # SUPERTREND bonus - major factor for intraday direction
        st_bullish = stock.get("supertrend") == "BULLISH"
        st_bearish = stock.get("supertrend") == "BEARISH"
        st_crossover = stock.get("supertrend_crossover", False)
        
        # VWAP bonus - price vs volume-weighted average
        vwap_bullish = stock.get("vwap_signal") == "BULLISH"
        vwap_bearish = stock.get("vwap_signal") == "BEARISH"
        vwap_cross_up = stock.get("vwap_crossed_above", False)
        vwap_cross_down = stock.get("vwap_crossed_below", False)
        
        # VOLATILITY BONUS - Higher volatility = Better for intraday scalping!
        volatility_score = stock.get("volatility_score", 0)
        volatility_bonus = volatility_score * 0.5  # Max ~50 points for highly volatile stocks
        vol_expansion = stock.get("vol_expansion", False)
        is_volatile = stock.get("is_volatile", False)
        
        # Long score: Stock moving UP with momentum (can hit target in 5-10 mins)
        stock["long_score"] = (
            price_activity +  # Stock is moving today
            volume_activity +  # High volume = active trading
            max(0, stock["momentum"] * 5) +  # Strong momentum (weight increased)
            (20 if stock["change_pct"] > 0.5 else 0) +  # Already moving up today
            (15 if range_position > 0.6 else 0) +  # Near day high (breakout potential)
            (10 if stock["ltp"] > stock["sma_5"] else 0) +  # Above short-term MA
            max(0, 50 - stock["rsi"]) * 0.5 +  # Slight bonus for oversold
            (30 if st_bullish else 0) +  # SUPERTREND bullish bonus
            (20 if st_crossover and st_bullish else 0) +  # Fresh ST crossover bonus
            (25 if vwap_bullish else 0) +  # VWAP bullish bonus
            (15 if vwap_cross_up else 0) +  # Just crossed above VWAP bonus
            volatility_bonus +  # VOLATILITY BONUS - prefer volatile stocks
            (20 if vol_expansion else 0)  # Extra bonus if volatility is expanding
        )
        
        # Short score: Stock moving DOWN with momentum
        stock["short_score"] = (
            price_activity +  # Stock is moving today
            volume_activity +  # High volume = active trading
            max(0, -stock["momentum"] * 5) +  # Strong negative momentum
            (20 if stock["change_pct"] < -0.5 else 0) +  # Already falling today
            (15 if range_position < 0.4 else 0) +  # Near day low (breakdown potential)
            (10 if stock["ltp"] < stock["sma_5"] else 0) +  # Below short-term MA
            max(0, stock["rsi"] - 50) * 0.5 +  # Slight bonus for overbought
            (30 if st_bearish else 0) +  # SUPERTREND bearish bonus
            (20 if st_crossover and st_bearish else 0) +  # Fresh ST crossover bonus
            (25 if vwap_bearish else 0) +  # VWAP bearish bonus
            (15 if vwap_cross_down else 0) +  # Just crossed below VWAP bonus
            volatility_bonus +  # VOLATILITY BONUS - prefer volatile stocks
            (20 if vol_expansion else 0)  # Extra bonus if volatility is expanding
        )
        
        # Store activity level for display
        stock["activity"] = "🔥 Hot" if (volume_activity + price_activity) > 40 else "⚡ Active" if (volume_activity + price_activity) > 20 else "😴 Slow"
        
        # Determine dominant direction for this stock
        if stock["long_score"] > stock["short_score"]:
            stock["direction"] = "LONG"
            stock["direction_score"] = stock["long_score"]
        else:
            stock["direction"] = "SHORT"
            stock["direction_score"] = stock["short_score"]
    
    # Separate stocks by their dominant direction
    # STRICT: Only include stocks where ST + VWAP are ALIGNED AND ADX is strong/rising
    long_stocks = [s for s in all_analysis 
                   if s["direction"] == "LONG" 
                   and s.get("signal") != "SHORT"
                   and s.get("supertrend") == "BULLISH"  # ST must be bullish
                   and s.get("vwap_signal") != "BEARISH"  # VWAP must not be bearish
                   and not s.get("adx_no_trend", False)  # ADX must be >= 20
                   and not s.get("adx_weakening", False)  # ADX must not be falling
                   and not (s.get("adx_flat", False) and s.get("adx", 0) < 25)]  # ADX must not be flat & weak
    
    short_stocks = [s for s in all_analysis 
                    if s["direction"] == "SHORT" 
                    and s.get("signal") != "LONG"
                    and s.get("supertrend") == "BEARISH"  # ST must be bearish
                    and s.get("vwap_signal") != "BULLISH"  # VWAP must not be bullish
                    and not s.get("adx_no_trend", False)  # ADX must be >= 20
                    and not s.get("adx_weakening", False)  # ADX must not be falling
                    and not (s.get("adx_flat", False) and s.get("adx", 0) < 25)]  # ADX must not be flat & weak
    
    # Further filter: require minimum activity score AND confidence
    min_activity_score = 20  # Increased from 15
    long_stocks = [s for s in long_stocks if s["long_score"] >= min_activity_score]
    short_stocks = [s for s in short_stocks if s["short_score"] >= min_activity_score]
    
    # Prioritize stocks where ST+VWAP are BOTH aligned (highest confidence)
    for s in long_stocks:
        if s.get("supertrend") == "BULLISH" and s.get("vwap_signal") == "BULLISH":
            s["long_score"] += 20  # Bonus for full alignment
            s["confidence"] = "HIGH"
        else:
            s["confidence"] = "MEDIUM"
    
    for s in short_stocks:
        if s.get("supertrend") == "BEARISH" and s.get("vwap_signal") == "BEARISH":
            s["short_score"] += 20  # Bonus for full alignment
            s["confidence"] = "HIGH"
        else:
            s["confidence"] = "MEDIUM"
    
    # Sort each group by their respective scores
    long_candidates = sorted(long_stocks, key=lambda x: x["long_score"], reverse=True)
    short_candidates = sorted(short_stocks, key=lambda x: x["short_score"], reverse=True)
    
    # Prepare long tips - RECALCULATE targets for LONG direction
    long_tips = []
    for stock in long_candidates[:num_each]:
        # Skip if original analysis was clearly bearish
        original_signal = stock.get("signal", "NEUTRAL")
        if original_signal == "SHORT":
            continue
        stock["signal"] = "LONG"
        stock["strength"] = min(5, max(1, int(stock["long_score"] / 10)))
        
        # RECALCULATE Entry/SL/Targets for LONG using S/R, Day Range, ATR
        ltp = stock["ltp"]
        entry = round(ltp, 2)
        
        # Get key levels
        support = stock.get("support", ltp * 0.98)
        resistance = stock.get("resistance", ltp * 1.02)
        day_high = stock.get("today_high", ltp * 1.015)
        day_low = stock.get("today_low", ltp * 0.985)
        atr = stock.get("atr", ltp * 0.012)  # Default ~1.2% ATR
        
        # === TIME-ADJUSTED TARGETS ===
        # Reduce target distance based on time remaining in market
        # After 2:30 PM: 50% targets (scalp only)
        # After 2:00 PM: 70% targets
        # Full targets only before 2 PM
        
        # === SCALPING MODE (5-10 min) - Use 0.5x ATR ===
        scalp_risk = min(atr * 0.4, ltp * 0.005)  # 0.4x ATR or max 0.5%
        scalp_sl = round(max(ltp - scalp_risk, day_low * 0.998), 2)  # Above day low
        # Scalp target: Aim for 0.6-0.8% move or towards day high (apply time multiplier)
        base_scalp_target = ltp + (scalp_risk * 2)
        scalp_target = round(min(ltp + (base_scalp_target - ltp) * target_multiplier, day_high * 0.998), 2)
        
        # === SWING MODE (30-60 min) - Use Support/Resistance ===
        # Stop loss: Below recent support or 1% below entry (SL doesn't change with time)
        swing_sl_support = support * 0.995  # Just below support
        swing_sl_pct = ltp * 0.99  # 1% below
        stoploss = round(max(swing_sl_support, swing_sl_pct, day_low * 0.995), 2)
        
        # Target: Apply time multiplier to reduce targets late in day
        target_resistance = resistance * 0.995
        target_day_high = day_high * 0.998
        base_target_pct = ltp * 1.015
        
        # Scale targets by time remaining
        target_distance1 = (max(base_target_pct, min(target_resistance, target_day_high)) - ltp) * target_multiplier
        target1 = round(ltp + target_distance1, 2)
        
        target_distance2 = (min(resistance * 1.005, ltp * 1.025) - ltp) * target_multiplier
        target2 = round(ltp + target_distance2, 2)
        
        # Validate LONG: SL < Entry < Target
        if stoploss >= entry:
            stoploss = round(entry * 0.99, 2)
        if target1 <= entry:
            target1 = round(entry * (1 + 0.015 * target_multiplier), 2)
        if target2 <= target1:
            target2 = round(entry * (1 + 0.025 * target_multiplier), 2)
        
        stock["entry"] = entry
        stock["stoploss"] = stoploss
        stock["target1"] = target1
        stock["target2"] = target2
        # Scalping levels
        stock["scalp_sl"] = scalp_sl
        stock["scalp_target"] = scalp_target
        stock["risk_reward"] = round((target1 - entry) / (entry - stoploss), 1) if (entry - stoploss) > 0 else 1.5
        
        # Time-aware outlook
        time_remaining = time_context["time_to_squareoff_mins"]
        if time_remaining < 30:
            stock["outlook"] = f"⚠️ SCALP ONLY: ₹{scalp_target:,.0f} ({time_remaining}m left)"
        elif time_remaining < 60:
            stock["outlook"] = f"Quick: ₹{scalp_target:,.0f} | Limited: ₹{target1:,.0f}"
        else:
            stock["outlook"] = f"Quick: ₹{scalp_target:,.0f} (5m) | Full: ₹{target1:,.0f} (30m)"
        
        # === CONVICTION PERCENTAGE (how sure are we?) ===
        base_conviction = 50  # Start at 50%
        
        # Add conviction based on indicators alignment
        if stock.get("supertrend") == "BULLISH":
            base_conviction += 15  # ST aligned
        if stock.get("supertrend_crossover"):
            base_conviction += 10  # Fresh crossover
        if stock.get("vwap_signal") == "BULLISH":
            base_conviction += 15  # VWAP aligned
        if stock.get("vwap_crossed_above"):
            base_conviction += 5  # Just crossed VWAP
        
        # Volume confirms move
        if stock["volume_ratio"] > 2:
            base_conviction += 8
        elif stock["volume_ratio"] > 1.5:
            base_conviction += 5
        
        # Momentum confirms direction
        if stock["momentum"] > 1:
            base_conviction += 5
        
        # Price action confirms (already moving in our direction)
        if stock["change_pct"] > 0.5:
            base_conviction += 5
        
        # Cap at 95%
        stock["conviction_pct"] = min(95, base_conviction)
        
        # === EXPECTED PROFIT PERCENTAGE ===
        stock["scalp_profit_pct"] = round(((scalp_target - entry) / entry) * 100, 2)
        stock["swing_profit_pct"] = round(((target1 - entry) / entry) * 100, 2)
        
        reasons = []
        # SUPERTREND first - most important
        if stock.get("supertrend") == "BULLISH":
            if stock.get("supertrend_crossover"):
                reasons.append("🔥 ST BUY")
            else:
                reasons.append("📈 ST+")
        # VWAP second
        if stock.get("vwap_signal") == "BULLISH":
            if stock.get("vwap_crossed_above"):
                reasons.append("🔥 VWAP↑")
            else:
                reasons.append("📊 >VWAP")
        activity = stock.get("activity", "")
        if activity and len(reasons) < 4:
            reasons.append(activity)
        if stock["volume_ratio"] > 1.5 and len(reasons) < 4:
            reasons.append(f"Vol {stock['volume_ratio']:.1f}x")
        if stock["change_pct"] > 0.5 and len(reasons) < 4:
            reasons.append(f"Up {stock['change_pct']:.1f}%")
        if stock["momentum"] > 1 and len(reasons) < 4:
            reasons.append(f"Mom +{stock['momentum']:.1f}%")
        
        # Add volatility label
        vol_rank = stock.get("volatility_rank", "LOW")
        vol_score = stock.get("volatility_score", 0)
        if vol_rank == "HIGH":
            stock["volatility_label"] = f"🔥 High Vol ({vol_score})"
        elif vol_rank == "MEDIUM":
            stock["volatility_label"] = f"⚡ Med Vol ({vol_score})"
        else:
            stock["volatility_label"] = f"💤 Low Vol ({vol_score})"
        
        stock["reason"] = " | ".join(reasons[:3]) if reasons else "Best long candidate"
        long_tips.append(stock)
    
    # Prepare short tips - RECALCULATE targets for SHORT direction
    short_tips = []
    for stock in short_candidates[:num_each]:
        # Skip if original analysis was clearly bullish
        original_signal = stock.get("signal", "NEUTRAL")
        if original_signal == "LONG":
            continue
        stock["signal"] = "SHORT"
        stock["strength"] = min(5, max(1, int(stock["short_score"] / 10)))
        
        # RECALCULATE Entry/SL/Targets for SHORT using S/R, Day Range, ATR
        ltp = stock["ltp"]
        entry = round(ltp, 2)
        
        # Get key levels
        support = stock.get("support", ltp * 0.98)
        resistance = stock.get("resistance", ltp * 1.02)
        day_high = stock.get("today_high", ltp * 1.015)
        day_low = stock.get("today_low", ltp * 0.985)
        atr = stock.get("atr", ltp * 0.012)  # Default ~1.2% ATR
        
        # === TIME-ADJUSTED TARGETS FOR SHORT ===
        # Same time multiplier logic as LONG
        
        # === SCALPING MODE (5-10 min) - Use 0.5x ATR ===
        scalp_risk = min(atr * 0.4, ltp * 0.005)  # 0.4x ATR or max 0.5%
        scalp_sl = round(min(ltp + scalp_risk, day_high * 1.002), 2)  # Below day high
        # Scalp target: Apply time multiplier
        base_scalp_target = ltp - (scalp_risk * 2)
        scalp_target = round(max(ltp - (ltp - base_scalp_target) * target_multiplier, day_low * 1.002), 2)
        
        # === SWING MODE (30-60 min) - Use Support/Resistance ===
        # Stop loss: Above recent resistance or 1% above entry (SL doesn't change with time)
        swing_sl_resistance = resistance * 1.005
        swing_sl_pct = ltp * 1.01
        stoploss = round(min(swing_sl_resistance, swing_sl_pct, day_high * 1.005), 2)
        
        # Target: Apply time multiplier to reduce targets late in day
        target_support = support * 1.005
        target_day_low = day_low * 1.002
        base_target_pct = ltp * 0.985
        
        # Scale targets by time remaining (for SHORT, target is below entry)
        target_distance1 = (ltp - min(base_target_pct, max(target_support, target_day_low))) * target_multiplier
        target1 = round(ltp - target_distance1, 2)
        
        target_distance2 = (ltp - max(support * 0.995, ltp * 0.975)) * target_multiplier
        target2 = round(ltp - target_distance2, 2)
        
        # Validate SHORT: Target < Entry < SL
        if stoploss <= entry:
            stoploss = round(entry * 1.01, 2)
        if target1 >= entry:
            target1 = round(entry * (1 - 0.015 * target_multiplier), 2)
        if target2 >= target1:
            target2 = round(entry * (1 - 0.025 * target_multiplier), 2)
        
        stock["entry"] = entry
        stock["stoploss"] = stoploss
        stock["target1"] = target1
        stock["target2"] = target2
        # Scalping levels
        stock["scalp_sl"] = scalp_sl
        stock["scalp_target"] = scalp_target
        stock["risk_reward"] = round((entry - target1) / (stoploss - entry), 1) if (stoploss - entry) > 0 else 1.5
        
        # Time-aware outlook
        time_remaining = time_context["time_to_squareoff_mins"]
        if time_remaining < 30:
            stock["outlook"] = f"⚠️ SCALP ONLY: ₹{scalp_target:,.0f} ({time_remaining}m left)"
        elif time_remaining < 60:
            stock["outlook"] = f"Quick: ₹{scalp_target:,.0f} | Limited: ₹{target1:,.0f}"
        else:
            stock["outlook"] = f"Quick: ₹{scalp_target:,.0f} (5m) | Full: ₹{target1:,.0f} (30m)"
        
        # === CONVICTION PERCENTAGE (how sure are we?) ===
        base_conviction = 50  # Start at 50%
        
        # Add conviction based on indicators alignment
        if stock.get("supertrend") == "BEARISH":
            base_conviction += 15  # ST aligned
        if stock.get("supertrend_crossover"):
            base_conviction += 10  # Fresh crossover
        if stock.get("vwap_signal") == "BEARISH":
            base_conviction += 15  # VWAP aligned
        if stock.get("vwap_crossed_below"):
            base_conviction += 5  # Just crossed VWAP
        
        # Volume confirms move
        if stock["volume_ratio"] > 2:
            base_conviction += 8
        elif stock["volume_ratio"] > 1.5:
            base_conviction += 5
        
        # Momentum confirms direction
        if stock["momentum"] < -1:
            base_conviction += 5
        
        # Price action confirms (already moving in our direction)
        if stock["change_pct"] < -0.5:
            base_conviction += 5
        
        # Cap at 95%
        stock["conviction_pct"] = min(95, base_conviction)
        
        # === EXPECTED PROFIT PERCENTAGE ===
        stock["scalp_profit_pct"] = round(((entry - scalp_target) / entry) * 100, 2)
        stock["swing_profit_pct"] = round(((entry - target1) / entry) * 100, 2)
        
        reasons = []
        # SUPERTREND first - most important
        if stock.get("supertrend") == "BEARISH":
            if stock.get("supertrend_crossover"):
                reasons.append("🔥 ST SELL")
            else:
                reasons.append("📉 ST-")
        # VWAP second
        if stock.get("vwap_signal") == "BEARISH":
            if stock.get("vwap_crossed_below"):
                reasons.append("🔥 VWAP↓")
            else:
                reasons.append("📊 <VWAP")
        activity = stock.get("activity", "")
        if activity and len(reasons) < 4:
            reasons.append(activity)
        if stock["volume_ratio"] > 1.5 and len(reasons) < 4:
            reasons.append(f"Vol {stock['volume_ratio']:.1f}x")
        if stock["change_pct"] < -0.5 and len(reasons) < 4:
            reasons.append(f"Down {stock['change_pct']:.1f}%")
        if stock["momentum"] < -1 and len(reasons) < 3:
            reasons.append(f"Mom {stock['momentum']:.1f}%")
        
        # Add volatility label
        vol_rank = stock.get("volatility_rank", "LOW")
        vol_score = stock.get("volatility_score", 0)
        if vol_rank == "HIGH":
            stock["volatility_label"] = f"🔥 High Vol ({vol_score})"
        elif vol_rank == "MEDIUM":
            stock["volatility_label"] = f"⚡ Med Vol ({vol_score})"
        else:
            stock["volatility_label"] = f"💤 Low Vol ({vol_score})"
        
        stock["reason"] = " | ".join(reasons[:3]) if reasons else "Best short candidate"
        short_tips.append(stock)
    
    # Add time context to each tip
    for tip in long_tips + short_tips:
        tip["time_warning"] = time_context.get("warning")
        tip["time_phase"] = time_context["phase"]
        tip["mins_to_squareoff"] = time_context["time_to_squareoff_mins"]
    
    return long_tips, short_tips, time_context


def get_available_indices() -> List[str]:
    """Get list of available indices for selection"""
    return list(STOCK_LISTS.keys())


def get_quick_tips(index_name: str = "NIFTY 50", num_tips: int = 2) -> Dict[str, Any]:
    """
    Get quick intraday trading tips based on CURRENT price action
    Focuses on what's happening NOW, not historical data
    
    TIME-AWARE: Includes market timing information
    - No tips after 3:00 PM
    - Reduced targets after 2:00 PM
    - Warnings when approaching square-off
    
    Args:
        index_name: Index to analyze (NIFTY 50, NIFTY BANK, NIFTY IT, etc.)
        num_tips: Number of tips per direction
    
    Returns dict with long_tips, short_tips, and time context
    """
    try:
        long_tips, short_tips, time_context = get_trading_tips(num_each=num_tips, index_name=index_name)
        
        # Add intraday-specific context
        for tip in long_tips + short_tips:
            # Calculate intraday range position
            if tip.get('today_high') and tip.get('today_low'):
                day_range = tip['today_high'] - tip['today_low']
                if day_range > 0:
                    range_position = (tip['ltp'] - tip['today_low']) / day_range
                    if range_position < 0.3:
                        tip['intraday_context'] = "Near day low - potential bounce"
                    elif range_position > 0.7:
                        tip['intraday_context'] = "Near day high - watch for reversal"
                    else:
                        tip['intraday_context'] = "Mid-range - wait for breakout"
        
        stocks_count = len(get_stocks_for_index(index_name))
        
        return {
            "long_tips": long_tips,
            "short_tips": short_tips,
            "index": index_name,
            "stocks_analyzed": stocks_count,
            "timestamp": datetime.now().isoformat(),
            "status": "success",
            "note": f"Analyzing {stocks_count} stocks from {index_name}",
            "time_context": time_context,
            "market_phase": time_context["phase"],
            "time_warning": time_context.get("warning"),
            "mins_to_squareoff": time_context["time_to_squareoff_mins"],
            "can_trade": time_context["can_trade"]
        }
    except Exception as e:
        logger.error(f"Failed to get tips: {e}")
        time_context = get_market_time_context()
        return {
            "long_tips": [],
            "short_tips": [],
            "index": index_name,
            "stocks_analyzed": 0,
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": str(e),
            "time_context": time_context,
            "market_phase": time_context["phase"],
            "can_trade": time_context["can_trade"]
        }


def detect_big_move_stocks(index_name: str = "NIFTY 50", num_stocks: int = 5) -> Dict[str, Any]:
    """
    Detect stocks where an INTRADAY BIG MOVE is about to happen
    
    TIME-AWARE: Adjusts based on time remaining until 3:15 PM square-off
    
    Uses 5-minute data to find:
    1. Volatility Squeeze - Low recent ATR (coiling for breakout)
    2. Volume Surge - Unusual volume in recent candles
    3. VWAP Position - Price relative to VWAP
    4. Near Intraday Key Levels - At day's high/low or opening range
    5. Supertrend Alignment - Trend confirmation
    6. Range Compression - Tight recent candles about to expand
    
    Returns stocks sorted by "intraday breakout potential"
    """
    # Get market time context
    time_context = get_market_time_context()
    target_multiplier = time_context["target_multiplier"]
    
    # Check if market is open for trading
    if not time_context["can_trade"]:
        return {
            "candidates": [],
            "index": index_name,
            "stocks_analyzed": 0,
            "stocks_with_data": 0,
            "timestamp": datetime.now().isoformat(),
            "time_context": time_context,
            "warning": time_context.get("warning", "Market closed for new positions")
        }
    
    try:
        stocks_to_analyze = get_stocks_for_index(index_name)
        big_move_candidates = []
        stocks_analyzed = 0
        stocks_with_data = 0
        
        logger.info(f"Breakout Alert: Scanning {len(stocks_to_analyze)} stocks from {index_name} (Time: {time_context['phase']})")
        
        for symbol in stocks_to_analyze:
            try:
                stocks_analyzed += 1
                yahoo_symbol = get_yahoo_symbol(symbol)
                ticker = yf.Ticker(yahoo_symbol)
                
                # Get 5-minute intraday data (5 days for enough history)
                hist = ticker.history(period="5d", interval="5m")
                
                if hist.empty or len(hist) < 50:
                    logger.debug(f"Breakout: {symbol} - insufficient data ({len(hist) if not hist.empty else 0} candles)")
                    continue
                
                stocks_with_data += 1
                
                # Filter to today's data for some calculations
                today = datetime.now().date()
                if hist.index.tz is not None:
                    today_data = hist[hist.index.date == today]
                else:
                    today_data = hist.tail(75)  # ~6 hours of 5-min candles
                
                if len(today_data) < 5:
                    today_data = hist.tail(30)
                
                # Current values
                ltp = hist['Close'].iloc[-1]
                prev_candle_close = hist['Close'].iloc[-2]
                
                # Today's OHLC
                if len(today_data) > 0:
                    day_open = today_data['Open'].iloc[0]
                    day_high = today_data['High'].max()
                    day_low = today_data['Low'].min()
                else:
                    day_open = hist['Open'].iloc[-30]
                    day_high = hist['High'].tail(30).max()
                    day_low = hist['Low'].tail(30).min()
                
                change_pct = ((ltp - day_open) / day_open) * 100
                day_range = day_high - day_low
                day_range_pct = (day_range / ltp) * 100
                
                # === 1. INTRADAY ATR SQUEEZE ===
                tr1 = hist['High'] - hist['Low']
                tr2 = abs(hist['High'] - hist['Close'].shift())
                tr3 = abs(hist['Low'] - hist['Close'].shift())
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr_20 = tr.rolling(20).mean().iloc[-1]  # 20 candles ~ 100 min
                atr_5 = tr.rolling(5).mean().iloc[-1]   # Recent 5 candles ~ 25 min
                
                atr_pct = (atr_20 / ltp) * 100
                
                # Squeeze: Recent volatility lower than average (coiling)
                atr_squeeze = atr_5 < atr_20 * 0.9  # Relaxed from 0.75 to 0.9
                atr_squeeze_score = 20 if atr_squeeze else 0
                
                # === 2. VOLUME SURGE ===
                avg_volume = hist['Volume'].rolling(50).mean().iloc[-1]
                recent_volume = hist['Volume'].tail(5).mean()
                current_volume = hist['Volume'].iloc[-1]
                
                volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
                volume_surge = volume_ratio > 1.2  # Relaxed from 1.5 to 1.2
                volume_score = min(20, int(volume_ratio * 10)) if volume_surge else 0
                
                # === 3. VWAP ANALYSIS ===
                vwap_data = calculate_vwap(hist)
                vwap = vwap_data.get("vwap", ltp)
                vwap_signal = vwap_data.get("signal", "NEUTRAL")
                vwap_distance = vwap_data.get("distance_pct", 0)
                
                vwap_score = 0
                if abs(vwap_distance) < 0.5:  # Relaxed from 0.3 to 0.5
                    vwap_score = 15
                if vwap_signal == "BULLISH":
                    vwap_score += 10
                elif vwap_signal == "BEARISH":
                    vwap_score += 10
                
                # === 4. NEAR INTRADAY KEY LEVELS ===
                # Opening Range (first 15 min = 3 candles)
                if len(today_data) >= 3:
                    opening_high = today_data['High'].iloc[:3].max()
                    opening_low = today_data['Low'].iloc[:3].min()
                else:
                    opening_high = day_high
                    opening_low = day_low
                
                # Relaxed thresholds from 0.2% to 1%
                near_day_high = ltp >= day_high * 0.99  # Within 1% of day high
                near_day_low = ltp <= day_low * 1.01   # Within 1% of day low
                near_opening_high = ltp >= opening_high * 0.99 and not near_day_high
                near_opening_low = ltp <= opening_low * 1.01 and not near_day_low
                
                level_score = 0
                breakout_direction = "NEUTRAL"
                if near_day_high:
                    level_score = 25
                    breakout_direction = "BULLISH"
                elif near_day_low:
                    level_score = 25
                    breakout_direction = "BEARISH"
                elif near_opening_high:
                    level_score = 15
                    breakout_direction = "BULLISH"
                elif near_opening_low:
                    level_score = 15
                    breakout_direction = "BEARISH"
                
                # === 5. SUPERTREND ALIGNMENT ===
                st_data = calculate_supertrend_simple(hist)
                supertrend = st_data.get("signal", "NEUTRAL")
                st_crossover = st_data.get("crossover", False)
                
                st_score = 0
                if st_crossover:  # Just crossed = strong momentum
                    st_score = 20
                elif supertrend == "BULLISH":
                    st_score = 12
                elif supertrend == "BEARISH":
                    st_score = 12
                
                # === 6. RANGE COMPRESSION (Recent candles) ===
                recent_range = (hist['High'].tail(5) - hist['Low'].tail(5)).mean()
                avg_range = (hist['High'] - hist['Low']).rolling(20).mean().iloc[-1]
                range_compression = recent_range < avg_range * 0.8  # Relaxed from 0.6 to 0.8
                range_score = 15 if range_compression else 0
                
                # === 7. MOMENTUM (RSI + Price action) ===
                rsi = calculate_rsi(hist['Close'], period=14)
                momentum_5 = ((ltp - hist['Close'].iloc[-6]) / hist['Close'].iloc[-6]) * 100
                
                momentum_score = 0
                # RSI extreme = about to reverse or continue
                if rsi > 60 or rsi < 40:
                    momentum_score = 10
                # Strong momentum building
                if abs(momentum_5) > 0.2 and volume_ratio > 1.1:
                    momentum_score += 8
                # Today moving significantly
                if abs(change_pct) > 0.5:
                    momentum_score += 5
                
                # === 8. VOLATILITY SCORE (NEW - prioritize volatile stocks) ===
                # Get daily data for volatility calculation
                try:
                    hist_daily = ticker.history(period="1mo", interval="1d")
                    volatility = calculate_volatility(hist_daily)
                except:
                    volatility = {
                        "volatility_score": 0,
                        "volatility_rank": "LOW",
                        "atr_pct": atr_pct,
                        "daily_range_pct": day_range_pct,
                        "is_volatile": False,
                        "vol_expansion": False
                    }
                
                # Volatility bonus - higher volatility = better for intraday breakout
                vol_score = int(volatility.get("volatility_score", 0) * 0.4)  # Max ~40 points
                if volatility.get("vol_expansion", False):
                    vol_score += 10  # Extra bonus for expanding volatility
                
                # === 9. ADX FILTER (CRITICAL - No signal if ADX weak/falling) ===
                try:
                    adx_data = calculate_adx(
                        hist_daily['High'], 
                        hist_daily['Low'], 
                        hist_daily['Close'],
                        di_length=10, adx_smoothing=10
                    )
                    adx_value = adx_data.get("adx", 0)
                    adx_rising = adx_data.get("rising", False)
                    adx_weakening = adx_data.get("weakening", False)
                    adx_flat = adx_data.get("flat", False)
                    adx_no_trend = adx_data.get("no_trend", True)
                    adx_change = adx_data.get("adx_change", 0)
                except:
                    adx_value = 0
                    adx_rising = False
                    adx_weakening = False
                    adx_flat = False
                    adx_no_trend = True
                    adx_change = 0
                
                # ADX HARD FILTER - Skip stocks with weak/falling ADX
                if adx_no_trend or adx_weakening or (adx_flat and adx_value < 25):
                    logger.debug(f"Breakout: {symbol} - ADX blocked (ADX={adx_value:.1f}, change={adx_change:+.1f})")
                    continue  # Skip this stock entirely
                
                # === TOTAL BREAKOUT POTENTIAL SCORE ===
                total_score = (
                    atr_squeeze_score +
                    volume_score +
                    vwap_score +
                    level_score +
                    st_score +
                    range_score +
                    momentum_score +
                    vol_score  # NEW: Volatility bonus
                )
                
                # Very low threshold - show almost any stock with some signal
                if total_score >= 15:
                    # Determine expected direction if neutral
                    if breakout_direction == "NEUTRAL":
                        if supertrend == "BULLISH" and vwap_signal == "BULLISH":
                            breakout_direction = "BULLISH"
                        elif supertrend == "BEARISH" and vwap_signal == "BEARISH":
                            breakout_direction = "BEARISH"
                        elif ltp > vwap:
                            breakout_direction = "BULLISH"
                        else:
                            breakout_direction = "BEARISH"
                    
                    # Expected move based on ATR (intraday = smaller)
                    expected_move_pct = min(atr_pct * 2, day_range_pct * 0.5)
                    
                    # Build signal text
                    signals = []
                    if atr_squeeze:
                        signals.append("🔥 Coiling")
                    if volume_surge:
                        signals.append(f"📊 Vol {volume_ratio:.1f}x")
                    if near_day_high:
                        signals.append("⬆️ Day High")
                    elif near_day_low:
                        signals.append("⬇️ Day Low")
                    elif near_opening_high:
                        signals.append("🔼 ORB High")
                    elif near_opening_low:
                        signals.append("🔽 ORB Low")
                    if st_crossover:
                        signals.append(f"🎯 ST Cross")
                    elif supertrend != "NEUTRAL":
                        signals.append(f"📈 ST {supertrend[:4]}")
                    if abs(vwap_distance) < 0.3:
                        signals.append("⚡ Near VWAP")
                    if range_compression:
                        signals.append("📉 Tight")
                    
                    # Calculate Entry, SL, Target based on direction
                    # Apply TIME MULTIPLIER to targets (reduce targets late in day)
                    entry = round(ltp, 2)
                    atr_value = atr_pct * ltp / 100  # Convert ATR% to value
                    
                    if breakout_direction == "BULLISH":
                        # LONG: SL below day low or 1%, Target at/above day high
                        stoploss = round(max(day_low * 0.998, ltp - atr_value), 2)
                        # Base targets
                        base_target1 = min(day_high * 1.005, ltp * 1.02)
                        base_target2 = ltp * 1.03
                        # Apply time multiplier (reduce targets late in day)
                        target1 = round(ltp + (base_target1 - ltp) * target_multiplier, 2)
                        target2 = round(ltp + (base_target2 - ltp) * target_multiplier, 2)
                    else:
                        # SHORT: SL above day high or 1%, Target at/below day low
                        stoploss = round(min(day_high * 1.002, ltp + atr_value), 2)
                        # Base targets
                        base_target1 = max(day_low * 0.995, ltp * 0.98)
                        base_target2 = ltp * 0.97
                        # Apply time multiplier (reduce targets late in day)
                        target1 = round(ltp - (ltp - base_target1) * target_multiplier, 2)
                        target2 = round(ltp - (ltp - base_target2) * target_multiplier, 2)
                    
                    # Calculate profit potential
                    if breakout_direction == "BULLISH":
                        profit_pct = round(((target1 - entry) / entry) * 100, 2)
                        risk_pct = round(((entry - stoploss) / entry) * 100, 2)
                    else:
                        profit_pct = round(((entry - target1) / entry) * 100, 2)
                        risk_pct = round(((stoploss - entry) / entry) * 100, 2)
                    
                    risk_reward = round(profit_pct / risk_pct, 1) if risk_pct > 0 else 1.5
                    
                    # Time-aware outlook
                    time_remaining = time_context["time_to_squareoff_mins"]
                    if time_remaining < 30:
                        time_note = f"⚠️ SCALP ({time_remaining}m left)"
                    elif time_remaining < 60:
                        time_note = f"Quick trade only ({time_remaining}m)"
                    else:
                        time_note = None
                    
                    # Volatility label
                    vol_rank = volatility.get("volatility_rank", "LOW")
                    vol_score_val = volatility.get("volatility_score", 0)
                    if vol_rank == "HIGH":
                        vol_label = f"🔥 High Vol ({vol_score_val})"
                    elif vol_rank == "MEDIUM":
                        vol_label = f"⚡ Med Vol ({vol_score_val})"
                    else:
                        vol_label = f"💤 Low Vol ({vol_score_val})"
                    
                    big_move_candidates.append({
                        "symbol": symbol,
                        "ltp": round(ltp, 2),
                        "change_pct": round(change_pct, 2),
                        "breakout_score": total_score,
                        "direction": breakout_direction,
                        "expected_move_pct": round(expected_move_pct, 2),
                        "atr_pct": round(atr_pct, 3),
                        "volume_ratio": round(volume_ratio, 1),
                        "vwap": round(vwap, 2),
                        "vwap_distance": round(vwap_distance, 2),
                        "supertrend": supertrend,
                        "rsi": round(rsi, 1),
                        "day_high": round(day_high, 2),
                        "day_low": round(day_low, 2),
                        "entry": entry,
                        "stoploss": stoploss,
                        "target1": target1,
                        "target2": target2,
                        "profit_pct": profit_pct,
                        "risk_pct": risk_pct,
                        "risk_reward": risk_reward,
                        "signals": signals,
                        "signal_text": " | ".join(signals[:4]),
                        "time_note": time_note,
                        "mins_to_squareoff": time_remaining,
                        # VOLATILITY DATA
                        "volatility_score": vol_score_val,
                        "volatility_rank": vol_rank,
                        "volatility_label": vol_label,
                        "is_volatile": volatility.get("is_volatile", False),
                        # ADX DATA (confirmation that ADX passed filter)
                        "adx": round(adx_value, 1),
                        "adx_rising": adx_rising,
                        "adx_change": round(adx_change, 1)
                    })
                    
            except Exception as e:
                logger.debug(f"Error analyzing {symbol} for big move: {e}")
                continue
        
        # Sort by breakout potential score (highest first)
        big_move_candidates.sort(key=lambda x: x["breakout_score"], reverse=True)
        
        logger.info(f"Breakout Alert: Analyzed {stocks_analyzed} stocks, {stocks_with_data} had data, {len(big_move_candidates)} passed threshold (Time: {time_context['phase']})")
        
        return {
            "status": "success",
            "big_move_stocks": big_move_candidates[:num_stocks],
            "total_candidates": len(big_move_candidates),
            "stocks_analyzed": stocks_analyzed,
            "stocks_with_data": stocks_with_data,
            "index": index_name,
            "timestamp": datetime.now().isoformat(),
            "time_context": time_context,
            "market_phase": time_context["phase"],
            "time_warning": time_context.get("warning"),
            "mins_to_squareoff": time_context["time_to_squareoff_mins"],
            "can_trade": time_context["can_trade"]
        }
        
    except Exception as e:
        logger.error(f"Failed to detect big move stocks: {e}")
        return {
            "status": "error",
            "big_move_stocks": [],
            "total_candidates": 0,
            "error": str(e)
        }


def get_tomorrow_outlook(index_name: str = "NIFTY 50", num_stocks: int = 6) -> Dict[str, Any]:
    """
    Analyze stocks for TOMORROW's INTRADAY trading
    
    This function identifies stocks good for INTRADAY tomorrow based on:
    1. Today's closing strength (strong close = gap up potential)
    2. Volatility (ATR %) - higher volatility = better intraday
    3. Volume surge today - indicates momentum continuation
    4. Near day high/low - breakout/breakdown potential
    5. Supertrend direction on daily - trend alignment
    6. Opening Range Breakout (ORB) potential
    
    Best used after 3 PM to prepare for next trading day's INTRADAY
    
    Returns:
        Dict with long_setups, short_setups for tomorrow's intraday (exit same day)
    """
    try:
        stocks_to_analyze = get_stocks_for_index(index_name)
        
        # For FULL MARKET, filter stocks > ₹20
        min_price = 20 if index_name == "FULL MARKET" else 0
        
        long_setups = []
        short_setups = []
        stocks_analyzed = 0
        
        logger.info(f"Tomorrow Intraday: Analyzing {len(stocks_to_analyze)} stocks from {index_name}")
        
        for symbol in stocks_to_analyze:
            try:
                stocks_analyzed += 1
                yahoo_symbol = get_yahoo_symbol(symbol)
                ticker = yf.Ticker(yahoo_symbol)
                
                # Get daily data for EOD analysis
                hist_daily = ticker.history(period="1mo", interval="1d")
                
                if hist_daily.empty or len(hist_daily) < 10:
                    continue
                
                # Current values (today's close)
                ltp = hist_daily['Close'].iloc[-1]
                
                # Filter by minimum price
                if ltp < min_price:
                    continue
                
                prev_close = hist_daily['Close'].iloc[-2]
                today_open = hist_daily['Open'].iloc[-1]
                today_high = hist_daily['High'].iloc[-1]
                today_low = hist_daily['Low'].iloc[-1]
                today_volume = hist_daily['Volume'].iloc[-1]
                
                # Price change today
                change_pct = ((ltp - prev_close) / prev_close) * 100
                
                # === 1. CLOSING STRENGTH ANALYSIS ===
                day_range = today_high - today_low if today_high > today_low else 0.01
                close_position = (ltp - today_low) / day_range  # 0 = at low, 1 = at high
                
                strong_close = close_position > 0.75  # Closed in top 25% of range
                weak_close = close_position < 0.25    # Closed in bottom 25% of range
                
                # === 2. VOLATILITY ANALYSIS (ATR %) ===
                atr = calculate_atr(hist_daily['High'], hist_daily['Low'], hist_daily['Close'], period=10)
                atr_pct = (atr / ltp) * 100
                
                # Good intraday volatility = 1.0% - 5% ATR (relaxed range)
                good_volatility = atr_pct >= 1.0  # Just need some volatility
                high_volatility = atr_pct > 2.0
                
                # === 3. VOLUME ANALYSIS ===
                avg_volume_20 = hist_daily['Volume'].tail(20).mean()
                volume_ratio = today_volume / avg_volume_20 if avg_volume_20 > 0 else 1
                volume_surge = volume_ratio > 1.5
                
                # === 4. GAP POTENTIAL ===
                gap_up_potential = strong_close and volume_surge and change_pct > 0.3
                gap_down_potential = weak_close and volume_surge and change_pct < -0.3
                
                # === 5. DAILY SUPERTREND ===
                st_daily = calculate_supertrend_simple(hist_daily)
                st_signal = st_daily.get("signal", "NEUTRAL")
                st_crossover = st_daily.get("crossover", False)
                
                # === 6. RSI ===
                rsi = calculate_rsi(hist_daily['Close'], period=14)
                rsi_oversold = rsi < 35
                rsi_overbought = rsi > 65
                
                # === 7. NEAR KEY LEVELS ===
                week_high = hist_daily['High'].tail(5).max()
                week_low = hist_daily['Low'].tail(5).min()
                
                near_week_high = (week_high - ltp) / ltp * 100 < 1.5
                near_week_low = (ltp - week_low) / ltp * 100 < 1.5
                
                # === 8. EXPECTED INTRADAY RANGE ===
                expected_range_pct = atr_pct * 1.2
                
                # === ADDITIONAL ANALYSIS ===
                # Consolidation detection (narrow range = ready to breakout)
                recent_5d_range = (hist_daily['High'].tail(5).max() - hist_daily['Low'].tail(5).min()) / ltp * 100
                avg_daily_range = ((hist_daily['High'] - hist_daily['Low']) / hist_daily['Close']).tail(20).mean() * 100
                is_consolidating = recent_5d_range < avg_daily_range * 1.5
                
                # Support/Resistance detection
                recent_low = hist_daily['Low'].tail(10).min()
                recent_high = hist_daily['High'].tail(10).max()
                at_support = (ltp - recent_low) / ltp * 100 < 2  # Within 2% of 10-day low
                at_resistance = (recent_high - ltp) / ltp * 100 < 2  # Within 2% of 10-day high
                
                # Accumulation pattern (volume increasing while price stable)
                recent_vol = hist_daily['Volume'].tail(3).mean()
                prev_vol = hist_daily['Volume'].tail(6).head(3).mean()
                volume_building = recent_vol > prev_vol * 1.2
                
                # Positive close (closed above open)
                positive_candle = ltp > today_open
                negative_candle = ltp < today_open
                
                # Moving average position
                sma_20 = hist_daily['Close'].rolling(20).mean().iloc[-1]
                above_sma = ltp > sma_20
                below_sma = ltp < sma_20
                
                # Breaking out of range
                prev_4d_high = hist_daily['High'].tail(5).head(4).max()
                prev_4d_low = hist_daily['Low'].tail(5).head(4).min()
                breaking_up = ltp > prev_4d_high
                breaking_down = ltp < prev_4d_low
                
                # === SCORING FOR INTRADAY TOMORROW ===
                long_score = 0
                short_score = 0
                long_signals = []
                short_signals = []
                
                # === LONG SCORING (expanded criteria) ===
                # Momentum continuation
                if strong_close:
                    long_score += 20
                    long_signals.append("💪 Strong Close")
                if gap_up_potential:
                    long_score += 15
                    long_signals.append("🌅 Gap Up")
                
                # Trend alignment
                if st_signal == "BULLISH":
                    long_score += 15
                    long_signals.append("📈 ST+")
                if st_crossover and st_signal == "BULLISH":
                    long_score += 15
                    long_signals.append("🔥 ST Cross")
                if above_sma:
                    long_score += 10
                    long_signals.append(">SMA20")
                
                # Breakout patterns
                if breaking_up:
                    long_score += 20
                    long_signals.append("🚀 Breaking Out")
                if near_week_high and volume_surge:
                    long_score += 15
                    long_signals.append("📊 Breakout+Vol")
                if is_consolidating and positive_candle:
                    long_score += 15
                    long_signals.append("🎯 Consolidation")
                
                # Reversal/Bounce patterns
                if at_support and positive_candle:
                    long_score += 20
                    long_signals.append("📍 Support Bounce")
                if rsi_oversold and positive_candle:
                    long_score += 15
                    long_signals.append(f"🔋 RSI {rsi:.0f}")
                
                # Volume confirmation
                if volume_surge:
                    long_score += 10
                    long_signals.append(f"Vol {volume_ratio:.1f}x")
                if volume_building:
                    long_score += 10
                    long_signals.append("📊 Accumulation")
                
                # Volatility & Momentum
                if high_volatility:
                    long_score += 10
                    long_signals.append(f"⚡ {atr_pct:.1f}%")
                if change_pct > 0.5:
                    long_score += 10
                    long_signals.append(f"🟢 +{change_pct:.1f}%")
                if change_pct > 2:
                    long_score += 10  # Extra bonus for big moves
                
                # === SHORT SCORING (expanded criteria) ===
                # Momentum continuation
                if weak_close:
                    short_score += 20
                    short_signals.append("😟 Weak Close")
                if gap_down_potential:
                    short_score += 15
                    short_signals.append("🌙 Gap Down")
                
                # Trend alignment
                if st_signal == "BEARISH":
                    short_score += 15
                    short_signals.append("📉 ST-")
                if st_crossover and st_signal == "BEARISH":
                    short_score += 15
                    short_signals.append("🔥 ST Cross")
                if below_sma:
                    short_score += 10
                    short_signals.append("<SMA20")
                
                # Breakdown patterns
                if breaking_down:
                    short_score += 20
                    short_signals.append("📉 Breaking Down")
                if near_week_low and volume_surge:
                    short_score += 15
                    short_signals.append("📊 Breakdown+Vol")
                if is_consolidating and negative_candle:
                    short_score += 15
                    short_signals.append("🎯 Consolidation")
                
                # Reversal patterns
                if at_resistance and negative_candle:
                    short_score += 20
                    short_signals.append("📍 Resistance Reject")
                if rsi_overbought and negative_candle:
                    short_score += 15
                    short_signals.append(f"⚡ RSI {rsi:.0f}")
                
                # Volume confirmation
                if volume_surge:
                    short_score += 10
                    short_signals.append(f"Vol {volume_ratio:.1f}x")
                if volume_building and change_pct < 0:
                    short_score += 10
                    short_signals.append("📊 Distribution")
                
                # Volatility & Momentum
                if high_volatility:
                    short_score += 10
                    short_signals.append(f"⚡ {atr_pct:.1f}%")
                if change_pct < -0.5:
                    short_score += 10
                    short_signals.append(f"🔴 {change_pct:.1f}%")
                if change_pct < -2:
                    short_score += 10  # Extra bonus for big moves
                
                # === BUILD SETUP DATA ===
                setup_data = {
                    "symbol": symbol,
                    "ltp": round(ltp, 2),
                    "change_pct": round(change_pct, 2),
                    "close_position": round(close_position * 100, 0),
                    "volume_ratio": round(volume_ratio, 1),
                    "atr_pct": round(atr_pct, 2),
                    "rsi": round(rsi, 1),
                    "st_signal": st_signal,
                    "today_high": round(today_high, 2),
                    "today_low": round(today_low, 2),
                    "expected_range_pct": round(expected_range_pct, 2),
                }
                
                # LONG setup (threshold 15, show more stocks)
                if long_score >= 15 and long_score > short_score:
                    setup_data["direction"] = "LONG"
                    setup_data["score"] = long_score
                    setup_data["signals"] = long_signals[:4]
                    setup_data["signal_text"] = " | ".join(long_signals[:3])
                    
                    # Tomorrow's intraday plan
                    orb_entry = round(today_high * 1.002, 2)
                    vwap_entry = round(ltp, 2)
                    stoploss = round(max(today_low * 0.998, ltp - atr * 1.2), 2)
                    target1 = round(ltp * (1 + atr_pct * 0.6 / 100), 2)
                    target2 = round(ltp * (1 + atr_pct * 1.0 / 100), 2)
                    
                    setup_data["tomorrow_plan"] = {
                        "action": "BUY",
                        "orb_entry": orb_entry,
                        "vwap_entry": vwap_entry,
                        "entry": vwap_entry,
                        "stoploss": stoploss,
                        "target1": target1,
                        "target2": target2,
                        "risk_pct": round(((vwap_entry - stoploss) / vwap_entry) * 100, 2),
                        "reward_pct": round(((target1 - vwap_entry) / vwap_entry) * 100, 2),
                        "strategy": "ORB Long" if near_week_high else "Gap & Go" if gap_up_potential else "Trend Continue"
                    }
                    
                    long_setups.append(setup_data)
                
                # SHORT setup (threshold 15, show more stocks)
                elif short_score >= 15 and short_score > long_score:
                    setup_data["direction"] = "SHORT"
                    setup_data["score"] = short_score
                    setup_data["signals"] = short_signals[:4]
                    setup_data["signal_text"] = " | ".join(short_signals[:3])
                    
                    # Tomorrow's intraday plan
                    orb_entry = round(today_low * 0.998, 2)
                    vwap_entry = round(ltp, 2)
                    stoploss = round(min(today_high * 1.002, ltp + atr * 1.2), 2)
                    target1 = round(ltp * (1 - atr_pct * 0.6 / 100), 2)
                    target2 = round(ltp * (1 - atr_pct * 1.0 / 100), 2)
                    
                    setup_data["tomorrow_plan"] = {
                        "action": "SELL",
                        "orb_entry": orb_entry,
                        "vwap_entry": vwap_entry,
                        "entry": vwap_entry,
                        "stoploss": stoploss,
                        "target1": target1,
                        "target2": target2,
                        "risk_pct": round(((stoploss - vwap_entry) / vwap_entry) * 100, 2),
                        "reward_pct": round(((vwap_entry - target1) / vwap_entry) * 100, 2),
                        "strategy": "ORB Short" if near_week_low else "Gap & Fade" if gap_down_potential else "Trend Continue"
                    }
                    
                    short_setups.append(setup_data)
                    
            except Exception as e:
                logger.debug(f"Error analyzing {symbol} for tomorrow intraday: {e}")
                continue
        
        # Sort by score
        long_setups.sort(key=lambda x: x["score"], reverse=True)
        short_setups.sort(key=lambda x: x["score"], reverse=True)
        
        # Market sentiment
        total_long = len(long_setups)
        total_short = len(short_setups)
        
        if total_long > total_short * 1.5:
            market_bias = "BULLISH"
            market_note = f"More long setups ({total_long}) than short ({total_short}) - favor BUY tomorrow"
        elif total_short > total_long * 1.5:
            market_bias = "BEARISH"
            market_note = f"More short setups ({total_short}) than long ({total_long}) - favor SELL tomorrow"
        else:
            market_bias = "NEUTRAL"
            market_note = f"Mixed - {total_long} long, {total_short} short setups"
        
        # Get tomorrow's date
        tomorrow = datetime.now() + timedelta(days=1)
        if tomorrow.weekday() >= 5:
            days_to_add = 7 - tomorrow.weekday()
            tomorrow = tomorrow + timedelta(days=days_to_add)
        
        logger.info(f"Tomorrow Intraday: Found {total_long} long, {total_short} short setups")
        
        return {
            "status": "success",
            "long_setups": long_setups[:num_stocks],
            "short_setups": short_setups[:num_stocks],
            "total_long": total_long,
            "total_short": total_short,
            "market_bias": market_bias,
            "market_note": market_note,
            "stocks_analyzed": stocks_analyzed,
            "index": index_name,
            "for_date": tomorrow.strftime("%A, %d %b %Y"),
            "generated_at": datetime.now().strftime("%I:%M %p"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get tomorrow intraday outlook: {e}")
        return {
            "status": "error",
            "long_setups": [],
            "short_setups": [],
            "error": str(e)
        }


def get_long_term_picks(index_name: str = "NIFTY 50", period: str = "6 Months", num_stocks: int = 10) -> Dict[str, Any]:
    """
    Analyze stocks for LONG-TERM investment based on selected period
    
    Uses weekly/monthly data and longer-term indicators:
    1. 50-day & 200-day Moving Averages (Golden/Death Cross)
    2. Long-term RSI (Weekly)
    3. Relative Strength vs Index
    4. Volume Accumulation over period
    5. Price performance over selected period
    6. Support/Resistance on higher timeframes
    7. Trend strength and consistency
    
    Args:
        index_name: Index to analyze
        period: Investment horizon - "1 Month", "3 Months", "6 Months", "1 Year", "2 Years", "5 Years"
        num_stocks: Number of stocks to return
    
    Returns:
        Dict with buy_picks, sell_picks, and analysis summary
    """
    try:
        # Map period to yfinance period string and description
        period_map = {
            "1 Month": ("3mo", 30, "short-term swing"),
            "3 Months": ("6mo", 90, "medium-term"),
            "6 Months": ("1y", 180, "medium-term investment"),
            "1 Year": ("2y", 365, "long-term investment"),
            "2 Years": ("5y", 730, "long-term wealth building"),
            "5 Years": ("10y", 1825, "wealth creation")
        }
        
        yf_period, days, horizon_desc = period_map.get(period, ("1y", 180, "medium-term"))
        
        stocks_to_analyze = get_stocks_for_index(index_name)
        
        # For FULL MARKET, filter stocks with price > ₹20
        min_price = 20 if index_name == "FULL MARKET" else 0
        
        buy_picks = []
        sell_picks = []
        stocks_analyzed = 0
        
        logger.info(f"Long Term Analysis: Analyzing {len(stocks_to_analyze)} stocks for {period} ({horizon_desc})")
        
        for symbol in stocks_to_analyze:
            try:
                stocks_analyzed += 1
                yahoo_symbol = get_yahoo_symbol(symbol)
                ticker = yf.Ticker(yahoo_symbol)
                
                # Get historical data based on period
                hist = ticker.history(period=yf_period, interval="1d")
                
                if hist.empty or len(hist) < 50:
                    continue
                
                # Current price
                ltp = hist['Close'].iloc[-1]
                
                # Filter by minimum price for FULL MARKET
                if ltp < min_price:
                    continue
                
                # === PRICE PERFORMANCE ===
                # Performance over different periods
                periods_back = min(len(hist) - 1, days)
                if periods_back > 0:
                    start_price = hist['Close'].iloc[-periods_back] if periods_back < len(hist) else hist['Close'].iloc[0]
                    period_return = ((ltp - start_price) / start_price) * 100
                else:
                    period_return = 0
                
                # 1 month return
                month_return = ((ltp - hist['Close'].iloc[-22]) / hist['Close'].iloc[-22]) * 100 if len(hist) >= 22 else 0
                
                # 1 week return
                week_return = ((ltp - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100 if len(hist) >= 5 else 0
                
                # === MOVING AVERAGES ===
                sma_50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else ltp
                sma_200 = hist['Close'].rolling(200).mean().iloc[-1] if len(hist) >= 200 else sma_50
                sma_20 = hist['Close'].rolling(20).mean().iloc[-1] if len(hist) >= 20 else ltp
                
                # MA signals
                above_50_sma = ltp > sma_50
                above_200_sma = ltp > sma_200
                golden_cross = sma_50 > sma_200  # 50 SMA above 200 SMA
                
                # Distance from MAs
                dist_from_50 = ((ltp - sma_50) / sma_50) * 100
                dist_from_200 = ((ltp - sma_200) / sma_200) * 100
                
                # === RSI (14-day) ===
                rsi = calculate_rsi(hist['Close'], period=14)
                
                # Weekly RSI approximation (using 5-day periods)
                weekly_closes = hist['Close'].iloc[::5]  # Every 5th day
                weekly_rsi = calculate_rsi(weekly_closes, period=14) if len(weekly_closes) >= 15 else rsi
                
                # === VOLUME ANALYSIS ===
                avg_volume_50 = hist['Volume'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else hist['Volume'].mean()
                recent_volume = hist['Volume'].tail(10).mean()
                volume_trend = recent_volume / avg_volume_50 if avg_volume_50 > 0 else 1
                
                # Accumulation: Price up + Volume up
                price_up_days = (hist['Close'].diff().tail(20) > 0).sum()
                volume_on_up_days = hist[hist['Close'].diff() > 0]['Volume'].tail(20).mean()
                volume_on_down_days = hist[hist['Close'].diff() < 0]['Volume'].tail(20).mean()
                accumulation = volume_on_up_days > volume_on_down_days * 1.2 if volume_on_down_days > 0 else False
                
                # === TREND STRENGTH ===
                # Higher highs and higher lows count
                highs = hist['High'].tail(20)
                lows = hist['Low'].tail(20)
                higher_highs = sum(1 for i in range(1, len(highs)) if highs.iloc[i] > highs.iloc[i-1])
                higher_lows = sum(1 for i in range(1, len(lows)) if lows.iloc[i] > lows.iloc[i-1])
                uptrend_strength = (higher_highs + higher_lows) / 38 * 100  # Max 38 (19+19)
                
                # === 52-WEEK HIGH/LOW ===
                high_52w = hist['High'].tail(252).max() if len(hist) >= 252 else hist['High'].max()
                low_52w = hist['Low'].tail(252).min() if len(hist) >= 252 else hist['Low'].min()
                dist_from_52w_high = ((high_52w - ltp) / high_52w) * 100
                dist_from_52w_low = ((ltp - low_52w) / low_52w) * 100
                near_52w_high = dist_from_52w_high < 5
                near_52w_low = ltp < low_52w * 1.1
                
                # === VOLATILITY ===
                returns = hist['Close'].pct_change().dropna()
                volatility = returns.std() * (252 ** 0.5) * 100  # Annualized
                
                # === SCORING ===
                bullish_score = 0
                bearish_score = 0
                bullish_signals = []
                bearish_signals = []
                
                # --- BULLISH SIGNALS ---
                # Trend
                if golden_cross:
                    bullish_score += 20
                    bullish_signals.append("🌟 Golden Cross")
                if above_200_sma:
                    bullish_score += 15
                    bullish_signals.append("📈 Above 200 SMA")
                if above_50_sma:
                    bullish_score += 10
                    bullish_signals.append("📊 Above 50 SMA")
                
                # Performance
                if period_return > 20:
                    bullish_score += 15
                    bullish_signals.append(f"🚀 +{period_return:.0f}% in {period}")
                elif period_return > 10:
                    bullish_score += 10
                    bullish_signals.append(f"📈 +{period_return:.0f}% gain")
                elif period_return > 0:
                    bullish_score += 5
                
                # Momentum
                if week_return > 3:
                    bullish_score += 10
                    bullish_signals.append("🔥 Strong week")
                if month_return > 5:
                    bullish_score += 8
                    bullish_signals.append(f"📈 +{month_return:.0f}% month")
                
                # RSI
                if 40 <= rsi <= 60:
                    bullish_score += 5  # Healthy range
                elif rsi < 40:
                    bullish_score += 10
                    bullish_signals.append("💎 Oversold RSI")
                
                # Volume
                if accumulation:
                    bullish_score += 12
                    bullish_signals.append("📊 Accumulation")
                if volume_trend > 1.3:
                    bullish_score += 8
                    bullish_signals.append("📈 Vol surge")
                
                # Near support (good entry)
                if dist_from_50 < 3 and dist_from_50 > -5:
                    bullish_score += 8
                    bullish_signals.append("🎯 Near 50 SMA")
                
                # 52-week breakout
                if near_52w_high:
                    bullish_score += 15
                    bullish_signals.append("🏆 52W High")
                
                # Uptrend strength
                if uptrend_strength > 60:
                    bullish_score += 10
                    bullish_signals.append("💪 Strong uptrend")
                
                # --- BEARISH SIGNALS ---
                # Death cross
                if not golden_cross and len(hist) >= 200:
                    bearish_score += 20
                    bearish_signals.append("☠️ Death Cross")
                
                # Below MAs
                if not above_200_sma:
                    bearish_score += 15
                    bearish_signals.append("📉 Below 200 SMA")
                if not above_50_sma:
                    bearish_score += 10
                    bearish_signals.append("📊 Below 50 SMA")
                
                # Performance
                if period_return < -20:
                    bearish_score += 15
                    bearish_signals.append(f"📉 {period_return:.0f}% loss")
                elif period_return < -10:
                    bearish_score += 10
                    bearish_signals.append(f"📉 Declining")
                elif period_return < 0:
                    bearish_score += 5
                
                # Momentum
                if week_return < -5:
                    bearish_score += 10
                    bearish_signals.append("🔻 Weak week")
                if month_return < -10:
                    bearish_score += 8
                    bearish_signals.append(f"📉 {month_return:.0f}% month")
                
                # RSI overbought
                if rsi > 75:
                    bearish_score += 12
                    bearish_signals.append("⚠️ Overbought")
                
                # Distribution
                if not accumulation and volume_trend > 1.3:
                    bearish_score += 10
                    bearish_signals.append("📊 Distribution")
                
                # Near 52-week low
                if near_52w_low:
                    bearish_score += 12
                    bearish_signals.append("⚠️ Near 52W Low")
                
                # High volatility (risky)
                if volatility > 50:
                    bearish_score += 5
                    bearish_signals.append("⚡ High volatility")
                
                # === CREATE STOCK DATA ===
                stock_data = {
                    "symbol": symbol,
                    "ltp": round(ltp, 2),
                    "period_return": round(period_return, 2),
                    "month_return": round(month_return, 2),
                    "week_return": round(week_return, 2),
                    "sma_50": round(sma_50, 2),
                    "sma_200": round(sma_200, 2),
                    "dist_from_50": round(dist_from_50, 2),
                    "dist_from_200": round(dist_from_200, 2),
                    "rsi": round(rsi, 1),
                    "weekly_rsi": round(weekly_rsi, 1),
                    "volume_trend": round(volume_trend, 2),
                    "volatility": round(volatility, 1),
                    "high_52w": round(high_52w, 2),
                    "low_52w": round(low_52w, 2),
                    "dist_from_52w_high": round(dist_from_52w_high, 2),
                    "golden_cross": golden_cross,
                    "above_200_sma": above_200_sma,
                    "accumulation": accumulation,
                    "uptrend_strength": round(uptrend_strength, 1)
                }
                
                # Classify and add targets
                if bullish_score >= 35 and bullish_score > bearish_score:
                    stock_data["score"] = bullish_score
                    stock_data["signals"] = bullish_signals[:5]
                    stock_data["signal_text"] = " | ".join(bullish_signals[:4])
                    stock_data["recommendation"] = "BUY"
                    
                    # Long-term targets based on resistance and performance
                    entry = round(ltp, 2)
                    stoploss = round(min(sma_50 * 0.95, ltp * 0.9), 2)
                    
                    # Target based on period
                    if period in ["1 Year", "2 Years", "5 Years"]:
                        target1 = round(ltp * 1.20, 2)  # 20% target
                        target2 = round(ltp * 1.40, 2)  # 40% target
                    elif period in ["6 Months"]:
                        target1 = round(ltp * 1.12, 2)  # 12% target
                        target2 = round(ltp * 1.20, 2)  # 20% target
                    else:
                        target1 = round(ltp * 1.08, 2)  # 8% target
                        target2 = round(ltp * 1.15, 2)  # 15% target
                    
                    # Use 52-week high as potential target
                    if high_52w > target1:
                        target1 = round(min(high_52w * 0.98, target2), 2)
                    
                    stock_data["entry"] = entry
                    stock_data["stoploss"] = stoploss
                    stock_data["target1"] = target1
                    stock_data["target2"] = target2
                    stock_data["potential_return"] = round(((target1 - entry) / entry) * 100, 2)
                    stock_data["risk_pct"] = round(((entry - stoploss) / entry) * 100, 2)
                    
                    buy_picks.append(stock_data)
                    
                elif bearish_score >= 35 and bearish_score > bullish_score:
                    stock_data["score"] = bearish_score
                    stock_data["signals"] = bearish_signals[:5]
                    stock_data["signal_text"] = " | ".join(bearish_signals[:4])
                    stock_data["recommendation"] = "AVOID/SELL"
                    
                    # Downside targets
                    stock_data["warning"] = "Consider exiting or avoiding"
                    stock_data["support1"] = round(sma_50 * 0.95, 2) if above_50_sma else round(low_52w, 2)
                    stock_data["support2"] = round(low_52w, 2)
                    stock_data["potential_downside"] = round(dist_from_52w_high, 2)
                    
                    sell_picks.append(stock_data)
                    
            except Exception as e:
                logger.debug(f"Error analyzing {symbol} for long-term: {e}")
                continue
        
        # Sort by score
        buy_picks.sort(key=lambda x: x["score"], reverse=True)
        sell_picks.sort(key=lambda x: x["score"], reverse=True)
        
        # === MARKET SUMMARY ===
        total_buys = len(buy_picks)
        total_sells = len(sell_picks)
        
        if total_buys > total_sells * 2:
            market_sentiment = "BULLISH"
            sentiment_note = f"Strong buying opportunities ({total_buys} stocks)"
        elif total_sells > total_buys * 2:
            market_sentiment = "BEARISH"
            sentiment_note = f"Caution advised ({total_sells} stocks to avoid)"
        elif total_buys > total_sells:
            market_sentiment = "MODERATELY BULLISH"
            sentiment_note = f"More buys ({total_buys}) than sells ({total_sells})"
        elif total_sells > total_buys:
            market_sentiment = "MODERATELY BEARISH"
            sentiment_note = f"More sells ({total_sells}) than buys ({total_buys})"
        else:
            market_sentiment = "NEUTRAL"
            sentiment_note = "Mixed signals across the market"
        
        logger.info(f"Long Term: Found {total_buys} buy picks, {total_sells} avoid/sell for {period}")
        
        return {
            "status": "success",
            "buy_picks": buy_picks[:num_stocks],
            "sell_picks": sell_picks[:num_stocks],
            "total_buys": total_buys,
            "total_sells": total_sells,
            "market_sentiment": market_sentiment,
            "sentiment_note": sentiment_note,
            "period": period,
            "horizon": horizon_desc,
            "stocks_analyzed": stocks_analyzed,
            "index": index_name,
            "generated_at": datetime.now().strftime("%I:%M %p, %d %b %Y"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get long-term picks: {e}")
        return {
            "status": "error",
            "buy_picks": [],
            "sell_picks": [],
            "error": str(e)
        }


def calculate_bollinger_bands(close: pd.Series, period: int = 20, std_dev: float = 2.0) -> Dict[str, Any]:
    """
    Calculate Bollinger Bands
    
    Returns:
        Dict with upper, middle, lower bands and signals
    """
    if len(close) < period:
        return {"upper": close.iloc[-1], "middle": close.iloc[-1], "lower": close.iloc[-1], 
                "signal": "NEUTRAL", "bandwidth": 0, "percent_b": 50}
    
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    current_price = close.iloc[-1]
    current_upper = upper.iloc[-1]
    current_lower = lower.iloc[-1]
    current_middle = middle.iloc[-1]
    
    # Bandwidth (volatility measure)
    bandwidth = ((current_upper - current_lower) / current_middle) * 100
    
    # %B (position within bands)
    percent_b = ((current_price - current_lower) / (current_upper - current_lower)) * 100 if (current_upper - current_lower) > 0 else 50
    
    # Signal
    if current_price <= current_lower:
        signal = "OVERSOLD"
    elif current_price >= current_upper:
        signal = "OVERBOUGHT"
    elif current_price > current_middle:
        signal = "BULLISH"
    elif current_price < current_middle:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"
    
    # Squeeze detection (low bandwidth)
    avg_bandwidth = ((upper - lower) / middle * 100).rolling(50).mean().iloc[-1] if len(close) >= 50 else bandwidth
    squeeze = bandwidth < avg_bandwidth * 0.75
    
    return {
        "upper": round(current_upper, 2),
        "middle": round(current_middle, 2),
        "lower": round(current_lower, 2),
        "signal": signal,
        "bandwidth": round(bandwidth, 2),
        "percent_b": round(percent_b, 1),
        "squeeze": squeeze
    }


def get_multi_timeframe_signals(index_name: str = "NIFTY 50", num_stocks: int = 6) -> Dict[str, Any]:
    """
    Multi-Timeframe Intraday Strategy
    
    Confirms trades using VWAP, Supertrend, and Bollinger Bands across:
    - 5-minute timeframe (entry timing)
    - 15-minute timeframe (trend confirmation)
    - Combined signal strength
    
    Only gives signals when ALL timeframes align!
    
    Returns:
        Dict with long_signals, short_signals, and analysis details
    """
    try:
        # Get market time context
        time_context = get_market_time_context()
        target_multiplier = time_context["target_multiplier"]
        
        # Allow analysis even outside market hours (for preparation)
        # Just show a warning but still generate signals
        market_warning = None
        if not time_context["can_trade"]:
            market_warning = time_context.get("warning", "Market closed - showing last available data")
        
        stocks_to_analyze = get_stocks_for_index(index_name)
        
        # For FULL MARKET, filter stocks > ₹20
        min_price = 20 if index_name == "FULL MARKET" else 0
        
        long_signals = []
        short_signals = []
        stocks_analyzed = 0
        
        logger.info(f"Multi-TF Strategy: Analyzing {len(stocks_to_analyze)} stocks from {index_name}")
        
        for symbol in stocks_to_analyze:
            try:
                stocks_analyzed += 1
                yahoo_symbol = get_yahoo_symbol(symbol)
                ticker = yf.Ticker(yahoo_symbol)
                
                # Get data for different timeframes
                # 5-minute data (5 days for other indicators)
                hist_5m_full = ticker.history(period="5d", interval="5m")
                
                if hist_5m_full.empty or len(hist_5m_full) < 50:
                    continue
                
                # ============== EXTRACT TODAY'S DATA FOR INTRADAY INDICATORS ==============
                # Supertrend and VWAP should be calculated on TODAY's data only
                from datetime import datetime
                import pytz
                IST = pytz.timezone('Asia/Kolkata')
                today = datetime.now(IST).date()
                
                # Filter for today's candles only
                hist_5m_today = hist_5m_full[hist_5m_full.index.date == today].copy()
                
                # Need at least 10 candles for Supertrend (starts calculating at 10:05 AM)
                if len(hist_5m_today) < 10:
                    logger.debug(f"Skipping {symbol}: Not enough today's candles ({len(hist_5m_today)} < 10)")
                    continue
                
                # Use full data for general analysis, today's data for intraday indicators
                hist_5m = hist_5m_full  # Keep full data for reference
                
                # 10-minute data (from TODAY only)
                hist_10m = hist_5m_today.resample('10min').agg({
                    'Open': 'first',
                    'High': 'max',
                    'Low': 'min',
                    'Close': 'last',
                    'Volume': 'sum'
                }).dropna()
                
                if hist_10m.empty or len(hist_10m) < 5:
                    continue
                
                ltp = hist_5m_today['Close'].iloc[-1]
                
                # Filter by minimum price
                if ltp < min_price:
                    continue
                
                # ============== 5-MINUTE ANALYSIS (TODAY'S DATA) ==============
                # VWAP (5m) - calculated on TODAY's data for intraday relevance
                vwap_5m_data = calculate_vwap(hist_5m_today['High'], hist_5m_today['Low'], hist_5m_today['Close'], hist_5m_today['Volume'])
                vwap_5m = vwap_5m_data.get("vwap", ltp)
                vwap_5m_signal = vwap_5m_data.get("signal", "NEUTRAL")
                vwap_5m_dist = vwap_5m_data.get("distance_pct", 0)
                
                # Supertrend (5m) - calculated on TODAY's data only
                st_5m_data = calculate_supertrend_simple(hist_5m_today['High'], hist_5m_today['Low'], hist_5m_today['Close'])
                st_5m_signal = st_5m_data.get("signal", "NEUTRAL")
                st_5m_value = st_5m_data.get("value", ltp)
                st_5m_crossover = st_5m_data.get("crossover", False)
                
                # Bollinger Bands (5m) - using today's data
                bb_5m_data = calculate_bollinger_bands(hist_5m_today['Close'], period=20)
                bb_5m_signal = bb_5m_data.get("signal", "NEUTRAL")
                bb_5m_upper = bb_5m_data.get("upper", ltp)
                bb_5m_lower = bb_5m_data.get("lower", ltp)
                bb_5m_middle = bb_5m_data.get("middle", ltp)
                bb_5m_squeeze = bb_5m_data.get("squeeze", False)
                bb_5m_pct_b = bb_5m_data.get("percent_b", 50)
                
                # ============== 10-MINUTE ANALYSIS ==============
                # VWAP (10m)
                vwap_10m_data = calculate_vwap(hist_10m['High'], hist_10m['Low'], hist_10m['Close'], hist_10m['Volume'])
                vwap_10m = vwap_10m_data.get("vwap", ltp)
                vwap_10m_signal = vwap_10m_data.get("signal", "NEUTRAL")
                
                # Supertrend (10m)
                st_10m_data = calculate_supertrend_simple(hist_10m['High'], hist_10m['Low'], hist_10m['Close'])
                st_10m_signal = st_10m_data.get("signal", "NEUTRAL")
                st_10m_value = st_10m_data.get("value", ltp)
                st_10m_crossover = st_10m_data.get("crossover", False)
                
                # Bollinger Bands (10m)
                bb_10m_data = calculate_bollinger_bands(hist_10m['Close'], period=20)
                bb_10m_signal = bb_10m_data.get("signal", "NEUTRAL")
                bb_10m_squeeze = bb_10m_data.get("squeeze", False)
                
                # ============== RSI & VOLUME (TODAY'S DATA) ==============
                rsi_5m = calculate_rsi(hist_5m_today['Close'], period=14)
                rsi_10m = calculate_rsi(hist_10m['Close'], period=14)
                
                # Volume comparison: today's vs historical average
                avg_volume = hist_5m_full['Volume'].rolling(50).mean().iloc[-1]  # Use full data for avg
                current_volume = hist_5m_today['Volume'].tail(5).mean()  # Today's recent volume
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
                
                # ============== ATR FOR TARGETS (TODAY'S DATA) ==============
                atr_5m = calculate_atr(hist_5m_today['High'], hist_5m_today['Low'], hist_5m_today['Close'], period=14)
                atr_pct = (atr_5m / ltp) * 100
                
                # ============== ADVANCED INDICATORS (TODAY'S DATA) ==============
                # ADX - Trend Strength Measurement (DI Length=10, ADX Smoothing=10 for balanced response)
                adx_data = calculate_adx(hist_5m_today['High'], hist_5m_today['Low'], hist_5m_today['Close'], 
                                         di_length=10, adx_smoothing=10)
                adx_value = adx_data.get("adx", 0)
                adx_trend_strength = adx_data.get("trend_strength", "WEAK")
                adx_weakening = adx_data.get("weakening", False)
                adx_rising = adx_data.get("rising", False)
                adx_flat = adx_data.get("flat", False)
                adx_no_trend = adx_data.get("no_trend", False)
                adx_change = adx_data.get("adx_change", 0)
                adx_direction = adx_data.get("trend_direction", "NEUTRAL")
                plus_di = adx_data.get("plus_di", 0)
                minus_di = adx_data.get("minus_di", 0)
                prev_plus_di = adx_data.get("prev_plus_di", 0)
                prev_minus_di = adx_data.get("prev_minus_di", 0)
                di_gap = adx_data.get("di_gap", 0)
                prev_di_gap = adx_data.get("prev_di_gap", 0)
                di_gap_change = adx_data.get("di_gap_change", 0)
                di_gap_narrowing = adx_data.get("di_gap_narrowing", False)
                di_gap_widening = adx_data.get("di_gap_widening", False)
                
                # ============== CRITICAL NaN CHECK ==============
                # Skip stock if ADX or Supertrend are not calculated (not enough data)
                # This prevents false signals at market open
                import math
                if (math.isnan(adx_value) or adx_value == 0 or 
                    math.isnan(st_5m_value) or st_5m_signal == "NEUTRAL" or
                    math.isnan(atr_5m) or atr_5m == 0):
                    logger.debug(f"Skipping {symbol}: Indicators not ready (ADX={adx_value}, ST={st_5m_value})")
                    continue  # Skip - indicators not calculated yet
                
                # ROC - Rate of Change / Momentum Divergence (TODAY'S DATA)
                roc_data = calculate_roc(hist_5m_today['Close'], period=10)
                roc_value = roc_data.get("roc", 0)
                roc_signal = roc_data.get("signal", "NEUTRAL")
                roc_bearish_divergence = roc_data.get("bearish_divergence", False)
                roc_bullish_divergence = roc_data.get("bullish_divergence", False)
                roc_weakening = roc_data.get("weakening", False)
                
                # Advanced Bollinger Bands - Squeeze, Walk, Curl (TODAY'S DATA)
                bb_adv_5m = calculate_bb_advanced(hist_5m_today['Close'], period=20)
                bb_squeeze = bb_adv_5m.get("squeeze", False)
                bb_walking_upper = bb_adv_5m.get("walking_upper", False)
                bb_walking_lower = bb_adv_5m.get("walking_lower", False)
                bb_curling_down = bb_adv_5m.get("curling_down", False)
                bb_curling_up = bb_adv_5m.get("curling_up", False)
                bb_percent_b = bb_adv_5m.get("percent_b", 50)
                
                # VWAP Distance - Rubber Band Effect (TODAY'S DATA)
                vwap_dist_data = calculate_vwap_distance(
                    hist_5m_today['High'], hist_5m_today['Low'], hist_5m_today['Close'], hist_5m_today['Volume']
                )
                vwap_overextended_up = vwap_dist_data.get("overextended_up", False)
                vwap_overextended_down = vwap_dist_data.get("overextended_down", False)
                vwap_extreme_up = vwap_dist_data.get("extreme_up", False)
                vwap_extreme_down = vwap_dist_data.get("extreme_down", False)
                vwap_rubber_band_signal = vwap_dist_data.get("signal", "NEUTRAL")
                
                # Day's high/low
                today = datetime.now().date()
                if hist_5m.index.tz is not None:
                    today_data = hist_5m[hist_5m.index.date == today]
                else:
                    today_data = hist_5m.tail(75)
                
                if len(today_data) > 0:
                    day_high = today_data['High'].max()
                    day_low = today_data['Low'].min()
                    day_open = today_data['Open'].iloc[0]
                else:
                    day_high = hist_5m['High'].tail(75).max()
                    day_low = hist_5m['Low'].tail(75).min()
                    day_open = hist_5m['Open'].iloc[-75]
                
                change_pct = ((ltp - day_open) / day_open) * 100
                
                # ============== MULTI-TIMEFRAME CONFIRMATION ==============
                # LONG CONFIRMATION
                long_confirmations = 0
                long_reasons = []
                long_warnings = []
                
                # 5m confirmations
                if vwap_5m_signal == "BULLISH":
                    long_confirmations += 1
                    long_reasons.append("5m >VWAP")
                if st_5m_signal == "BULLISH":
                    long_confirmations += 1
                    if st_5m_crossover:
                        long_confirmations += 1
                        long_reasons.append("🔥 5m ST Cross")
                    else:
                        long_reasons.append("5m ST+")
                if bb_5m_signal in ["OVERSOLD", "BULLISH"]:
                    long_confirmations += 1
                    if bb_5m_signal == "OVERSOLD":
                        long_reasons.append("5m BB Oversold")
                    else:
                        long_reasons.append("5m >BB Mid")
                
                # 10m confirmations
                if vwap_10m_signal == "BULLISH":
                    long_confirmations += 1
                    long_reasons.append("10m >VWAP")
                if st_10m_signal == "BULLISH":
                    long_confirmations += 1
                    if st_10m_crossover:
                        long_confirmations += 1
                        long_reasons.append("🔥 10m ST Cross")
                    else:
                        long_reasons.append("10m ST+")
                if bb_10m_signal in ["OVERSOLD", "BULLISH"]:
                    long_confirmations += 1
                
                # ============== ADVANCED LONG CONFIRMATIONS ==============
                # ADX - Strong bullish trend ONLY if ADX is RISING
                if adx_value >= 25 and adx_direction == "BULLISH" and plus_di > minus_di:
                    if adx_rising:
                        # ADX rising = trend strengthening = BEST signal
                        long_confirmations += 2
                        long_reasons.append(f"🔥 ADX Rising {adx_value:.0f}")
                    elif not adx_weakening and not adx_flat:
                        # ADX stable but strong
                        long_confirmations += 1
                        long_reasons.append(f"ADX {adx_value:.0f}")
                    # If ADX is flat or falling, no confirmation bonus
                
                # ROC - Bullish momentum or bullish divergence
                if roc_signal == "BULLISH" and not roc_weakening:
                    long_confirmations += 1
                    long_reasons.append("ROC+")
                if roc_bullish_divergence:
                    long_confirmations += 2  # Divergence is strong signal
                    long_reasons.append("🔥 ROC Bull Divergence")
                
                # BB Squeeze - Breakout potential
                if bb_squeeze and st_5m_signal == "BULLISH":
                    long_confirmations += 1
                    long_reasons.append("🎯 BB Squeeze")
                
                # BB Curling up from lower band (reversal from oversold)
                if bb_curling_up:
                    long_confirmations += 1
                    long_reasons.append("BB Curl Up")
                
                # VWAP Overextended DOWN = Rubber band snap UP (mean reversion long)
                if vwap_overextended_down and st_5m_signal == "BULLISH":
                    long_confirmations += 1
                    long_reasons.append("🎯 VWAP Snap")
                
                # ============== LONG WARNINGS (RISK FACTORS) ==============
                # ADX weakening = trend fading - STRONG WARNING
                if adx_weakening and adx_direction == "BULLISH":
                    long_warnings.append(f"⚠️ ADX Falling ({adx_change:+.1f})")
                    long_confirmations -= 2  # Stronger penalty
                
                # ADX flat = no momentum - CAUTION
                if adx_flat and adx_value >= 20:
                    long_warnings.append("⚠️ ADX Flat")
                    long_confirmations -= 1
                
                # ADX too low = NO TREND - MAJOR WARNING
                if adx_no_trend:
                    long_warnings.append(f"⛔ No Trend (ADX {adx_value:.0f})")
                    long_confirmations -= 2  # Strong penalty for no trend
                
                # ROC bearish divergence = price rising but momentum falling
                if roc_bearish_divergence:
                    long_warnings.append("⚠️ ROC Divergence")
                    long_confirmations -= 2  # Strong warning
                
                # BB Walking upper band = may be exhausted
                if bb_walking_upper and bb_curling_down:
                    long_warnings.append("⚠️ BB Curl Down")
                    long_confirmations -= 1
                
                # VWAP overextended UP = too stretched, may snap back
                if vwap_overextended_up or vwap_extreme_up:
                    long_warnings.append("⚠️ VWAP Stretched")
                    long_confirmations -= 1
                
                # SHORT CONFIRMATION
                short_confirmations = 0
                short_reasons = []
                short_warnings = []
                
                # 5m confirmations
                if vwap_5m_signal == "BEARISH":
                    short_confirmations += 1
                    short_reasons.append("5m <VWAP")
                if st_5m_signal == "BEARISH":
                    short_confirmations += 1
                    if st_5m_crossover:
                        short_confirmations += 1
                        short_reasons.append("🔥 5m ST Cross")
                    else:
                        short_reasons.append("5m ST-")
                if bb_5m_signal in ["OVERBOUGHT", "BEARISH"]:
                    short_confirmations += 1
                    if bb_5m_signal == "OVERBOUGHT":
                        short_reasons.append("5m BB Overbought")
                    else:
                        short_reasons.append("5m <BB Mid")
                
                # 10m confirmations
                if vwap_10m_signal == "BEARISH":
                    short_confirmations += 1
                    short_reasons.append("10m <VWAP")
                if st_10m_signal == "BEARISH":
                    short_confirmations += 1
                    if st_10m_crossover:
                        short_confirmations += 1
                        short_reasons.append("🔥 10m ST Cross")
                    else:
                        short_reasons.append("10m ST-")
                if bb_10m_signal in ["OVERBOUGHT", "BEARISH"]:
                    short_confirmations += 1
                
                # ============== ADVANCED SHORT CONFIRMATIONS ==============
                # ADX - Strong bearish trend ONLY if ADX is RISING
                if adx_value >= 25 and adx_direction == "BEARISH" and minus_di > plus_di:
                    if adx_rising:
                        # ADX rising = trend strengthening = BEST signal
                        short_confirmations += 2
                        short_reasons.append(f"🔥 ADX Rising {adx_value:.0f}")
                    elif not adx_weakening and not adx_flat:
                        # ADX stable but strong
                        short_confirmations += 1
                        short_reasons.append(f"ADX {adx_value:.0f}")
                    # If ADX is flat or falling, no confirmation bonus
                
                # ROC - Bearish momentum or bearish divergence
                if roc_signal == "BEARISH" and not roc_weakening:
                    short_confirmations += 1
                    short_reasons.append("ROC-")
                if roc_bearish_divergence:
                    short_confirmations += 2  # Divergence is strong signal
                    short_reasons.append("🔥 ROC Bear Divergence")
                
                # BB Squeeze - Breakout potential (for shorts)
                if bb_squeeze and st_5m_signal == "BEARISH":
                    short_confirmations += 1
                    short_reasons.append("🎯 BB Squeeze")
                
                # BB Curling down from upper band (reversal from overbought)
                if bb_curling_down:
                    short_confirmations += 1
                    short_reasons.append("BB Curl Down")
                
                # VWAP Overextended UP = Rubber band snap DOWN (mean reversion short)
                if vwap_overextended_up and st_5m_signal == "BEARISH":
                    short_confirmations += 1
                    short_reasons.append("🎯 VWAP Snap")
                
                # ============== SHORT WARNINGS (RISK FACTORS) ==============
                # ADX weakening = trend fading - STRONG WARNING
                if adx_weakening and adx_direction == "BEARISH":
                    short_warnings.append(f"⚠️ ADX Falling ({adx_change:+.1f})")
                    short_confirmations -= 2  # Stronger penalty
                
                # ADX flat = no momentum - CAUTION
                if adx_flat and adx_value >= 20:
                    short_warnings.append("⚠️ ADX Flat")
                    short_confirmations -= 1
                
                # ADX too low = NO TREND - MAJOR WARNING
                if adx_no_trend:
                    short_warnings.append(f"⛔ No Trend (ADX {adx_value:.0f})")
                    short_confirmations -= 2  # Strong penalty for no trend
                
                # ROC bullish divergence = price falling but momentum rising
                if roc_bullish_divergence:
                    short_warnings.append("⚠️ ROC Divergence")
                    short_confirmations -= 2
                
                # BB Walking lower band = may be exhausted
                if bb_walking_lower and bb_curling_up:
                    short_warnings.append("⚠️ BB Curl Up")
                    short_confirmations -= 1
                
                # VWAP overextended DOWN = too stretched, may snap back up
                if vwap_overextended_down or vwap_extreme_down:
                    short_warnings.append("⚠️ VWAP Stretched")
                    short_confirmations -= 1
                
                # ============== SIGNAL GENERATION ==============
                # Need at least 4 confirmations for a signal (relaxed for more signals)
                min_confirmations = 4
                
                signal_data = {
                    "symbol": symbol,
                    "ltp": round(ltp, 2),
                    "change_pct": round(change_pct, 2),
                    "day_high": round(day_high, 2),
                    "day_low": round(day_low, 2),
                    # 5m indicators
                    "vwap_5m": round(vwap_5m, 2),
                    "vwap_5m_signal": vwap_5m_signal,
                    "vwap_5m_dist": round(vwap_5m_dist, 2),
                    "st_5m_signal": st_5m_signal,
                    "st_5m_value": round(st_5m_value, 2),
                    "st_5m_crossover": st_5m_crossover,
                    "bb_5m_signal": bb_5m_signal,
                    "bb_5m_upper": round(bb_5m_upper, 2),
                    "bb_5m_lower": round(bb_5m_lower, 2),
                    "bb_5m_middle": round(bb_5m_middle, 2),
                    "bb_5m_squeeze": bb_5m_squeeze,
                    # 10m indicators
                    "vwap_10m": round(vwap_10m, 2),
                    "vwap_10m_signal": vwap_10m_signal,
                    "st_10m_signal": st_10m_signal,
                    "st_10m_value": round(st_10m_value, 2),
                    "st_10m_crossover": st_10m_crossover,
                    "bb_10m_signal": bb_10m_signal,
                    "bb_10m_squeeze": bb_10m_squeeze,
                    # Other
                    "rsi_5m": round(rsi_5m, 1),
                    "rsi_10m": round(rsi_10m, 1),
                    "volume_ratio": round(volume_ratio, 2),
                    "atr_pct": round(atr_pct, 2),
                    # ADVANCED INDICATORS
                    "adx": round(adx_value, 1),
                    "adx_strength": adx_trend_strength,
                    "adx_direction": adx_direction,
                    "adx_rising": adx_rising,
                    "adx_weakening": adx_weakening,
                    "adx_flat": adx_flat,
                    "adx_no_trend": adx_no_trend,
                    "adx_change": round(adx_change, 1),
                    "plus_di": round(plus_di, 1),
                    "minus_di": round(minus_di, 1),
                    "di_gap": round(di_gap, 1),
                    "di_gap_change": round(di_gap_change, 1),
                    "di_gap_narrowing": di_gap_narrowing,
                    "di_gap_widening": di_gap_widening,
                    "roc": round(roc_value, 2),
                    "roc_signal": roc_signal,
                    "roc_bearish_div": roc_bearish_divergence,
                    "roc_bullish_div": roc_bullish_divergence,
                    "roc_weakening": roc_weakening,
                    "bb_squeeze": bb_squeeze,
                    "bb_walking_upper": bb_walking_upper,
                    "bb_walking_lower": bb_walking_lower,
                    "bb_curling_down": bb_curling_down,
                    "bb_curling_up": bb_curling_up,
                    "bb_percent_b": round(bb_percent_b, 1),
                    "vwap_overextended_up": vwap_overextended_up,
                    "vwap_overextended_down": vwap_overextended_down,
                    "vwap_extreme_up": vwap_extreme_up,
                    "vwap_extreme_down": vwap_extreme_down
                }
                
                # ============== HARD ADX FILTER ==============
                # STRICT: Only allow signals when ADX is RISING (trend strengthening)
                # This prevents false signals in choppy/sideways markets
                adx_blocks_long = False
                adx_blocks_short = False
                
                # RULE 0: ADX must be a valid number (not NaN) - CRITICAL CHECK
                # This prevents signals when indicators haven't calculated yet (e.g., market open)
                import math
                if math.isnan(adx_value) or adx_value == 0:
                    adx_blocks_long = True
                    adx_blocks_short = True
                    long_warnings.append("⛔ BLOCKED: ADX Not Ready (NaN)")
                    short_warnings.append("⛔ BLOCKED: ADX Not Ready (NaN)")
                
                # RULE 1: ADX must be >= 20 (minimum trend strength)
                elif adx_no_trend:
                    adx_blocks_long = True
                    adx_blocks_short = True
                    long_warnings.append(f"⛔ BLOCKED: No Trend (ADX {adx_value:.0f} < 20)")
                    short_warnings.append(f"⛔ BLOCKED: No Trend (ADX {adx_value:.0f} < 20)")
                
                # RULE 2: ADX must NOT be falling (trend must not be weakening)
                elif adx_weakening:
                    adx_blocks_long = True
                    adx_blocks_short = True
                    long_warnings.append(f"⛔ BLOCKED: ADX Falling ({adx_change:+.1f})")
                    short_warnings.append(f"⛔ BLOCKED: ADX Falling ({adx_change:+.1f})")
                
                # RULE 3: ADX must be RISING (except if already very strong >= 30)
                elif not adx_rising and adx_value < 30:
                    adx_blocks_long = True
                    adx_blocks_short = True
                    long_warnings.append(f"⛔ BLOCKED: ADX Not Rising ({adx_value:.0f}, {adx_change:+.1f})")
                    short_warnings.append(f"⛔ BLOCKED: ADX Not Rising ({adx_value:.0f}, {adx_change:+.1f})")
                
                # ============== NEW RULE 4: ADX EXHAUSTION FILTER ==============
                # When ADX > 80, the trend is likely exhausted and may reverse
                # This catches late entries into overextended trends (like HAPPSTMNDS at ADX 91.6)
                if adx_value > 80:
                    adx_blocks_long = True
                    adx_blocks_short = True
                    long_warnings.append(f"⛔ BLOCKED: ADX Exhausted ({adx_value:.0f} > 80 - trend may reverse)")
                    short_warnings.append(f"⛔ BLOCKED: ADX Exhausted ({adx_value:.0f} > 80 - trend may reverse)")
                
                # ============== NEW RULE 5: DI GAP NARROWING FILTER ==============
                # If the gap between +DI and -DI is shrinking, momentum is weakening
                # This catches trades like ONGC and HCLTECH where DI crossover happened shortly after entry
                if di_gap_narrowing and di_gap < 15:
                    # DI gap is narrowing AND gap is small (< 15 points) = momentum shift likely
                    adx_blocks_long = True
                    adx_blocks_short = True
                    long_warnings.append(f"⛔ BLOCKED: DI Gap Narrowing ({di_gap:.0f}, {di_gap_change:+.1f} - momentum weakening)")
                    short_warnings.append(f"⛔ BLOCKED: DI Gap Narrowing ({di_gap:.0f}, {di_gap_change:+.1f} - momentum weakening)")
                elif di_gap_narrowing and not di_gap_widening:
                    # DI gap is narrowing but still decent - add warning but don't block
                    long_warnings.append(f"⚠️ CAUTION: DI Gap Shrinking ({di_gap:.0f}, {di_gap_change:+.1f})")
                    short_warnings.append(f"⚠️ CAUTION: DI Gap Shrinking ({di_gap:.0f}, {di_gap_change:+.1f})")
                
                # ============== HARD SUPERTREND FILTER ==============
                # STRICT: Supertrend direction MUST match signal direction
                # This prevents SHORT signals when trend is BULLISH (and vice versa)
                st_blocks_long = False
                st_blocks_short = False
                
                # For LONG: Both 5m AND 10m Supertrend must be BULLISH
                if st_5m_signal != "BULLISH":
                    st_blocks_long = True
                    long_warnings.append(f"⛔ BLOCKED: 5m ST not Bullish ({st_5m_signal})")
                if st_10m_signal != "BULLISH":
                    st_blocks_long = True
                    long_warnings.append(f"⛔ BLOCKED: 10m ST not Bullish ({st_10m_signal})")
                
                # For SHORT: Both 5m AND 10m Supertrend must be BEARISH
                if st_5m_signal != "BEARISH":
                    st_blocks_short = True
                    short_warnings.append(f"⛔ BLOCKED: 5m ST not Bearish ({st_5m_signal})")
                if st_10m_signal != "BEARISH":
                    st_blocks_short = True
                    short_warnings.append(f"⛔ BLOCKED: 10m ST not Bearish ({st_10m_signal})")
                
                if long_confirmations >= min_confirmations and long_confirmations > short_confirmations and not adx_blocks_long and not st_blocks_long:
                    signal_data["signal"] = "LONG"
                    signal_data["confirmations"] = long_confirmations
                    signal_data["reasons"] = long_reasons[:6]
                    signal_data["reason_text"] = " | ".join(long_reasons[:5])
                    signal_data["warnings"] = long_warnings
                    signal_data["warning_text"] = " | ".join(long_warnings) if long_warnings else ""
                    
                    # Confidence based on confirmations
                    if long_confirmations >= 8:
                        signal_data["confidence"] = "VERY HIGH"
                        signal_data["confidence_pct"] = 90
                    elif long_confirmations >= 7:
                        signal_data["confidence"] = "HIGH"
                        signal_data["confidence_pct"] = 80
                    elif long_confirmations >= 6:
                        signal_data["confidence"] = "GOOD"
                        signal_data["confidence_pct"] = 70
                    else:
                        signal_data["confidence"] = "MODERATE"
                        signal_data["confidence_pct"] = 60
                    
                    # Entry & Targets for LONG (relaxed entry - small pullback from current)
                    # Simple logic: Use VWAP/ST if close, otherwise small 0.15% pullback
                    
                    # Check if VWAP is a good nearby entry (within 0.5% below current)
                    vwap_diff_pct = ((ltp - vwap_5m) / ltp) * 100 if ltp > 0 else 0
                    
                    if vwap_5m < ltp and 0.1 < vwap_diff_pct < 0.5:
                        # VWAP is close below - use it as entry
                        entry = round(vwap_5m, 2)
                        entry_type = "VWAP"
                    elif st_5m_value < ltp and 0.1 < ((ltp - st_5m_value) / ltp) * 100 < 0.5:
                        # Supertrend support is close below - use it
                        entry = round(st_5m_value, 2)
                        entry_type = "ST Support"
                    else:
                        # Default: Small 0.15% pullback (easy to achieve)
                        entry = round(ltp * 0.9985, 2)
                        entry_type = "Limit"
                    
                    signal_data["entry_type"] = entry_type
                    signal_data["current_price"] = round(ltp, 2)
                    
                    # Use ATR for dynamic stops and targets
                    # Stoploss: 1.5x ATR below entry (gives room for noise)
                    atr_stop = entry - (atr_5m * 1.5)
                    # Also respect key levels but with buffer
                    level_stop = max(st_5m_value * 0.997, day_low * 0.998)
                    stoploss = round(max(atr_stop, level_stop), 2)
                    
                    # Targets: ATR-based (more achievable)
                    # T1: 1x ATR (quick scalp target)
                    # T2: 1.5x ATR or BB upper (swing target)
                    target1 = round(entry + (atr_5m * 1.0 * target_multiplier), 2)
                    target2 = round(min(entry + (atr_5m * 1.5 * target_multiplier), bb_5m_upper), 2)
                    
                    # If we have strong momentum (crossover), extend targets
                    if st_5m_crossover or st_10m_crossover:
                        target1 = round(entry + (atr_5m * 1.2 * target_multiplier), 2)
                        target2 = round(entry + (atr_5m * 2.0 * target_multiplier), 2)
                    
                    # Validate minimum distances
                    if stoploss >= entry:
                        stoploss = round(entry * 0.995, 2)  # 0.5% minimum
                    if target1 <= entry * 1.003:
                        target1 = round(entry * 1.005, 2)  # 0.5% minimum
                    if target2 <= target1:
                        target2 = round(target1 * 1.005, 2)
                    
                    signal_data["entry"] = entry
                    signal_data["stoploss"] = stoploss
                    signal_data["target1"] = target1
                    signal_data["target2"] = target2
                    signal_data["risk_pct"] = round(((entry - stoploss) / entry) * 100, 2)
                    signal_data["reward_pct"] = round(((target1 - entry) / entry) * 100, 2)
                    signal_data["risk_reward"] = round(signal_data["reward_pct"] / signal_data["risk_pct"], 1) if signal_data["risk_pct"] > 0 else 1.5
                    
                    # Calculate profit potential (distance to target as %)
                    profit_potential_t1 = ((target1 - ltp) / ltp) * 100
                    profit_potential_t2 = ((target2 - ltp) / ltp) * 100
                    signal_data["profit_potential"] = round(profit_potential_t1, 2)
                    signal_data["profit_potential_t2"] = round(profit_potential_t2, 2)
                    
                    # Check if target is nearly achieved (within 0.3% of T1)
                    target_nearly_achieved = profit_potential_t1 <= 0.3
                    signal_data["target_status"] = "🎯 ACHIEVED" if profit_potential_t1 <= 0 else "⏳ NEAR" if target_nearly_achieved else "🚀 ACTIVE"
                    
                    # Only add signals with profit potential remaining
                    if profit_potential_t1 > 0.3:
                        long_signals.append(signal_data)
                    else:
                        logger.info(f"LONG {symbol}: Target nearly achieved ({profit_potential_t1:.2f}% to T1), skipping")
                    
                elif short_confirmations >= min_confirmations and short_confirmations > long_confirmations and not adx_blocks_short and not st_blocks_short:
                    signal_data["signal"] = "SHORT"
                    signal_data["confirmations"] = short_confirmations
                    signal_data["reasons"] = short_reasons[:6]
                    signal_data["reason_text"] = " | ".join(short_reasons[:5])
                    signal_data["warnings"] = short_warnings
                    signal_data["warning_text"] = " | ".join(short_warnings) if short_warnings else ""
                    
                    # Confidence based on confirmations
                    if short_confirmations >= 8:
                        signal_data["confidence"] = "VERY HIGH"
                        signal_data["confidence_pct"] = 90
                    elif short_confirmations >= 7:
                        signal_data["confidence"] = "HIGH"
                        signal_data["confidence_pct"] = 80
                    elif short_confirmations >= 6:
                        signal_data["confidence"] = "GOOD"
                        signal_data["confidence_pct"] = 70
                    else:
                        signal_data["confidence"] = "MODERATE"
                        signal_data["confidence_pct"] = 60
                    
                    # Entry & Targets for SHORT (relaxed entry - small bounce from current)
                    # Simple logic: Use VWAP/ST if close, otherwise small 0.15% bounce
                    
                    # Check if VWAP is a good nearby entry (within 0.5% above current)
                    vwap_diff_pct = ((vwap_5m - ltp) / ltp) * 100 if ltp > 0 else 0
                    
                    if vwap_5m > ltp and 0.1 < vwap_diff_pct < 0.5:
                        # VWAP is close above - use it as entry
                        entry = round(vwap_5m, 2)
                        entry_type = "VWAP"
                    elif st_5m_value > ltp and 0.1 < ((st_5m_value - ltp) / ltp) * 100 < 0.5:
                        # Supertrend resistance is close above - use it
                        entry = round(st_5m_value, 2)
                        entry_type = "ST Resist"
                    else:
                        # Default: Small 0.15% bounce (easy to achieve)
                        entry = round(ltp * 1.0015, 2)
                        entry_type = "Limit"
                    
                    signal_data["entry_type"] = entry_type
                    signal_data["current_price"] = round(ltp, 2)
                    
                    # Use ATR for dynamic stops and targets
                    # Stoploss: 1.5x ATR above entry (gives room for noise)
                    atr_stop = entry + (atr_5m * 1.5)
                    # Also respect key levels but with buffer
                    level_stop = min(st_5m_value * 1.003, day_high * 1.002)
                    stoploss = round(min(atr_stop, level_stop), 2)
                    
                    # Targets: ATR-based (more achievable)
                    # T1: 1x ATR (quick scalp target)
                    # T2: 1.5x ATR or BB lower (swing target)
                    target1 = round(entry - (atr_5m * 1.0 * target_multiplier), 2)
                    target2 = round(max(entry - (atr_5m * 1.5 * target_multiplier), bb_5m_lower), 2)
                    
                    # If we have strong momentum (crossover), extend targets
                    if st_5m_crossover or st_10m_crossover:
                        target1 = round(entry - (atr_5m * 1.2 * target_multiplier), 2)
                        target2 = round(entry - (atr_5m * 2.0 * target_multiplier), 2)
                    
                    # Validate minimum distances
                    if stoploss <= entry:
                        stoploss = round(entry * 1.005, 2)  # 0.5% minimum
                    if target1 >= entry * 0.997:
                        target1 = round(entry * 0.995, 2)  # 0.5% minimum
                    if target2 >= target1:
                        target2 = round(target1 * 0.995, 2)
                    
                    signal_data["entry"] = entry
                    signal_data["stoploss"] = stoploss
                    signal_data["target1"] = target1
                    signal_data["target2"] = target2
                    signal_data["risk_pct"] = round(((stoploss - entry) / entry) * 100, 2)
                    signal_data["reward_pct"] = round(((entry - target1) / entry) * 100, 2)
                    signal_data["risk_reward"] = round(signal_data["reward_pct"] / signal_data["risk_pct"], 1) if signal_data["risk_pct"] > 0 else 1.5
                    
                    # Calculate profit potential (distance to target as %) - For shorts, target is below
                    profit_potential_t1 = ((ltp - target1) / ltp) * 100
                    profit_potential_t2 = ((ltp - target2) / ltp) * 100
                    signal_data["profit_potential"] = round(profit_potential_t1, 2)
                    signal_data["profit_potential_t2"] = round(profit_potential_t2, 2)
                    
                    # Check if target is nearly achieved (within 0.3% of T1)
                    target_nearly_achieved = profit_potential_t1 <= 0.3
                    signal_data["target_status"] = "🎯 ACHIEVED" if profit_potential_t1 <= 0 else "⏳ NEAR" if target_nearly_achieved else "🚀 ACTIVE"
                    
                    # Only add signals with profit potential remaining
                    if profit_potential_t1 > 0.3:
                        short_signals.append(signal_data)
                    else:
                        logger.info(f"SHORT {symbol}: Target nearly achieved ({profit_potential_t1:.2f}% to T1), skipping")
                    
            except Exception as e:
                logger.debug(f"Error analyzing {symbol} for multi-TF: {e}")
                continue
        
        # Sort by profit potential first, then confirmations (bigger profits + stronger signals first)
        # Score = profit_potential * 2 + confirmations (weight profit potential more)
        long_signals.sort(key=lambda x: (x.get("profit_potential", 0) * 2 + x["confirmations"]), reverse=True)
        short_signals.sort(key=lambda x: (x.get("profit_potential", 0) * 2 + x["confirmations"]), reverse=True)
        
        # Count filtered signals
        total_before_filter = stocks_analyzed
        logger.info(f"Multi-TF: Found {len(long_signals)} LONG, {len(short_signals)} SHORT signals (filtered for profit potential)")
        
        return {
            "status": "success",
            "long_signals": long_signals[:num_stocks],
            "short_signals": short_signals[:num_stocks],
            "total_long": len(long_signals),
            "total_short": len(short_signals),
            "stocks_analyzed": stocks_analyzed,
            "index": index_name,
            "time_context": time_context,
            "mins_to_squareoff": time_context.get("time_to_squareoff_mins", 0),
            "market_phase": time_context.get("phase", "UNKNOWN"),
            "generated_at": datetime.now().strftime("%I:%M:%S %p"),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get multi-TF signals: {e}")
        return {
            "status": "error",
            "long_signals": [],
            "short_signals": [],
            "error": str(e)
        }


def get_options_signals(index_name: str = "FNO_STOCKS", num_stocks: int = 6) -> Dict[str, Any]:
    """
    Options Trading Strategy - Designed for F&O stocks
    
    Key Differences from DayTrade:
    1. Only F&O stocks (liquid options)
    2. Larger targets (1.5-2%+) for option premium gains
    3. ATR-based volatility filtering (need volatile stocks)
    4. Expiry awareness (weekly Thursday)
    5. Strike recommendations (ATM/OTM)
    
    Args:
        index_name: Index to scan - "FNO_STOCKS", "NIFTY 50", "NIFTY 100", "NIFTY IT", etc.
        num_stocks: Number of signals to return
    
    Returns:
        Dict with call_signals, put_signals, and analysis
    """
    try:
        time_context = get_market_time_context()
        
        # Check expiry day (Thursday)
        today = datetime.now()
        is_expiry_day = today.weekday() == 3  # Thursday
        days_to_expiry = (3 - today.weekday()) % 7
        if days_to_expiry == 0 and today.hour >= 15:
            days_to_expiry = 7
        
        # Get stocks based on index selection
        # For options, we intersect with F&O stocks to ensure liquidity
        fno_stocks_list = STOCK_LISTS.get("FNO_STOCKS", [])
        
        if index_name == "FNO_STOCKS" or index_name == "ALL F&O":
            stocks_to_scan = fno_stocks_list
        else:
            # Get index stocks and filter to only F&O eligible
            index_stocks = get_stocks_for_index(index_name)
            # Intersect with F&O stocks
            stocks_to_scan = [s for s in index_stocks if s in fno_stocks_list]
            
            # If no overlap, just use the index stocks (they might have F&O)
            if not stocks_to_scan:
                stocks_to_scan = index_stocks
        
        fno_stocks = stocks_to_scan
        
        call_signals = []  # BUY CALL
        put_signals = []   # BUY PUT
        stocks_analyzed = 0
        no_data_count = 0
        low_volatility_count = 0
        low_score_count = 0
        
        logger.info(f"Options Strategy: Analyzing {len(fno_stocks)} F&O stocks from {index_name}")
        
        for symbol in fno_stocks:
            try:
                stocks_analyzed += 1
                yahoo_symbol = get_yahoo_symbol(symbol)
                ticker = yf.Ticker(yahoo_symbol)
                
                # Get 5-minute data
                hist_5m = ticker.history(period="5d", interval="5m")
                
                if hist_5m.empty or len(hist_5m) < 50:
                    no_data_count += 1
                    continue
                
                # Resample to 15m for options (slightly longer timeframe)
                hist_15m = hist_5m.resample('15min').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min',
                    'Close': 'last', 'Volume': 'sum'
                }).dropna()
                
                if len(hist_15m) < 20:
                    continue
                
                ltp = hist_5m['Close'].iloc[-1]
                
                # ============== VOLATILITY CHECK ==============
                # Options need volatility - filter low-volatility stocks
                atr_5m = calculate_atr(hist_5m['High'], hist_5m['Low'], hist_5m['Close'], period=14)
                atr_pct = (atr_5m / ltp) * 100
                
                # Original: 1.2% ATR minimum for F&O stocks
                if atr_pct < 1.2:
                    low_volatility_count += 1
                    continue
                
                # ============== INDICATORS ==============
                # VWAP
                vwap_data = calculate_vwap(hist_5m['High'], hist_5m['Low'], hist_5m['Close'], hist_5m['Volume'])
                vwap = vwap_data.get("vwap", ltp)
                vwap_signal = vwap_data.get("signal", "NEUTRAL")
                vwap_dist = vwap_data.get("distance_pct", 0)
                
                # Supertrend (5m)
                st_5m = calculate_supertrend_simple(hist_5m['High'], hist_5m['Low'], hist_5m['Close'])
                st_5m_signal = st_5m.get("signal", "NEUTRAL")
                st_5m_crossover = st_5m.get("crossover", False)
                st_5m_value = st_5m.get("value", ltp)
                
                # Supertrend (15m)
                st_15m = calculate_supertrend_simple(hist_15m['High'], hist_15m['Low'], hist_15m['Close'])
                st_15m_signal = st_15m.get("signal", "NEUTRAL")
                st_15m_crossover = st_15m.get("crossover", False)
                
                # Bollinger Bands
                bb_data = calculate_bollinger_bands(hist_5m['Close'], period=20)
                bb_signal = bb_data.get("signal", "NEUTRAL")
                bb_upper = bb_data.get("upper", ltp)
                bb_lower = bb_data.get("lower", ltp)
                bb_squeeze = bb_data.get("squeeze", False)
                
                # ADX (for trend strength - important for options)
                adx_data = calculate_adx(hist_5m['High'], hist_5m['Low'], hist_5m['Close'], 
                                         di_length=10, adx_smoothing=10)
                adx_value = adx_data.get("adx", 0)
                adx_direction = adx_data.get("trend_direction", "NEUTRAL")
                adx_strength = adx_data.get("trend_strength", "WEAK")
                
                # ROC (momentum)
                roc_data = calculate_roc(hist_5m['Close'], period=10)
                roc_value = roc_data.get("roc", 0)
                roc_signal = roc_data.get("signal", "NEUTRAL")
                roc_divergence = roc_data.get("bearish_divergence", False) or roc_data.get("bullish_divergence", False)
                
                # Day's range
                today_data = hist_5m.tail(75)
                day_high = today_data['High'].max()
                day_low = today_data['Low'].min()
                day_open = today_data['Open'].iloc[0] if len(today_data) > 0 else ltp
                change_pct = ((ltp - day_open) / day_open) * 100
                day_range_pct = ((day_high - day_low) / day_low) * 100
                
                # ============== CALL SIGNAL (BUY CALL) ==============
                call_score = 0
                call_reasons = []
                
                # Trend confirmations
                if vwap_signal == "BULLISH":
                    call_score += 1
                    call_reasons.append(">VWAP")
                if st_5m_signal == "BULLISH":
                    call_score += 1
                    if st_5m_crossover:
                        call_score += 2
                        call_reasons.append("🔥 ST Cross")
                    else:
                        call_reasons.append("ST+")
                if st_15m_signal == "BULLISH":
                    call_score += 1
                    if st_15m_crossover:
                        call_score += 2
                        call_reasons.append("🔥 15m Cross")
                    else:
                        call_reasons.append("15m ST+")
                
                # Momentum
                if roc_signal == "BULLISH":
                    call_score += 1
                    call_reasons.append("ROC+")
                
                # ADX trend strength (strong trends are good for options)
                if adx_value >= 25 and adx_direction == "BULLISH":
                    call_score += 2
                    call_reasons.append(f"ADX {adx_value:.0f}")
                
                # BB Squeeze (breakout potential)
                if bb_squeeze and st_5m_signal == "BULLISH":
                    call_score += 2
                    call_reasons.append("🎯 Squeeze")
                
                # Oversold bounce
                if bb_signal == "OVERSOLD":
                    call_score += 1
                    call_reasons.append("BB Oversold")
                
                # ============== PUT SIGNAL (BUY PUT) ==============
                put_score = 0
                put_reasons = []
                
                # Trend confirmations
                if vwap_signal == "BEARISH":
                    put_score += 1
                    put_reasons.append("<VWAP")
                if st_5m_signal == "BEARISH":
                    put_score += 1
                    if st_5m_crossover:
                        put_score += 2
                        put_reasons.append("🔥 ST Cross")
                    else:
                        put_reasons.append("ST-")
                if st_15m_signal == "BEARISH":
                    put_score += 1
                    if st_15m_crossover:
                        put_score += 2
                        put_reasons.append("🔥 15m Cross")
                    else:
                        put_reasons.append("15m ST-")
                
                # Momentum
                if roc_signal == "BEARISH":
                    put_score += 1
                    put_reasons.append("ROC-")
                
                # ADX trend strength
                if adx_value >= 25 and adx_direction == "BEARISH":
                    put_score += 2
                    put_reasons.append(f"ADX {adx_value:.0f}")
                
                # BB Squeeze (breakout potential)
                if bb_squeeze and st_5m_signal == "BEARISH":
                    put_score += 2
                    put_reasons.append("🎯 Squeeze")
                
                # Overbought reversal
                if bb_signal == "OVERBOUGHT":
                    put_score += 1
                    put_reasons.append("BB Overbought")
                
                # ============== GENERATE SIGNALS ==============
                # Original threshold
                min_score = 5  # 5 confirmations required
                
                # Calculate strike prices
                strike_interval = 50 if ltp > 1000 else 25 if ltp > 500 else 10 if ltp > 100 else 5
                atm_strike = round(ltp / strike_interval) * strike_interval
                
                if call_score >= min_score and call_score > put_score:
                    # Calculate targets (larger for options - 1.5-2%)
                    entry = ltp
                    stoploss = max(st_5m_value * 0.995, entry - (atr_5m * 2))
                    target1 = entry + (atr_5m * 1.5)
                    target2 = entry + (atr_5m * 2.5)
                    
                    # Strike recommendation
                    if st_5m_crossover or st_15m_crossover:
                        # Strong momentum - can go slightly OTM
                        recommended_strike = atm_strike + strike_interval
                        strike_type = "OTM"
                    else:
                        recommended_strike = atm_strike
                        strike_type = "ATM"
                    
                    # Original confidence levels
                    if call_score >= 8:
                        confidence = "VERY HIGH"
                        confidence_pct = 85
                    elif call_score >= 7:
                        confidence = "HIGH"
                        confidence_pct = 75
                    elif call_score >= 6:
                        confidence = "GOOD"
                        confidence_pct = 65
                    else:
                        confidence = "MODERATE"
                        confidence_pct = 55
                    
                    call_signals.append({
                        "symbol": symbol,
                        "signal": "BUY CALL",
                        "ltp": round(ltp, 2),
                        "change_pct": round(change_pct, 2),
                        "entry": round(entry, 2),
                        "stoploss": round(stoploss, 2),
                        "target1": round(target1, 2),
                        "target2": round(target2, 2),
                        "recommended_strike": recommended_strike,
                        "strike_type": strike_type,
                        "score": call_score,
                        "confidence": confidence,
                        "confidence_pct": confidence_pct,
                        "reasons": call_reasons[:5],
                        "reason_text": " | ".join(call_reasons[:4]),
                        "atr_pct": round(atr_pct, 2),
                        "adx": round(adx_value, 1),
                        "adx_strength": adx_strength,
                        "vwap_dist": round(vwap_dist, 2),
                        "day_range_pct": round(day_range_pct, 2),
                        "bb_squeeze": bb_squeeze,
                        "st_crossover": st_5m_crossover or st_15m_crossover,
                        "profit_potential": round(((target1 - entry) / entry) * 100, 2)
                    })
                
                elif put_score >= min_score and put_score > call_score:
                    # Calculate targets
                    entry = ltp
                    stoploss = min(st_5m_value * 1.005, entry + (atr_5m * 2))
                    target1 = entry - (atr_5m * 1.5)
                    target2 = entry - (atr_5m * 2.5)
                    
                    # Strike recommendation
                    if st_5m_crossover or st_15m_crossover:
                        recommended_strike = atm_strike - strike_interval
                        strike_type = "OTM"
                    else:
                        recommended_strike = atm_strike
                        strike_type = "ATM"
                    
                    # Original confidence levels
                    if put_score >= 8:
                        confidence = "VERY HIGH"
                        confidence_pct = 85
                    elif put_score >= 7:
                        confidence = "HIGH"
                        confidence_pct = 75
                    elif put_score >= 6:
                        confidence = "GOOD"
                        confidence_pct = 65
                    else:
                        confidence = "MODERATE"
                        confidence_pct = 55
                    
                    put_signals.append({
                        "symbol": symbol,
                        "signal": "BUY PUT",
                        "ltp": round(ltp, 2),
                        "change_pct": round(change_pct, 2),
                        "entry": round(entry, 2),
                        "stoploss": round(stoploss, 2),
                        "target1": round(target1, 2),
                        "target2": round(target2, 2),
                        "recommended_strike": recommended_strike,
                        "strike_type": strike_type,
                        "score": put_score,
                        "confidence": confidence,
                        "confidence_pct": confidence_pct,
                        "reasons": put_reasons[:5],
                        "reason_text": " | ".join(put_reasons[:4]),
                        "atr_pct": round(atr_pct, 2),
                        "adx": round(adx_value, 1),
                        "adx_strength": adx_strength,
                        "vwap_dist": round(vwap_dist, 2),
                        "day_range_pct": round(day_range_pct, 2),
                        "bb_squeeze": bb_squeeze,
                        "st_crossover": st_5m_crossover or st_15m_crossover,
                        "profit_potential": round(((entry - target1) / entry) * 100, 2)
                    })
                
                else:
                    # Track why no signal generated
                    low_score_count += 1
                    
            except Exception as e:
                logger.debug(f"Error analyzing {symbol} for options: {e}")
                continue
        
        # Sort by score and profit potential
        call_signals.sort(key=lambda x: (x["score"] * 2 + x["profit_potential"]), reverse=True)
        put_signals.sort(key=lambda x: (x["score"] * 2 + x["profit_potential"]), reverse=True)
        
        logger.info(f"Options: Found {len(call_signals)} CALL, {len(put_signals)} PUT signals")
        logger.info(f"Options Filter Stats: {no_data_count} no data, {low_volatility_count} low ATR, {low_score_count} low score")
        
        return {
            "status": "success",
            "call_signals": call_signals[:num_stocks],
            "put_signals": put_signals[:num_stocks],
            "total_calls": len(call_signals),
            "total_puts": len(put_signals),
            "stocks_analyzed": stocks_analyzed,
            "index": index_name,
            "is_expiry_day": is_expiry_day,
            "days_to_expiry": days_to_expiry,
            "time_context": time_context,
            "generated_at": datetime.now().strftime("%I:%M:%S %p"),
            "timestamp": datetime.now().isoformat(),
            # Diagnostic info
            "filter_stats": {
                "no_data": no_data_count,
                "low_volatility": low_volatility_count,
                "low_score": low_score_count
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to get options signals: {e}")
        return {
            "status": "error",
            "call_signals": [],
            "put_signals": [],
            "error": str(e)
        }
