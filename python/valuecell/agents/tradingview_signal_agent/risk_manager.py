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
    
    def calculate_atr_based_stop_loss(
        self,
        entry_price: float,
        atr14: float,
        atr3: float = None,
        side: PositionSide = PositionSide.LONG,
        risk_profile: str = "moderate"
    ) -> Dict[str, float]:
        """
        Calculate dynamic stop loss based on ATR (Phase 2 Enhancement)
        
        Args:
            entry_price: Entry price
            atr14: 14-period ATR (long-term volatility)
            atr3: 3-period ATR (short-term volatility, optional)
            side: Position side (LONG or SHORT)
            risk_profile: "conservative", "moderate", or "aggressive"
            
        Returns:
            Dict with stop loss recommendations:
            - stop_price: Recommended stop loss price
            - stop_distance: Distance from entry
            - atr_multiple: ATR multiple used
            - risk_pct: Risk as % of entry price
        """
        # ATR multiples by risk profile
        atr_multiples = {
            "conservative": 2.5,
            "moderate": 2.0,
            "aggressive": 1.5
        }
        
        atr_multiple = atr_multiples.get(risk_profile, 2.0)
        
        # Use short-term ATR for aggressive, long-term for conservative
        if risk_profile == "aggressive" and atr3:
            atr_value = atr3
        else:
            atr_value = atr14
        
        stop_distance = atr_value * atr_multiple
        
        # Calculate stop price based on side
        if side == PositionSide.LONG:
            stop_price = entry_price - stop_distance
        else:  # SHORT
            stop_price = entry_price + stop_distance
        
        risk_pct = (stop_distance / entry_price) * 100 if entry_price > 0 else 0
        
        return {
            "stop_price": stop_price,
            "stop_distance": stop_distance,
            "atr_multiple": atr_multiple,
            "atr_value": atr_value,
            "risk_pct": risk_pct,
            "risk_profile": risk_profile
        }
    
    def adjust_position_size_for_volatility(
        self,
        base_position_size: float,
        atr3: float,
        atr14: float,
        entry_price: float
    ) -> Dict[str, float]:
        """
        Adjust position size based on current volatility (Phase 2 Enhancement)
        
        High volatility -> Reduce position size
        Low volatility -> Can maintain or increase position size
        
        Args:
            base_position_size: Base position size (quantity)
            atr3: Short-term ATR
            atr14: Long-term ATR
            entry_price: Entry price
            
        Returns:
            Dict with adjusted position size
        """
        if atr14 == 0:
            return {
                "adjusted_quantity": base_position_size,
                "adjustment_factor": 1.0,
                "volatility_state": "unknown"
            }
        
        atr_ratio = atr3 / atr14
        atr_pct = (atr14 / entry_price) * 100 if entry_price > 0 else 0
        
        # Determine adjustment factor
        if atr_ratio > 1.3:
            # Rapidly expanding volatility - reduce size significantly
            adjustment_factor = 0.6
            volatility_state = "rapidly_expanding"
        elif atr_ratio > 1.1:
            # Expanding volatility - reduce size moderately
            adjustment_factor = 0.8
            volatility_state = "expanding"
        elif atr_ratio < 0.7:
            # Contracting volatility - can increase size
            adjustment_factor = 1.2
            volatility_state = "contracting"
        elif atr_ratio < 0.9:
            # Slightly contracting - maintain or slightly increase
            adjustment_factor = 1.1
            volatility_state = "slightly_contracting"
        else:
            # Stable volatility
            adjustment_factor = 1.0
            volatility_state = "stable"
        
        # Additional adjustment for absolute volatility level
        if atr_pct > 3.0:
            # Very high volatility
            adjustment_factor *= 0.8
        elif atr_pct < 1.0:
            # Very low volatility
            adjustment_factor *= 1.1
        
        # Cap adjustment factor
        adjustment_factor = max(0.3, min(1.5, adjustment_factor))
        
        adjusted_quantity = base_position_size * adjustment_factor
        
        return {
            "adjusted_quantity": adjusted_quantity,
            "adjustment_factor": adjustment_factor,
            "volatility_state": volatility_state,
            "atr_ratio": atr_ratio,
            "atr_pct": atr_pct
        }
    
    def get_volatility_adjusted_leverage(
        self,
        base_leverage: int,
        atr3: float,
        atr14: float,
        entry_price: float
    ) -> Dict[str, any]:
        """
        Adjust leverage based on current volatility (Phase 2 Enhancement)
        
        High volatility -> Lower leverage
        Low volatility -> Can use higher leverage
        
        Args:
            base_leverage: Base leverage from confidence level
            atr3: Short-term ATR
            atr14: Long-term ATR
            entry_price: Entry price
            
        Returns:
            Dict with adjusted leverage
        """
        if atr14 == 0:
            return {
                "adjusted_leverage": base_leverage,
                "reason": "No ATR data available"
            }
        
        atr_ratio = atr3 / atr14
        atr_pct = (atr14 / entry_price) * 100 if entry_price > 0 else 0
        
        # Determine leverage adjustment
        if atr_ratio > 1.3 or atr_pct > 3.0:
            # High volatility - reduce leverage significantly
            adjusted_leverage = max(5, int(base_leverage * 0.6))
            reason = "High volatility detected - leverage reduced for safety"
        elif atr_ratio > 1.1 or atr_pct > 2.0:
            # Elevated volatility - reduce leverage moderately
            adjusted_leverage = max(5, int(base_leverage * 0.8))
            reason = "Elevated volatility - leverage reduced moderately"
        elif atr_ratio < 0.7 and atr_pct < 1.5:
            # Low volatility - can maintain or increase leverage
            adjusted_leverage = min(40, int(base_leverage * 1.1))
            reason = "Low volatility - leverage can be maintained or increased"
        else:
            # Normal volatility - maintain base leverage
            adjusted_leverage = base_leverage
            reason = "Normal volatility - base leverage maintained"
        
        return {
            "adjusted_leverage": adjusted_leverage,
            "base_leverage": base_leverage,
            "atr_ratio": atr_ratio,
            "atr_pct": atr_pct,
            "reason": reason
        }
    
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

