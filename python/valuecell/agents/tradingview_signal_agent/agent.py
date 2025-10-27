"""Main TradingView Signal Agent with Position Management"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator, Dict, Optional

from agno.models.openrouter import OpenRouter

from valuecell.core.agent.responses import streaming
from valuecell.core.types import BaseAgent, StreamResponse

from .constants import (
    DEFAULT_CRYPTO_SYMBOLS,
    DEFAULT_DECISION_MODEL,
    DEFAULT_INITIAL_CAPITAL,
)
from .decision_engine import COTDecisionEngine
from .formatters import MessageFormatter
from .indicator_store import IndicatorDataStore
from .models import (
    InvalidationCondition,
    MarketContext,
    OperationType,
    Position,
    PositionSide,
    TradingMode,
    TradingSessionConfig,
)
from .portfolio_manager import PortfolioManager
from .technical_analyzer import TradingViewTechnicalAnalyzer

logger = logging.getLogger(__name__)


class TradingViewSignalAgent(BaseAgent):
    """
    TradingView Signal Agent with comprehensive position management
    
    Features:
    - Receives indicator data from Svix API polling (1-minute intervals)
    - Performs technical analysis on MACD, RSI, EMA, ATR indicators
    - Manages positions with risk controls
    - Generates AI-powered trading recommendations using COT reasoning
    - Supports paper trading mode
    - Tracks performance and P&L
    """
    
    def __init__(self):
        super().__init__()
        
        # Session management: {session_id: PortfolioManager}
        self.sessions: Dict[str, PortfolioManager] = {}
        
        # Components
        self.indicator_store = IndicatorDataStore()
        self.technical_analyzer = TradingViewTechnicalAnalyzer()
        
        logger.info("TradingView Signal Agent initialized")
    
    async def stream(
        self,
        query: str,
        session_id: str,
        task_id: str,
        dependencies: Optional[Dict] = None,
    ) -> AsyncGenerator[StreamResponse, None]:
        """
        Process user requests
        
        Supported commands:
        - "Setup trading with $X for BTC, ETH..."
        - "Analyze BTCUSDT"
        - "Portfolio status"
        - "Close BTCUSDT"
        """
        try:
            query_lower = query.lower().strip()
            
            # 1. Setup command
            if "setup" in query_lower or "initialize" in query_lower:
                async for response in self._handle_setup(query, session_id):
                    yield response
                return
            
            # 2. Check if session exists
            if session_id not in self.sessions:
                yield streaming.message_chunk(
                    "⚠️ **No trading session found.**\n\n"
                    "Please setup a trading session first:\n"
                    "Example: `Setup trading with $100,000 for BTCUSDT and ETHUSDT`\n"
                )
                return
            
            portfolio_manager = self.sessions[session_id]
            
            # 3. Route to appropriate handler
            if "analyze" in query_lower or "signal" in query_lower:
                async for response in self._handle_analyze(query, session_id, portfolio_manager):
                    yield response
            
            elif "portfolio" in query_lower or "status" in query_lower:
                async for response in self._handle_portfolio_status(session_id, portfolio_manager):
                    yield response
            
            elif "close" in query_lower or "exit" in query_lower:
                async for response in self._handle_close_position(query, session_id, portfolio_manager):
                    yield response
            
            elif "performance" in query_lower or "history" in query_lower:
                async for response in self._handle_performance(session_id, portfolio_manager):
                    yield response
            
            else:
                yield streaming.message_chunk(
                    "🤖 **Available Commands:**\n\n"
                    "- `analyze BTCUSDT` - Get trading recommendation\n"
                    "- `portfolio status` - View positions and P&L\n"
                    "- `performance` - View trading statistics\n"
                    "- `close BTCUSDT` - Close a position\n"
                )
        
        except Exception as e:
            logger.error(f"Error in stream: {e}", exc_info=True)
            yield streaming.failed(f"Error: {str(e)}")
    
    async def _handle_setup(
        self,
        query: str,
        session_id: str
    ) -> AsyncGenerator[StreamResponse, None]:
        """Setup trading session"""
        yield streaming.message_chunk("🔧 **Setting up trading session...**\n\n")
        
        # Parse configuration from query
        config = await self._parse_setup_config(query)
        
        # Create session configuration
        session_config = TradingSessionConfig(
            session_id=session_id,
            initial_capital=config["initial_capital"],
            current_capital=config["initial_capital"],
            supported_symbols=config["symbols"],
            trading_mode=TradingMode.PAPER,
            decision_model=DEFAULT_DECISION_MODEL
        )
        
        # Create portfolio manager
        portfolio_manager = PortfolioManager(session_config)
        self.sessions[session_id] = portfolio_manager
        
        # Save to database
        await portfolio_manager.db.save_session(session_config)
        
        # Output confirmation
        yield streaming.message_chunk(
            f"✅ **Trading Session Created**\n\n"
            f"**Configuration:**\n"
            f"- Session ID: `{session_id[:8]}...`\n"
            f"- Initial Capital: ${config['initial_capital']:,.2f}\n"
            f"- Symbols: {', '.join(config['symbols'])}\n"
            f"- Mode: Paper Trading (Simulation)\n"
            f"- Max Position Size: 20% per trade\n"
            f"- Risk Per Trade: 2%\n"
            f"- Max Concurrent Positions: 5\n\n"
            f"🚀 **Ready to analyze and trade!**\n"
        )
    
    async def _handle_analyze(
        self,
        query: str,
        session_id: str,
        portfolio_manager: PortfolioManager
    ) -> AsyncGenerator[StreamResponse, None]:
        """Analyze symbol and generate recommendation"""
        # Extract symbol from query
        symbol = self._extract_symbol(query)
        
        if not symbol:
            yield streaming.message_chunk("⚠️ Please specify a symbol (e.g., BTCUSDT)\n")
            return
        
        yield streaming.message_chunk(f"🔍 **Analyzing {symbol}...**\n\n")
        
        # 1. Get latest indicator data
        yield streaming.message_chunk("📊 Fetching indicator data...\n")
        latest_data = await self.indicator_store.get_latest_data(symbol, timeframe="1m")
        
        if not latest_data:
            yield streaming.message_chunk(
                f"⚠️ No data available for {symbol}.\n"
                "Please ensure Svix polling service is running and collecting data.\n"
            )
            return
        
        # Check data freshness (should be within 5 minutes for 1m data)
        from datetime import timedelta
        data_age = datetime.now(timezone.utc) - latest_data.timestamp
        if data_age > timedelta(minutes=5):
            yield streaming.message_chunk(
                f"⚠️ **Data Freshness Warning**: Latest data is {int(data_age.total_seconds() / 60)} minutes old.\n"
                f"   Data timestamp: {latest_data.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                f"   Expected refresh: Every 3 minutes\n\n"
            )
        else:
            yield streaming.message_chunk(
                f"✓ Data is fresh ({int(data_age.total_seconds())}s old)\n"
            )
        
        # Get historical data
        historical_data = await self.indicator_store.get_recent_data(symbol, limit=100, timeframe="1m")
        
        # 2. Get current position
        current_position = portfolio_manager.position_manager.get_position(symbol)
        portfolio_snapshot = await portfolio_manager.get_portfolio_summary()
        
        yield streaming.message_chunk(
            f"💹 Current Price: ${latest_data.ohlcv['close']:,.2f}\n"
            f"💼 Position: {MessageFormatter.format_position_brief(current_position)}\n\n"
        )
        
        # 3. Technical analysis (Enhanced with Phase 2 improvements)
        yield streaming.message_chunk("📈 Running enhanced technical analysis...\n")
        
        # Use TimeSeriesIndicatorData directly for analysis
        technical_result = self.technical_analyzer.synthesize_technical_signals(
            latest_data,
            historical_data
        )
        
        # Display enhanced analysis results
        yield streaming.message_chunk("\n**📊 Technical Analysis Summary:**\n")
        yield streaming.message_chunk(f"- Signal Strength: {technical_result['signal_strength']:.1f}\n")
        yield streaming.message_chunk(f"- Confidence: {technical_result['confidence']:.1%}\n")
        yield streaming.message_chunk(f"- Trend: {technical_result['trend']}\n\n")
        
        # EMA Trend Analysis
        if "ema_analysis" in technical_result and technical_result["ema_analysis"]:
            ema = technical_result["ema_analysis"]
            if "trend_direction" in ema:
                yield streaming.message_chunk(
                    f"**📐 EMA Trend:** {ema['trend_direction'].upper()} "
                    f"(strength: {ema.get('trend_strength', 0):.1f})\n"
                )
                yield streaming.message_chunk(f"- Price position: {ema.get('price_position', 'unknown')}\n")
        
        # RSI Divergence Analysis
        if "rsi_divergence_analysis" in technical_result and technical_result["rsi_divergence_analysis"]:
            rsi_div = technical_result["rsi_divergence_analysis"]
            if rsi_div.get("divergence_type") != "neutral":
                yield streaming.message_chunk(
                    f"**🎯 RSI Divergence:** {rsi_div['divergence_type'].upper()} "
                    f"(RSI7: {latest_data.indicators.get('rsi7', 0):.1f}, RSI14: {latest_data.indicators.get('rsi14', 0):.1f})\n"
                )
        
        # Volatility Context
        if "volatility_analysis" in technical_result and technical_result["volatility_analysis"]:
            vol = technical_result["volatility_analysis"]
            yield streaming.message_chunk(
                f"**📉 Volatility:** {vol['volatility_state'].replace('_', ' ').title()} "
                f"(Risk: {vol['risk_level']})\n"
            )
            if "suggested_stop_distance" in vol and vol["suggested_stop_distance"]:
                stops = vol["suggested_stop_distance"]
                if "moderate" in stops:
                    mod_stop = stops["moderate"]
                    yield streaming.message_chunk(
                        f"- Suggested stop (ATR-based): ${mod_stop.get('stop_price_long', 0):,.2f} "
                        f"({mod_stop.get('risk_pct', 0):.2f}% risk)\n"
                    )
        
        yield streaming.message_chunk("\n")
        
        # 4. Generate recommendation using COT engine
        yield streaming.message_chunk("🧠 Generating AI-powered recommendation...\n\n")
        
        decision_engine = COTDecisionEngine(portfolio_manager.config.decision_model)
        
        # Build market context
        candles_3m = await self.indicator_store.get_candles(symbol, "3m", limit=20)
        candles_15m = await self.indicator_store.get_candles(symbol, "15m", limit=50)
        
        from .models import CryptoTechnicalIndicators
        
        market_context = MarketContext(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            current_indicators=CryptoTechnicalIndicators(
                symbol=symbol,
                timestamp=latest_data.timestamp,
                timeframe=latest_data.timeframe,
                close_price=latest_data.ohlcv["close"],
                open_price=latest_data.ohlcv["open"],
                high_price=latest_data.ohlcv["high"],
                low_price=latest_data.ohlcv["low"],
                volume=latest_data.ohlcv["volume"],
                rsi=latest_data.indicators["rsi"]["value"],
                macd=latest_data.indicators["macd"]["macd_line"],
                macd_signal=latest_data.indicators["macd"]["signal_line"],
                ema_20=latest_data.indicators.get("ema_20")
            ),
            recent_candles_3m=candles_3m,
            recent_candles_15m=candles_15m
        )
        
        # Call COT decision engine
        positions = {symbol: current_position} if current_position else {}
        
        cot_recommendation = await decision_engine.make_decisions_with_cot(
            portfolio_snapshot,
            {symbol: market_context},
            positions,
            portfolio_manager.config
        )
        
        # 5. Display recommendation
        if symbol in cot_recommendation.decisions:
            decision = cot_recommendation.decisions[symbol]
            
            yield streaming.message_chunk("📋 **Trading Recommendation:**\n\n")
            yield streaming.message_chunk(f"**Signal:** {decision.signal.upper()}\n")
            yield streaming.message_chunk(f"**Confidence:** {decision.confidence*100:.0f}%\n")
            yield streaming.message_chunk(f"**Quantity:** {decision.quantity:.4f}\n")
            yield streaming.message_chunk(f"**Profit Target:** ${decision.profit_target:.2f}\n")
            yield streaming.message_chunk(f"**Stop Loss:** ${decision.stop_loss:.2f}\n")
            yield streaming.message_chunk(f"**Leverage:** {decision.leverage}x\n")
            yield streaming.message_chunk(f"**Risk:** ${decision.risk_usd:.2f}\n\n")
            
            if decision.justification:
                yield streaming.message_chunk(f"**Reasoning:**\n{decision.justification}\n\n")
            
            # Show COT reasoning
            yield streaming.message_chunk("**Chain of Thought:**\n```\n")
            # Show first 500 chars of COT
            cot_preview = cot_recommendation.chain_of_thought[:500]
            yield streaming.message_chunk(f"{cot_preview}...\n```\n")
        
        yield streaming.message_chunk("\n✅ **Analysis complete!**\n")
    
    async def _handle_portfolio_status(
        self,
        session_id: str,
        portfolio_manager: PortfolioManager
    ) -> AsyncGenerator[StreamResponse, None]:
        """Display portfolio status"""
        yield streaming.message_chunk("📊 **Loading portfolio status...**\n\n")
        
        snapshot = await portfolio_manager.get_portfolio_summary()
        positions = portfolio_manager.position_manager.get_open_positions()
        
        status_text = MessageFormatter.format_portfolio_status(snapshot, positions)
        yield streaming.message_chunk(status_text)
    
    async def _handle_close_position(
        self,
        query: str,
        session_id: str,
        portfolio_manager: PortfolioManager
    ) -> AsyncGenerator[StreamResponse, None]:
        """Close a position"""
        symbol = self._extract_symbol(query)
        
        if not symbol:
            yield streaming.message_chunk("⚠️ Please specify which symbol to close\n")
            return
        
        position = portfolio_manager.position_manager.get_position(symbol)
        
        if not position:
            yield streaming.message_chunk(f"⚠️ No open position found for {symbol}\n")
            return
        
        # Get current price
        latest_data = await self.indicator_store.get_latest_data(symbol)
        if not latest_data:
            yield streaming.message_chunk(f"⚠️ Cannot get current price for {symbol}\n")
            return
        
        exit_price = latest_data.ohlcv["close"]
        
        # Close position
        closed_position = await portfolio_manager.position_manager.close_position(
            symbol,
            exit_price,
            "manual"
        )
        
        if closed_position:
            pnl_emoji = "🟢" if closed_position.realized_pnl > 0 else "🔴"
            yield streaming.message_chunk(
                f"✅ **Position Closed**\n\n"
                f"Symbol: {symbol}\n"
                f"Exit Price: ${exit_price:.2f}\n"
                f"P&L: {pnl_emoji} ${closed_position.realized_pnl:.2f} ({closed_position.realized_pnl_pct:.2f}%)\n"
            )
    
    async def _handle_performance(
        self,
        session_id: str,
        portfolio_manager: PortfolioManager
    ) -> AsyncGenerator[StreamResponse, None]:
        """Display performance statistics"""
        yield streaming.message_chunk("📈 **Performance Analytics**\n\n")
        
        stats = portfolio_manager.performance_analytics.calculate_statistics()
        
        yield streaming.message_chunk(
            f"**Trading Statistics:**\n"
            f"- Total Trades: {stats['total_trades']}\n"
            f"- Win Rate: {stats['win_rate']*100:.1f}%\n"
            f"- Profit Factor: {stats['profit_factor']:.2f}\n"
            f"- Average Win: ${stats['avg_win']:.2f}\n"
            f"- Average Loss: ${stats['avg_loss']:.2f}\n"
            f"- Largest Win: ${stats['largest_win']:.2f}\n"
            f"- Largest Loss: ${stats['largest_loss']:.2f}\n"
        )
    
    async def _parse_setup_config(self, query: str) -> Dict:
        """Parse setup configuration from query"""
        import re
        
        # Extract capital
        capital_match = re.search(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', query)
        initial_capital = float(capital_match.group(1).replace(',', '')) if capital_match else DEFAULT_INITIAL_CAPITAL
        
        # Extract symbols
        symbols = []
        for symbol in DEFAULT_CRYPTO_SYMBOLS:
            if symbol.lower() in query.lower() or symbol.replace('USDT', '').lower() in query.lower():
                symbols.append(symbol)
        
        if not symbols:
            symbols = DEFAULT_CRYPTO_SYMBOLS[:2]  # Default to BTC and ETH
        
        return {
            "initial_capital": initial_capital,
            "symbols": symbols
        }
    
    def _extract_symbol(self, query: str) -> Optional[str]:
        """Extract trading symbol from query"""
        query_upper = query.upper()
        
        # Check for explicit symbols
        for symbol in DEFAULT_CRYPTO_SYMBOLS:
            if symbol in query_upper:
                return symbol
            # Check without USDT suffix
            base = symbol.replace('USDT', '')
            if base in query_upper:
                return symbol
        
        return None

