# TradingView Polling Service Setup Guide

## 📋 Overview

The TradingView Signal Agent now uses a **polling-based** approach instead of webhooks to fetch indicator data from Svix API.

### Key Changes

- ❌ **Removed**: Webhook service (port 8001)
- ✅ **Added**: Scheduled polling service (3-minute intervals)
- ✅ **Data Source**: Svix API
- ✅ **Backward Compatible**: Existing agent code works without changes

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
export SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"

# Optional (has defaults)
export SVIX_API_URL="https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6"
```

### Polling Schedule

- **Interval**: Every 3 minutes
- **Start Time**: At :00 seconds (e.g., 10:00:00, 10:03:00, 10:06:00)
- **Data Timeframe**: 1-minute candles from API
- **Pagination**: Automatically handles multiple pages

---

## 🚀 Usage

### Start Polling Service

```bash
# Using the startup script
./scripts/start_tradingview_polling.sh

# Or directly with Python
cd python
python -m valuecell.agents.tradingview_signal_agent.polling_service
```

### Test the Service

```bash
# Run test suite
cd python
python -m valuecell.agents.tradingview_signal_agent.test_polling

# Options:
# 1. Test with mock data (no API calls)
# 2. Test with real Svix API
# 3. Run both tests
```

---

## 📊 Data Flow

```
┌─────────────────┐
│   Svix API      │
│  (TradingView)  │
└────────┬────────┘
         │ Poll every 3 min
         ▼
┌─────────────────┐
│ Polling Service │
│  - Fetch data   │
│  - Parse JSON   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ IndicatorStore  │
│  - Validate     │
│  - Transform    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │
│ (indicators.db) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TradingView     │
│ Signal Agent    │
└─────────────────┘
```

---

## 🗃️ Database Schema

No changes to database schema - uses the same `indicator_data` table:

```sql
CREATE TABLE indicator_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    timeframe TEXT NOT NULL,
    ohlcv TEXT NOT NULL,
    indicators TEXT NOT NULL,
    raw_payload TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timestamp, timeframe)
);
```

---

## 📝 API Response Format

**Real Svix API response format** (with pagination):

```json
{
  "iterator": "eyJvZmZzZXQiOi05MjIzMzc",
  "data": [
    {
      "symbol": "BTCUSDT",
      "time": 1761504480000,
      "timeframe_base": "1",
      "layout_name": "rst-BTC-1m-rule",
      "price": 113727.02,
      "mid_price": 113719.57,
      "volume": 2.73071,
      "avg_volume": 7.1376495,
      "ema20": 113668.69,
      "ema50": 113616.15,
      "rsi7": 63.07,
      "rsi14": 62.95,
      "atr3": 34.60,
      "atr14": 29.58,
      "macd": 39.93,
      "macd_signal": 42.68,
      "macd_hist": -2.75
    }
  ],
  "done": false
}
```

**Key fields:**
- `time`: Unix timestamp in milliseconds
- `timeframe_base`: "1" for 1-minute candles
- `rsi7` / `rsi14`: Two RSI periods
- `atr3` / `atr14`: ATR indicators
- `macd`, `macd_signal`, `macd_hist`: MACD components
- `ema20`, `ema50`: Moving averages (lowercase)

---

## 🔍 Monitoring

### Check Service Status

```bash
# Check if service is running
ps aux | grep polling_service

# View logs
tail -f logs/polling_service.log
```

### Monitor Database

```bash
# Check latest data
sqlite3 tradingview_indicators.db "SELECT symbol, timestamp, timeframe FROM indicator_data ORDER BY timestamp DESC LIMIT 10;"

# Count records
sqlite3 tradingview_indicators.db "SELECT COUNT(*) FROM indicator_data;"

# Check symbols
sqlite3 tradingview_indicators.db "SELECT DISTINCT symbol FROM indicator_data;"
```

---

## 🐛 Troubleshooting

### Service Not Starting

1. Check environment variables:
   ```bash
   echo $SVIX_API_TOKEN
   echo $SVIX_CONSUMER_ID
   ```

2. Verify Python dependencies:
   ```bash
   pip install httpx apscheduler
   ```

3. Check logs for errors

### No Data Being Stored

1. Test API connection manually:
   ```bash
   curl -X GET \
     "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/MY_CONSUMER_ID" \
     -H "Accept: application/json" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

2. Run test with mock data:
   ```bash
   python -m valuecell.agents.tradingview_signal_agent.test_polling
   # Choose option 1 (mock data)
   ```

3. Check database permissions:
   ```bash
   ls -l tradingview_indicators.db
   ```

### API Authentication Errors

- Verify token is correct and not expired
- Check API URL is correct
- Ensure consumer ID matches

---

## 🔄 Migration from Webhook Service

### What Changed

| Component | Old (Webhook) | New (Polling) |
|-----------|---------------|---------------|
| Data Source | TradingView Push | Svix API Pull |
| Service Port | 8001 | N/A (no port) |
| Trigger | On webhook receive | Every 3 minutes |
| Security | HMAC signature | Bearer token |
| Startup Script | `start_tradingview_webhook.sh` | `start_tradingview_polling.sh` |

### What Stayed the Same

- ✅ Database schema (no migration needed)
- ✅ Data models (backward compatible)
- ✅ Agent code (no changes required)
- ✅ Query APIs (`get_recent_data`, `get_latest_data`)

### Old Files (Archived)

- `webhook_service.py.deprecated` - Kept for reference
- `start_tradingview_webhook.sh` - Still exists but obsolete

---

## 📚 Related Documentation

- [Database Setup](DATABASE_AND_LOGGING_SETUP.md)
- [Agent Implementation](IMPLEMENTATION_SUMMARY.md)
- [Logging Guide](LOGGING.md)

---

## 🆘 Support

If you encounter issues:

1. Check logs: `logs/polling_service.log`
2. Run test suite with mock data
3. Verify environment variables
4. Check API credentials
5. Review database permissions

---

**Last Updated**: 2025-10-26  
**Version**: 2.0 (Polling-based)

