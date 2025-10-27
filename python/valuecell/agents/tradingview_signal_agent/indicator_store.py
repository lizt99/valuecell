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
    
    def _row_to_timeseries_data(self, row: tuple) -> TimeSeriesIndicatorData:
        """
        Convert database row to TimeSeriesIndicatorData
        
        Helper method to avoid code duplication
        """
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
        
        from datetime import timezone
        return TimeSeriesIndicatorData(
            id=row[0],
            symbol=row[1],
            timestamp=datetime.fromisoformat(row[2]),
            timeframe=row[3],
            ohlcv=ohlcv,
            indicators=indicators,
            raw_payload=row[20],
            created_at=datetime.fromisoformat(row[21]) if row[21] else datetime.now(timezone.utc)
        )
    
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
                data = self._row_to_timeseries_data(row)
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
    
    async def get_latest_data_batch(
        self,
        symbols: List[str],
        timeframe: str = "1m"
    ) -> dict[str, Optional[TimeSeriesIndicatorData]]:
        """
        Get latest indicator data for multiple symbols (batch query)
        
        Args:
            symbols: List of symbol names
            timeframe: Timeframe (default: "1m")
            
        Returns:
            Dict mapping symbol to latest data (None if no data)
            
        Performance: Single SQL query with IN clause
        """
        if not symbols:
            return {}
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Use IN clause for batch query with subquery to get latest per symbol
            placeholders = ','.join('?' * len(symbols))
            query = f"""
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
                WHERE symbol IN ({placeholders}) AND timeframe = ?
                    AND timestamp = (
                        SELECT MAX(timestamp) 
                        FROM indicator_data AS sub
                        WHERE sub.symbol = indicator_data.symbol 
                        AND sub.timeframe = ?
                    )
            """
            
            params = list(symbols) + [timeframe, timeframe]
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Build result dict
            result = {symbol: None for symbol in symbols}
            
            for row in rows:
                symbol = row[1]
                data = self._row_to_timeseries_data(row)
                result[symbol] = data
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to batch get latest data: {e}")
            return {symbol: None for symbol in symbols}
        finally:
            conn.close()
    
    async def get_by_layout_name(
        self,
        layout_name: str,
        limit: int = 100,
        timeframe: str = "1m"
    ) -> List[TimeSeriesIndicatorData]:
        """
        Get indicator data by layout/strategy name
        
        Args:
            layout_name: Strategy name (e.g., "rst-BTC-1m-rule")
            limit: Maximum number of records
            timeframe: Timeframe filter
            
        Returns:
            List of indicator data for the strategy
        """
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
                WHERE layout_name = ? AND timeframe = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (layout_name, timeframe, limit))
            
            rows = cursor.fetchall()
            result = []
            for row in rows:
                data = self._row_to_timeseries_data(row)
                result.append(data)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get data by layout {layout_name}: {e}")
            return []
        finally:
            conn.close()
    
    async def get_trend_analysis(
        self,
        symbol: str,
        timeframe: str = "1m"
    ) -> Optional[dict]:
        """
        Get EMA trend analysis for a symbol
        
        Returns:
            Dict with trend analysis:
            - trend_direction: "bullish", "bearish", "neutral"
            - ema_alignment: bool (ema_20 > ema_50)
            - price_vs_ema20: "above" or "below"
            - price_vs_ema50: "above" or "below"
            - trend_strength: float (0-1)
        """
        latest = await self.get_latest_data(symbol, timeframe)
        if not latest:
            return None
        
        price = latest.ohlcv.get("price", 0)
        ema_20 = latest.indicators.get("ema_20")
        ema_50 = latest.indicators.get("ema_50")
        
        if ema_20 is None or ema_50 is None:
            return None
        
        # Determine trend
        ema_aligned = ema_20 > ema_50
        price_above_20 = price > ema_20
        price_above_50 = price > ema_50
        
        # Trend direction
        if ema_aligned and price_above_20 and price_above_50:
            trend_direction = "bullish"
            trend_strength = min(
                (ema_20 - ema_50) / ema_50 * 100,  # EMA spread
                (price - ema_20) / ema_20 * 100     # Price above EMA
            ) / 2
        elif not ema_aligned and not price_above_20 and not price_above_50:
            trend_direction = "bearish"
            trend_strength = min(
                (ema_50 - ema_20) / ema_50 * 100,
                (ema_20 - price) / ema_20 * 100
            ) / 2
        else:
            trend_direction = "neutral"
            trend_strength = 0.0
        
        return {
            "symbol": symbol,
            "timestamp": latest.timestamp,
            "trend_direction": trend_direction,
            "ema_alignment": ema_aligned,
            "price_position": "above_both" if price_above_20 and price_above_50 else (
                "below_both" if not price_above_20 and not price_above_50 else "between"
            ),
            "price_vs_ema20": "above" if price_above_20 else "below",
            "price_vs_ema50": "above" if price_above_50 else "below",
            "trend_strength": abs(trend_strength),
            "ema_20": ema_20,
            "ema_50": ema_50,
            "price": price
        }
    
    async def get_volatility_context(
        self,
        symbol: str,
        timeframe: str = "1m"
    ) -> Optional[dict]:
        """
        Get ATR-based volatility analysis
        
        Returns:
            Dict with volatility context:
            - volatility_state: "expanding", "contracting", "stable"
            - atr3: Short-term ATR
            - atr14: Long-term ATR
            - atr_ratio: atr3 / atr14 (>1 = expanding)
            - volatility_percentile: Relative to recent history
        """
        latest = await self.get_latest_data(symbol, timeframe)
        if not latest:
            return None
        
        atr3 = latest.indicators.get("atr3")
        atr14 = latest.indicators.get("atr14")
        
        if atr3 is None or atr14 is None or atr14 == 0:
            return None
        
        atr_ratio = atr3 / atr14
        
        # Determine volatility state
        if atr_ratio > 1.2:
            volatility_state = "expanding"
        elif atr_ratio < 0.8:
            volatility_state = "contracting"
        else:
            volatility_state = "stable"
        
        # Get recent ATR values for percentile calculation
        recent_data = await self.get_recent_data(symbol, limit=50, timeframe=timeframe)
        if recent_data:
            atr14_values = [
                d.indicators.get("atr14") 
                for d in recent_data 
                if d.indicators.get("atr14") is not None
            ]
            if atr14_values:
                sorted_atrs = sorted(atr14_values)
                percentile = (sorted_atrs.index(atr14) / len(sorted_atrs) * 100 
                             if atr14 in sorted_atrs else 50.0)
            else:
                percentile = 50.0
        else:
            percentile = 50.0
        
        return {
            "symbol": symbol,
            "timestamp": latest.timestamp,
            "volatility_state": volatility_state,
            "atr3": atr3,
            "atr14": atr14,
            "atr_ratio": atr_ratio,
            "volatility_percentile": percentile,
            "price": latest.ohlcv.get("price", 0)
        }
    
    async def get_signal_crossovers(
        self,
        symbol: str,
        lookback_periods: int = 5,
        timeframe: str = "1m"
    ) -> Optional[dict]:
        """
        Detect MACD and RSI crossover signals
        
        Args:
            symbol: Symbol name
            lookback_periods: Number of periods to check for crossovers
            timeframe: Timeframe
            
        Returns:
            Dict with crossover signals:
            - macd_crossover: "bullish", "bearish", or None
            - macd_crossover_bars_ago: int (0 = current bar)
            - rsi_crossover_30: bool (RSI crossed above 30)
            - rsi_crossover_70: bool (RSI crossed below 70)
            - rsi7_vs_rsi14: "bullish_divergence" or "bearish_divergence" or None
        """
        recent_data = await self.get_recent_data(symbol, limit=lookback_periods + 1, timeframe=timeframe)
        
        if len(recent_data) < 2:
            return None
        
        # Recent data is in DESC order, reverse for analysis
        recent_data.reverse()
        
        result = {
            "symbol": symbol,
            "timestamp": recent_data[-1].timestamp,
            "macd_crossover": None,
            "macd_crossover_bars_ago": None,
            "rsi_crossover_30": False,
            "rsi_crossover_70": False,
            "rsi7_vs_rsi14": None
        }
        
        # Check MACD crossovers
        for i in range(1, len(recent_data)):
            prev = recent_data[i - 1]
            curr = recent_data[i]
            
            prev_macd_line = prev.indicators.get("macd", {}).get("macd_line", 0)
            prev_macd_signal = prev.indicators.get("macd", {}).get("signal_line", 0)
            curr_macd_line = curr.indicators.get("macd", {}).get("macd_line", 0)
            curr_macd_signal = curr.indicators.get("macd", {}).get("signal_line", 0)
            
            # Bullish crossover: MACD line crosses above signal
            if prev_macd_line <= prev_macd_signal and curr_macd_line > curr_macd_signal:
                result["macd_crossover"] = "bullish"
                result["macd_crossover_bars_ago"] = len(recent_data) - 1 - i
                break
            
            # Bearish crossover: MACD line crosses below signal
            if prev_macd_line >= prev_macd_signal and curr_macd_line < curr_macd_signal:
                result["macd_crossover"] = "bearish"
                result["macd_crossover_bars_ago"] = len(recent_data) - 1 - i
                break
        
        # Check RSI crossovers (latest bar)
        if len(recent_data) >= 2:
            prev_rsi14 = recent_data[-2].indicators.get("rsi14", 50)
            curr_rsi14 = recent_data[-1].indicators.get("rsi14", 50)
            
            # RSI crosses above 30 (oversold exit)
            if prev_rsi14 <= 30 and curr_rsi14 > 30:
                result["rsi_crossover_30"] = True
            
            # RSI crosses below 70 (overbought exit)
            if prev_rsi14 >= 70 and curr_rsi14 < 70:
                result["rsi_crossover_70"] = True
            
            # RSI7 vs RSI14 divergence
            rsi7 = recent_data[-1].indicators.get("rsi7")
            rsi14 = recent_data[-1].indicators.get("rsi14")
            
            if rsi7 is not None and rsi14 is not None:
                if rsi7 > rsi14 + 5:  # RSI7 significantly above RSI14
                    result["rsi7_vs_rsi14"] = "bullish_divergence"
                elif rsi7 < rsi14 - 5:  # RSI7 significantly below RSI14
                    result["rsi7_vs_rsi14"] = "bearish_divergence"
        
        return result
    
    async def get_candles(
        self,
        symbol: str,
        timeframe: str = "1m",
        limit: int = 50
    ) -> List[dict]:
        """
        Get recent candles - uses price for OHLC (API doesn't provide OHLC)
        
        Returns candles with Unix timestamp (float) for compatibility with MarketContext
        """
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
                # Convert datetime to Unix timestamp (float) for MarketContext compatibility
                dt = datetime.fromisoformat(row[0])
                timestamp_unix = dt.timestamp()
                
                # Use price for OHLC (API doesn't provide actual OHLC)
                candle = {
                    "timestamp": timestamp_unix,  # Unix timestamp (float)
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

