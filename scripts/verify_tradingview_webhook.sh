#!/bin/bash
# TradingView Webhook Service Verification Script
# Usage: ./scripts/verify_tradingview_webhook.sh

set -e

WEBHOOK_URL="http://localhost:8001"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 TradingView Webhook Service Verification"
echo "=========================================="
echo ""

# Function to print test result
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
    fi
}

# Test 1: Check if service is running
echo "Test 1: Checking if webhook service is running on port 8001..."
if lsof -i :8001 -sTCP:LISTEN > /dev/null 2>&1; then
    print_result 0 "Webhook service is running"
else
    print_result 1 "Webhook service is NOT running"
    echo -e "${YELLOW}💡 Tip: Start the service with: ./scripts/start_tradingview_webhook.sh${NC}"
    exit 1
fi
echo ""

# Test 2: Health check endpoint
echo "Test 2: Testing health check endpoint..."
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" ${WEBHOOK_URL}/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Health check endpoint responding"
    echo "   Response: $BODY"
else
    print_result 1 "Health check endpoint failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 3: Webhook endpoint with test data
echo "Test 3: Testing webhook endpoint with sample data..."
WEBHOOK_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST ${WEBHOOK_URL}/api/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "timestamp": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",
    "timeframe": "15m",
    "price": 67500.50,
    "open": 67450.00,
    "high": 67580.00,
    "low": 67420.00,
    "close": 67500.50,
    "volume": 1234567.89,
    "macd": {
      "macd_line": 150.25,
      "signal_line": 145.30,
      "histogram": 4.95
    },
    "rsi": {
      "value": 65.5
    },
    "chart_prime": {
      "trend_strength": 75.5,
      "trend_direction": "bullish",
      "momentum_score": 68.0
    },
    "ema_20": 67200.00,
    "ema_50": 66800.00
  }')

HTTP_CODE=$(echo "$WEBHOOK_RESPONSE" | tail -1)
BODY=$(echo "$WEBHOOK_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Webhook endpoint accepting data"
    echo "   Response: $BODY"
else
    print_result 1 "Webhook endpoint failed (HTTP $HTTP_CODE)"
    echo "   Response: $BODY"
fi
echo ""

# Test 4: Query indicators endpoint
echo "Test 4: Testing indicators query endpoint..."
sleep 1  # Give time for data to be saved

INDICATORS_RESPONSE=$(curl -s -w "\n%{http_code}" "${WEBHOOK_URL}/api/indicators/BTCUSDT?limit=5")
HTTP_CODE=$(echo "$INDICATORS_RESPONSE" | tail -1)
BODY=$(echo "$INDICATORS_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_result 0 "Indicators query endpoint working"
    COUNT=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])" 2>/dev/null || echo "0")
    echo "   Found $COUNT indicator records for BTCUSDT"
else
    print_result 1 "Indicators query endpoint failed (HTTP $HTTP_CODE)"
fi
echo ""

# Test 5: Check database
echo "Test 5: Checking database..."
DB_PATH="python/tradingview_indicators.db"
if [ -f "$DB_PATH" ]; then
    print_result 0 "Database file exists"
    RECORD_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM indicator_data;" 2>/dev/null || echo "0")
    echo "   Total records in database: $RECORD_COUNT"
else
    print_result 1 "Database file not found at $DB_PATH"
fi
echo ""

# Test 6: Check TradingView Signal Agent
echo "Test 6: Checking TradingView Signal Agent..."
if lsof -i :10005 -sTCP:LISTEN > /dev/null 2>&1; then
    print_result 0 "TradingView Signal Agent is running on port 10005"
else
    print_result 1 "TradingView Signal Agent is NOT running on port 10005"
    echo -e "${YELLOW}💡 Tip: Start the agent with: ./scripts/start_tradingview_agent.sh${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "📊 Verification Summary"
echo "=========================================="
echo ""
echo -e "${GREEN}Service Status:${NC}"
echo "  • Webhook Service: Running on http://localhost:8001"
echo "  • Health Endpoint: /health"
echo "  • Webhook Endpoint: /api/webhook/tradingview"
echo "  • Query Endpoint: /api/indicators/{symbol}"
echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "  1. Configure TradingView webhook URL: http://your-domain:8001/api/webhook/tradingview"
echo "  2. Set up webhook secret: export TRADINGVIEW_WEBHOOK_SECRET='your-secret'"
echo "  3. Review documentation: WEBHOOK_SERVICE_VERIFICATION.md"
echo ""
echo -e "${GREEN}✅ Verification Complete!${NC}"

