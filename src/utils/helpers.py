"""
SIDDHI Helper Utilities
Common utility functions for the trading platform
"""

import os
import yaml
from typing import Dict, Any, List, Optional
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger


def load_env(env_file: str = "config/.env") -> None:
    """Load environment variables from .env file"""
    env_path = Path(env_file)
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded environment from {env_file}")
    else:
        logger.warning(f"Environment file not found: {env_file}")


def load_config(config_file: str = "config/settings.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file"""
    config_path = Path(config_file)
    
    if not config_path.exists():
        logger.warning(f"Config file not found: {config_file}, using defaults")
        return get_default_config()
    
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return get_default_config()


def load_instruments(instruments_file: str = "config/instruments.yaml") -> Dict[str, List[Dict]]:
    """Load instrument watchlist from YAML file"""
    instruments_path = Path(instruments_file)
    
    if not instruments_path.exists():
        logger.warning(f"Instruments file not found: {instruments_file}")
        return {"equity": [], "fno": [], "indices": []}
    
    try:
        with open(instruments_path, "r") as f:
            instruments = yaml.safe_load(f)
        
        enabled_equity = [i for i in instruments.get("equity", []) if i.get("enabled", True)]
        enabled_fno = [i for i in instruments.get("fno", []) if i.get("enabled", True)]
        
        logger.info(f"Loaded {len(enabled_equity)} equity and {len(enabled_fno)} F&O instruments")
        return instruments
    except Exception as e:
        logger.error(f"Failed to load instruments: {e}")
        return {"equity": [], "fno": [], "indices": []}


def get_default_config() -> Dict[str, Any]:
    """Return default configuration"""
    return {
        "trading": {
            "mode": "paper",
            "capital": 100000
        },
        "risk": {
            "max_position_pct": 10,
            "max_daily_loss_pct": 2,
            "max_open_positions": 3,
            "mandatory_stoploss": True,
            "default_stoploss_pct": 1.5,
            "default_target_pct": 3.0
        },
        "segments": {
            "equity": True,
            "fno": True
        },
        "intraday": {
            "enabled": True,
            "squareoff_time": "15:15",
            "start_time": "09:20",
            "end_time": "15:00"
        },
        "swing": {
            "enabled": True,
            "max_holding_days": 10
        },
        "orders": {
            "default_product": "MIS",
            "default_order_type": "LIMIT",
            "retry_attempts": 3,
            "retry_delay_seconds": 2,
            "duplicate_order_cooldown_seconds": 60
        },
        "logging": {
            "level": "INFO",
            "file_path": "logs/trading.log",
            "max_file_size_mb": 10,
            "backup_count": 5
        }
    }


def get_credentials() -> Dict[str, str]:
    """Get API credentials from environment variables"""
    load_env()
    
    credentials = {
        "consumer_key": os.getenv("KOTAK_CONSUMER_KEY", ""),
        "consumer_secret": os.getenv("KOTAK_CONSUMER_SECRET", ""),
        "mobile_number": os.getenv("KOTAK_MOBILE_NUMBER", ""),
        "password": os.getenv("KOTAK_PASSWORD", ""),
        "mpin": os.getenv("KOTAK_MPIN", ""),
        "environment": os.getenv("KOTAK_ENVIRONMENT", "uat")
    }
    
    # Validate credentials
    missing = [k for k, v in credentials.items() if not v and k != "environment"]
    if missing:
        logger.warning(f"Missing credentials: {', '.join(missing)}")
    
    return credentials


def format_currency(amount: float) -> str:
    """Format amount as Indian currency"""
    if amount >= 10000000:  # 1 Crore
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # 1 Lakh
        return f"₹{amount/100000:.2f} L"
    else:
        return f"₹{amount:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage with color indicator"""
    if value >= 0:
        return f"+{value:.2f}%"
    else:
        return f"{value:.2f}%"


def is_market_open() -> bool:
    """Check if Indian stock market is open"""
    from datetime import datetime, time
    
    now = datetime.now()
    
    # Check if weekend
    if now.weekday() >= 5:
        return False
    
    # Market hours: 9:15 AM to 3:30 PM IST
    market_open = time(9, 15)
    market_close = time(15, 30)
    current_time = now.time()
    
    return market_open <= current_time <= market_close


def calculate_risk_reward(entry: float, stoploss: float, target: float) -> float:
    """Calculate risk-reward ratio"""
    risk = abs(entry - stoploss)
    reward = abs(target - entry)
    
    if risk == 0:
        return 0
    
    return reward / risk
