# Svix API Response Format Reference

## Overview

This document describes the **actual** Svix API response format used by the TradingView Signal Agent polling service.

---

## Response Structure

### Top-level Response (Paginated)

```json
{
  "iterator": "eyJvZmZzZXQiOi05MjIzMzc",
  "data": [...],
  "done": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `iterator` | string | Pagination cursor for next page |
| `data` | array | Array of indicator data items |
| `done` | boolean | `true` if no more pages available |

---

## Data Item Format

Each item in the `data` array:

```json
{
  "symbol": "BTCUSDT",
  "time": 1761504480000,
  "timeframe_base": "1",
  "layout_name": "rst-BTC-1m-rule",
  "price": 113727.02,
  "mid_price": 113719.57,
  "volume": 2.73071,
  "avg_volume": 7.1376495,
  "ema20": 113668.6931425036,
  "ema50": 113616.1458435876,
  "rsi7": 63.0689404869,
  "rsi14": 62.9510623295,
  "atr3": 34.6048393763,
  "atr14": 29.5772957569,
  "macd": 39.9260687318,
  "macd_signal": 42.6756581034,
  "macd_hist": -2.7495893716
}
```

---

## Field Descriptions

### Identification Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `symbol` | string | Trading pair symbol | "BTCUSDT" |
| `time` | integer | Unix timestamp in **milliseconds** | 1761504480000 |
| `timeframe_base` | string | Base timeframe (minutes) | "1" |
| `layout_name` | string | Strategy/layout identifier | "rst-BTC-1m-rule" |

### Price Data

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `price` | float | Current price | 113727.02 |
| `mid_price` | float | Mid price (bid+ask)/2 | 113719.57 |
| `volume` | float | Current volume | 2.73071 |
| `avg_volume` | float | Average volume | 7.1376495 |

**Note**: No OHLC data provided - use `price` for all OHLC values.

### MACD Indicators

| Field | Type | Description | Range |
|-------|------|-------------|-------|
| `macd` | float | MACD line | Any |
| `macd_signal` | float | Signal line | Any |
| `macd_hist` | float | Histogram (macd - signal) | Any |

### RSI Indicators

| Field | Type | Description | Range |
|-------|------|-------------|-------|
| `rsi7` | float | 7-period RSI | 0-100 |
| `rsi14` | float | 14-period RSI (default) | 0-100 |

**Usage**: Use `rsi14` as the primary RSI indicator.

### Moving Averages

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `ema20` | float | 20-period EMA | 113668.69 |
| `ema50` | float | 50-period EMA | 113616.15 |

**Note**: Field names are **lowercase** in API response.

### ATR (Average True Range)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `atr3` | float | 3-period ATR | 34.60 |
| `atr14` | float | 14-period ATR | 29.58 |

---

## Data Conversions

### Timestamp Conversion

```python
# API provides milliseconds
time_ms = 1761504480000

# Convert to datetime
from datetime import datetime, timezone
timestamp = datetime.fromtimestamp(time_ms / 1000.0, tz=timezone.utc)
```

### Timeframe Conversion

```python
# API provides string number
timeframe_base = "1"

# Convert to standard format
timeframe = f"{timeframe_base}m"  # "1m"
```

### OHLC Compatibility

```python
# Since API doesn't provide OHLC, use price for all
price = 113727.02
ohlcv = {
    "open": price,
    "high": price,
    "low": price,
    "close": price,
    "volume": 2.73071
}
```

---

## Pagination Example

### First Request

```bash
GET /api/v1/app/.../poller/.../consumer/MY_CONSUMER_ID
```

Response:
```json
{
  "iterator": "abc123",
  "data": [/* 50 items */],
  "done": false
}
```

### Subsequent Request

```bash
GET /api/v1/app/.../poller/.../consumer/MY_CONSUMER_ID?iterator=abc123
```

Response:
```json
{
  "iterator": "xyz789",
  "data": [/* 50 items */],
  "done": false
}
```

### Final Request

```bash
GET /api/v1/app/.../poller/.../consumer/MY_CONSUMER_ID?iterator=xyz789
```

Response:
```json
{
  "iterator": null,
  "data": [/* 10 items */],
  "done": true
}
```

---

## Complete Example

### Real API Response

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
      "ema20": 113668.6931425036,
      "ema50": 113616.1458435876,
      "rsi7": 63.0689404869,
      "rsi14": 62.9510623295,
      "atr3": 34.6048393763,
      "atr14": 29.5772957569,
      "macd": 39.9260687318,
      "macd_signal": 42.6756581034,
      "macd_hist": -2.7495893716
    },
    {
      "symbol": "ETHUSDT",
      "time": 1761504480000,
      "timeframe_base": "1",
      "layout_name": "rst-ETH-1m-rule",
      "price": 3450.75,
      "mid_price": 3449.80,
      "volume": 15.42,
      "avg_volume": 12.3,
      "ema20": 3445.20,
      "ema50": 3440.10,
      "rsi7": 55.2,
      "rsi14": 58.3,
      "atr3": 5.2,
      "atr14": 4.8,
      "macd": 8.25,
      "macd_signal": 7.50,
      "macd_hist": 0.75
    }
  ],
  "done": false
}
```

### Parsed to SvixIndicatorData

```python
from models import SvixIndicatorData

# For each item in response["data"]:
indicator = SvixIndicatorData.from_api_response(item)

print(f"Symbol: {indicator.symbol}")
print(f"Timestamp: {indicator.timestamp}")
print(f"Price: ${indicator.price:,.2f}")
print(f"RSI14: {indicator.rsi14:.2f}")
print(f"MACD: {indicator.macd.macd_line:.2f}")
```

---

## Important Notes

1. **Timestamp Format**: Milliseconds, not seconds
2. **Field Names**: Lowercase (ema20, not ema_20)
3. **No OHLC**: Only single price point provided
4. **Two RSI Values**: rsi7 and rsi14 available
5. **Pagination**: Must handle multiple pages
6. **Timeframe**: Always "1" (1-minute data)

---

## Testing

Use the test script to verify parsing:

```bash
cd python
python -m valuecell.agents.tradingview_signal_agent.test_polling
# Choose option 1 for mock data test
```

---

**Last Updated**: 2025-10-26  
**API Version**: v1

