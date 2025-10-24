"""Logging configuration for TradingView Signal Agent"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(
    log_dir: str = "logs",
    log_level: int = logging.INFO,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
):
    """
    Setup comprehensive logging for TradingView Signal Agent
    
    Args:
        log_dir: Directory to store log files (can be existing timestamped dir)
        log_level: Logging level
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep
    """
    # Check if log_dir already has a timestamp directory (launched from launch.py)
    # or if we need to create one ourselves
    log_path = Path(log_dir)
    
    # If log_dir doesn't look like a timestamped directory, create one
    # (timestamped dirs have format YYYYMMDDHHmmss - 14 digits)
    if not log_path.name.isdigit() or len(log_path.name) != 14:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        log_path = log_path / timestamp
    
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Log file paths
    agent_log_file = log_path / "tradingview_agent.log"
    error_log_file = log_path / "tradingview_error.log"
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler (INFO and above)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for all logs
    file_handler = RotatingFileHandler(
        agent_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # File handler for errors only
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_handler)
    
    # Configure specific loggers
    
    # TradingView Signal Agent
    agent_logger = logging.getLogger('valuecell.agents.tradingview_signal_agent')
    agent_logger.setLevel(log_level)
    
    # Suppress noisy libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info("="*80)
    logger.info("TradingView Signal Agent - Logging Initialized")
    logger.info(f"Log directory: {log_path}")
    logger.info(f"Agent log: {agent_log_file}")
    logger.info(f"Error log: {error_log_file}")
    logger.info(f"Log level: {logging.getLevelName(log_level)}")
    logger.info("="*80)
    
    return log_path


def get_logger(name: str) -> logging.Logger:
    """Get logger for a specific module"""
    return logging.getLogger(f'valuecell.agents.tradingview_signal_agent.{name}')


# Log level helpers
def set_debug_mode():
    """Enable debug logging"""
    logging.getLogger('valuecell.agents.tradingview_signal_agent').setLevel(logging.DEBUG)
    logger = get_logger('logging_config')
    logger.info("Debug mode enabled")


def set_production_mode():
    """Set production logging (WARNING and above)"""
    logging.getLogger('valuecell.agents.tradingview_signal_agent').setLevel(logging.WARNING)
    logger = get_logger('logging_config')
    logger.warning("Production mode enabled - only warnings and errors will be logged")

