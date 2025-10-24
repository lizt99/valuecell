"""Portfolio manager coordinating position, risk, and performance management"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from .models import (
    OperationType,
    PortfolioSnapshot,
    Position,
    PositionSide,
    TradingSessionConfig,
)
from .performance_analytics import PerformanceAnalytics
from .position_database import PositionDatabase
from .position_manager import PositionManager
from .risk_manager import RiskManager

logger = logging.getLogger(__name__)


class PortfolioManager:
    """
    Portfolio manager - coordinates all portfolio-level operations
    
    Responsibilities:
    - Manage session configuration
    - Coordinate position manager and risk manager
    - Generate portfolio-level analysis and reports
    - Check trading constraints
    """
    
    def __init__(self, session_config: TradingSessionConfig):
        self.config = session_config
        self.position_manager = PositionManager(session_config)
        self.risk_manager = RiskManager(session_config)
        self.performance_analytics = PerformanceAnalytics(session_config)
        self.db = PositionDatabase()
    
    async def get_portfolio_summary(self) -> PortfolioSnapshot:
        """Get comprehensive portfolio summary"""
        positions = self.position_manager.get_open_positions()
        
        # Calculate capital
        total_position_value = sum(
            pos.notional_value for pos in positions
        )
        available_capital = self.config.current_capital
        total_capital = available_capital + total_position_value
        
        # Calculate P&L
        unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
        realized_pnl = self.position_manager.get_total_realized_pnl()
        total_pnl = unrealized_pnl + realized_pnl
        
        # Calculate risk indicators
        portfolio_heat = self.risk_manager.calculate_portfolio_heat(positions)
        exposure_pct = (total_position_value / total_capital * 100) if total_capital > 0 else 0
        
        # Get performance statistics
        stats = self.performance_analytics.calculate_statistics()
        
        snapshot = PortfolioSnapshot(
            session_id=self.config.session_id,
            timestamp=datetime.now(timezone.utc),
            total_capital=total_capital,
            available_capital=available_capital,
            used_capital=total_position_value,
            open_positions_count=len(positions),
            total_position_value=total_position_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            total_pnl=total_pnl,
            total_return_pct=(total_pnl / self.config.initial_capital * 100) if self.config.initial_capital > 0 else 0,
            portfolio_heat=portfolio_heat,
            exposure_pct=exposure_pct,
            total_trades=stats.get("total_trades", 0),
            winning_trades=stats.get("winning_trades", 0),
            losing_trades=stats.get("losing_trades", 0),
            win_rate=stats.get("win_rate", 0),
            avg_win=stats.get("avg_win", 0),
            avg_loss=stats.get("avg_loss", 0),
            profit_factor=stats.get("profit_factor", 0)
        )
        
        return snapshot
    
    async def can_open_new_position(
        self,
        symbol: str,
        position_size_usd: float
    ) -> Tuple[bool, str]:
        """Check if can open new position"""
        # 1. Check max positions limit
        current_positions = len(self.position_manager.get_open_positions())
        if current_positions >= self.config.max_concurrent_positions:
            return False, f"Max positions reached ({self.config.max_concurrent_positions})"
        
        # 2. Check single position size limit
        max_position_size = self.config.current_capital * self.config.max_position_size_pct
        if position_size_usd > max_position_size:
            return False, f"Position size exceeds limit (max: ${max_position_size:.2f})"
        
        # 3. Check available capital
        if position_size_usd > self.config.current_capital:
            return False, "Insufficient capital"
        
        # 4. Check total exposure
        positions = self.position_manager.get_open_positions()
        total_exposure = self.risk_manager.get_total_exposure(positions)
        new_exposure_pct = (total_exposure + position_size_usd) / (
            self.config.current_capital + total_exposure
        )
        if new_exposure_pct > self.config.max_total_exposure_pct:
            return False, f"Total exposure exceeds limit ({self.config.max_total_exposure_pct*100}%)"
        
        # 5. Check if already have position in this symbol
        if self.position_manager.has_position(symbol):
            if not self.config.allow_pyramiding:
                return False, f"Already have position in {symbol} and pyramiding is disabled"
        
        return True, "OK"
    
    async def save_snapshot(self, snapshot: Optional[PortfolioSnapshot] = None):
        """Save portfolio snapshot"""
        if snapshot is None:
            snapshot = await self.get_portfolio_summary()
        
        await self.db.save_snapshot(snapshot)
    
    async def get_portfolio_history(self, limit: int = 100) -> List[PortfolioSnapshot]:
        """Get portfolio snapshot history"""
        return await self.db.get_snapshots(self.config.session_id, limit)
    
    def get_margin_status(self) -> Dict:
        """Get margin usage status"""
        positions = self.position_manager.get_open_positions()
        return self.risk_manager.check_margin_requirements(
            positions,
            self.config.current_capital
        )
    
    async def update_all_positions(self, current_prices: Dict[str, float]):
        """Update all positions with current prices"""
        await self.position_manager.update_positions(current_prices)
    
    async def check_all_invalidations(self, market_data: Dict[str, List[Dict]]):
        """Check invalidation conditions for all positions"""
        for symbol in list(self.position_manager.positions.keys()):
            if symbol in market_data:
                candles = market_data[symbol]
                await self.position_manager.check_invalidation_conditions(
                    symbol,
                    candles
                )

