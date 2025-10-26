# Database Schema - indicator_data Table

## 概述

`indicator_data` 表使用扁平化结构存储所有技术指标，每个指标作为独立列，便于高效查询和分析。

---

## 表结构

```sql
CREATE TABLE indicator_data (
    -- 主键
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 标识字段
    symbol TEXT NOT NULL,                    -- 交易对 (如 BTCUSDT)
    timestamp DATETIME NOT NULL,             -- 时间戳
    timeframe TEXT NOT NULL DEFAULT '1m',    -- 时间周期 (1m, 5m, 15m等)
    
    -- 价格数据
    price REAL NOT NULL,                     -- 当前价格
    volume REAL NOT NULL,                    -- 成交量
    mid_price REAL,                          -- 中间价 (bid+ask)/2
    avg_volume REAL,                         -- 平均成交量
    
    -- OHLCV (兼容性)
    open REAL,                               -- 开盘价
    high REAL,                               -- 最高价
    low REAL,                                -- 最低价
    close REAL,                              -- 收盘价
    
    -- MACD 指标
    macd_line REAL,                          -- MACD线
    macd_signal REAL,                        -- 信号线
    macd_histogram REAL,                     -- 柱状图
    
    -- RSI 指标
    rsi7 REAL,                               -- 7周期RSI
    rsi14 REAL,                              -- 14周期RSI
    
    -- 移动平均线
    ema_9 REAL,                              -- 9周期EMA
    ema_20 REAL,                             -- 20周期EMA
    ema_21 REAL,                             -- 21周期EMA
    ema_50 REAL,                             -- 50周期EMA
    ema_200 REAL,                            -- 200周期EMA
    
    -- ATR 指标
    atr3 REAL,                               -- 3周期ATR
    atr14 REAL,                              -- 14周期ATR
    
    -- 布林带
    bollinger_upper REAL,                    -- 布林上轨
    bollinger_middle REAL,                   -- 布林中轨
    bollinger_lower REAL,                    -- 布林下轨
    
    -- 元数据
    source TEXT DEFAULT 'svix',              -- 数据源
    layout_name TEXT,                        -- 策略/布局名称
    timeframe_base TEXT,                     -- 原始时间周期基数
    raw_payload TEXT,                        -- 原始API响应 (JSON)
    
    -- 系统字段
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束
    UNIQUE(symbol, timestamp, timeframe)
);
```

---

## 索引

```sql
-- 按交易对和时间查询（最常用）
CREATE INDEX idx_symbol_timestamp 
ON indicator_data(symbol, timestamp DESC);

-- 按交易对、时间周期和时间查询
CREATE INDEX idx_symbol_timeframe 
ON indicator_data(symbol, timeframe, timestamp DESC);

-- 按策略名称查询
CREATE INDEX idx_layout 
ON indicator_data(layout_name);

-- 按创建时间查询
CREATE INDEX idx_created 
ON indicator_data(created_at DESC);
```

---

## 字段说明

### 标识字段

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `symbol` | TEXT | ✅ | 交易对符号 | "BTCUSDT" |
| `timestamp` | DATETIME | ✅ | 数据时间戳 (ISO格式) | "2025-10-26T15:08:00+00:00" |
| `timeframe` | TEXT | ✅ | 时间周期 | "1m", "5m", "15m" |

### 价格和成交量

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `price` | REAL | ✅ | 当前价格 | 113727.02 |
| `volume` | REAL | ✅ | 成交量 | 2.73071 |
| `mid_price` | REAL | ❌ | 中间价 | 113719.57 |
| `avg_volume` | REAL | ❌ | 平均成交量 | 7.1376495 |
| `open` | REAL | ❌ | 开盘价 | 113727.02 |
| `high` | REAL | ❌ | 最高价 | 113727.02 |
| `low` | REAL | ❌ | 最低价 | 113727.02 |
| `close` | REAL | ❌ | 收盘价 | 113727.02 |

**注意**: API不提供OHLC数据，这些字段使用`price`填充以保持兼容性。

### 技术指标

#### MACD

| 字段 | 类型 | 说明 | 范围 |
|------|------|------|------|
| `macd_line` | REAL | MACD线 | 任意实数 |
| `macd_signal` | REAL | 信号线 | 任意实数 |
| `macd_histogram` | REAL | 柱状图 (MACD - Signal) | 任意实数 |

**金叉**: `macd_line > macd_signal` 且 `macd_histogram > 0`  
**死叉**: `macd_line < macd_signal` 且 `macd_histogram < 0`

#### RSI

| 字段 | 类型 | 说明 | 范围 |
|------|------|------|------|
| `rsi7` | REAL | 7周期RSI | 0-100 |
| `rsi14` | REAL | 14周期RSI (主要) | 0-100 |

**超买**: RSI > 70  
**超卖**: RSI < 30  
**中性**: 40 ≤ RSI ≤ 60

#### 移动平均线 (EMA)

| 字段 | 类型 | 说明 |
|------|------|------|
| `ema_9` | REAL | 9周期EMA |
| `ema_20` | REAL | 20周期EMA |
| `ema_21` | REAL | 21周期EMA |
| `ema_50` | REAL | 50周期EMA |
| `ema_200` | REAL | 200周期EMA |

**多头排列**: EMA_9 > EMA_20 > EMA_50  
**空头排列**: EMA_9 < EMA_20 < EMA_50

#### ATR (Average True Range)

| 字段 | 类型 | 说明 |
|------|------|------|
| `atr3` | REAL | 3周期ATR (短期波动) |
| `atr14` | REAL | 14周期ATR (标准) |

用于衡量市场波动性。

#### 布林带

| 字段 | 类型 | 说明 |
|------|------|------|
| `bollinger_upper` | REAL | 上轨 |
| `bollinger_middle` | REAL | 中轨 (通常是20日SMA) |
| `bollinger_lower` | REAL | 下轨 |

### 元数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `source` | TEXT | 数据源标识 (固定为"svix") |
| `layout_name` | TEXT | 策略名称 (如 "rst-BTC-1m-rule") |
| `timeframe_base` | TEXT | 原始周期值 (如 "1") |
| `raw_payload` | TEXT | 完整API响应 (JSON字符串) |

---

## 数据类型映射

| Pydantic Model | Database Column | SQLite Type |
|----------------|-----------------|-------------|
| `symbol: str` | `symbol` | TEXT |
| `timestamp: datetime` | `timestamp` | DATETIME |
| `price: float` | `price` | REAL |
| `macd.macd_line: float` | `macd_line` | REAL |
| `rsi14: Optional[float]` | `rsi14` | REAL (nullable) |

---

## 查询示例

### 基础查询

```sql
-- 获取最新数据
SELECT * FROM indicator_data 
WHERE symbol = 'BTCUSDT' 
ORDER BY timestamp DESC 
LIMIT 1;

-- 获取特定时间范围
SELECT * FROM indicator_data
WHERE symbol = 'BTCUSDT'
  AND timestamp >= '2025-10-26 00:00:00'
  AND timestamp < '2025-10-27 00:00:00'
ORDER BY timestamp;
```

### 技术分析查询

```sql
-- RSI超买股票
SELECT symbol, timestamp, price, rsi14
FROM indicator_data
WHERE rsi14 > 70
  AND timeframe = '1m'
ORDER BY timestamp DESC;

-- MACD金叉
SELECT symbol, timestamp, price, macd_line, macd_signal
FROM indicator_data
WHERE macd_line > macd_signal
  AND macd_histogram > 0
  AND timeframe = '1m'
ORDER BY timestamp DESC;

-- 价格突破EMA20
SELECT symbol, timestamp, price, ema_20
FROM indicator_data
WHERE price > ema_20
  AND timeframe = '1m'
ORDER BY timestamp DESC;

-- 多条件筛选
SELECT symbol, timestamp, price, rsi14, macd_histogram
FROM indicator_data
WHERE rsi14 BETWEEN 40 AND 60
  AND macd_histogram > 0
  AND price > ema_20
  AND timeframe = '1m'
ORDER BY timestamp DESC
LIMIT 10;
```

### 统计分析

```sql
-- RSI分布统计
SELECT 
    CASE 
        WHEN rsi14 < 30 THEN 'Oversold'
        WHEN rsi14 > 70 THEN 'Overbought'
        WHEN rsi14 BETWEEN 40 AND 60 THEN 'Neutral'
        ELSE 'Trending'
    END as rsi_zone,
    COUNT(*) as count,
    ROUND(AVG(price), 2) as avg_price
FROM indicator_data
WHERE symbol = 'BTCUSDT'
  AND timestamp > datetime('now', '-24 hours')
GROUP BY rsi_zone;

-- 价格与EMA关系
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN price > ema_20 THEN 1 ELSE 0 END) as above_ema20,
    SUM(CASE WHEN price > ema_50 THEN 1 ELSE 0 END) as above_ema50,
    ROUND(100.0 * SUM(CASE WHEN price > ema_20 THEN 1 ELSE 0 END) / COUNT(*), 2) as pct_above_ema20
FROM indicator_data
WHERE symbol = 'BTCUSDT'
  AND timestamp > datetime('now', '-24 hours');

-- 波动性分析
SELECT 
    symbol,
    AVG(atr14) as avg_atr,
    MAX(atr14) as max_atr,
    MIN(atr14) as min_atr
FROM indicator_data
WHERE timestamp > datetime('now', '-24 hours')
GROUP BY symbol
ORDER BY avg_atr DESC;
```

### 时间序列分析

```sql
-- 每小时平均价格和RSI
SELECT 
    strftime('%Y-%m-%d %H:00:00', timestamp) as hour,
    COUNT(*) as data_points,
    ROUND(AVG(price), 2) as avg_price,
    ROUND(AVG(rsi14), 2) as avg_rsi14,
    ROUND(AVG(volume), 4) as avg_volume
FROM indicator_data
WHERE symbol = 'BTCUSDT'
  AND timestamp > datetime('now', '-24 hours')
GROUP BY hour
ORDER BY hour;
```

---

## 性能优化

### 索引使用

```sql
-- ✅ 使用索引 (快)
SELECT * FROM indicator_data 
WHERE symbol = 'BTCUSDT' 
ORDER BY timestamp DESC;

-- ❌ 不使用索引 (慢)
SELECT * FROM indicator_data 
WHERE rsi14 > 70;  -- rsi14没有索引
```

### 查询优化技巧

1. **总是使用symbol过滤** - symbol有索引
2. **限制时间范围** - 减少扫描行数
3. **使用LIMIT** - 限制返回结果
4. **避免SELECT *** - 只选择需要的列

```sql
-- 优化示例
SELECT symbol, timestamp, price, rsi14
FROM indicator_data
WHERE symbol = 'BTCUSDT'
  AND timestamp > datetime('now', '-1 hour')
ORDER BY timestamp DESC
LIMIT 100;
```

---

## 数据导出

### 导出为CSV

```sql
.mode csv
.output btc_indicators.csv
SELECT symbol, timestamp, price, volume, rsi14, macd_line, ema_20, ema_50
FROM indicator_data
WHERE symbol = 'BTCUSDT'
ORDER BY timestamp DESC
LIMIT 1000;
.output stdout
```

### 导出为JSON

```python
import sqlite3
import json

conn = sqlite3.connect('tradingview_indicators.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT symbol, timestamp, price, rsi14, macd_line
    FROM indicator_data
    WHERE symbol = 'BTCUSDT'
    LIMIT 100
""")

rows = cursor.fetchall()
data = [dict(zip(['symbol', 'timestamp', 'price', 'rsi14', 'macd_line'], row)) for row in rows]

with open('export.json', 'w') as f:
    json.dump(data, f, indent=2)
```

---

## 数据维护

### 清理旧数据

```sql
-- 删除30天前的数据
DELETE FROM indicator_data
WHERE timestamp < datetime('now', '-30 days');

-- 优化数据库
VACUUM;
```

### 查看数据库大小

```sql
-- 查看表信息
SELECT 
    COUNT(*) as total_records,
    COUNT(DISTINCT symbol) as unique_symbols,
    MIN(timestamp) as oldest_data,
    MAX(timestamp) as newest_data
FROM indicator_data;

-- 按交易对统计
SELECT 
    symbol,
    COUNT(*) as records,
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record
FROM indicator_data
GROUP BY symbol
ORDER BY records DESC;
```

---

## 完整示例

### 插入数据

```python
cursor.execute("""
    INSERT OR REPLACE INTO indicator_data (
        symbol, timestamp, timeframe,
        price, volume, mid_price,
        macd_line, macd_signal, macd_histogram,
        rsi7, rsi14,
        ema_20, ema_50,
        atr3, atr14,
        layout_name, raw_payload
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    'BTCUSDT', '2025-10-26T15:08:00+00:00', '1m',
    113727.02, 2.73071, 113719.57,
    39.93, 42.68, -2.75,
    63.07, 62.95,
    113668.69, 113616.15,
    34.60, 29.58,
    'rst-BTC-1m-rule', '{...}'
))
```

### 查询数据

```python
cursor.execute("""
    SELECT symbol, timestamp, price, rsi14, macd_line
    FROM indicator_data
    WHERE symbol = ? AND timeframe = ?
    ORDER BY timestamp DESC
    LIMIT ?
""", ('BTCUSDT', '1m', 100))

rows = cursor.fetchall()
for row in rows:
    print(f"{row[0]} @ {row[1]}: ${row[2]:.2f}, RSI={row[3]:.2f}")
```

---

## 注意事项

1. ✅ **所有指标字段都可为NULL** - API可能不提供某些指标
2. ✅ **UNIQUE约束** - 同一symbol、timestamp、timeframe组合只能有一条记录
3. ✅ **自动更新updated_at** - 使用 `INSERT OR REPLACE` 时自动更新
4. ✅ **原始数据备份** - `raw_payload` 保存完整API响应
5. ⚠️ **OHLC数据不完整** - 使用price填充，不适合K线分析

---

**数据库文件**: `tradingview_indicators.db`  
**Schema版本**: v2 (扁平化结构)  
**最后更新**: 2025-10-26

