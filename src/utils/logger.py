"""
SIDDHI Logger Configuration
Sets up loguru for platform logging
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logger(
    log_file: str = "logs/trading.log",
    level: str = "INFO",
    max_size: str = "10 MB",
    backup_count: int = 5
) -> None:
    """
    Configure loguru logger for SIDDHI platform
    
    Args:
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        max_size: Maximum size before rotation
        backup_count: Number of backup files to keep
    """
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        colorize=True
    )
    
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # File handler with rotation
    logger.add(
        log_file,
        level=level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=max_size,
        retention=backup_count,
        compression="zip"
    )
    
    # Separate error log
    error_log = str(log_path.parent / "errors.log")
    logger.add(
        error_log,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=max_size,
        retention=backup_count
    )
    
    # Trade log for audit trail
    trade_log = str(log_path.parent / "trades.log")
    logger.add(
        trade_log,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {message}",
        filter=lambda record: "trade" in record["extra"],
        rotation="1 day",
        retention="30 days"
    )
    
    logger.info("Logger configured successfully")


def log_trade(
    action: str,
    symbol: str,
    quantity: int,
    price: float,
    **kwargs
) -> None:
    """Log a trade for audit purposes"""
    extra_info = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.bind(trade=True).info(
        f"{action} | {symbol} | qty={quantity} | price={price:.2f} | {extra_info}"
    )
