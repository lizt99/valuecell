"""Constants and configuration for TradingView Signal Agent"""

from typing import Dict

# ==================== Leverage Configuration ====================

LEVERAGE_RANGES = {
    "conservative": (5, 10),
    "moderate": (10, 20),
    "aggressive": (20, 40)
}

LEVERAGE_BY_CONFIDENCE = {
    "high": 15,      # confidence > 0.75
    "medium": 10,    # confidence > 0.65
    "low": 5         # confidence <= 0.65
}

# ==================== Timeframe Configuration ====================

TIMEFRAME_TO_MINUTES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "1h": 60,
    "4h": 240,
    "1d": 1440
}

# ==================== Default Parameters ====================

DEFAULT_INITIAL_CAPITAL = 100000.0
DEFAULT_MAX_POSITION_SIZE_PCT = 0.20
DEFAULT_MAX_TOTAL_EXPOSURE_PCT = 0.60
DEFAULT_MAX_CONCURRENT_POSITIONS = 5
DEFAULT_RISK_PER_TRADE_PCT = 0.02
DEFAULT_LEVERAGE = 10

# ==================== Invalidation Condition Templates ====================

INVALIDATION_TEMPLATES = {
    "price_close_below": "If the price closes below {price} on a {timeframe} candle",
    "price_close_above": "If the price closes above {price} on a {timeframe} candle",
    "consecutive_closes_below": "If {n} consecutive {timeframe} candles close below {price}",
    "consecutive_closes_above": "If {n} consecutive {timeframe} candles close above {price}",
    "time_based": "If position held for more than {hours} hours without {condition}",
}

# ==================== COT Analysis Steps ====================

COT_ANALYSIS_STEPS = [
    "Check existing positions and invalidation conditions",
    "Analyze technical indicators for each position",
    "Review funding rates and market context",
    "Determine hold/close decisions for existing positions",
    "Assess new entry opportunities for available slots",
    "Calculate position sizes for new entries based on risk",
]

# ==================== Technical Indicator Thresholds ====================

RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
RSI_NEUTRAL_LOW = 40
RSI_NEUTRAL_HIGH = 60

# ==================== Risk Management ====================

MAX_PORTFOLIO_HEAT = 0.10  # 10% maximum total risk
MARGIN_CALL_THRESHOLD = 0.80  # 80% margin usage warning

# ==================== Confidence Level Thresholds ====================

CONFIDENCE_THRESHOLDS = {
    "very_high": 0.90,
    "high": 0.75,
    "medium": 0.50,
    "low": 0.25
}

# ==================== Default Supported Symbols ====================

DEFAULT_CRYPTO_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "BNBUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "MATICUSDT",
]

# ==================== Agent Configuration ====================

DEFAULT_DECISION_MODEL = "anthropic/claude-sonnet-4.5"
DEFAULT_PARSER_MODEL = "anthropic/claude-sonnet-4.5"

# ==================== Database Configuration ====================

DEFAULT_DB_PATH = "tradingview_signal_agent.db"
INDICATOR_DB_PATH = "tradingview_indicators.db"

# ==================== Webhook Configuration ====================

WEBHOOK_PORT = 8001
WEBHOOK_SECRET_ENV = "TRADINGVIEW_WEBHOOK_SECRET"

# ==================== Agent Server Configuration ====================

AGENT_PORT = 10004
AGENT_HOST = "localhost"
AGENT_URL = f"http://{AGENT_HOST}:{AGENT_PORT}"

