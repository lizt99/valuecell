"""Performance analytics and statistics calculation"""

import logging
from datetime import datetime
from typing import Dict, List

from .models import ClosedPosition, TradingSessionConfig, TradingStatistics

logger = logging.getLogger(__name__)


class PerformanceAnalytics:
    """Calculate and track trading performance metrics"""
    
    def __init__(self, config: TradingSessionConfig):
        self.config = config
        self.closed_positions: List[ClosedPosition] = []
    
    def add_closed_position(self, position: ClosedPosition):
        """Add closed position for analysis"""
        self.closed_positions.append(position)
    
    def calculate_statistics(self) -> Dict:
        """Calculate comprehensive trading statistics"""
        if not self.closed_positions:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0
            }
        
        # Basic stats
        total_trades = len(self.closed_positions)
        winning_trades = [p for p in self.closed_positions if p.realized_pnl > 0]
        losing_trades = [p for p in self.closed_positions if p.realized_pnl < 0]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        
        # Win rate
        win_rate = num_wins / total_trades if total_trades > 0 else 0.0
        
        # Average win/loss
        avg_win = sum(p.realized_pnl for p in winning_trades) / num_wins if num_wins > 0 else 0.0
        avg_loss = sum(p.realized_pnl for p in losing_trades) / num_losses if num_losses > 0 else 0.0
        
        # Largest win/loss
        largest_win = max((p.realized_pnl for p in winning_trades), default=0.0)
        largest_loss = min((p.realized_pnl for p in losing_trades), default=0.0)
        
        # Profit factor
        total_wins = sum(p.realized_pnl for p in winning_trades)
        total_losses = abs(sum(p.realized_pnl for p in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        # Average holding time
        avg_holding_time = sum(p.holding_duration for p in self.closed_positions) / total_trades
        
        return {
            "total_trades": total_trades,
            "winning_trades": num_wins,
            "losing_trades": num_losses,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "avg_holding_time": avg_holding_time
        }
    
    def calculate_max_drawdown(self, equity_curve: List[float]) -> tuple[float, float]:
        """Calculate maximum drawdown from equity curve"""
        if not equity_curve:
            return 0.0, 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_pct = 0.0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            
            dd = peak - value
            dd_pct = (dd / peak * 100) if peak > 0 else 0.0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
        
        return max_dd, max_dd_pct
    
    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        risk_free_rate: float = 0.02
    ) -> float:
        """Calculate Sharpe ratio"""
        if not returns or len(returns) < 2:
            return 0.0
        
        import statistics
        
        avg_return = statistics.mean(returns)
        std_return = statistics.stdev(returns)
        
        if std_return == 0:
            return 0.0
        
        sharpe = (avg_return - risk_free_rate) / std_return
        return sharpe
    
    def get_trading_statistics(
        self,
        period_start: datetime,
        period_end: datetime
    ) -> TradingStatistics:
        """Get comprehensive trading statistics for a period"""
        # Filter positions by period
        period_positions = [
            p for p in self.closed_positions
            if period_start <= p.closed_at <= period_end
        ]
        
        if not period_positions:
            return TradingStatistics(
                session_id=self.config.session_id,
                period_start=period_start,
                period_end=period_end
            )
        
        # Calculate stats
        stats = self.calculate_statistics()
        
        # Build equity curve
        equity_curve = [self.config.initial_capital]
        current_equity = self.config.initial_capital
        
        for pos in sorted(period_positions, key=lambda x: x.closed_at):
            current_equity += pos.realized_pnl
            equity_curve.append(current_equity)
        
        # Calculate drawdown
        max_dd, max_dd_pct = self.calculate_max_drawdown(equity_curve)
        
        # Calculate returns for Sharpe
        returns = []
        for i in range(1, len(equity_curve)):
            ret = (equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]
            returns.append(ret)
        
        sharpe = self.calculate_sharpe_ratio(returns)
        
        return TradingStatistics(
            session_id=self.config.session_id,
            period_start=period_start,
            period_end=period_end,
            total_trades=stats["total_trades"],
            winning_trades=stats["winning_trades"],
            losing_trades=stats["losing_trades"],
            win_rate=stats["win_rate"],
            total_pnl=sum(p.realized_pnl for p in period_positions),
            avg_win=stats["avg_win"],
            avg_loss=stats["avg_loss"],
            largest_win=stats["largest_win"],
            largest_loss=stats["largest_loss"],
            profit_factor=stats["profit_factor"],
            max_drawdown=max_dd,
            max_drawdown_pct=max_dd_pct,
            sharpe_ratio=sharpe,
            avg_holding_time=stats["avg_holding_time"]
        )

