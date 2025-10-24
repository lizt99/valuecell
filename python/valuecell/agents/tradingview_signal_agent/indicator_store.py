"""Indicator data storage using SQLite"""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from .constants import INDICATOR_DB_PATH
from .models import TimeSeriesIndicatorData, TradingViewWebhookPayload

logger = logging.getLogger(__name__)


class IndicatorDataStore:
    """Store and retrieve indicator data"""
    
    def __init__(self, db_path: str = INDICATOR_DB_PATH):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
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
        
        conn.commit()
        conn.close()
        logger.info(f"Initialized indicator database at {self.db_path}")
    
    async def save_indicator_data(
        self, 
        payload: TradingViewWebhookPayload
    ) -> int:
        """Save indicator data from webhook"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            ohlcv = {
                "open": payload.open,
                "high": payload.high,
                "low": payload.low,
                "close": payload.close,
                "volume": payload.volume
            }
            
            indicators = {
                "macd": payload.macd.dict(),
                "rsi": payload.rsi.dict(),
                "chart_prime": payload.chart_prime.dict() if payload.chart_prime else None,
                "ema_9": payload.ema_9,
                "ema_20": payload.ema_20,
                "ema_21": payload.ema_21,
                "ema_50": payload.ema_50,
                "ema_200": payload.ema_200,
                "bollinger_upper": payload.bollinger_upper,
                "bollinger_middle": payload.bollinger_middle,
                "bollinger_lower": payload.bollinger_lower,
            }
            
            cursor.execute("""
                INSERT OR REPLACE INTO indicator_data 
                (symbol, timestamp, timeframe, ohlcv, indicators, raw_payload)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                payload.symbol,
                payload.timestamp.isoformat(),
                payload.timeframe,
                json.dumps(ohlcv),
                json.dumps(indicators, default=str),
                payload.json()
            ))
            
            row_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"Saved indicator data for {payload.symbol} at {payload.timestamp}")
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
        timeframe: str = "15m"
    ) -> List[TimeSeriesIndicatorData]:
        """Get recent indicator data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM indicator_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, timeframe, limit))
            
            rows = cursor.fetchall()
            
            result = []
            for row in rows:
                data = TimeSeriesIndicatorData(
                    id=row[0],
                    symbol=row[1],
                    timestamp=datetime.fromisoformat(row[2]),
                    timeframe=row[3],
                    ohlcv=json.loads(row[4]),
                    indicators=json.loads(row[5]),
                    raw_payload=row[6],
                    created_at=datetime.fromisoformat(row[7])
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
        timeframe: str = "15m"
    ) -> Optional[TimeSeriesIndicatorData]:
        """Get latest indicator data for a symbol"""
        data = await self.get_recent_data(symbol, limit=1, timeframe=timeframe)
        return data[0] if data else None
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 50
    ) -> List[dict]:
        """Get recent candles for invalidation checking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT timestamp, ohlcv FROM indicator_data
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (symbol, timeframe, limit))
            
            rows = cursor.fetchall()
            
            candles = []
            for row in rows:
                timestamp = datetime.fromisoformat(row[0])
                ohlcv = json.loads(row[1])
                candle = {
                    "timestamp": timestamp,
                    "open": ohlcv["open"],
                    "high": ohlcv["high"],
                    "low": ohlcv["low"],
                    "close": ohlcv["close"],
                    "volume": ohlcv["volume"]
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

