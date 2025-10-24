"""Database upgrade and initialization script"""

import logging
import sqlite3
from pathlib import Path
from datetime import datetime

from .constants import DEFAULT_DB_PATH, INDICATOR_DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseUpgrade:
    """Database schema upgrade manager"""
    
    def __init__(self):
        self.position_db_path = DEFAULT_DB_PATH
        self.indicator_db_path = INDICATOR_DB_PATH
    
    def upgrade_all(self):
        """Upgrade all databases"""
        logger.info("Starting database upgrade...")
        
        # Upgrade position database
        self.upgrade_position_db()
        
        # Upgrade indicator database
        self.upgrade_indicator_db()
        
        logger.info("✅ Database upgrade completed successfully!")
    
    def upgrade_position_db(self):
        """Upgrade position and portfolio database"""
        logger.info(f"Upgrading position database: {self.position_db_path}")
        
        conn = sqlite3.connect(self.position_db_path)
        cursor = conn.cursor()
        
        try:
            # Get current schema version
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            current_version = result[0] if result[0] else 0
            
            logger.info(f"Current schema version: {current_version}")
            
            # Apply migrations
            if current_version < 1:
                self._apply_migration_v1(cursor)
                cursor.execute("""
                    INSERT INTO schema_version (version, description)
                    VALUES (1, 'Initial schema')
                """)
                logger.info("✓ Applied migration v1: Initial schema")
            
            # Future migrations can be added here
            # if current_version < 2:
            #     self._apply_migration_v2(cursor)
            
            conn.commit()
            logger.info(f"✅ Position database upgraded successfully")
            
        except Exception as e:
            logger.error(f"Error upgrading position database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _apply_migration_v1(self, cursor):
        """Initial schema creation"""
        
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
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_trade_records_session 
            ON trade_records(session_id, timestamp DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recommendations_session 
            ON recommendations(session_id, timestamp DESC)
        """)
    
    def upgrade_indicator_db(self):
        """Upgrade indicator database"""
        logger.info(f"Upgrading indicator database: {self.indicator_db_path}")
        
        conn = sqlite3.connect(self.indicator_db_path)
        cursor = conn.cursor()
        
        try:
            # Create indicator_data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS indicator_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timestamp DATETIME NOT NULL,
                    timeframe TEXT NOT NULL,
                    ohlcv TEXT NOT NULL,
                    indicators TEXT NOT NULL,
                    raw_payload TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(symbol, timestamp, timeframe)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_timestamp 
                ON indicator_data(symbol, timestamp DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_symbol_timeframe 
                ON indicator_data(symbol, timeframe, timestamp DESC)
            """)
            
            # Create schema version tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """)
            
            cursor.execute("SELECT MAX(version) FROM schema_version")
            result = cursor.fetchone()
            current_version = result[0] if result[0] else 0
            
            if current_version < 1:
                cursor.execute("""
                    INSERT INTO schema_version (version, description)
                    VALUES (1, 'Initial indicator schema')
                """)
                logger.info("✓ Applied migration v1: Initial indicator schema")
            
            conn.commit()
            logger.info(f"✅ Indicator database upgraded successfully")
            
        except Exception as e:
            logger.error(f"Error upgrading indicator database: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def verify_databases(self):
        """Verify database integrity"""
        logger.info("Verifying databases...")
        
        # Verify position database
        conn = sqlite3.connect(self.position_db_path)
        cursor = conn.cursor()
        
        tables = [
            'schema_version',
            'trading_sessions',
            'positions',
            'closed_positions',
            'portfolio_snapshots',
            'trade_records',
            'recommendations'
        ]
        
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?", (table,))
            if cursor.fetchone()[0] == 0:
                logger.error(f"❌ Table {table} not found in position database")
                return False
            else:
                logger.info(f"✓ Table {table} exists")
        
        conn.close()
        
        # Verify indicator database
        conn = sqlite3.connect(self.indicator_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='indicator_data'")
        if cursor.fetchone()[0] == 0:
            logger.error("❌ Table indicator_data not found in indicator database")
            return False
        else:
            logger.info("✓ Table indicator_data exists")
        
        conn.close()
        
        logger.info("✅ All databases verified successfully!")
        return True
    
    def get_database_stats(self):
        """Get database statistics"""
        logger.info("\n" + "="*60)
        logger.info("Database Statistics")
        logger.info("="*60)
        
        # Position database stats
        conn = sqlite3.connect(self.position_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM trading_sessions")
        sessions_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM positions WHERE status='open'")
        open_positions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM closed_positions")
        closed_positions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM portfolio_snapshots")
        snapshots = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM trade_records")
        trades = cursor.fetchone()[0]
        
        logger.info(f"\n📊 Position Database ({self.position_db_path}):")
        logger.info(f"  - Trading Sessions: {sessions_count}")
        logger.info(f"  - Open Positions: {open_positions}")
        logger.info(f"  - Closed Positions: {closed_positions}")
        logger.info(f"  - Portfolio Snapshots: {snapshots}")
        logger.info(f"  - Trade Records: {trades}")
        
        conn.close()
        
        # Indicator database stats
        conn = sqlite3.connect(self.indicator_db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM indicator_data")
        indicators = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM indicator_data")
        symbols = cursor.fetchone()[0]
        
        logger.info(f"\n📈 Indicator Database ({self.indicator_db_path}):")
        logger.info(f"  - Total Indicators: {indicators}")
        logger.info(f"  - Unique Symbols: {symbols}")
        
        if indicators > 0:
            cursor.execute("""
                SELECT symbol, COUNT(*) as cnt 
                FROM indicator_data 
                GROUP BY symbol 
                ORDER BY cnt DESC 
                LIMIT 5
            """)
            logger.info("  - Top 5 symbols:")
            for row in cursor.fetchall():
                logger.info(f"    • {row[0]}: {row[1]} records")
        
        conn.close()
        
        logger.info("="*60 + "\n")


def main():
    """Main upgrade function"""
    print("\n" + "="*60)
    print("TradingView Signal Agent - Database Upgrade")
    print("="*60 + "\n")
    
    upgrader = DatabaseUpgrade()
    
    # Perform upgrade
    upgrader.upgrade_all()
    
    # Verify
    if upgrader.verify_databases():
        print("\n✅ All databases are ready!")
    else:
        print("\n❌ Database verification failed!")
        return 1
    
    # Show stats
    upgrader.get_database_stats()
    
    print("\n🎉 Database upgrade completed successfully!\n")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

