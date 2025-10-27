"""AI-powered decision engine with COT reasoning"""

import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from agno.models.openrouter import OpenRouter

from .models import (
    COTStyleRecommendation,
    ConfidenceLevel,
    EnhancedTradingRecommendation,
    InvalidationCondition,
    MarketContext,
    OperationType,
    Position,
    PositionAction,
    PositionSide,
    PortfolioSnapshot,
    TradeSignalArgs,
    TradingSessionConfig,
)

logger = logging.getLogger(__name__)


class COTDecisionEngine:
    """
    Chain-of-Thought decision engine
    
    Generates trading decisions using structured COT reasoning,
    compatible with the provided COT prompt style.
    """
    
    def __init__(self, model_id: str = "anthropic/claude-sonnet-4.5"):
        self.model_id = model_id
        try:
            self.llm = OpenRouter(id=model_id)
            logger.info(f"Initialized COT Decision Engine with model: {model_id}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
    
    async def make_decisions_with_cot(
        self,
        portfolio_state: PortfolioSnapshot,
        market_contexts: Dict[str, MarketContext],
        positions: Dict[str, Position],
        config: TradingSessionConfig
    ) -> COTStyleRecommendation:
        """
        Generate decisions using COT reasoning
        
        Replicates the COT thought process from the provided example
        """
        if not self.llm:
            logger.error("LLM not initialized, cannot generate COT decisions")
            # Return hold decisions for all positions
            return self._fallback_decisions(positions, portfolio_state, config)
        
        # Build COT prompt
        cot_prompt = self._build_cot_prompt(
            portfolio_state, market_contexts, positions, config
        )
        
        # Call LLM for COT reasoning
        try:
            logger.info("Generating COT reasoning...")
            response = await self.llm.arun(cot_prompt)
            cot_text = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"COT reasoning generated ({len(cot_text)} chars)")
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return self._fallback_decisions(positions, portfolio_state, config)
        
        # Parse COT output to structured decisions
        decisions = self._parse_cot_to_decisions(cot_text, positions)
        
        return COTStyleRecommendation(
            timestamp=datetime.now(timezone.utc),
            session_id=config.session_id,
            chain_of_thought=cot_text,
            decisions=decisions,
            available_cash=portfolio_state.available_capital,
            total_positions=len(positions),
            tradable_tokens=config.supported_symbols
        )
    
    def _build_cot_prompt(
        self,
        portfolio_state: PortfolioSnapshot,
        market_contexts: Dict[str, MarketContext],
        positions: Dict[str, Position],
        config: TradingSessionConfig
    ) -> str:
        """Build COT prompt following the provided example format"""
        
        prompt = f"""You are an expert cryptocurrency trader managing a portfolio with ${portfolio_state.available_capital:,.2f} available cash.

**Current Positions:**
"""
        
        # List each position with details
        for symbol, pos in positions.items():
            context = market_contexts.get(symbol)
            if not context:
                continue
            
            indicators = context.current_indicators
            
            # Get additional indicators from context if available
            rsi7 = getattr(indicators, 'rsi7', None)
            rsi14 = getattr(indicators, 'rsi14', indicators.rsi)
            ema_50 = getattr(indicators, 'ema_50', None)
            atr3 = getattr(indicators, 'atr3', None)
            atr14 = getattr(indicators, 'atr14', None)
            
            prompt += f"""
- **{symbol}**:
  - Entry Price: ${pos.entry_price:.2f}
  - Current Price: ${indicators.close_price:.2f}
  - Quantity: {pos.quantity:.4f}
  - Leverage: {pos.leverage}x
  - Unrealized P&L: ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_pct:.2f}%)
  - Profit Target: ${pos.profit_target:.2f}
  - Stop Loss: ${pos.stop_loss_price:.2f}
  - Invalidation Condition: {pos.invalidation_condition.description}
  - **Technical Indicators (Enhanced Phase 2)**:
    - RSI7: {rsi7:.2f if rsi7 else 'N/A'} | RSI14: {rsi14:.2f}
    - EMA20: ${indicators.ema_20:.2f if indicators.ema_20 else 'N/A'} | EMA50: ${ema_50:.2f if ema_50 else 'N/A'}
    - MACD: {indicators.macd:.3f} | Signal: {indicators.macd_signal:.3f}
    - ATR3: {atr3:.2f if atr3 else 'N/A'} | ATR14: {atr14:.2f if atr14 else 'N/A'} (Volatility)
  - Funding Rate: {indicators.funding_rate:.6f if indicators.funding_rate else 'N/A'}
"""
        
        prompt += f"""

**Tradable Tokens:** {config.supported_symbols}

**Portfolio State:**
- Total Capital: ${portfolio_state.total_capital:,.2f}
- Available Cash: ${portfolio_state.available_capital:,.2f}
- Total P&L: ${portfolio_state.total_pnl:.2f} ({portfolio_state.total_return_pct:.2f}%)
- Open Positions: {portfolio_state.open_positions_count}/{config.max_concurrent_positions}
- Portfolio Heat: {portfolio_state.portfolio_heat:.2%}

**Trading Rules:**
- Pyramiding (adding to positions): {"ALLOWED" if config.allow_pyramiding else "NOT ALLOWED"}
- If pyramiding is not allowed, size correctly on entry because you won't be able to scale up your position.
- Max concurrent positions: {config.max_concurrent_positions}
- Current open positions: {len(positions)}

**Task:**
For each position, decide whether to:
1. **HOLD**: Keep the position if invalidation condition is not triggered and signals remain favorable
2. **CLOSE**: Exit if invalidation condition is triggered or other exit criteria met
3. **ENTRY**: Open new position if strong signal and you have available position slots

**Think step by step (Chain of Thought):**
1. First, review each existing position:
   - Is the invalidation condition triggered?
   - Is the current price near stop loss or profit target?
   - **Enhanced Multi-Period Analysis (Phase 2)**:
     * RSI Momentum: Compare RSI7 vs RSI14 for short-term momentum shifts
     * EMA Trend: Check EMA20 vs EMA50 alignment and price position
     * MACD: Analyze MACD line vs signal line for momentum
     * Volatility: Check ATR3 vs ATR14 for volatility expansion/contraction
   - What is the funding rate telling us?
   - What is the current P&L?

2. Then, consider new entries (only if you have available position slots and are not already in the coin):
   - Check if you have less than {config.max_concurrent_positions} positions
   - Analyze technical indicators for symbols you're not in:
     * Multi-period RSI analysis (RSI7 vs RSI14 divergence)
     * EMA trend alignment (price vs EMA20 vs EMA50)
     * Volatility context (ATR3 vs ATR14 ratio) - adjust position size for high volatility
   - Assess confidence and calculate appropriate position size (consider volatility)

**Output Format:**
Provide your detailed chain of thought reasoning first, then output JSON for each coin.

For **HOLD** (existing position to maintain):
```json
{{
  "SYMBOL": {{
    "trade_signal_args": {{
      "coin": "SYMBOL",
      "signal": "hold",
      "quantity": <current_quantity>,
      "profit_target": <target_price>,
      "stop_loss": <stop_price>,
      "invalidation_condition": "<condition_description>",
      "leverage": <int>,
      "confidence": <0-1>,
      "risk_usd": <float>
    }}
  }}
}}
```

For **CLOSE** (exit position):
```json
{{
  "SYMBOL": {{
    "trade_signal_args": {{
      "coin": "SYMBOL",
      "signal": "close",
      "quantity": <current_quantity>,
      "profit_target": <target_price>,
      "stop_loss": <stop_price>,
      "invalidation_condition": "<condition_description>",
      "leverage": <int>,
      "confidence": <0-1>,
      "risk_usd": <float>,
      "justification": "<reason_for_closing>"
    }}
  }}
}}
```

For **ENTRY** (new position):
```json
{{
  "SYMBOL": {{
    "trade_signal_args": {{
      "coin": "SYMBOL",
      "signal": "entry",
      "quantity": <calculated_quantity>,
      "profit_target": <target_price>,
      "stop_loss": <stop_price>,
      "invalidation_condition": "<new_condition>",
      "leverage": <5-40>,
      "confidence": <0-1>,
      "risk_usd": <risk_amount>,
      "justification": "<entry_reasoning>"
    }}
  }}
}}
```

Begin your analysis with "First, I need to check..." and work through each position systematically:
"""
        
        return prompt
    
    def _parse_cot_to_decisions(
        self,
        cot_text: str,
        existing_positions: Dict[str, Position]
    ) -> Dict[str, TradeSignalArgs]:
        """Parse COT output to structured decisions"""
        decisions = {}
        
        # Try to extract JSON from the COT text
        # Look for JSON blocks
        json_matches = re.findall(r'\{[\s\S]*?\}(?=\s*(?:\{|$))', cot_text)
        
        if not json_matches:
            logger.warning("No JSON found in COT output, using fallback")
            # Fallback: hold all existing positions
            for symbol, pos in existing_positions.items():
                decisions[symbol] = TradeSignalArgs(
                    coin=symbol,
                    signal="hold",
                    quantity=pos.quantity,
                    profit_target=pos.profit_target,
                    stop_loss=pos.stop_loss_price,
                    invalidation_condition=pos.invalidation_condition.description,
                    leverage=pos.leverage,
                    confidence=pos.confidence,
                    risk_usd=pos.risk_usd
                )
            return decisions
        
        # Try to parse each JSON match
        for json_str in json_matches:
            try:
                parsed = json.loads(json_str)
                
                # Check if it's a symbol-level dict
                for symbol, data in parsed.items():
                    if "trade_signal_args" in data:
                        args = data["trade_signal_args"]
                        decisions[symbol] = TradeSignalArgs(**args)
                    elif "coin" in parsed:
                        # Direct signal args
                        decisions[parsed["coin"]] = TradeSignalArgs(**parsed)
                        break
                        
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                continue
            except Exception as e:
                logger.warning(f"Failed to create TradeSignalArgs: {e}")
                continue
        
        # Ensure all existing positions have decisions (default to hold)
        for symbol, pos in existing_positions.items():
            if symbol not in decisions:
                decisions[symbol] = TradeSignalArgs(
                    coin=symbol,
                    signal="hold",
                    quantity=pos.quantity,
                    profit_target=pos.profit_target,
                    stop_loss=pos.stop_loss_price,
                    invalidation_condition=pos.invalidation_condition.description,
                    leverage=pos.leverage,
                    confidence=pos.confidence,
                    risk_usd=pos.risk_usd
                )
        
        return decisions
    
    def _fallback_decisions(
        self,
        positions: Dict[str, Position],
        portfolio_state: PortfolioSnapshot,
        config: TradingSessionConfig
    ) -> COTStyleRecommendation:
        """Generate fallback hold decisions when LLM fails"""
        decisions = {}
        
        for symbol, pos in positions.items():
            decisions[symbol] = TradeSignalArgs(
                coin=symbol,
                signal="hold",
                quantity=pos.quantity,
                profit_target=pos.profit_target,
                stop_loss=pos.stop_loss_price,
                invalidation_condition=pos.invalidation_condition.description,
                leverage=pos.leverage,
                confidence=pos.confidence,
                risk_usd=pos.risk_usd
            )
        
        return COTStyleRecommendation(
            timestamp=datetime.now(timezone.utc),
            session_id=config.session_id,
            chain_of_thought="LLM unavailable, defaulting to hold all positions",
            decisions=decisions,
            available_cash=portfolio_state.available_capital,
            total_positions=len(positions),
            tradable_tokens=config.supported_symbols
        )
    
    @staticmethod
    def _get_confidence_level(confidence: float) -> ConfidenceLevel:
        """Convert confidence value to level"""
        if confidence >= 0.90:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.75:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.50:
            return ConfidenceLevel.MEDIUM
        elif confidence >= 0.25:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

