"""
Test script for Svix polling service

Tests:
1. Svix API connection
2. Data parsing
3. Database storage
4. Data retrieval
"""

import asyncio
import logging
from datetime import datetime, timezone

from .polling_service import SvixPollingService
from .indicator_store import IndicatorDataStore
from .models import SvixIndicatorData

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_polling_service():
    """Test the polling service"""
    logger.info("=" * 60)
    logger.info("Testing Svix Polling Service")
    logger.info("=" * 60)
    
    # Test 1: Initialize service
    logger.info("\n[Test 1] Initializing polling service...")
    service = SvixPollingService()
    logger.info("✅ Service initialized")
    
    # Test 2: Run polling once
    logger.info("\n[Test 2] Running polling task once...")
    try:
        await service.run_once()
        logger.info("✅ Polling task completed")
    except Exception as e:
        logger.error(f"❌ Polling task failed: {e}")
        return
    
    # Test 3: Check database
    logger.info("\n[Test 3] Checking database for stored data...")
    store = IndicatorDataStore()
    
    # Try to get data for common symbols
    test_symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    
    for symbol in test_symbols:
        data = await store.get_latest_data(symbol, timeframe="1m")
        if data:
            logger.info(f"✅ Found data for {symbol}:")
            logger.info(f"   Timestamp: {data.timestamp}")
            logger.info(f"   Price: ${data.ohlcv.get('price', data.ohlcv.get('close', 0)):,.2f}")
            logger.info(f"   RSI14: {data.indicators.get('rsi14', 'N/A')}")
            logger.info(f"   Volume: {data.ohlcv.get('volume', 0):.4f}")
        else:
            logger.info(f"⚠️  No data found for {symbol}")
    
    logger.info("\n" + "=" * 60)
    logger.info("Test completed")
    logger.info("=" * 60)


async def test_mock_data():
    """Test with mock data matching real API format"""
    logger.info("=" * 60)
    logger.info("Testing with Mock Data (Real API Format)")
    logger.info("=" * 60)
    
    # Create mock indicator data matching ONLY API fields
    mock_data = SvixIndicatorData(
        # Identification
        symbol="BTCUSDT",
        timestamp=datetime.now(timezone.utc),
        timeframe="1m",
        # Price data (from API)
        price=113727.02,
        mid_price=113719.57,
        volume=2.73071,
        avg_volume=7.1376495,
        # MACD (from API: macd, macd_signal, macd_hist)
        macd_line=39.9260687318,
        macd_signal=42.6756581034,
        macd_histogram=-2.7495893716,
        # RSI (from API: rsi7, rsi14)
        rsi7=63.0689404869,
        rsi14=62.9510623295,
        # EMAs (from API: ema20, ema50)
        ema_20=113668.6931425036,
        ema_50=113616.1458435876,
        # ATR (from API: atr3, atr14)
        atr3=34.6048393763,
        atr14=29.5772957569,
        # Metadata
        layout_name="rst-BTC-1m-rule",
        timeframe_base="1"
    )
    
    logger.info(f"Created mock data for {mock_data.symbol}")
    logger.info(f"  Price: ${mock_data.price:,.2f}")
    logger.info(f"  RSI14: {mock_data.rsi14:.2f}")
    logger.info(f"  MACD: {mock_data.macd_line:.2f}")
    
    # Save to database
    store = IndicatorDataStore()
    try:
        row_id = await store.save_svix_indicator_data(mock_data)
        logger.info(f"✅ Saved mock data with row_id={row_id}")
    except Exception as e:
        logger.error(f"❌ Failed to save mock data: {e}")
        logger.exception(e)
        return
    
    # Retrieve data
    retrieved = await store.get_latest_data("BTCUSDT", timeframe="1m")
    if retrieved:
        logger.info(f"✅ Retrieved data:")
        logger.info(f"   Symbol: {retrieved.symbol}")
        logger.info(f"   Timestamp: {retrieved.timestamp}")
        logger.info(f"   Price: ${retrieved.ohlcv.get('price', 0):,.2f}")
        logger.info(f"   Volume: {retrieved.ohlcv.get('volume', 0):.4f}")
        logger.info(f"   RSI14: {retrieved.indicators.get('rsi14', 'N/A')}")
        logger.info(f"   RSI7: {retrieved.indicators.get('rsi7', 'N/A')}")
        logger.info(f"   MACD: {retrieved.indicators['macd']['macd_line']:.4f}")
        logger.info(f"   MACD Signal: {retrieved.indicators['macd']['signal_line']:.4f}")
        logger.info(f"   EMA20: {retrieved.indicators.get('ema_20', 'N/A')}")
        logger.info(f"   ATR14: {retrieved.indicators.get('atr14', 'N/A')}")
        logger.info(f"   Layout: {retrieved.indicators.get('layout_name', 'N/A')}")
    else:
        logger.error("❌ Failed to retrieve data")
    
    logger.info("=" * 60)


async def main():
    """Main test runner"""
    print("\n")
    print("=" * 60)
    print("TradingView Polling Service - Test Suite")
    print("=" * 60)
    print("\nChoose test mode:")
    print("1. Test with mock data (safe, no API calls)")
    print("2. Test with real Svix API (requires valid credentials)")
    print("3. Run both tests")
    print("\n")
    
    choice = input("Enter choice (1/2/3): ").strip()
    
    if choice == "1":
        await test_mock_data()
    elif choice == "2":
        await test_polling_service()
    elif choice == "3":
        await test_mock_data()
        print("\n\n")
        await test_polling_service()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())

