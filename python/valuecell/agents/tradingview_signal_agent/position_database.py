"""Position and portfolio database storage"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import List, Optional

from .constants import DEFAULT_DB_PATH
from .models import (
    ClosedPosition,
    Position,
    PortfolioSnapshot,
    TradingSessionConfig,
)

logger = logging.getLogger(__name__)


class PositionDatabase:
    """Database for position and portfolio management"""
    
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize all database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Trading sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT,
                initial_capital REAL NOT NULL,
                current_capital REAL NOT NULL,
                config_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS positions (
                position_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                leverage INTEGER NOT NULL,
                profit_target REAL NOT NULL,
                stop_loss_price REAL NOT NULL,
                invalidation_condition TEXT NOT NULL,
                risk_usd REAL NOT NULL,
                confidence REAL NOT NULL,
                take_profit_targets TEXT,
                funding_rate REAL,
                opened_at TIMESTAMP NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'open',
                FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
            )
        """)
        
        # Closed positions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS closed_positions (
                position_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                realized_pnl_pct REAL NOT NULL,
                opened_at TIMESTAMP NOT NULL,
                closed_at TIMESTAMP NOT NULL,
                holding_duration REAL NOT NULL,
                exit_reason TEXT NOT NULL,
                exit_signal_id TEXT,
                FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
            )
        """)
        
        # Portfolio snapshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                total_capital REAL NOT NULL,
                available_capital REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                total_pnl REAL NOT NULL,
                total_return_pct REAL NOT NULL,
                snapshot_json TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id),
                UNIQUE(session_id, timestamp)
            )
        """)
        
        # Trade records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                position_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                action TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                pnl REAL,
                record_json TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
            )
        """)
        
        # Recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations (
                recommendation_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                operation TEXT NOT NULL,
                confidence REAL NOT NULL,
                recommendation_json TEXT NOT NULL,
                executed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
            )
        """)
        
        # Create indexes
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_session_symbol 
            ON positions(session_id, symbol)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_positions_status 
            ON positions(status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_closed_positions_session 
            ON closed_positions(session_id, closed_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_session_time 
            ON portfolio_snapshots(session_id, timestamp DESC)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized position database at {self.db_path}")
    
    # ==================== Session Management ====================
    
    async def save_session(self, config: TradingSessionConfig) -> bool:
        """Save or update trading session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO trading_sessions
                (session_id, user_id, initial_capital, current_capital, config_json, last_updated, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                config.session_id,
                config.user_id,
                config.initial_capital,
                config.current_capital,
                config.json(),
                datetime.utcnow().isoformat(),
                config.is_active
            ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def get_session(self, session_id: str) -> Optional[TradingSessionConfig]:
        """Get trading session configuration"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT config_json FROM trading_sessions
                WHERE session_id = ?
            """, (session_id,))
            
            row = cursor.fetchone()
            if row:
                return TradingSessionConfig.parse_raw(row[0])
            return None
        finally:
            conn.close()
    
    # ==================== Position Management ====================
    
    async def save_position(self, position: Position) -> bool:
        """Save position to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO positions
                (position_id, session_id, symbol, side, quantity, entry_price, leverage,
                 profit_target, stop_loss_price, invalidation_condition, risk_usd, confidence,
                 take_profit_targets, funding_rate, opened_at, last_updated, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.position_id,
                position.session_id,
                position.symbol,
                position.side.value,
                position.quantity,
                position.entry_price,
                position.leverage,
                position.profit_target,
                position.stop_loss_price,
                position.invalidation_condition.json(),
                position.risk_usd,
                position.confidence,
                json.dumps(position.take_profit_targets),
                position.funding_rate,
                position.opened_at.isoformat(),
                position.last_updated.isoformat(),
                'open'
            ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save position: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def update_position(self, position: Position) -> bool:
        """Update existing position"""
        return await self.save_position(position)
    
    async def save_closed_position(self, closed_position: ClosedPosition) -> bool:
        """Save closed position record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert closed position
            cursor.execute("""
                INSERT INTO closed_positions
                (position_id, session_id, symbol, side, quantity, entry_price, exit_price,
                 realized_pnl, realized_pnl_pct, opened_at, closed_at, holding_duration,
                 exit_reason, exit_signal_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                closed_position.position_id,
                closed_position.session_id,
                closed_position.symbol,
                closed_position.side.value,
                closed_position.quantity,
                closed_position.entry_price,
                closed_position.exit_price,
                closed_position.realized_pnl,
                closed_position.realized_pnl_pct,
                closed_position.opened_at.isoformat(),
                closed_position.closed_at.isoformat(),
                closed_position.holding_duration,
                closed_position.exit_reason,
                closed_position.exit_signal_id
            ))
            
            # Update position status
            cursor.execute("""
                UPDATE positions SET status = 'closed'
                WHERE position_id = ?
            """, (closed_position.position_id,))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save closed position: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def get_closed_positions(self, session_id: str) -> List[ClosedPosition]:
        """Get all closed positions for a session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM closed_positions
                WHERE session_id = ?
                ORDER BY closed_at DESC
            """, (session_id,))
            
            rows = cursor.fetchall()
            return [self._row_to_closed_position(row) for row in rows]
        finally:
            conn.close()
    
    # ==================== Portfolio Snapshots ====================
    
    async def save_snapshot(self, snapshot: PortfolioSnapshot) -> bool:
        """Save portfolio snapshot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO portfolio_snapshots
                (session_id, timestamp, total_capital, available_capital, unrealized_pnl,
                 realized_pnl, total_pnl, total_return_pct, snapshot_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.session_id,
                snapshot.timestamp.isoformat(),
                snapshot.total_capital,
                snapshot.available_capital,
                snapshot.unrealized_pnl,
                snapshot.realized_pnl,
                snapshot.total_pnl,
                snapshot.total_return_pct,
                snapshot.json()
            ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def get_snapshots(
        self,
        session_id: str,
        limit: int = 100
    ) -> List[PortfolioSnapshot]:
        """Get recent portfolio snapshots"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT snapshot_json FROM portfolio_snapshots
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            rows = cursor.fetchall()
            return [PortfolioSnapshot.parse_raw(row[0]) for row in rows]
        finally:
            conn.close()
    
    # ==================== Trade Records ====================
    
    async def save_trade_record(self, session_id: str, record: dict) -> bool:
        """Save trade record"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO trade_records
                (session_id, position_id, timestamp, action, symbol, side, quantity, price, pnl, record_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                record.get("position_id", ""),
                record["timestamp"].isoformat(),
                record["action"],
                record["symbol"],
                record["side"],
                record["quantity"],
                record["price"],
                record.get("pnl"),
                json.dumps(record, default=str)
            ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save trade record: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ==================== Recommendations ====================
    
    async def save_recommendation(
        self,
        recommendation_id: str,
        session_id: str,
        symbol: str,
        operation: str,
        confidence: float,
        recommendation_json: str
    ) -> bool:
        """Save recommendation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO recommendations
                (recommendation_id, session_id, symbol, timestamp, operation, confidence, recommendation_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                recommendation_id,
                session_id,
                symbol,
                datetime.utcnow().isoformat(),
                operation,
                confidence,
                recommendation_json
            ))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save recommendation: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ==================== Helper Methods ====================
    
    def _row_to_closed_position(self, row) -> ClosedPosition:
        """Convert database row to ClosedPosition"""
        from .models import PositionSide
        
        return ClosedPosition(
            position_id=row[0],
            session_id=row[1],
            symbol=row[2],
            side=PositionSide(row[3]),
            quantity=row[4],
            entry_price=row[5],
            exit_price=row[6],
            realized_pnl=row[7],
            realized_pnl_pct=row[8],
            opened_at=datetime.fromisoformat(row[9]),
            closed_at=datetime.fromisoformat(row[10]),
            holding_duration=row[11],
            exit_reason=row[12],
            exit_signal_id=row[13]
        )

