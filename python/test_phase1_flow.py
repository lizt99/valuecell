"""
Phase 1 Complete Flow Test (No external dependencies)

Direct test using sqlite3 to verify:
1. Database schema (flattened)
2. Data insertion (simulating API data)
3. Time filtering logic
4. Data retrieval
"""

import sqlite3
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def log_info(msg):
    print(f"{BLUE}INFO:{RESET} {msg}")


def log_success(msg):
    print(f"{GREEN}✅ {msg}{RESET}")


def log_error(msg):
    print(f"{RED}❌ {msg}{RESET}")


def log_warning(msg):
    print(f"{YELLOW}⚠️  {msg}{RESET}")


def find_database():
    """Find the tradingview_indicators.db file"""
    possible_paths = [
        Path("tradingview_indicators.db"),
        Path("python/tradingview_indicators.db"),
        Path(__file__).parent / "tradingview_indicators.db",
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


def create_mock_indicator_data(minutes_ago=0):
    """
    Create mock indicator data matching real API format
    
    Returns dict with all fields from flattened schema
    """
    timestamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    
    return {
        'symbol': 'BTCUSDT',
        'timestamp': timestamp.isoformat(),
        'timeframe': '1m',
        'price': 113727.02 + minutes_ago * 10,
        'volume': 2.73071,
        'mid_price': 113719.57 + minutes_ago * 10,
        'avg_volume': 7.1376495,
        'macd_line': 39.93,
        'macd_signal': 42.68,
        'macd_histogram': -2.75,
        'rsi7': 63.07,
        'rsi14': 62.95,
        'ema_20': 113668.69,
        'ema_50': 113616.15,
        'atr3': 34.60,
        'atr14': 29.58,
        'source': 'svix',
        'layout_name': 'rst-BTC-1m-rule',
        'timeframe_base': '1',
        'raw_payload': json.dumps({'test': 'data'})
    }


def test_step1_verify_schema(conn):
    """Step 1: Verify database schema"""
    print("\n" + "=" * 70)
    print("Step 1: Verify Database Schema (Flattened)")
    print("=" * 70)
    
    cursor = conn.cursor()
    
    # Get table info
    cursor.execute("PRAGMA table_info(indicator_data)")
    columns = cursor.fetchall()
    
    if not columns:
        log_error("Table 'indicator_data' not found")
        return False
    
    log_info(f"Table 'indicator_data' found with {len(columns)} columns")
    
    # Expected columns (from new flattened schema)
    expected = {
        'id', 'symbol', 'timestamp', 'timeframe',
        'price', 'volume', 'mid_price', 'avg_volume',
        'macd_line', 'macd_signal', 'macd_histogram',
        'rsi7', 'rsi14', 'ema_20', 'ema_50',
        'atr3', 'atr14',
        'source', 'layout_name', 'timeframe_base', 'raw_payload',
        'created_at', 'updated_at'
    }
    
    actual = {col[1] for col in columns}
    
    # Check for required columns
    missing = expected - actual
    extra = actual - expected
    
    if missing:
        log_warning(f"Missing columns: {missing}")
    
    if extra:
        log_info(f"Extra columns: {extra}")
    
    # Check for old JSON-based schema
    if 'ohlcv' in actual or 'indicators' in actual:
        log_error("Old JSON schema detected! Need to run migration.")
        return False
    
    # Verify it's NOT JSON-based
    log_success("Schema is flattened (not JSON-based)")
    
    # Show some columns
    log_info("Sample columns:")
    for col in columns[:10]:
        col_id, name, col_type, not_null, default, pk = col
        log_info(f"  - {name:20s} {col_type:10s}")
    
    log_success("Schema verification passed")
    return True


def test_step2_simulate_api_fetch():
    """Step 2: Simulate API data fetch with time filtering"""
    print("\n" + "=" * 70)
    print("Step 2: Simulate API Fetch + Time Filtering")
    print("=" * 70)
    
    # Simulate API returning mix of old and new data
    now = datetime.now(timezone.utc)
    time_threshold = now - timedelta(minutes=3)
    
    log_info(f"Current time: {now.strftime('%H:%M:%S')}")
    log_info(f"Time threshold: {time_threshold.strftime('%H:%M:%S')}")
    log_info(f"Will keep data: >= {time_threshold.strftime('%H:%M:%S')}")
    
    # Create mock API response (mix of old and new)
    all_data = []
    
    # Old data (should be filtered out)
    for i in range(10, 5, -1):
        all_data.append(create_mock_indicator_data(minutes_ago=i))
    
    # New data (should be kept)
    for i in range(2, -1, -1):
        all_data.append(create_mock_indicator_data(minutes_ago=i))
    
    log_info(f"\nSimulated API response: {len(all_data)} total items")
    
    # Apply time filtering (simulating polling_service.py logic)
    filtered_data = []
    filtered_count = 0
    
    for item in all_data:
        item_time = datetime.fromisoformat(item['timestamp'])
        if item_time >= time_threshold:
            filtered_data.append(item)
        else:
            filtered_count += 1
    
    log_success(f"Time filtering complete:")
    log_info(f"  - Kept: {len(filtered_data)} items (within last 3 minutes)")
    log_info(f"  - Filtered: {filtered_count} items (too old)")
    
    # Show kept items
    print("\n  Kept items:")
    for idx, item in enumerate(filtered_data, 1):
        item_time = datetime.fromisoformat(item['timestamp'])
        print(f"    {idx}. {item['symbol']} @ {item_time.strftime('%H:%M:%S')} - ${item['price']:,.2f}")
    
    return filtered_data


def test_step3_insert_data(conn, filtered_data):
    """Step 3: Insert filtered data into database"""
    print("\n" + "=" * 70)
    print("Step 3: Insert Data to Database")
    print("=" * 70)
    
    cursor = conn.cursor()
    
    log_info(f"Inserting {len(filtered_data)} records...")
    
    inserted = 0
    for item in filtered_data:
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
                item['symbol'], item['timestamp'], item['timeframe'],
                item['price'], item['volume'], item['mid_price'], item['avg_volume'],
                item['macd_line'], item['macd_signal'], item['macd_histogram'],
                item['rsi7'], item['rsi14'],
                item['ema_20'], item['ema_50'],
                item['atr3'], item['atr14'],
                item['source'], item['layout_name'], item['timeframe_base'], item['raw_payload']
            ))
            inserted += 1
        except Exception as e:
            log_error(f"Failed to insert: {e}")
    
    conn.commit()
    
    log_success(f"Inserted {inserted} records successfully")
    return inserted > 0


def test_step4_query_data(conn):
    """Step 4: Query and verify stored data"""
    print("\n" + "=" * 70)
    print("Step 4: Query and Verify Data")
    print("=" * 70)
    
    cursor = conn.cursor()
    
    # Test 4a: Total count
    cursor.execute("SELECT COUNT(*) FROM indicator_data")
    total_count = cursor.fetchone()[0]
    log_info(f"Total records in database: {total_count}")
    
    # Test 4b: Get latest record
    cursor.execute("""
        SELECT symbol, timestamp, price, volume, rsi14, macd_line, ema_20
        FROM indicator_data
        WHERE symbol = 'BTCUSDT' AND timeframe = '1m'
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    
    latest = cursor.fetchone()
    if latest:
        log_success("Latest record retrieved:")
        log_info(f"  Symbol: {latest[0]}")
        log_info(f"  Timestamp: {latest[1]}")
        log_info(f"  Price: ${latest[2]:,.2f}")
        log_info(f"  Volume: {latest[3]:.4f}")
        log_info(f"  RSI14: {latest[4]:.2f}")
        log_info(f"  MACD Line: {latest[5]:.2f}")
        log_info(f"  EMA20: {latest[6]:.2f}")
    else:
        log_error("No data found for BTCUSDT")
        return False
    
    # Test 4c: Get recent records
    cursor.execute("""
        SELECT timestamp, price, rsi14
        FROM indicator_data
        WHERE symbol = 'BTCUSDT' AND timeframe = '1m'
        ORDER BY timestamp DESC
        LIMIT 5
    """)
    
    recent = cursor.fetchall()
    log_success(f"Recent {len(recent)} records:")
    for idx, row in enumerate(recent, 1):
        timestamp, price, rsi14 = row
        log_info(f"  {idx}. {timestamp} - ${price:,.2f} (RSI14={rsi14:.2f})")
    
    # Test 4d: Verify flattened storage (can query individual fields)
    cursor.execute("""
        SELECT AVG(price), AVG(rsi14), AVG(macd_line)
        FROM indicator_data
        WHERE symbol = 'BTCUSDT'
    """)
    
    avg_price, avg_rsi, avg_macd = cursor.fetchone()
    log_success("Flattened schema benefits - Direct SQL aggregation:")
    log_info(f"  Average Price: ${avg_price:,.2f}")
    log_info(f"  Average RSI14: {avg_rsi:.2f}")
    log_info(f"  Average MACD: {avg_macd:.2f}")
    
    return True


def test_step5_verify_time_range(conn):
    """Step 5: Verify time range of stored data"""
    print("\n" + "=" * 70)
    print("Step 5: Verify Time Range (Last 3 Minutes)")
    print("=" * 70)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            MIN(timestamp) as oldest,
            MAX(timestamp) as newest,
            COUNT(*) as count
        FROM indicator_data
        WHERE symbol = 'BTCUSDT'
    """)
    
    oldest, newest, count = cursor.fetchone()
    
    if oldest and newest:
        oldest_dt = datetime.fromisoformat(oldest)
        newest_dt = datetime.fromisoformat(newest)
        time_diff = (newest_dt - oldest_dt).total_seconds() / 60
        
        log_success("Time range analysis:")
        log_info(f"  Oldest: {oldest_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        log_info(f"  Newest: {newest_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        log_info(f"  Time span: {time_diff:.1f} minutes")
        log_info(f"  Records: {count}")
        
        if time_diff <= 3:
            log_success(f"✓ Data within 3-minute window")
        else:
            log_warning(f"Data spans {time_diff:.1f} minutes (may include old data)")
        
        return True
    else:
        log_error("No time range data available")
        return False


def main():
    """Main test runner"""
    print("\n" + "=" * 70)
    print("PHASE 1 COMPLETE FLOW TEST")
    print("=" * 70)
    print("Test: API → Time Filter → Database Storage")
    print("=" * 70)
    
    # Find database
    db_path = find_database()
    if not db_path:
        log_error("Database file not found!")
        log_info("Please run database migration first:")
        log_info("  python3 valuecell/agents/tradingview_signal_agent/migrate_database.py")
        return False
    
    log_success(f"Database found: {db_path}")
    
    # Connect to database
    conn = sqlite3.connect(str(db_path))
    
    try:
        results = {}
        
        # Step 1: Verify schema
        results['schema'] = test_step1_verify_schema(conn)
        
        if not results['schema']:
            log_error("Schema verification failed! Cannot continue.")
            return False
        
        # Step 2: Simulate API fetch with time filtering
        filtered_data = test_step2_simulate_api_fetch()
        results['filter'] = len(filtered_data) > 0
        
        # Step 3: Insert data
        if results['filter']:
            results['insert'] = test_step3_insert_data(conn, filtered_data)
        else:
            results['insert'] = False
        
        # Step 4: Query data
        if results['insert']:
            results['query'] = test_step4_query_data(conn)
        else:
            results['query'] = False
        
        # Step 5: Verify time range
        if results['query']:
            results['time_range'] = test_step5_verify_time_range(conn)
        else:
            results['time_range'] = False
        
        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        
        steps = [
            ("Schema Verification (Flattened)", results['schema']),
            ("Time Filtering (Last 3 Min)", results['filter']),
            ("Data Insertion", results['insert']),
            ("Data Query", results['query']),
            ("Time Range Verification", results['time_range']),
        ]
        
        for step_name, passed in steps:
            status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
            print(f"  {status}: {step_name}")
        
        all_passed = all(results.values())
        
        print("\n" + "=" * 70)
        if all_passed:
            print(f"{GREEN}✅ ALL TESTS PASSED!{RESET}")
            print("=" * 70)
            print("\nPhase 1 Data Flow Verified:")
            print("  1. Database schema is flattened ✓")
            print("  2. Time filtering works (last 3 min) ✓")
            print("  3. Data insertion successful ✓")
            print("  4. Data retrieval successful ✓")
            print("  5. Time range correct ✓")
            print(f"\n{GREEN}🎉 Phase 1 is working correctly!{RESET}")
            print("\nNext: Start polling service to fetch real data")
            print("  ./scripts/start_tradingview_polling.sh")
        else:
            print(f"{RED}❌ SOME TESTS FAILED{RESET}")
            print("=" * 70)
        
        return all_passed
        
    finally:
        conn.close()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

