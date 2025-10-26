"""Indicator data storage using SQLite"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .constants import INDICATOR_DB_PATH
from .models import TimeSeriesIndicatorData, SvixIndicatorData

logger = logging.getLogger(__name__)


class IndicatorDataStore:
    """Store and retrieve indicator data"""
    
    def __init__(self, db_path: str = INDICATOR_DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables - only fields from API"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Polling state table for iterator management
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS polling_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                consumer_id TEXT UNIQUE NOT NULL,
                last_iterator TEXT,
                last_poll_time DATETIME,
                total_messages_fetched INTEGER DEFAULT 0,
                last_message_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS indicator_data (
                -- Primary Key
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Identification (3 fields)
                symbol TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                timeframe TEXT NOT NULL DEFAULT '1m',
                
                -- Price Data (4 fields from API)
                price REAL NOT NULL,
                volume REAL NOT NULL,
                mid_price REAL,
                avg_volume REAL,
                
                -- MACD (3 fields from API: macd, macd_signal, macd_hist)
                macd_line REAL,
                macd_signal REAL,
                macd_histogram REAL,
                
                -- RSI (2 fields from API: rsi7, rsi14)
                rsi7 REAL,
                rsi14 REAL,
                
                -- EMAs (2 fields from API: ema20, ema50)
                ema_20 REAL,
                ema_50 REAL,
                
                -- ATR (2 fields from API: atr3, atr14)
                atr3 REAL,
                atr14 REAL,
                
                -- Metadata (4 fields)
                source TEXT DEFAULT 'svix',
                layout_name TEXT,
                timeframe_base TEXT,
                raw_payload TEXT,
                
                -- System Fields (2 fields)
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraint
                UNIQUE(symbol, timestamp, timeframe)
            )
        """)
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_symbol_timestamp ON indicator_data(symbol, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_symbol_timeframe ON indicator_data(symbol, timeframe, timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_layout ON indicator_data(layout_name)",
        ]
        
        for idx_sql in indexes:
            cursor.execute(idx_sql)
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized indicator database at {self.db_path}")
    
    async def save_svix_indicator_data(
        self,
        data: SvixIndicatorData
    ) -> int:
        """
        Save indicator data from Svix API
        
        Only saves fields that API actually provides.
        
        Args:
            data: SvixIndicatorData object
            
        Returns:
            Row ID of saved data
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO indicator_data (
                    symbol, timestamp, timeframe,
                    price, volume, mid_price, avg_volume,
                    macd_line, macd_signal, macd_histogram,
                    rsi7, rsi14,
                    ema_20, ema_50,
                    atr3, atr14,
                    source, layout_name, timeframe_base, raw_payload,
                    updated_at
                ) VALUES (
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    CURRENT_TIMESTAMP
                )
            """, (
                # Identification
                data.symbol,
                data.timestamp.isoformat(),
                data.timeframe,
                # Price data
                data.price,
                data.volume,
                data.mid_price,
                data.avg_volume,
                # MACD
                data.macd_line,
                data.macd_signal,
                data.macd_histogram,
                # RSI
                data.rsi7,
                data.rsi14,
                # EMAs
                data.ema_20,
                data.ema_50,
                # ATR
                data.atr3,
                data.atr14,
                # Metadata
                data.source,
                data.layout_name,
                data.timeframe_base,
                json.dumps(data.raw_data) if data.raw_data else None,
            ))
            
            row_id = cursor.lastrowid
            conn.commit()
            
            logger.debug(
                f"Saved: {data.symbol} @ {data.timestamp}, "
                f"price=${data.price:.2f}, rsi14={data.rsi14 or 0:.2f}"
            )
            return row_id
            
        except Exception as e:
            logger.error(f"Failed to save indicator data: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    async def get_recent_data(
        self, 
        symbol: str, 
        limit: int = 100,
        timeframe: str = "1m"
    ) -> List[TimeSeriesIndicatorData]:
        """Get recent indicator data - only fields from API"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    id, symbol, timestamp, timeframe,
                    price, volume, mid_price, avg_volume,
                    macd_line, macd_signal, macd_histogram,
                    rsi7, rsi14,
                    ema_20, ema_50,
                    atr3, atr14,
                    source, layout_name, timeframe_base,
                    raw_payload, created_at
                FROM indicator_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, timeframe, limit))
            
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                # Reconstruct OHLCV dict (for backward compatibility)
                ohlcv = {
                    "price": row[4],
                    "volume": row[5],
                    "mid_price": row[6],
                    "avg_volume": row[7],
                    # Use price for OHLC (not provided by API)
                    "open": row[4],
                    "high": row[4],
                    "low": row[4],
                    "close": row[4],
                }
                
                # Reconstruct indicators dict (for backward compatibility)
                indicators = {
                    "macd": {
                        "macd_line": row[8],
                        "signal_line": row[9],
                        "histogram": row[10]
                    },
                    "rsi": {
                        "value": row[12] if row[12] is not None else 50.0  # Use rsi14
                    },
                    "rsi7": row[11],
                    "rsi14": row[12],
                    "ema_20": row[13],
                    "ema_50": row[14],
                    "atr3": row[15],
                    "atr14": row[16],
                    "source": row[17],
                    "layout_name": row[18],
                    "timeframe_base": row[19],
                }
                
                data = TimeSeriesIndicatorData(
                    id=row[0],
                    symbol=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    timeframe=row[3],
                    ohlcv=ohlcv,
                    indicators=indicators,
                    raw_payload=row[20],
                    created_at=datetime.fromisoformat(row[21]) if row[21] else datetime.now(timezone.utc)
                )
                result.append(data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get recent data for {symbol}: {e}")
            return []
        finally:
            conn.close()
    
    async def get_latest_data(
        self,
        symbol: str,
        timeframe: str = "1m"
    ) -> Optional[TimeSeriesIndicatorData]:
        """Get latest indicator data for a symbol"""
        data = await self.get_recent_data(symbol, limit=1, timeframe=timeframe)
        return data[0] if data else None
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 50
    ) -> List[dict]:
        """Get recent candles - uses price for OHLC (API doesn't provide OHLC)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT timestamp, price, volume
                FROM indicator_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, timeframe, limit))
            
            rows = cursor.fetchall()
            
            candles = []
            for row in rows:
                # Use price for OHLC (API doesn't provide actual OHLC)
                candle = {
                    "timestamp": datetime.fromisoformat(row[0]),
                    "open": row[1],
                    "high": row[1],
                    "low": row[1],
                    "close": row[1],
                    "volume": row[2]
                }
                candles.append(candle)
            
            # Reverse to get chronological order
            candles.reverse()
            return candles
            
        except Exception as e:
            logger.error(f"Failed to get candles for {symbol}: {e}")
            return []
        finally:
            conn.close()
    
    # ==================== Iterator Management ====================
    
    async def get_last_iterator(self, consumer_id: str) -> Optional[str]:
        """
        Get last saved iterator for resuming polling
        
        Args:
            consumer_id: Svix consumer ID
            
        Returns:
            Last iterator string or None if first poll
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT last_iterator 
                FROM polling_state 
                WHERE consumer_id = ?
            """, (consumer_id,))
            
            row = cursor.fetchone()
            return row[0] if row and row[0] else None
            
        except Exception as e:
            logger.error(f"Failed to get iterator: {e}")
            return None
        finally:
            conn.close()
    
    async def save_iterator(
        self,
        consumer_id: str,
        iterator: str,
        message_count: int = 0
    ):
        """
        Save iterator for next polling cycle
        
        Args:
            consumer_id: Svix consumer ID
            iterator: New iterator from API response
            message_count: Number of messages in this batch
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO polling_state (
                    consumer_id,
                    last_iterator,
                    last_poll_time,
                    last_message_count,
                    total_messages_fetched,
                    updated_at
                ) VALUES (
                    ?, ?, CURRENT_TIMESTAMP, ?,
                    ?, CURRENT_TIMESTAMP
                )
                ON CONFLICT(consumer_id) DO UPDATE SET
                    last_iterator = excluded.last_iterator,
                    last_poll_time = excluded.last_poll_time,
                    last_message_count = excluded.last_message_count,
                    total_messages_fetched = total_messages_fetched + excluded.last_message_count,
                    updated_at = CURRENT_TIMESTAMP
            """, (consumer_id, iterator, message_count, message_count))
            
            conn.commit()
            logger.debug(f"Saved iterator: {iterator[:20]}... ({message_count} messages)")
            
        except Exception as e:
            logger.error(f"Failed to save iterator: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    async def get_polling_stats(self, consumer_id: str) -> Optional[dict]:
        """
        Get polling statistics
        
        Returns:
            Dict with stats or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    last_poll_time,
                    total_messages_fetched,
                    last_message_count,
                    created_at
                FROM polling_state
                WHERE consumer_id = ?
            """, (consumer_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "last_poll_time": row[0],
                    "total_messages_fetched": row[1],
                    "last_message_count": row[2],
                    "first_poll_time": row[3]
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return None
        finally:
            conn.close()
    
    async def clear_iterator(self, consumer_id: str):
        """
        Clear iterator (for reset/troubleshooting)
        
        Args:
            consumer_id: Svix consumer ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM polling_state
                WHERE consumer_id = ?
            """, (consumer_id,))
            
            conn.commit()
            logger.info(f"Cleared iterator for consumer: {consumer_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear iterator: {e}")
            conn.rollback()
        finally:
            conn.close()

