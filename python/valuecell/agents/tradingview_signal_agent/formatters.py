"""Output formatters for trading recommendations and reports"""

import logging
from typing import Dict, List

from .models import (
    EnhancedTradingRecommendation,
    OperationType,
    Position,
    PortfolioSnapshot,
)

logger = logging.getLogger(__name__)


class MessageFormatter:
    """Format trading messages and reports"""
    
    @staticmethod
    def format_recommendation_output(recommendation: EnhancedTradingRecommendation) -> str:
        """Format recommendation for display"""
        action = recommendation.action
        
        # Header with operation and confidence
        confidence_emoji = "🟢" if recommendation.confidence > 0.75 else "🟡" if recommendation.confidence > 0.5 else "🟠"
        
        output = f"""
{confidence_emoji} **{action.operation.value.upper()} Signal - {recommendation.symbol}** (Confidence: {recommendation.confidence*100:.0f}%)

**Current Status:**
- Current Price: ${recommendation.current_price:,.2f}
"""
        
        if recommendation.has_position:
            pos = recommendation.current_position
            pnl_emoji = "🟢" if pos.unrealized_pnl > 0 else "🔴"
            output += f"""- Existing Position: {pos.side.value.upper()} {pos.quantity:.4f} @ ${pos.entry_price:.2f}
- Unrealized P&L: {pnl_emoji} ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_pct:.2f}%)
"""
        
        # Operation-specific details
        if action.operation in [OperationType.OPEN, OperationType.ADD]:
            output += f"""
**Action Required: {action.operation.value.upper()}**
- Direction: **{action.side.value.upper()}**
- Suggested Quantity: {action.quantity:.4f} ({action.quantity_usd:.2f} USD)
- Entry Price: ${action.suggested_price:.2f}
- Stop Loss: ${action.stop_loss:.2f} ({MessageFormatter._calculate_stop_pct(action.suggested_price, action.stop_loss)}%)
"""
            
            if action.take_profit_targets:
                output += "- Take Profit Targets:\n"
                for i, tp in enumerate(action.take_profit_targets, 1):
                    output += f"  - TP{i}: ${tp['price']:.2f} ({tp.get('qty_pct', 100)}% of position)\n"
            
            output += f"- Leverage: {recommendation.leverage}x\n"
            output += f"- Risk: ${recommendation.risk_usd:.2f}\n"
        
        elif action.operation == OperationType.CLOSE:
            output += f"""
**Action Required: CLOSE POSITION**
- Close at: ${action.suggested_price:.2f}
- Reason: {action.reasoning}
"""
        
        elif action.operation == OperationType.REDUCE:
            output += f"""
**Action Required: REDUCE POSITION**
- Reduce by: {action.quantity:.4f} ({action.quantity_pct*100:.0f}% of position)
- Exit Price: ${action.suggested_price:.2f}
"""
        
        elif action.operation == OperationType.HOLD:
            output += f"""
**Action: HOLD**
- Maintain current position
"""
        
        # Invalidation condition
        output += f"""
**Invalidation Condition:**
{recommendation.invalidation_condition.description}

**Technical Analysis:**
{recommendation.technical_summary}

**Key Factors:**
"""
        for factor in recommendation.key_factors[:5]:  # Top 5
            output += f"- {factor}\n"
        
        # AI Reasoning
        output += f"""
**AI Analysis:**
{recommendation.ai_reasoning}

**Risks:**
"""
        for risk in recommendation.risks[:3]:  # Top 3
            output += f"⚠️ {risk}\n"
        
        return output
    
    @staticmethod
    def format_portfolio_status(snapshot: PortfolioSnapshot, positions: List[Position]) -> str:
        """Format portfolio status report"""
        pnl_emoji = "🟢" if snapshot.total_pnl > 0 else "🔴"
        pnl_sign = "+" if snapshot.total_pnl > 0 else ""
        
        output = f"""
📊 **Portfolio Status Report**

**Capital Overview:**
- Total Capital: ${snapshot.total_capital:,.2f}
- Available Cash: ${snapshot.available_capital:,.2f}
- Used Capital: ${snapshot.used_capital:,.2f}

**Performance:**
- Total P&L: {pnl_emoji} **{pnl_sign}${snapshot.total_pnl:.2f}** ({pnl_sign}{snapshot.total_return_pct:.2f}%)
- Unrealized P&L: ${snapshot.unrealized_pnl:.2f}
- Realized P&L: ${snapshot.realized_pnl:.2f}

**Risk Metrics:**
- Portfolio Heat: {snapshot.portfolio_heat:.2%}
- Exposure: {snapshot.exposure_pct:.2f}%
- Open Positions: {snapshot.open_positions_count}

**Trading Statistics:**
- Total Trades: {snapshot.total_trades}
- Win Rate: {snapshot.win_rate*100:.1f}%
- Profit Factor: {snapshot.profit_factor:.2f}
"""
        
        if positions:
            output += "\n**Open Positions:**\n"
            for pos in positions:
                pnl_emoji = "🟢" if pos.unrealized_pnl > 0 else "🔴"
                output += f"""
- **{pos.symbol}** ({pos.side.value.upper()})
  - Entry: ${pos.entry_price:.2f} | Current: ${pos.current_price:.2f}
  - Quantity: {pos.quantity:.4f} | Leverage: {pos.leverage}x
  - P&L: {pnl_emoji} ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_pct:.2f}%)
"""
        
        return output
    
    @staticmethod
    def format_position_brief(position: Position = None) -> str:
        """Format brief position description"""
        if not position:
            return "No position"
        
        pnl_emoji = "🟢" if position.unrealized_pnl > 0 else "🔴"
        return f"{position.side.value.upper()} {position.quantity:.4f} @ ${position.entry_price:.2f} {pnl_emoji} {position.unrealized_pnl_pct:+.2f}%"
    
    @staticmethod
    def _calculate_stop_pct(entry: float, stop: float) -> float:
        """Calculate stop loss percentage"""
        return abs((entry - stop) / entry * 100)

