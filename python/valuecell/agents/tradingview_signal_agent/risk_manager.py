"""Risk management for position sizing and portfolio exposure"""

import logging
from typing import Dict, List

from .models import (
    OperationType,
    Position,
    PositionSide,
    TradingSessionConfig,
)

logger = logging.getLogger(__name__)


class RiskManager:
    """Risk management for trading"""
    
    def __init__(self, config: TradingSessionConfig):
        self.config = config
    
    def calculate_position_size(
        self,
        symbol: str,
        entry_price: float,
        stop_loss_price: float,
        available_capital: float,
        confidence: float = 0.5
    ) -> Dict[str, float]:
        """
        Calculate recommended position size based on risk
        
        Formula: position_size = (total_capital * risk_pct) / price_risk
        """
        if entry_price <= 0 or stop_loss_price <= 0:
            return {"error": "Invalid prices", "quantity": 0, "notional_value": 0}
        
        # Calculate risk per trade in USD
        risk_amount = available_capital * self.config.risk_per_trade_pct
        
        # Calculate price risk
        price_risk = abs(entry_price - stop_loss_price)
        
        if price_risk == 0:
            return {"error": "Invalid stop loss", "quantity": 0, "notional_value": 0}
        
        # Calculate quantity based on risk
        quantity = risk_amount / price_risk
        notional_value = quantity * entry_price
        
        # Check against max position size limit
        max_notional = available_capital * self.config.max_position_size_pct
        if notional_value > max_notional:
            # Scale down to max limit
            quantity = max_notional / entry_price
            notional_value = max_notional
            actual_risk = quantity * price_risk
        else:
            actual_risk = risk_amount
        
        # Check against available capital
        if notional_value > available_capital:
            quantity = available_capital / entry_price
            notional_value = available_capital
            actual_risk = quantity * price_risk
        
        return {
            "quantity": quantity,
            "notional_value": notional_value,
            "capital_usage_pct": (notional_value / available_capital) * 100 if available_capital > 0 else 0,
            "actual_risk_amount": actual_risk,
            "actual_risk_pct": (actual_risk / available_capital) * 100 if available_capital > 0 else 0,
            "recommended_leverage": self._get_leverage_for_confidence(confidence)
        }
    
    def _get_leverage_for_confidence(self, confidence: float) -> int:
        """Get recommended leverage based on confidence level"""
        if confidence >= 0.75:
            return self.config.leverage_by_confidence["high"]
        elif confidence >= 0.65:
            return self.config.leverage_by_confidence["medium"]
        else:
            return self.config.leverage_by_confidence["low"]
    
    def calculate_portfolio_heat(self, positions: List[Position]) -> float:
        """
        Calculate portfolio heat (total risk exposure)
        
        Portfolio Heat = sum(all position risks) / total capital
        """
        total_risk = sum(pos.risk_usd for pos in positions)
        
        # Calculate total capital (available + used)
        total_capital = self.config.current_capital + sum(
            pos.notional_value for pos in positions
        )
        
        if total_capital == 0:
            return 0.0
        
        return total_risk / total_capital
    
    def get_total_exposure(self, positions: List[Position]) -> float:
        """Get total exposure (sum of all position notional values)"""
        return sum(pos.notional_value for pos in positions)
    
    def assess_trade_risk(
        self,
        symbol: str,
        action: OperationType,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        current_positions: List[Position],
        available_capital: float
    ) -> Dict[str, any]:
        """Assess risk of a potential trade"""
        notional_value = quantity * entry_price
        risk_amount = quantity * abs(entry_price - stop_loss)
        
        # Calculate total capital
        total_capital = available_capital + sum(
            pos.notional_value for pos in current_positions
        )
        
        if total_capital == 0:
            return {
                "is_acceptable": False,
                "risks": ["No capital available"],
                "warnings": [],
                "metrics": {}
            }
        
        # Calculate new portfolio metrics
        new_position_heat = risk_amount / total_capital
        current_heat = self.calculate_portfolio_heat(current_positions)
        new_portfolio_heat = current_heat + new_position_heat
        
        # Check various limits
        risks = []
        warnings = []
        
        # Check position size limit
        if notional_value > available_capital * self.config.max_position_size_pct:
            risks.append(f"Exceeds max position size limit ({self.config.max_position_size_pct*100}%)")
        
        # Check portfolio heat limit
        if new_portfolio_heat > self.config.max_total_exposure_pct:
            risks.append(f"Exceeds portfolio heat limit ({self.config.max_total_exposure_pct*100}%)")
        
        # Check concurrent positions limit
        if action == OperationType.OPEN and len(current_positions) >= self.config.max_concurrent_positions:
            risks.append(f"Max concurrent positions reached ({self.config.max_concurrent_positions})")
        
        # Check available capital
        if notional_value > available_capital:
            risks.append("Insufficient available capital")
        
        # Warnings
        if new_portfolio_heat > 0.10:  # 10% total risk
            warnings.append("High portfolio risk (>10%)")
        
        if notional_value > available_capital * 0.15:
            warnings.append("Large position size (>15% of capital)")
        
        return {
            "is_acceptable": len(risks) == 0,
            "risks": risks,
            "warnings": warnings,
            "metrics": {
                "position_risk_pct": (risk_amount / total_capital) * 100,
                "new_portfolio_heat": new_portfolio_heat,
                "capital_usage_pct": (notional_value / available_capital) * 100 if available_capital > 0 else 0,
                "total_exposure_after": sum(p.notional_value for p in current_positions) + notional_value
            }
        }
    
    def calculate_stop_loss(
        self,
        entry_price: float,
        side: PositionSide,
        atr: float = None,
        percentage: float = 0.02
    ) -> float:
        """
        Calculate stop loss price
        
        Can use ATR-based or percentage-based
        """
        if atr and atr > 0:
            # ATR-based stop loss (2x ATR)
            multiplier = 2.0
            if side == PositionSide.LONG:
                return entry_price - (atr * multiplier)
            else:
                return entry_price + (atr * multiplier)
        else:
            # Percentage-based stop loss
            if side == PositionSide.LONG:
                return entry_price * (1 - percentage)
            else:
                return entry_price * (1 + percentage)
    
    def calculate_take_profit_targets(
        self,
        entry_price: float,
        stop_loss: float,
        side: PositionSide,
        risk_reward_ratios: List[float] = [2.0, 3.0, 4.0]
    ) -> List[Dict[str, float]]:
        """
        Calculate take profit targets based on risk-reward ratios
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            side: Position side
            risk_reward_ratios: List of R:R ratios for targets
        
        Returns:
            List of take profit targets with prices and quantities
        """
        risk = abs(entry_price - stop_loss)
        targets = []
        
        # Quantity percentages for each target
        qty_percentages = [50, 30, 20]  # 50% at TP1, 30% at TP2, 20% at TP3
        
        for i, rr_ratio in enumerate(risk_reward_ratios[:3]):
            reward = risk * rr_ratio
            
            if side == PositionSide.LONG:
                tp_price = entry_price + reward
            else:
                tp_price = entry_price - reward
            
            targets.append({
                "price": tp_price,
                "qty_pct": qty_percentages[i] if i < len(qty_percentages) else 100,
                "risk_reward_ratio": rr_ratio
            })
        
        return targets
    
    def check_margin_requirements(
        self,
        positions: List[Position],
        available_capital: float
    ) -> Dict[str, any]:
        """Check margin requirements and usage"""
        total_notional = sum(pos.notional_value for pos in positions)
        total_margin_used = sum(pos.notional_value / pos.leverage for pos in positions)
        
        margin_usage_pct = (total_margin_used / available_capital) * 100 if available_capital > 0 else 0
        
        return {
            "total_margin_used": total_margin_used,
            "available_margin": available_capital,
            "margin_usage_pct": margin_usage_pct,
            "is_warning": margin_usage_pct > 80,  # Warning at 80%
            "is_critical": margin_usage_pct > 90  # Critical at 90%
        }

