"""
Trade Logger
Logs all trades (paper and live) to a JSON file for dashboard display
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger

TRADES_FILE = "logs/trades.json"
MAX_TRADES = 100  # Keep last 100 trades


def _ensure_file():
    """Ensure trades file exists"""
    path = Path(TRADES_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with open(path, "w") as f:
            json.dump({"trades": [], "positions": []}, f)


def log_trade(
    symbol: str,
    action: str,  # BUY, SELL, SL_HIT, TARGET_HIT
    quantity: int,
    price: float,
    order_type: str = "MARKET",
    product: str = "MIS",
    mode: str = "PAPER",
    stoploss: float = 0,
    target: float = 0,
    pnl: float = 0,
    reason: str = "",
    order_id: str = ""
) -> Dict[str, Any]:
    """
    Log a trade to the trades file
    
    Returns the trade record
    """
    _ensure_file()
    
    trade = {
        "id": f"{mode}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "action": action,
        "quantity": quantity,
        "price": price,
        "value": quantity * price,
        "order_type": order_type,
        "product": product,
        "mode": mode,
        "stoploss": stoploss,
        "target": target,
        "pnl": pnl,
        "reason": reason,
        "order_id": order_id,
        "status": "EXECUTED"
    }
    
    try:
        with open(TRADES_FILE, "r") as f:
            data = json.load(f)
        
        data["trades"].insert(0, trade)  # Add to beginning
        data["trades"] = data["trades"][:MAX_TRADES]  # Keep last N
        
        with open(TRADES_FILE, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Trade logged: {action} {quantity} {symbol} @ ₹{price:.2f}")
        
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")
    
    return trade


def update_position(
    symbol: str,
    quantity: int,
    entry_price: float,
    current_price: float,
    stoploss: float,
    target: float,
    product: str = "MIS",
    mode: str = "PAPER",
    pnl: float = 0,
    pnl_pct: float = 0
):
    """Update or add a position"""
    _ensure_file()
    
    position = {
        "symbol": symbol,
        "quantity": quantity,
        "entry_price": entry_price,
        "current_price": current_price,
        "stoploss": stoploss,
        "target": target,
        "product": product,
        "mode": mode,
        "pnl": pnl,
        "pnl_pct": pnl_pct,
        "updated_at": datetime.now().isoformat()
    }
    
    try:
        with open(TRADES_FILE, "r") as f:
            data = json.load(f)
        
        # Update existing or add new
        found = False
        for i, pos in enumerate(data["positions"]):
            if pos["symbol"] == symbol:
                data["positions"][i] = position
                found = True
                break
        
        if not found:
            data["positions"].append(position)
        
        with open(TRADES_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to update position: {e}")


def close_position(symbol: str, exit_price: float, pnl: float, reason: str = ""):
    """Remove a position when closed"""
    _ensure_file()
    
    try:
        with open(TRADES_FILE, "r") as f:
            data = json.load(f)
        
        data["positions"] = [p for p in data["positions"] if p["symbol"] != symbol]
        
        with open(TRADES_FILE, "w") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to close position: {e}")


def get_trades(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent trades"""
    _ensure_file()
    
    try:
        with open(TRADES_FILE, "r") as f:
            data = json.load(f)
        return data.get("trades", [])[:limit]
    except:
        return []


def get_positions() -> List[Dict[str, Any]]:
    """Get current positions"""
    _ensure_file()
    
    try:
        with open(TRADES_FILE, "r") as f:
            data = json.load(f)
        return data.get("positions", [])
    except:
        return []


def get_daily_summary() -> Dict[str, Any]:
    """Get today's trading summary"""
    _ensure_file()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    try:
        with open(TRADES_FILE, "r") as f:
            data = json.load(f)
        
        today_trades = [
            t for t in data.get("trades", [])
            if t["timestamp"].startswith(today)
        ]
        
        total_trades = len(today_trades)
        buy_trades = len([t for t in today_trades if t["action"] == "BUY"])
        sell_trades = len([t for t in today_trades if t["action"] in ["SELL", "SL_HIT", "TARGET_HIT"]])
        total_pnl = sum(t.get("pnl", 0) for t in today_trades)
        
        wins = len([t for t in today_trades if t.get("pnl", 0) > 0])
        losses = len([t for t in today_trades if t.get("pnl", 0) < 0])
        
        return {
            "date": today,
            "total_trades": total_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "total_pnl": total_pnl,
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        }
    except:
        return {
            "date": today,
            "total_trades": 0,
            "buy_trades": 0,
            "sell_trades": 0,
            "total_pnl": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0
        }


def clear_all():
    """Clear all trades and positions"""
    _ensure_file()
    with open(TRADES_FILE, "w") as f:
        json.dump({"trades": [], "positions": []}, f)
