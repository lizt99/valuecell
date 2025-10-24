"""Position management for tracking and managing all holdings"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import (
    ClosedPosition,
    InvalidationCondition,
    Position,
    PositionSide,
    TradingSessionConfig,
)
from .position_database import PositionDatabase

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Position manager - tracks and manages all holdings
    
    Responsibilities:
    - Open, add to, reduce, close positions
    - Update position status
    - Check stop loss and take profit
    - Check invalidation conditions
    - Maintain position history
    """
    
    def __init__(self, session_config: TradingSessionConfig):
        self.config = session_config
        self.positions: Dict[str, Position] = {}  # {symbol: Position}
        self.closed_positions: List[ClosedPosition] = []
        self.trade_history: List[Dict] = []
        
        # Database
        self.db = PositionDatabase()
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.positions.values())
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for specific symbol"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if has position"""
        return symbol in self.positions
    
    async def open_position(
        self,
        symbol: str,
        side: PositionSide,
        quantity: float,
        entry_price: float,
        profit_target: float,
        stop_loss: float,
        invalidation_condition: InvalidationCondition,
        leverage: int,
        confidence: float,
        risk_usd: float,
        signal_id: Optional[str] = None,
        reasoning: Optional[str] = None
    ) -> Position:
        """Open new position"""
        position_id = str(uuid.uuid4())
        
        notional_value = quantity * entry_price
        risk_amount = quantity * abs(entry_price - stop_loss)
        reward_potential = quantity * abs(profit_target - entry_price)
        risk_reward_ratio = reward_potential / risk_amount if risk_amount > 0 else 0
        
        position = Position(
            position_id=position_id,
            session_id=self.config.session_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            notional_value=notional_value,
            leverage=leverage,
            entry_price=entry_price,
            current_price=entry_price,
            profit_target=profit_target,
            stop_loss_price=stop_loss,
            take_profit_targets=[],
            invalidation_condition=invalidation_condition,
            risk_usd=risk_usd,
            risk_amount=risk_amount,
            reward_potential=reward_potential,
            risk_reward_ratio=risk_reward_ratio,
            confidence=confidence,
            opened_at=datetime.now(timezone.utc),
            entry_signal_id=signal_id,
            entry_reasoning=reasoning
        )
        
        self.positions[symbol] = position
        
        # Update available capital (considering leverage)
        margin_required = notional_value / leverage
        self.config.current_capital -= margin_required
        
        # Record trade
        await self._record_trade("OPEN", position)
        
        # Save to database
        await self.db.save_position(position)
        
        logger.info(
            f"Opened {side.value} position: {symbol} @ ${entry_price:.2f}, "
            f"qty: {quantity:.4f}, leverage: {leverage}x, risk: ${risk_usd:.2f}"
        )
        
        return position
    
    async def close_position(
        self,
        symbol: str,
        exit_price: float,
        exit_reason: str = "signal",
        signal_id: Optional[str] = None
    ) -> Optional[ClosedPosition]:
        """Close position"""
        if symbol not in self.positions:
            logger.warning(f"No position found for {symbol}")
            return None
        
        position = self.positions[symbol]
        
        # Calculate realized P&L
        if position.side == PositionSide.LONG:
            realized_pnl = (exit_price - position.entry_price) * position.quantity
        else:
            realized_pnl = (position.entry_price - exit_price) * position.quantity
        
        realized_pnl_pct = (realized_pnl / position.notional_value) * 100 if position.notional_value > 0 else 0
        
        # Create closed position record
        closed_at = datetime.now(timezone.utc)
        holding_duration = (closed_at - position.opened_at).total_seconds() / 3600
        
        closed_position = ClosedPosition(
            position_id=position.position_id,
            session_id=position.session_id,
            symbol=symbol,
            side=position.side,
            quantity=position.quantity,
            entry_price=position.entry_price,
            exit_price=exit_price,
            realized_pnl=realized_pnl,
            realized_pnl_pct=realized_pnl_pct,
            opened_at=position.opened_at,
            closed_at=closed_at,
            holding_duration=holding_duration,
            exit_reason=exit_reason,
            exit_signal_id=signal_id
        )
        
        # Update available capital
        exit_value = position.quantity * exit_price
        margin_returned = position.notional_value / position.leverage
        self.config.current_capital += margin_returned + realized_pnl
        
        # Remove from open positions
        del self.positions[symbol]
        self.closed_positions.append(closed_position)
        
        # Record trade
        await self._record_trade("CLOSE", position, exit_price, realized_pnl)
        
        # Save to database
        await self.db.save_closed_position(closed_position)
        
        logger.info(
            f"Closed {position.side.value} position: {symbol} @ ${exit_price:.2f}, "
            f"P&L: ${realized_pnl:.2f} ({realized_pnl_pct:.2f}%), reason: {exit_reason}"
        )
        
        return closed_position
    
    async def add_to_position(
        self,
        symbol: str,
        additional_quantity: float,
        entry_price: float,
        signal_id: Optional[str] = None
    ) -> Position:
        """Add to existing position (if pyramiding allowed)"""
        if not self.config.allow_pyramiding:
            raise ValueError(
                "Pyramiding not allowed. Size correctly on entry as position scaling is disabled."
            )
        
        if symbol not in self.positions:
            raise ValueError(f"No position found for {symbol}")
        
        position = self.positions[symbol]
        
        # Calculate new average entry price
        total_cost = (position.quantity * position.entry_price) + (additional_quantity * entry_price)
        new_quantity = position.quantity + additional_quantity
        new_avg_price = total_cost / new_quantity
        
        # Update position
        old_notional = position.notional_value
        position.quantity = new_quantity
        position.entry_price = new_avg_price
        position.notional_value = new_quantity * new_avg_price
        position.last_updated = datetime.now(timezone.utc)
        
        # Update available capital
        additional_margin = (additional_quantity * entry_price) / position.leverage
        self.config.current_capital -= additional_margin
        
        # Record trade
        await self._record_trade("ADD", position, entry_price, additional_quantity)
        
        # Update database
        await self.db.update_position(position)
        
        logger.info(
            f"Added to position: {symbol}, new qty: {new_quantity:.4f}, "
            f"new avg price: ${new_avg_price:.2f}"
        )
        
        return position
    
    async def reduce_position(
        self,
        symbol: str,
        reduce_quantity: float,
        exit_price: float,
        reason: str = "partial_profit"
    ) -> tuple[Optional[Position], float]:
        """Reduce position size"""
        if symbol not in self.positions:
            raise ValueError(f"No position found for {symbol}")
        
        position = self.positions[symbol]
        
        if reduce_quantity >= position.quantity:
            # Close entire position if reduce >= total
            closed = await self.close_position(symbol, exit_price, reason)
            return None, closed.realized_pnl if closed else 0.0
        
        # Calculate partial P&L
        if position.side == PositionSide.LONG:
            partial_pnl = (exit_price - position.entry_price) * reduce_quantity
        else:
            partial_pnl = (position.entry_price - exit_price) * reduce_quantity
        
        # Update position
        position.quantity -= reduce_quantity
        position.notional_value = position.quantity * position.entry_price
        position.last_updated = datetime.now(timezone.utc)
        
        # Update available capital
        margin_returned = (reduce_quantity * position.entry_price) / position.leverage
        self.config.current_capital += margin_returned + partial_pnl
        
        # Record trade
        await self._record_trade("REDUCE", position, exit_price, reduce_quantity, partial_pnl)
        
        # Update database
        await self.db.update_position(position)
        
        logger.info(
            f"Reduced position: {symbol}, remaining qty: {position.quantity:.4f}, "
            f"partial P&L: ${partial_pnl:.2f}"
        )
        
        return position, partial_pnl
    
    async def update_positions(self, current_prices: Dict[str, float]):
        """Update all positions with current prices and check exit conditions"""
        for symbol, position in list(self.positions.items()):
            if symbol in current_prices:
                current_price = current_prices[symbol]
                position.calculate_unrealized_pnl(current_price)
                
                # Check stop loss and take profit
                await self._check_stop_loss_take_profit(position, current_price)
    
    async def check_invalidation_conditions(
        self,
        symbol: str,
        recent_candles: List[Dict[str, float]]
    ) -> bool:
        """Check if invalidation condition is triggered"""
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        
        if position.check_invalidation(recent_candles):
            logger.warning(
                f"Invalidation condition triggered for {symbol}: "
                f"{position.invalidation_condition.description}"
            )
            
            # Close position
            current_price = recent_candles[-1]["close"]
            await self.close_position(
                symbol=symbol,
                exit_price=current_price,
                exit_reason="invalidation_triggered"
            )
            return True
        
        return False
    
    async def _check_stop_loss_take_profit(self, position: Position, current_price: float):
        """Check if stop loss or take profit is hit"""
        # Check stop loss
        if position.side == PositionSide.LONG:
            if current_price <= position.stop_loss_price:
                logger.warning(f"Stop loss hit for {position.symbol} @ ${current_price:.2f}")
                await self.close_position(position.symbol, current_price, "stop_loss")
                return
        else:  # SHORT
            if current_price >= position.stop_loss_price:
                logger.warning(f"Stop loss hit for {position.symbol} @ ${current_price:.2f}")
                await self.close_position(position.symbol, current_price, "stop_loss")
                return
        
        # Check take profit target
        if position.side == PositionSide.LONG and current_price >= position.profit_target:
            logger.info(f"Take profit hit for {position.symbol} @ ${current_price:.2f}")
            await self.close_position(position.symbol, current_price, "take_profit")
        elif position.side == PositionSide.SHORT and current_price <= position.profit_target:
            logger.info(f"Take profit hit for {position.symbol} @ ${current_price:.2f}")
            await self.close_position(position.symbol, current_price, "take_profit")
    
    def get_total_realized_pnl(self) -> float:
        """Get total realized P&L from closed positions"""
        return sum(cp.realized_pnl for cp in self.closed_positions)
    
    def get_trade_history(self) -> List[Dict]:
        """Get trade history"""
        return self.trade_history
    
    async def _record_trade(
        self,
        action: str,
        position: Position,
        price: float = None,
        extra_data: any = None,
        pnl: float = None
    ):
        """Record trade in history"""
        trade_record = {
            "position_id": position.position_id,
            "timestamp": datetime.now(timezone.utc),
            "action": action,
            "symbol": position.symbol,
            "side": position.side.value,
            "quantity": position.quantity,
            "price": price or position.entry_price,
            "extra": extra_data,
            "pnl": pnl
        }
        
        self.trade_history.append(trade_record)
        await self.db.save_trade_record(self.config.session_id, trade_record)

