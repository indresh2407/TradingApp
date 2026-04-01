#!/usr/bin/env python3
"""
SIDDHI - Intelligent Trading Platform
Main Entry Point - Live trading system using Neo API
"""

import os
import sys
import time
import signal
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.api import KotakClient, MarketData
from src.core import RiskManager, OrderManager, PositionTracker
from src.core.risk_manager import RiskConfig
from src.strategies.intraday import RSIReversalStrategy
from src.strategies.swing import EMACrossoverStrategy
from src.utils import setup_logger, load_config, load_instruments
from src.utils.helpers import get_credentials, format_currency, format_percentage, is_market_open

console = Console()


class TradingSystem:
    """Main trading system orchestrator"""
    
    def __init__(self, config: dict, paper_mode: bool = True):
        self.config = config
        self.paper_mode = paper_mode
        self._running = False
        
        # Initialize components
        self._init_logging()
        self._init_risk_manager()
        self._init_client()
        self._init_order_manager()
        self._init_position_tracker()
        self._init_strategies()
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
    
    def _init_logging(self):
        log_config = self.config.get("logging", {})
        setup_logger(
            log_file=log_config.get("file_path", "logs/trading.log"),
            level=log_config.get("level", "INFO")
        )
    
    def _init_risk_manager(self):
        risk_config = self.config.get("risk", {})
        trading_config = self.config.get("trading", {})
        
        self.risk_manager = RiskManager(RiskConfig(
            capital=trading_config.get("capital", 100000),
            max_position_pct=risk_config.get("max_position_pct", 10),
            max_daily_loss_pct=risk_config.get("max_daily_loss_pct", 2),
            max_open_positions=risk_config.get("max_open_positions", 3),
            mandatory_stoploss=risk_config.get("mandatory_stoploss", True),
            default_stoploss_pct=risk_config.get("default_stoploss_pct", 1.5),
            default_target_pct=risk_config.get("default_target_pct", 3.0)
        ))
    
    def _init_client(self):
        if self.paper_mode:
            self.client = None
            # Use PaperMarketData which fetches live data via Yahoo Finance
            from src.api.market_data import PaperMarketData
            self.market_data = PaperMarketData()
            logger.info("Running in PAPER TRADING mode - using Yahoo Finance for market data")
        else:
            credentials = get_credentials()
            self.client = KotakClient(
                consumer_key=credentials["consumer_key"],
                consumer_secret=credentials["consumer_secret"],
                mobile_number=credentials["mobile_number"],
                password=credentials["password"],
                mpin=credentials["mpin"],
                environment=credentials["environment"]
            )
            self.market_data = MarketData(self.client)
    
    def _init_order_manager(self):
        order_config = self.config.get("orders", {})
        self.order_manager = OrderManager(
            kotak_client=self.client,
            risk_manager=self.risk_manager,
            paper_mode=self.paper_mode,
            retry_attempts=order_config.get("retry_attempts", 3),
            retry_delay=order_config.get("retry_delay_seconds", 2),
            duplicate_cooldown=order_config.get("duplicate_order_cooldown_seconds", 60)
        )
    
    def _init_position_tracker(self):
        intraday_config = self.config.get("intraday", {})
        self.position_tracker = PositionTracker(
            kotak_client=self.client,
            risk_manager=self.risk_manager,
            order_manager=self.order_manager,
            squareoff_time=intraday_config.get("squareoff_time", "15:15")
        )
    
    def _init_strategies(self):
        instruments = load_instruments()
        equity_symbols = [i["symbol"] for i in instruments.get("equity", [])]
        
        self.strategies = []
        
        # Intraday strategy
        if self.config.get("intraday", {}).get("enabled", True) and equity_symbols:
            self.strategies.append(RSIReversalStrategy(
                market_data=self.market_data,
                risk_manager=self.risk_manager,
                symbols=equity_symbols[:5]  # Limit to 5 symbols
            ))
        
        # Swing strategy
        if self.config.get("swing", {}).get("enabled", True) and equity_symbols:
            self.strategies.append(EMACrossoverStrategy(
                market_data=self.market_data,
                risk_manager=self.risk_manager,
                symbols=equity_symbols[:5]
            ))
    
    def _handle_shutdown(self, signum, frame):
        logger.warning("Shutdown signal received")
        self.stop()
    
    def connect(self, totp: str) -> bool:
        """Connect to Kotak API"""
        if self.paper_mode:
            logger.info("Paper mode - skipping API connection")
            return True
        
        if self.client:
            return self.client.connect(totp)
        return False
    
    def start(self):
        """Start the trading system"""
        self._running = True
        logger.info("Trading system started")
        
        for strategy in self.strategies:
            strategy.activate()
        
        while self._running:
            try:
                self._trading_loop()
                time.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                time.sleep(10)
    
    def _trading_loop(self):
        """Main trading loop"""
        # Check market hours
        if not is_market_open() and not self.paper_mode:
            return
        
        # Update positions
        if not self.paper_mode:
            self.position_tracker.update_all_prices()
        
        # Check for intraday square-off
        if self.position_tracker.should_squareoff():
            self.position_tracker.squareoff_intraday()
        
        # Run strategies
        for strategy in self.strategies:
            signals = strategy.run()
            for signal in signals:
                self._execute_signal(signal)
        
        # Check stop-losses and targets
        sl_triggered = self.position_tracker.check_stoploss()
        for symbol in sl_triggered:
            self.position_tracker.close_position(symbol, reason="stoploss")
        
        target_triggered = self.position_tracker.check_targets()
        for symbol in target_triggered:
            self.position_tracker.close_position(symbol, reason="target")
    
    def _execute_signal(self, signal):
        """Execute a trading signal"""
        if signal.is_buy:
            order = self.order_manager.place_order(
                symbol=signal.symbol,
                exchange="NSE",
                transaction_type="B",
                quantity=signal.quantity,
                price=signal.price,
                order_type="MKT",
                product=signal.metadata.get("product", "MIS"),
                stoploss_price=signal.stoploss,
                target_price=signal.target
            )
            
            if order and order.status.value == "complete":
                self.position_tracker.add_position(
                    symbol=signal.symbol,
                    exchange="NSE",
                    quantity=signal.quantity,
                    entry_price=order.average_price or signal.price,
                    stoploss_price=signal.stoploss,
                    target_price=signal.target,
                    product=signal.metadata.get("product", "MIS")
                )
        
        elif signal.is_sell:
            self.position_tracker.close_position(
                symbol=signal.symbol,
                exit_price=signal.price,
                reason=signal.reason
            )
    
    def stop(self):
        """Stop the trading system"""
        self._running = False
        
        for strategy in self.strategies:
            strategy.deactivate()
        
        # Close all positions if needed
        if self.position_tracker.positions:
            logger.warning("Closing all open positions...")
            self.position_tracker.close_all_positions(reason="shutdown")
        
        if self.client and not self.paper_mode:
            self.client.disconnect()
        
        logger.info("Trading system stopped")
    
    def get_dashboard_data(self) -> dict:
        """Get data for dashboard display"""
        risk_summary = self.risk_manager.get_summary()
        position_summary = self.position_tracker.get_summary()
        order_summary = self.order_manager.get_summary()
        
        return {
            "mode": "PAPER" if self.paper_mode else "LIVE",
            "capital": format_currency(risk_summary["capital"]),
            "available": format_currency(risk_summary["available_capital"]),
            "daily_pnl": format_currency(risk_summary["daily_pnl"]),
            "daily_pnl_pct": format_percentage(
                (risk_summary["daily_pnl"] / risk_summary["capital"]) * 100
                if risk_summary["capital"] > 0 else 0
            ),
            "open_positions": position_summary["open_positions"],
            "max_positions": risk_summary["max_positions"],
            "unrealized_pnl": format_currency(position_summary["unrealized_pnl"]),
            "daily_trades": risk_summary["daily_trades"],
            "win_rate": f"{risk_summary['win_rate']:.1f}%",
            "trading_enabled": "YES" if risk_summary["trading_enabled"] else "NO",
            "kill_switch": "ACTIVE" if risk_summary["kill_switch"] else "OFF",
            "strategies": [s.name for s in self.strategies]
        }


# CLI Commands
@click.group()
@click.option("--config", "-c", default="config/settings.yaml", help="Config file path")
@click.pass_context
def cli(ctx, config):
    """SIDDHI - Intelligent Trading Platform CLI"""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.pass_context
def web(ctx):
    """Launch the web dashboard (recommended)"""
    import subprocess
    console.print(Panel(
        "[cyan]Launching SIDDHI Web Dashboard[/cyan]\n\n"
        "The dashboard will open in your browser.\n"
        "Press Ctrl+C to stop.",
        title="SIDDHI"
    ))
    subprocess.run(["streamlit", "run", "dashboard.py"])


@cli.command()
@click.pass_context
def status(ctx):
    """Show system status"""
    config = ctx.obj["config"]
    
    console.print(Panel(
        f"[cyan]SIDDHI Platform Status[/cyan]\n\n"
        f"Mode: Analysis\n"
        f"Config: config/settings.yaml\n"
        f"Market Open: {'Yes' if is_market_open() else 'No'}\n\n"
        f"[yellow]Launch dashboard:[/yellow]\n"
        f"  streamlit run dashboard.py\n"
        f"  OR: python main.py web",
        title="Status"
    ))


if __name__ == "__main__":
    cli()
