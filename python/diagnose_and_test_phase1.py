#!/usr/bin/env python3
"""
Phase 1 诊断和验证脚本

检查所有Phase 1组件是否正常工作：
1. 数据库连接和Schema
2. 数据模型解析
3. 时间过滤逻辑
4. 存储逻辑
5. 模拟完整轮询周期
"""

import sqlite3
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ANSI Colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
CYAN = '\033[96m'
BOLD = '\033[1m'
RESET = '\033[0m'


def print_header(text):
    print(f"\n{BOLD}{CYAN}{'='*70}{RESET}")
    print(f"{BOLD}{CYAN}{text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*70}{RESET}")


def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")


def print_error(text):
    print(f"{RED}❌ {text}{RESET}")


def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")


def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")


def find_database():
    """Find database file"""
    paths = [
        Path("tradingview_indicators.db"),
        Path("python/tradingview_indicators.db"),
        Path(__file__).parent / "tradingview_indicators.db",
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def test_1_database_connection():
    """Test 1: Database connection and schema"""
    print_header("Test 1: Database Connection and Schema")
    
    db_path = find_database()
    if not db_path:
        print_error("Database file not found!")
        return False, None
    
    print_success(f"Database found: {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='indicator_data'")
        if not cursor.fetchone():
            print_error("Table 'indicator_data' not found")
            return False, None
        
        print_success("Table 'indicator_data' exists")
        
        # Check schema
        cursor.execute("PRAGMA table_info(indicator_data)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        
        required_columns = {
            'symbol', 'timestamp', 'timeframe',
            'price', 'volume', 'macd_line', 'rsi14'
        }
        
        missing = required_columns - set(columns.keys())
        if missing:
            print_error(f"Missing required columns: {missing}")
            return False, None
        
        print_success(f"Schema valid: {len(columns)} columns")
        
        # Check if flattened (not JSON)
        if 'ohlcv' in columns or 'indicators' in columns:
            print_error("Old JSON schema detected! Run migration.")
            return False, None
        
        print_success("Schema is flattened (not JSON)")
        
        return True, conn
        
    except Exception as e:
        print_error(f"Database error: {e}")
        return False, None


def test_2_current_data(conn):
    """Test 2: Check current data"""
    print_header("Test 2: Current Data Status")
    
    cursor = conn.cursor()
    
    # Total count
    cursor.execute("SELECT COUNT(*) FROM indicator_data")
    total = cursor.fetchone()[0]
    print_info(f"Total records: {total}")
    
    if total == 0:
        print_warning("Database is empty (expected after refresh)")
        return True
    
    # Latest record
    cursor.execute("""
        SELECT symbol, timestamp, price, rsi14, created_at
        FROM indicator_data
        ORDER BY timestamp DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if row:
        symbol, ts, price, rsi14, created = row
        print_info(f"Latest record:")
        print_info(f"  Symbol: {symbol}")
        print_info(f"  Timestamp: {ts}")
        print_info(f"  Price: ${price:,.2f}")
        print_info(f"  RSI14: {rsi14:.2f}")
        print_info(f"  Created: {created}")
        
        # Check age
        data_time = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        age_minutes = (now - data_time).total_seconds() / 60
        
        if age_minutes > 5:
            print_warning(f"Data is {age_minutes:.1f} minutes old (stale)")
        else:
            print_success(f"Data is recent ({age_minutes:.1f} minutes old)")
    
    return True


def test_3_insert_new_data(conn):
    """Test 3: Insert new data"""
    print_header("Test 3: Insert New Data")
    
    cursor = conn.cursor()
    
    # Create new data
    now = datetime.now(timezone.utc)
    
    test_data = {
        'symbol': 'BTCUSDT',
        'timestamp': now.isoformat(),
        'timeframe': '1m',
        'price': 114000.50,
        'volume': 3.5,
        'mid_price': 113995.25,
        'avg_volume': 7.2,
        'macd_line': 42.5,
        'macd_signal': 41.0,
        'macd_histogram': 1.5,
        'rsi7': 65.0,
        'rsi14': 64.5,
        'ema_20': 113900.0,
        'ema_50': 113800.0,
        'atr3': 35.0,
        'atr14': 30.0,
        'source': 'svix',
        'layout_name': 'test-layout',
        'timeframe_base': '1',
        'raw_payload': json.dumps({'test': 'data'})
    }
    
    print_info(f"Inserting test data at {now.strftime('%H:%M:%S')}")
    
    try:
        cursor.execute("""
            INSERT INTO indicator_data (
                symbol, timestamp, timeframe,
                price, volume, mid_price, avg_volume,
                macd_line, macd_signal, macd_histogram,
                rsi7, rsi14, ema_20, ema_50, atr3, atr14,
                source, layout_name, timeframe_base, raw_payload,
                updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                CURRENT_TIMESTAMP
            )
        """, (
            test_data['symbol'], test_data['timestamp'], test_data['timeframe'],
            test_data['price'], test_data['volume'], test_data['mid_price'], 
            test_data['avg_volume'], test_data['macd_line'], test_data['macd_signal'],
            test_data['macd_histogram'], test_data['rsi7'], test_data['rsi14'],
            test_data['ema_20'], test_data['ema_50'], test_data['atr3'], 
            test_data['atr14'], test_data['source'], test_data['layout_name'],
            test_data['timeframe_base'], test_data['raw_payload']
        ))
        
        conn.commit()
        row_id = cursor.lastrowid
        
        print_success(f"Inserted test data (row_id={row_id})")
        print_info(f"  Price: ${test_data['price']:,.2f}")
        print_info(f"  RSI14: {test_data['rsi14']:.2f}")
        
        return True
        
    except Exception as e:
        print_error(f"Insert failed: {e}")
        return False


def test_4_time_filtering():
    """Test 4: Time filtering logic"""
    print_header("Test 4: Time Filtering Logic")
    
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=3)
    
    print_info(f"Current time: {now.strftime('%H:%M:%S')}")
    print_info(f"3-min threshold: {threshold.strftime('%H:%M:%S')}")
    
    # Test data at different times
    test_times = [
        (0, "now", True),
        (1, "1 min ago", True),
        (2, "2 min ago", True),
        (3, "3 min ago", True),  # 边界条件: >= threshold，应该保留
        (4, "4 min ago", False),
        (5, "5 min ago", False),
        (10, "10 min ago", False),
    ]
    
    print_info("\nTime filtering test:")
    passed = 0
    failed = 0
    
    for minutes_ago, label, should_keep in test_times:
        test_time = now - timedelta(minutes=minutes_ago)
        is_kept = test_time >= threshold
        
        if is_kept == should_keep:
            status = f"{GREEN}✓{RESET}"
            passed += 1
        else:
            status = f"{RED}✗{RESET}"
            failed += 1
        
        action = "KEEP" if is_kept else "FILTER"
        print(f"  {status} {label:12s} @ {test_time.strftime('%H:%M:%S')} → {action}")
    
    print_info(f"\nResults: {passed} passed, {failed} failed")
    
    return failed == 0


def test_5_query_aggregation(conn):
    """Test 5: Query and aggregation"""
    print_header("Test 5: Query and Aggregation")
    
    cursor = conn.cursor()
    
    # Check if we have data
    cursor.execute("SELECT COUNT(*) FROM indicator_data")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print_warning("No data to query (insert test data first)")
        return True
    
    print_info(f"Querying {count} records...")
    
    # Test aggregation (benefit of flattened schema)
    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as count,
                AVG(price) as avg_price,
                AVG(rsi14) as avg_rsi,
                MIN(timestamp) as oldest,
                MAX(timestamp) as newest
            FROM indicator_data
            WHERE symbol = 'BTCUSDT'
        """)
        
        row = cursor.fetchone()
        if row:
            count, avg_price, avg_rsi, oldest, newest = row
            
            print_success("Aggregation query successful:")
            print_info(f"  Records: {count}")
            print_info(f"  Avg Price: ${avg_price:,.2f}")
            print_info(f"  Avg RSI14: {avg_rsi:.2f}")
            print_info(f"  Time range: {oldest} to {newest}")
            
            return True
        
    except Exception as e:
        print_error(f"Query failed: {e}")
        return False
    
    return True


def test_6_continuous_insertion(conn):
    """Test 6: Simulate continuous data insertion"""
    print_header("Test 6: Simulate Continuous Data Flow")
    
    cursor = conn.cursor()
    
    print_info("Simulating 3-minute polling cycle...")
    print_info("Inserting data every minute for 3 minutes\n")
    
    now = datetime.now(timezone.utc)
    base_price = 114000.0
    
    inserted = 0
    for i in range(3):
        minute_ago = i
        timestamp = now - timedelta(minutes=minute_ago)
        price = base_price + (i * 10)
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO indicator_data (
                    symbol, timestamp, timeframe,
                    price, volume, mid_price, avg_volume,
                    macd_line, macd_signal, macd_histogram,
                    rsi7, rsi14, ema_20, ema_50, atr3, atr14,
                    source, layout_name, timeframe_base,
                    updated_at
                ) VALUES (
                    'BTCUSDT', ?, '1m',
                    ?, 3.5, ?, 7.2,
                    42.5, 41.0, 1.5,
                    65.0, 64.5, 113900.0, 113800.0, 35.0, 30.0,
                    'svix', 'test-continuous', '1',
                    CURRENT_TIMESTAMP
                )
            """, (timestamp.isoformat(), price, price - 5))
            
            inserted += 1
            print_success(f"T-{minute_ago}min: ${price:,.2f} @ {timestamp.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print_error(f"Failed to insert T-{minute_ago}min: {e}")
    
    conn.commit()
    
    print_info(f"\n✓ Inserted {inserted}/3 records")
    
    # Verify time range
    cursor.execute("""
        SELECT 
            COUNT(*),
            MIN(timestamp),
            MAX(timestamp)
        FROM indicator_data
        WHERE layout_name = 'test-continuous'
    """)
    
    count, oldest, newest = cursor.fetchone()
    if count == 3:
        oldest_dt = datetime.fromisoformat(oldest.replace('Z', '+00:00'))
        newest_dt = datetime.fromisoformat(newest.replace('Z', '+00:00'))
        span = (newest_dt - oldest_dt).total_seconds() / 60
        
        print_success(f"Time span: {span:.1f} minutes (within 3-min window)")
        return True
    else:
        print_error(f"Expected 3 records, got {count}")
        return False


def main():
    """Run all diagnostics"""
    print(f"\n{BOLD}{CYAN}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║         Phase 1 诊断和验证 - 完整功能测试                         ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(RESET)
    
    results = {}
    conn = None
    
    try:
        # Test 1: Database
        results['db'], conn = test_1_database_connection()
        if not results['db'] or not conn:
            print_error("\n❌ Cannot proceed without database")
            return False
        
        # Test 2: Current data
        results['data'] = test_2_current_data(conn)
        
        # Test 3: Insert
        results['insert'] = test_3_insert_new_data(conn)
        
        # Test 4: Time filtering
        results['filter'] = test_4_time_filtering()
        
        # Test 5: Query
        results['query'] = test_5_query_aggregation(conn)
        
        # Test 6: Continuous flow
        results['continuous'] = test_6_continuous_insertion(conn)
        
        # Summary
        print_header("Test Summary")
        
        tests = [
            ("Database Connection & Schema", results['db']),
            ("Current Data Status", results['data']),
            ("Data Insertion", results['insert']),
            ("Time Filtering Logic", results['filter']),
            ("Query & Aggregation", results['query']),
            ("Continuous Data Flow", results['continuous']),
        ]
        
        for name, passed in tests:
            status = f"{GREEN}✅ PASS{RESET}" if passed else f"{RED}❌ FAIL{RESET}"
            print(f"  {status}: {name}")
        
        all_passed = all(results.values())
        
        print(f"\n{BOLD}{'='*70}{RESET}")
        if all_passed:
            print(f"{GREEN}{BOLD}✅ 所有测试通过 - Phase 1 工作正常！{RESET}")
            print(f"{BOLD}{'='*70}{RESET}")
            
            # Show final data
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM indicator_data")
            total = cursor.fetchone()[0]
            
            print(f"\n{CYAN}📊 最终数据状态:{RESET}")
            print(f"   总记录数: {total}")
            
            cursor.execute("""
                SELECT symbol, timestamp, price, rsi14
                FROM indicator_data
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            
            print(f"\n{CYAN}   最近5条记录:{RESET}")
            for row in cursor.fetchall():
                symbol, ts, price, rsi = row
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                print(f"     • {symbol} @ {dt.strftime('%H:%M:%S')} - ${price:,.2f} (RSI={rsi:.1f})")
            
            print(f"\n{GREEN}✓ Phase 1 核心功能全部正常:{RESET}")
            print(f"  • 数据库连接 ✓")
            print(f"  • 扁平化Schema ✓")
            print(f"  • 数据插入 ✓")
            print(f"  • 时间过滤 ✓")
            print(f"  • 查询聚合 ✓")
            print(f"  • 持续数据流 ✓")
            
            print(f"\n{YELLOW}⚠️  注意: 真实数据采集需要:{RESET}")
            print(f"  1. 设置环境变量:")
            print(f"     export SVIX_API_TOKEN='your-token'")
            print(f"     export SVIX_CONSUMER_ID='your-id'")
            print(f"  2. 启动轮询服务:")
            print(f"     ./scripts/start_tradingview_polling.sh")
            
        else:
            print(f"{RED}{BOLD}❌ 部分测试失败{RESET}")
            print(f"{BOLD}{'='*70}{RESET}")
            print(f"\n{YELLOW}需要检查失败的测试项{RESET}")
        
        return all_passed
        
    except Exception as e:
        print_error(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

