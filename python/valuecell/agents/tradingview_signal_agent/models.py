"""Data models for TradingView Signal Agent"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ==================== Enums ====================

class TradingMode(str, Enum):
    """Trading mode"""
    PAPER = "paper"
    ADVISORY = "advisory"
    LIVE = "live"


class PositionSide(str, Enum):
    """Position direction"""
    LONG = "long"
    SHORT = "short"


class OperationType(str, Enum):
    """Operation type"""
    OPEN = "open"
    ADD = "add"
    REDUCE = "reduce"
    CLOSE = "close"
    HOLD = "hold"
    REVERSE = "reverse"


class ConfidenceLevel(str, Enum):
    """Confidence level"""
    VERY_HIGH = "very_high"  # 0.90-1.0
    HIGH = "high"            # 0.75-0.89
    MEDIUM = "medium"        # 0.50-0.74
    LOW = "low"              # 0.25-0.49
    VERY_LOW = "very_low"    # 0-0.24


# ==================== Invalidation Condition ====================

class InvalidationCondition(BaseModel):
    """Invalidation condition (more flexible than simple stop loss)"""
    description: str  # Human-readable description
    
    # Structured fields for programmatic checking
    condition_type: str = "price_close_below"  # "price_close_below", "price_close_above", "time_based"
    trigger_price: Optional[float] = None
    timeframe: str = "3m"  # "1m", "3m", "5m", "15m"
    candle_closes: int = 1  # Number of candles that need to satisfy condition
    
    def is_triggered(self, recent_candles: List[Dict[str, float]]) -> bool:
        """Check if invalidation condition is triggered"""
        if not recent_candles or len(recent_candles) < self.candle_closes:
            return False
        
        if self.condition_type == "price_close_below" and self.trigger_price:
            closes = [c["close"] for c in recent_candles[-self.candle_closes:]]
            return all(close < self.trigger_price for close in closes)
        
        elif self.condition_type == "price_close_above" and self.trigger_price:
            closes = [c["close"] for c in recent_candles[-self.candle_closes:]]
            return all(close > self.trigger_price for close in closes)
        
        return False


# ==================== Technical Indicators ====================

class MACDIndicator(BaseModel):
    """MACD indicator"""
    macd_line: float
    signal_line: float
    histogram: float
    
    @property
    def is_bullish_crossover(self) -> bool:
        """MACD line crosses above signal line"""
        return self.macd_line > self.signal_line and self.histogram > 0
    
    @property
    def is_bearish_crossover(self) -> bool:
        """MACD line crosses below signal line"""
        return self.macd_line < self.signal_line and self.histogram < 0


class RSIIndicator(BaseModel):
    """RSI indicator"""
    value: float = Field(..., ge=0, le=100)
    
    @property
    def is_overbought(self) -> bool:
        return self.value > 70
    
    @property
    def is_oversold(self) -> bool:
        return self.value < 30
    
    @property
    def is_neutral(self) -> bool:
        return 40 <= self.value <= 60


class ChartPrimeIndicators(BaseModel):
    """Chart Prime indicator suite"""
    trend_strength: Optional[float] = None  # -100 to 100
    trend_direction: Optional[str] = None   # "bullish", "bearish", "neutral"
    momentum_score: Optional[float] = None  # 0-100
    volatility_index: Optional[float] = None
    custom_signals: Optional[Dict[str, Any]] = Field(default_factory=dict)


# ==================== Webhook Payload ====================

class TradingViewWebhookPayload(BaseModel):
    """TradingView webhook data structure"""
    symbol: str
    timestamp: datetime
    timeframe: str = "15m"
    
    # Price data
    price: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    # Technical indicators
    macd: MACDIndicator
    rsi: RSIIndicator
    chart_prime: Optional[ChartPrimeIndicators] = None
    
    # Optional indicators
    ema_9: Optional[float] = None
    ema_20: Optional[float] = None
    ema_21: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    
    # Metadata
    strategy_name: Optional[str] = None
    alert_message: Optional[str] = None


class CryptoTechnicalIndicators(BaseModel):
    """Extended crypto technical indicators"""
    symbol: str
    timestamp: datetime
    timeframe: str
    
    # Price data
    close_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: float
    
    # Technical indicators
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    
    rsi: Optional[float] = None
    
    ema_20: Optional[float] = None  # COT重点
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    
    # Crypto-specific indicators
    funding_rate: Optional[float] = None
    funding_rate_8h: Optional[float] = None
    open_interest: Optional[float] = None
    long_short_ratio: Optional[float] = None
    
    # Chart Prime
    chart_prime: Optional[ChartPrimeIndicators] = None


class MarketContext(BaseModel):
    """Market context for COT reasoning"""
    symbol: str
    timestamp: datetime
    
    # Current market data
    current_indicators: CryptoTechnicalIndicators
    
    # Historical candles for invalidation checking
    recent_candles_3m: List[Dict[str, float]] = Field(default_factory=list)
    recent_candles_15m: List[Dict[str, float]] = Field(default_factory=list)
    
    # Market sentiment
    market_sentiment: Optional[str] = None  # "bullish", "bearish", "neutral"
    fear_greed_index: Optional[float] = None


class TimeSeriesIndicatorData(BaseModel):
    """Time series indicator data for storage"""
    id: Optional[int] = None
    symbol: str
    timestamp: datetime
    timeframe: str
    
    ohlcv: Dict[str, float]  # {open, high, low, close, volume}
    indicators: Dict[str, Any]  # All technical indicators
    raw_payload: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== Position Management ====================

class Position(BaseModel):
    """Position information"""
    position_id: str
    session_id: str
    symbol: str
    side: PositionSide
    
    # Position size
    quantity: float
    notional_value: float
    leverage: int = Field(..., ge=1, le=40)
    
    # Price information
    entry_price: float
    current_price: Optional[float] = None
    
    # Exit strategy
    profit_target: float
    stop_loss_price: float
    take_profit_targets: List[Dict[str, float]] = Field(default_factory=list)
    invalidation_condition: InvalidationCondition
    
    # Risk indicators
    risk_usd: float
    risk_amount: float = 0.0
    reward_potential: float = 0.0
    risk_reward_ratio: float = 0.0
    confidence: float = Field(..., ge=0, le=1)
    
    # P&L information
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    
    # Crypto-specific
    funding_rate: Optional[float] = None
    last_funding_time: Optional[datetime] = None
    
    # Time information
    opened_at: datetime
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Source information
    entry_signal_id: Optional[str] = None
    entry_reasoning: Optional[str] = None
    
    @property
    def is_profitable(self) -> bool:
        return self.unrealized_pnl > 0
    
    def calculate_unrealized_pnl(self, current_price: float) -> float:
        """Calculate unrealized P&L"""
        if self.side == PositionSide.LONG:
            pnl = (current_price - self.entry_price) * self.quantity
        else:  # SHORT
            pnl = (self.entry_price - current_price) * self.quantity
        
        self.current_price = current_price
        self.unrealized_pnl = pnl
        if self.notional_value > 0:
            self.unrealized_pnl_pct = (pnl / self.notional_value) * 100
        return pnl
    
    def check_invalidation(self, recent_candles: List[Dict[str, float]]) -> bool:
        """Check if invalidation condition is triggered"""
        return self.invalidation_condition.is_triggered(recent_candles)


class ClosedPosition(BaseModel):
    """Closed position record"""
    position_id: str
    session_id: str
    symbol: str
    side: PositionSide
    
    # Position information
    quantity: float
    entry_price: float
    exit_price: float
    
    # P&L
    realized_pnl: float
    realized_pnl_pct: float
    
    # Time
    opened_at: datetime
    closed_at: datetime
    holding_duration: float  # hours
    
    # Reason
    exit_reason: str  # "stop_loss", "take_profit", "invalidation_triggered", "signal_reverse", "manual"
    exit_signal_id: Optional[str] = None


class PortfolioSnapshot(BaseModel):
    """Portfolio snapshot for history"""
    session_id: str
    timestamp: datetime
    
    # Capital state
    total_capital: float
    available_capital: float
    used_capital: float
    
    # Position state
    open_positions_count: int
    total_position_value: float
    
    # P&L
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    total_return_pct: float
    
    # Risk indicators
    portfolio_heat: float
    exposure_pct: float
    
    # Performance indicators
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0


# ==================== Trading Configuration ====================

class TradingSessionConfig(BaseModel):
    """Trading session configuration"""
    session_id: str
    user_id: Optional[str] = None
    
    # Capital configuration
    initial_capital: float = Field(..., gt=0)
    current_capital: float
    
    # Risk parameters
    max_position_size_pct: float = 0.20
    max_total_exposure_pct: float = 0.60
    max_concurrent_positions: int = 5
    risk_per_trade_pct: float = 0.02
    
    # Trading rules
    allow_pyramiding: bool = False
    allow_hedging: bool = False
    max_leverage: int = 20
    default_leverage: int = 10
    leverage_by_confidence: Dict[str, int] = Field(default_factory=lambda: {
        "high": 15,
        "medium": 10,
        "low": 5
    })
    
    # Timeframes
    primary_timeframe: str = "15m"
    invalidation_timeframe: str = "3m"
    
    # Trading pairs
    supported_symbols: List[str] = Field(default_factory=list)
    trading_mode: TradingMode = TradingMode.PAPER
    
    # AI configuration
    decision_model: str = "anthropic/claude-sonnet-4.5"
    use_cot_reasoning: bool = True
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


# ==================== Trading Signals ====================

class PositionAction(BaseModel):
    """Specific position action recommendation"""
    operation: OperationType
    symbol: str
    side: PositionSide
    
    # Quantity recommendation
    quantity: Optional[float] = None
    quantity_usd: Optional[float] = None
    quantity_pct: Optional[float] = None
    
    # Price recommendation
    suggested_price: float
    price_range: Optional[tuple[float, float]] = None
    
    # Stop loss and take profit
    stop_loss: Optional[float] = None
    take_profit_targets: Optional[List[Dict[str, float]]] = None
    
    # Reasoning
    reasoning: str
    urgency: str = "normal"  # "low", "normal", "high", "urgent"


class TradeSignalArgs(BaseModel):
    """COT-style trade signal arguments"""
    coin: str
    signal: str  # "hold", "entry", "exit", "close"
    quantity: float
    profit_target: float
    stop_loss: float
    invalidation_condition: str
    leverage: int = Field(..., ge=5, le=40)
    confidence: float = Field(..., ge=0, le=1)
    risk_usd: float
    justification: Optional[str] = None  # Only for entry/exit/close


class SignalSource(BaseModel):
    """Signal source scoring"""
    name: str
    score: float = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0, le=1)
    reasoning: Optional[str] = None


class EnhancedTradingRecommendation(BaseModel):
    """Enhanced trading recommendation"""
    recommendation_id: str
    session_id: str
    symbol: str
    timestamp: datetime
    
    # Current position
    current_position: Optional[Position] = None
    has_position: bool = False
    
    # Core recommendation
    action: PositionAction
    confidence: float = Field(..., ge=0, le=1)
    confidence_level: ConfidenceLevel
    
    # Risk indicators
    risk_usd: float
    leverage: int = Field(default=10, ge=5, le=40)
    invalidation_condition: InvalidationCondition
    
    # Market analysis
    current_price: float
    technical_analysis: Dict[str, Any]
    market_context: MarketContext
    external_analysis: Optional[Dict[str, Any]] = None
    
    # Analysis sources
    signal_sources: List[SignalSource] = Field(default_factory=list)
    technical_summary: str = ""
    trend: str = "neutral"
    key_levels: Dict[str, float] = Field(default_factory=dict)
    
    # AI reasoning
    chain_of_thought: Optional[str] = None
    ai_reasoning: str
    key_factors: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    
    # Portfolio impact
    portfolio_impact: Dict[str, float] = Field(default_factory=dict)
    
    # Scenario analysis
    scenario_analysis: Dict[str, float] = Field(default_factory=dict)
    
    # Metadata
    agent_model: str
    valid_until: Optional[datetime] = None
    
    def to_cot_signal(self) -> TradeSignalArgs:
        """Convert to COT-style signal"""
        signal_map = {
            OperationType.OPEN: "entry",
            OperationType.ADD: "entry",
            OperationType.REDUCE: "exit",
            OperationType.CLOSE: "close",
            OperationType.HOLD: "hold"
        }
        
        return TradeSignalArgs(
            coin=self.symbol,
            signal=signal_map.get(self.action.operation, "hold"),
            quantity=self.action.quantity or (
                self.current_position.quantity if self.current_position else 0
            ),
            profit_target=self.action.take_profit_targets[0]["price"] if self.action.take_profit_targets else 0,
            stop_loss=self.action.stop_loss or 0,
            invalidation_condition=self.invalidation_condition.description,
            leverage=self.leverage,
            confidence=self.confidence,
            risk_usd=self.risk_usd,
            justification=self.ai_reasoning if self.action.operation != OperationType.HOLD else None
        )


class COTStyleRecommendation(BaseModel):
    """COT-style complete output"""
    timestamp: datetime
    session_id: str
    chain_of_thought: str
    decisions: Dict[str, TradeSignalArgs]
    available_cash: float
    total_positions: int
    tradable_tokens: List[str]
    
    def to_cot_format(self) -> Dict:
        """Convert to COT expected output format"""
        output = {}
        for symbol, args in self.decisions.items():
            output[symbol] = {
                "trade_signal_args": args.dict(exclude_none=True)
            }
        return output


class MultiSymbolRecommendations(BaseModel):
    """Multi-symbol recommendations summary"""
    timestamp: datetime
    recommendations: List[EnhancedTradingRecommendation]
    market_sentiment: str = "mixed"
    total_symbols_analyzed: int
    high_confidence_signals: int
    top_opportunities: List[str] = Field(default_factory=list)


# ==================== Performance Analytics ====================

class TradingStatistics(BaseModel):
    """Trading statistics"""
    session_id: str
    period_start: datetime
    period_end: datetime
    
    # Trading statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L statistics
    total_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    profit_factor: float = 0.0
    
    # Risk indicators
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    
    # Position statistics
    avg_holding_time: float = 0.0  # hours
    max_concurrent_positions: int = 0

