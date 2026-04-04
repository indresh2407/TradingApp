# SIDDHI - Intelligent Trading Platform

A Python-based **stock analysis platform** with multi-timeframe analysis and intelligent stock recommendations. Get intraday tips, DayTrade signals, Options buying signals, and long-term picks.

## Features

- **Intelligent Stock Analysis**: VWAP, Supertrend, Bollinger Bands, ADX, ROC, and more
- **Multi-Timeframe Confirmation**: 5m + 15m timeframe analysis for high-confidence trades
- **Intraday Tips**: Real-time BUY/SELL recommendations with entry, SL, targets
- **DayTrade Strategy**: Advanced multi-timeframe intraday signals with BB Squeeze, VWAP distance
- **Options Strategy**: F&O signals with strike recommendations and expiry-aware logic
- **Tomorrow's Outlook**: Next-day stock picks based on EOD analysis
- **Long-Term Picks**: Investment recommendations for 1 month to 5 years
- **Full Market Scan**: Analyze 500+ stocks across all sectors
- **Beautiful Dashboard**: Real-time Streamlit web interface
- **Volatility Analysis**: Prioritizes high-volatility stocks for intraday

---

## Quick Start (Analysis Only)

**No Kotak account needed** - uses Yahoo Finance for market data.

### Step 1: Clone Repository
```bash
git clone <your-repo-url>
cd kotak-trading-system
```

### Step 2: Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```
> **Windows:** `venv\Scripts\activate`

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run Dashboard
```bash
streamlit run dashboard.py
```

### Step 5: Open Browser
Go to **http://localhost:8501**

---

## One-Liner Setup (Copy-Paste)

```bash
cd kotak-trading-system && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && streamlit run dashboard.py
```

---

## System Requirements

| Requirement | Version |
|-------------|---------|
| Python | 3.9 or higher |
| pip | Latest |
| Internet | Required for live data |

---

## Full Setup (With Live Trading)

### 1. Kotak Securities Account

You need an active Kotak Securities trading account with API access enabled.

### 2. API Registration (One-time Setup)

1. Open **Kotak Neo App** on your phone
2. Go to **More → Trade API**
3. Click **Create New Application**
4. Note down your **Consumer Key** and **Consumer Secret**
5. Register for **TOTP** authentication using Google/Microsoft Authenticator

### 3. Install Kotak Neo API Client

```bash
pip install "git+https://github.com/Kotak-Neo/kotak-neo-api.git#egg=neo_api_client"
```

### 4. Configure Credentials

```bash
cp config/.env.example config/.env
```

Edit `config/.env` with your credentials:

```env
KOTAK_CONSUMER_KEY=your_consumer_key
KOTAK_CONSUMER_SECRET=your_consumer_secret
KOTAK_MOBILE_NUMBER=+919999999999
KOTAK_PASSWORD=your_trading_password
KOTAK_MPIN=your_mpin
KOTAK_ENVIRONMENT=uat  # Use 'prod' for live trading
```

## Configuration

Edit `config/settings.yaml` to customize trading parameters:

```yaml
trading:
  mode: "paper"      # "paper" or "live"
  capital: 100000    # Your trading capital in INR

risk:
  max_position_pct: 10       # Max 10% of capital per trade
  max_daily_loss_pct: 2      # Stop trading after 2% loss
  max_open_positions: 3      # Maximum simultaneous positions
  mandatory_stoploss: true   # Require stop-loss for all orders
  default_stoploss_pct: 1.5  # Default stop-loss percentage
  default_target_pct: 3.0    # Default target percentage
```

Edit `config/instruments.yaml` to set your watchlist.

## Usage

### Quick Start

```bash
# Launch the dashboard (recommended)
streamlit run dashboard.py

# Or use CLI
python main.py status
```

### Dashboard Features

| Tab | Description |
|-----|-------------|
| **Dashboard** | Intraday Tips with entry, SL, targets |
| **⚡ DayTrade** | Multi-timeframe intraday signals with advanced indicators |
| **🎯 Options** | F&O BUY CALL/PUT signals with strike recommendations |
| **🌅 Tomorrow** | Next day's intraday stock picks |
| **📊 Long Term** | Investment picks for 1M to 5Y |
| **⚙️ Settings** | Configuration options |

### Options Strategy Features

- **F&O Stock Filter**: Only liquid F&O stocks
- **Strike Recommendation**: ATM/OTM suggestions
- **Expiry-Aware**: Duration advice based on days to expiry
- **Volatility Filter**: ATR ≥ 1.2% for good premium moves
- **Multi-Timeframe**: 5m + 15m Supertrend confirmation
- **Index Filters**: NIFTY 50, NIFTY BANK, NIFTY IT, etc.

## Trading Strategies

### 1. RSI Reversal (Intraday)

- **Entry**: Buy when RSI < 30 and turning up
- **Exit**: Sell when RSI > 70, or stop-loss/target hit
- **Product**: MIS (Intraday)

### 2. EMA Crossover (Swing)

- **Entry**: Buy when EMA 9 crosses above EMA 21
- **Exit**: Sell when EMA 9 crosses below EMA 21, or stop-loss/target hit
- **Product**: CNC (Delivery)

## Risk Management

The system enforces several risk controls:

| Rule | Default | Description |
|------|---------|-------------|
| Max Position Size | 10% | Maximum capital per single trade |
| Max Daily Loss | 2% | Trading halts after this loss |
| Max Open Positions | 3 | Limit on simultaneous positions |
| Mandatory Stop-Loss | Yes | All orders must have stop-loss |
| Intraday Square-off | 3:15 PM | Auto-close MIS positions |

## Project Structure

```
kotak-trading-system/
├── config/
│   ├── .env.example        # API credentials template
│   ├── settings.yaml       # Trading configuration
│   └── instruments.yaml    # Watchlist
├── src/
│   ├── api/
│   │   ├── kotak_client.py # API wrapper
│   │   └── market_data.py  # Market data handler
│   ├── core/
│   │   ├── risk_manager.py # Risk management
│   │   ├── order_manager.py# Order handling
│   │   └── position_tracker.py # Position monitoring
│   ├── strategies/
│   │   ├── base_strategy.py    # Strategy base class
│   │   ├── intraday/           # Intraday strategies
│   │   └── swing/              # Swing strategies
│   └── utils/
│       ├── logger.py       # Logging setup
│       └── helpers.py      # Utility functions
├── logs/                   # Log files
├── main.py                 # CLI entry point
├── requirements.txt        # Dependencies
└── README.md
```

## Analysis Features

### Core Indicators
| Indicator | Purpose |
|-----------|---------|
| **VWAP** | Institutional price level |
| **Supertrend** | Trend direction & crossovers |
| **Bollinger Bands** | Squeeze, Walk, Curl patterns |
| **ADX (7,7)** | Trend strength |
| **ROC/Momentum** | Divergence detection |
| **ATR** | Volatility & target calculation |

### Advanced Features
1. **Multi-Timeframe Analysis**: 5m + 15m + 10m confirmation
2. **VWAP Distance**: "Rubber Band" overextension detection
3. **BB Squeeze Detection**: Breakout anticipation
4. **Supertrend Crossovers**: +2 score boost for fresh signals
5. **Dynamic Targets**: ATR-based realistic targets
6. **Profit Potential Filter**: Prioritizes high-potential trades
7. **Comprehensive Logging**: All analysis logged with loguru

## Troubleshooting

### API Connection Issues

```
Error: neo_api_client not installed
```
→ Run: `pip install "git+https://github.com/Kotak-Neo/kotak-neo-api.git#egg=neo_api_client"`

### Authentication Failed

- Verify TOTP is correct and not expired
- Check credentials in `config/.env`
- Ensure mobile number includes +91 prefix

### Order Rejected

- Check if trading is enabled (not hit daily loss limit)
- Verify sufficient margin/capital
- Ensure stop-loss is set (if mandatory)

## Disclaimer

This software is for **educational and analysis purposes only**. Trading in financial markets carries significant risk. The authors are not responsible for any financial losses incurred through the use of this software.

**Always:**
- Do your own research before trading
- Understand the risks involved
- Never trade with money you can't afford to lose
- Use this as a tool for analysis, not as financial advice

## License

MIT License - Use at your own risk.

## Support

For API-related issues, refer to:
- [Kotak Neo API Documentation](https://www.kotaksecurities.com/investing-guide/trading-account/kotak-neo-trade-api-guide/)
- [Kotak Neo GitHub](https://github.com/Kotak-Neo/kotak-neo-api)
