# 仓位管理快速参考手册

## 目录
- [快速开始](#快速开始)
- [核心类参考](#核心类参考)
- [常用操作](#常用操作)
- [配置参数](#配置参数)
- [风险指标](#风险指标)
- [数据库查询](#数据库查询)
- [故障排查](#故障排查)

---

## 快速开始

### 初始化系统

```python
from valuecell.agents.tradingview_signal_agent import (
    PortfolioManager,
    TradingSessionConfig
)

# 创建会话配置
config = TradingSessionConfig(
    session_id="session_001",
    user_id="user_123",
    initial_capital=10000.0,
    current_capital=10000.0,
    max_position_size_pct=0.20,
    risk_per_trade_pct=0.02
)

# 初始化组合管理器
portfolio = PortfolioManager(config)
```

### 开仓完整流程

```python
# 1. 检查能否开仓
can_open, reason = await portfolio.can_open_new_position(
    symbol="BTC/USDT",
    position_size_usd=2000.0
)

if not can_open:
    print(f"Cannot open: {reason}")
    return

# 2. 计算仓位大小
sizing = portfolio.risk_manager.calculate_position_size(
    symbol="BTC/USDT",
    entry_price=50000.0,
    stop_loss_price=49000.0,
    available_capital=portfolio.config.current_capital,
    confidence=0.75
)

# 3. 开仓
position = await portfolio.position_manager.open_position(
    symbol="BTC/USDT",
    side=PositionSide.LONG,
    quantity=sizing["quantity"],
    entry_price=50000.0,
    profit_target=52000.0,
    stop_loss=49000.0,
    invalidation_condition=invalidation,
    leverage=sizing["recommended_leverage"],
    confidence=0.75,
    risk_usd=sizing["actual_risk_amount"]
)

print(f"Position opened: {position.position_id}")
```

### 监控和平仓

```python
# 更新仓位
prices = {"BTC/USDT": 51000.0}
await portfolio.update_all_positions(prices)

# 手动平仓
closed = await portfolio.position_manager.close_position(
    symbol="BTC/USDT",
    exit_price=51000.0,
    exit_reason="manual"
)

print(f"Realized P&L: ${closed.realized_pnl:.2f}")
```

---

## 核心类参考

### PortfolioManager

**导入**: `from valuecell.agents.tradingview_signal_agent import PortfolioManager`

#### 初始化
```python
portfolio = PortfolioManager(session_config: TradingSessionConfig)
```

#### 主要方法

| 方法 | 用途 | 返回值 |
|------|------|--------|
| `get_portfolio_summary()` | 获取组合摘要 | `PortfolioSnapshot` |
| `can_open_new_position(symbol, size)` | 检查能否开仓 | `(bool, str)` |
| `update_all_positions(prices)` | 更新所有仓位 | `None` |
| `check_all_invalidations(market_data)` | 检查失效条件 | `None` |
| `save_snapshot()` | 保存组合快照 | `None` |
| `get_portfolio_history(limit)` | 获取历史快照 | `List[PortfolioSnapshot]` |
| `get_margin_status()` | 获取保证金状态 | `Dict` |

#### 示例
```python
# 获取组合摘要
summary = await portfolio.get_portfolio_summary()
print(f"Total Capital: ${summary.total_capital:.2f}")
print(f"Unrealized P&L: ${summary.unrealized_pnl:.2f}")
print(f"Portfolio Heat: {summary.portfolio_heat:.2%}")

# 检查保证金
margin = portfolio.get_margin_status()
if margin["is_warning"]:
    print("Warning: High margin usage!")
```

---

### PositionManager

**导入**: 通过 `portfolio.position_manager` 访问

#### 主要方法

| 方法 | 用途 | 参数 | 返回值 |
|------|------|------|--------|
| `open_position()` | 开仓 | symbol, side, quantity, entry_price, profit_target, stop_loss, etc. | `Position` |
| `close_position()` | 平仓 | symbol, exit_price, exit_reason, signal_id | `ClosedPosition` |
| `add_to_position()` | 加仓 | symbol, quantity, entry_price, signal_id | `Position` |
| `reduce_position()` | 减仓 | symbol, reduce_quantity, exit_price, reason | `(Position, float)` |
| `update_positions()` | 更新仓位 | current_prices: Dict | `None` |
| `get_open_positions()` | 获取所有开仓 | - | `List[Position]` |
| `get_position()` | 获取特定仓位 | symbol | `Position` |
| `has_position()` | 检查是否有仓位 | symbol | `bool` |
| `get_total_realized_pnl()` | 获取总已实现盈亏 | - | `float` |

#### 示例
```python
pm = portfolio.position_manager

# 获取所有开仓
positions = pm.get_open_positions()
for pos in positions:
    print(f"{pos.symbol}: {pos.side.value} {pos.quantity}")

# 检查特定仓位
if pm.has_position("BTC/USDT"):
    pos = pm.get_position("BTC/USDT")
    print(f"Unrealized P&L: ${pos.unrealized_pnl:.2f}")

# 减仓
remaining, partial_pnl = await pm.reduce_position(
    symbol="BTC/USDT",
    reduce_quantity=0.5,
    exit_price=51000.0,
    reason="partial_profit"
)
```

---

### RiskManager

**导入**: 通过 `portfolio.risk_manager` 访问

#### 主要方法

| 方法 | 用途 | 返回值 |
|------|------|--------|
| `calculate_position_size()` | 计算仓位大小 | `Dict` |
| `calculate_portfolio_heat()` | 计算组合热度 | `float` |
| `get_total_exposure()` | 获取总暴露 | `float` |
| `assess_trade_risk()` | 评估交易风险 | `Dict` |
| `calculate_stop_loss()` | 计算止损价格 | `float` |
| `calculate_take_profit_targets()` | 计算止盈目标 | `List[Dict]` |
| `check_margin_requirements()` | 检查保证金 | `Dict` |

#### 计算仓位大小示例
```python
rm = portfolio.risk_manager

sizing = rm.calculate_position_size(
    symbol="ETH/USDT",
    entry_price=3000.0,
    stop_loss_price=2900.0,
    available_capital=10000.0,
    confidence=0.7
)

print(f"Quantity: {sizing['quantity']:.4f}")
print(f"Notional Value: ${sizing['notional_value']:.2f}")
print(f"Risk Amount: ${sizing['actual_risk_amount']:.2f}")
print(f"Risk %: {sizing['actual_risk_pct']:.2%}")
print(f"Leverage: {sizing['recommended_leverage']}x")
```

#### 风险评估示例
```python
assessment = rm.assess_trade_risk(
    symbol="ETH/USDT",
    action=OperationType.OPEN,
    quantity=1.0,
    entry_price=3000.0,
    stop_loss=2900.0,
    current_positions=pm.get_open_positions(),
    available_capital=config.current_capital
)

if assessment["is_acceptable"]:
    print("Trade is acceptable")
else:
    print(f"Risks: {assessment['risks']}")
    
if assessment["warnings"]:
    print(f"Warnings: {assessment['warnings']}")

print(f"Metrics: {assessment['metrics']}")
```

#### 止损止盈计算
```python
# ATR 基础止损
stop_loss = rm.calculate_stop_loss(
    entry_price=50000.0,
    side=PositionSide.LONG,
    atr=500.0  # ATR值
)

# 百分比止损
stop_loss = rm.calculate_stop_loss(
    entry_price=50000.0,
    side=PositionSide.LONG,
    percentage=0.02  # 2%
)

# 多级止盈目标
tp_targets = rm.calculate_take_profit_targets(
    entry_price=50000.0,
    stop_loss=49000.0,
    side=PositionSide.LONG,
    risk_reward_ratios=[2.0, 3.0, 4.0]
)

for i, tp in enumerate(tp_targets, 1):
    print(f"TP{i}: ${tp['price']:.2f} ({tp['qty_pct']}%)")
```

---

### PerformanceAnalytics

**导入**: 通过 `portfolio.performance_analytics` 访问

#### 主要方法

| 方法 | 用途 | 返回值 |
|------|------|--------|
| `calculate_statistics()` | 计算交易统计 | `Dict` |
| `calculate_max_drawdown()` | 计算最大回撤 | `(float, float)` |
| `calculate_sharpe_ratio()` | 计算夏普比率 | `float` |
| `get_trading_statistics()` | 获取综合统计 | `TradingStatistics` |

#### 示例
```python
pa = portfolio.performance_analytics

# 基础统计
stats = pa.calculate_statistics()
print(f"Total Trades: {stats['total_trades']}")
print(f"Win Rate: {stats['win_rate']:.2%}")
print(f"Profit Factor: {stats['profit_factor']:.2f}")
print(f"Avg Win: ${stats['avg_win']:.2f}")
print(f"Avg Loss: ${stats['avg_loss']:.2f}")

# 获取综合统计
from datetime import datetime, timedelta
period_stats = pa.get_trading_statistics(
    period_start=datetime.now() - timedelta(days=30),
    period_end=datetime.now()
)

print(f"Max Drawdown: ${period_stats.max_drawdown:.2f} ({period_stats.max_drawdown_pct:.2%})")
print(f"Sharpe Ratio: {period_stats.sharpe_ratio:.2f}")
```

---

### PositionDatabase

**导入**: `from valuecell.agents.tradingview_signal_agent import PositionDatabase`

#### 主要方法

| 方法 | 用途 | 返回值 |
|------|------|--------|
| `save_session()` | 保存会话 | `bool` |
| `get_session()` | 获取会话 | `TradingSessionConfig` |
| `save_position()` | 保存仓位 | `bool` |
| `update_position()` | 更新仓位 | `bool` |
| `save_closed_position()` | 保存平仓 | `bool` |
| `get_closed_positions()` | 获取历史平仓 | `List[ClosedPosition]` |
| `save_snapshot()` | 保存快照 | `bool` |
| `get_snapshots()` | 获取快照历史 | `List[PortfolioSnapshot]` |
| `save_trade_record()` | 保存交易记录 | `bool` |

#### 示例
```python
db = PositionDatabase()

# 获取历史平仓
closed = await db.get_closed_positions(session_id="session_001")
for cp in closed:
    print(f"{cp.symbol}: {cp.realized_pnl:.2f} ({cp.exit_reason})")

# 获取快照历史
snapshots = await db.get_snapshots(
    session_id="session_001",
    limit=10
)

for snap in snapshots:
    print(f"{snap.timestamp}: ${snap.total_capital:.2f}")
```

---

## 常用操作

### 1. 查看当前持仓

```python
# 方法 1: 获取所有仓位
positions = portfolio.position_manager.get_open_positions()

for pos in positions:
    print(f"""
    Symbol: {pos.symbol}
    Side: {pos.side.value}
    Quantity: {pos.quantity}
    Entry: ${pos.entry_price:.2f}
    Current: ${pos.current_price:.2f}
    Unrealized P&L: ${pos.unrealized_pnl:.2f} ({pos.unrealized_pnl_pct:.2f}%)
    """)

# 方法 2: 从组合摘要获取
summary = await portfolio.get_portfolio_summary()
print(f"Open Positions: {summary.open_positions_count}")
print(f"Total Position Value: ${summary.total_position_value:.2f}")
```

### 2. 监控风险指标

```python
# 组合热度
heat = portfolio.risk_manager.calculate_portfolio_heat(
    portfolio.position_manager.get_open_positions()
)
print(f"Portfolio Heat: {heat:.2%}")

# 保证金状态
margin = portfolio.get_margin_status()
print(f"Margin Used: ${margin['total_margin_used']:.2f}")
print(f"Margin Usage: {margin['margin_usage_pct']:.2f}%")

if margin['is_critical']:
    print("⚠️ CRITICAL: Margin usage above 90%!")
elif margin['is_warning']:
    print("⚠️ WARNING: Margin usage above 80%")
```

### 3. 查看绩效

```python
# 当前绩效
summary = await portfolio.get_portfolio_summary()
print(f"""
Total Capital: ${summary.total_capital:.2f}
Available: ${summary.available_capital:.2f}
In Positions: ${summary.used_capital:.2f}

Unrealized P&L: ${summary.unrealized_pnl:.2f}
Realized P&L: ${summary.realized_pnl:.2f}
Total P&L: ${summary.total_pnl:.2f}
Return: {summary.total_return_pct:.2f}%

Win Rate: {summary.win_rate:.2%}
Profit Factor: {summary.profit_factor:.2f}
""")

# 历史统计
stats = portfolio.performance_analytics.calculate_statistics()
print(f"""
Total Trades: {stats['total_trades']}
Wins: {stats['winning_trades']} / Losses: {stats['losing_trades']}
Avg Win: ${stats['avg_win']:.2f}
Avg Loss: ${stats['avg_loss']:.2f}
Largest Win: ${stats['largest_win']:.2f}
Largest Loss: ${stats['largest_loss']:.2f}
""")
```

### 4. 批量操作

```python
# 平掉所有仓位
async def close_all_positions(current_prices: Dict[str, float]):
    positions = portfolio.position_manager.get_open_positions()
    
    for pos in positions:
        if pos.symbol in current_prices:
            await portfolio.position_manager.close_position(
                symbol=pos.symbol,
                exit_price=current_prices[pos.symbol],
                exit_reason="close_all"
            )
            print(f"Closed {pos.symbol}")

# 更新所有止损
async def update_all_stop_losses(new_stop_pct: float = 0.02):
    positions = portfolio.position_manager.get_open_positions()
    
    for pos in positions:
        if pos.side == PositionSide.LONG:
            new_stop = pos.entry_price * (1 - new_stop_pct)
        else:
            new_stop = pos.entry_price * (1 + new_stop_pct)
        
        pos.stop_loss_price = new_stop
        await portfolio.position_manager.db.update_position(pos)
        print(f"Updated stop loss for {pos.symbol}: ${new_stop:.2f}")
```

---

## 配置参数

### TradingSessionConfig 参数详解

```python
config = TradingSessionConfig(
    session_id="unique_id",           # 会话唯一标识
    user_id="user_id",                # 用户ID
    
    # 资金配置
    initial_capital=10000.0,          # 初始资金
    current_capital=10000.0,          # 当前资金
    
    # 风险参数
    max_position_size_pct=0.20,       # 单仓最大占比 (20%)
    max_total_exposure_pct=0.60,      # 总暴露最大占比 (60%)
    max_concurrent_positions=5,        # 最大并发仓位数
    risk_per_trade_pct=0.02,          # 单笔风险比例 (2%)
    
    # 交易规则
    allow_pyramiding=False,            # 是否允许加仓
    allow_hedging=False,               # 是否允许对冲
    max_leverage=20,                   # 最大杠杆
    default_leverage=10,               # 默认杠杆
    
    # 杠杆配置
    leverage_by_confidence={
        "high": 10,      # 高信心: 10x
        "medium": 5,     # 中信心: 5x
        "low": 2         # 低信心: 2x
    },
    
    # 交易限制
    min_trade_size=10.0,              # 最小交易金额
    max_daily_trades=20,              # 每日最大交易次数
    
    # 状态
    is_active=True                    # 会话是否活跃
)
```

### 预设配置模板

#### 保守型
```python
CONSERVATIVE_CONFIG = {
    "max_position_size_pct": 0.10,      # 10%
    "max_total_exposure_pct": 0.40,     # 40%
    "max_concurrent_positions": 3,
    "risk_per_trade_pct": 0.01,         # 1%
    "allow_pyramiding": False,
    "max_leverage": 5,
    "default_leverage": 2,
    "leverage_by_confidence": {
        "high": 5,
        "medium": 3,
        "low": 2
    }
}
```

#### 平衡型
```python
BALANCED_CONFIG = {
    "max_position_size_pct": 0.20,      # 20%
    "max_total_exposure_pct": 0.60,     # 60%
    "max_concurrent_positions": 5,
    "risk_per_trade_pct": 0.02,         # 2%
    "allow_pyramiding": False,
    "max_leverage": 10,
    "default_leverage": 5,
    "leverage_by_confidence": {
        "high": 10,
        "medium": 5,
        "low": 3
    }
}
```

#### 激进型
```python
AGGRESSIVE_CONFIG = {
    "max_position_size_pct": 0.30,      # 30%
    "max_total_exposure_pct": 0.80,     # 80%
    "max_concurrent_positions": 8,
    "risk_per_trade_pct": 0.03,         # 3%
    "allow_pyramiding": True,
    "max_leverage": 20,
    "default_leverage": 10,
    "leverage_by_confidence": {
        "high": 20,
        "medium": 10,
        "low": 5
    }
}
```

---

## 风险指标

### 关键指标说明

| 指标 | 含义 | 计算公式 | 良好值 |
|------|------|----------|--------|
| **Portfolio Heat** | 组合风险暴露 | Σ(position_risk) / total_capital | < 10% |
| **Win Rate** | 胜率 | winning_trades / total_trades | > 50% |
| **Profit Factor** | 盈利因子 | total_wins / |total_losses| | > 2.0 |
| **Sharpe Ratio** | 夏普比率 | (avg_return - rf) / std_return | > 2.0 |
| **Max Drawdown** | 最大回撤 | max(peak - trough) / peak | < 20% |
| **Exposure %** | 暴露百分比 | total_position_value / total_capital | < 60% |
| **Margin Usage** | 保证金使用率 | margin_used / available_capital | < 80% |

### 风险级别判断

```python
def assess_risk_level(portfolio: PortfolioManager) -> str:
    """评估风险级别"""
    summary = await portfolio.get_portfolio_summary()
    
    # 组合热度
    if summary.portfolio_heat > 0.15:
        return "CRITICAL"
    elif summary.portfolio_heat > 0.10:
        return "HIGH"
    elif summary.portfolio_heat > 0.05:
        return "MEDIUM"
    else:
        return "LOW"

# 使用
risk_level = assess_risk_level(portfolio)
print(f"Current Risk Level: {risk_level}")
```

---

## 数据库查询

### 直接 SQL 查询

```python
import sqlite3

def query_database(db_path: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 查询所有开仓
    cursor.execute("""
        SELECT symbol, side, quantity, entry_price, 
               unrealized_pnl, opened_at
        FROM positions
        WHERE status = 'open'
        ORDER BY opened_at DESC
    """)
    
    for row in cursor.fetchall():
        print(row)
    
    # 查询历史绩效
    cursor.execute("""
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
            AVG(realized_pnl) as avg_pnl,
            SUM(realized_pnl) as total_pnl
        FROM closed_positions
        WHERE session_id = ?
    """, (session_id,))
    
    stats = cursor.fetchone()
    print(f"Stats: {stats}")
    
    conn.close()
```

### 常用查询

```python
# 查询最近的交易
"""
SELECT * FROM trade_records
WHERE session_id = ?
ORDER BY timestamp DESC
LIMIT 10
"""

# 查询盈利最多的交易
"""
SELECT * FROM closed_positions
WHERE session_id = ?
ORDER BY realized_pnl DESC
LIMIT 5
"""

# 查询亏损最多的交易
"""
SELECT * FROM closed_positions
WHERE session_id = ?
ORDER BY realized_pnl ASC
LIMIT 5
"""

# 查询持仓时间最长的交易
"""
SELECT * FROM closed_positions
WHERE session_id = ?
ORDER BY holding_duration DESC
LIMIT 5
"""

# 按标的统计
"""
SELECT 
    symbol,
    COUNT(*) as trade_count,
    SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) as wins,
    SUM(realized_pnl) as total_pnl,
    AVG(realized_pnl) as avg_pnl
FROM closed_positions
WHERE session_id = ?
GROUP BY symbol
ORDER BY total_pnl DESC
"""

# 按日期统计
"""
SELECT 
    DATE(closed_at) as trade_date,
    COUNT(*) as trades,
    SUM(realized_pnl) as daily_pnl
FROM closed_positions
WHERE session_id = ?
GROUP BY DATE(closed_at)
ORDER BY trade_date DESC
"""
```

---

## 故障排查

### 常见问题

#### 1. 无法开仓

**检查清单**:
```python
# 1. 检查配置
print(f"Current Capital: ${config.current_capital:.2f}")
print(f"Max Positions: {config.max_concurrent_positions}")

# 2. 检查现有仓位数
positions_count = len(portfolio.position_manager.get_open_positions())
print(f"Open Positions: {positions_count}")

# 3. 检查暴露
total_exposure = portfolio.risk_manager.get_total_exposure(
    portfolio.position_manager.get_open_positions()
)
exposure_pct = total_exposure / config.current_capital
print(f"Exposure: {exposure_pct:.2%}")

# 4. 尝试开仓并查看原因
can_open, reason = await portfolio.can_open_new_position(
    symbol="BTC/USDT",
    position_size_usd=1000.0
)
print(f"Can Open: {can_open}, Reason: {reason}")
```

#### 2. 仓位未自动平仓

**检查清单**:
```python
# 1. 检查止损止盈设置
pos = portfolio.position_manager.get_position("BTC/USDT")
print(f"Current Price: ${pos.current_price:.2f}")
print(f"Stop Loss: ${pos.stop_loss_price:.2f}")
print(f"Take Profit: ${pos.profit_target:.2f}")

# 2. 手动触发检查
prices = {"BTC/USDT": current_price}
await portfolio.update_all_positions(prices)

# 3. 检查更新频率
# 确保监控循环正在运行
```

#### 3. 数据不一致

**修复步骤**:
```python
# 1. 重新计算资金
total_margin = sum(
    pos.notional_value / pos.leverage 
    for pos in portfolio.position_manager.get_open_positions()
)

# 理论可用资金
theoretical_available = config.initial_capital - total_margin + realized_pnl

# 实际可用资金
actual_available = config.current_capital

if abs(theoretical_available - actual_available) > 1.0:
    print("⚠️ Capital mismatch detected!")
    print(f"Theoretical: ${theoretical_available:.2f}")
    print(f"Actual: ${actual_available:.2f}")
    
    # 修正
    config.current_capital = theoretical_available
    await portfolio.position_manager.db.save_session(config)
```

#### 4. 性能问题

**优化建议**:
```python
# 1. 批量更新而非逐个更新
# 好 ✓
prices = {pos.symbol: get_price(pos.symbol) for pos in positions}
await portfolio.update_all_positions(prices)

# 差 ✗
for pos in positions:
    price = get_price(pos.symbol)
    await portfolio.update_all_positions({pos.symbol: price})

# 2. 使用索引查询
# 数据库已建立索引，直接使用

# 3. 减少快照频率
# 不要每次更新都保存快照，建议：
# - 开仓/平仓时保存
# - 每小时保存一次
# - 重大变动时保存
```

### 日志和调试

```python
import logging

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 针对特定模块
logging.getLogger("valuecell.agents.tradingview_signal_agent.position_manager").setLevel(logging.DEBUG)

# 记录关键操作
logger = logging.getLogger(__name__)

logger.info(f"Opening position: {symbol}")
logger.debug(f"Position details: {position.dict()}")
logger.warning(f"High portfolio heat: {heat:.2%}")
logger.error(f"Failed to open position: {error}")
```

### 健康检查

```python
async def health_check(portfolio: PortfolioManager):
    """系统健康检查"""
    issues = []
    
    # 1. 资金一致性
    summary = await portfolio.get_portfolio_summary()
    if summary.available_capital < 0:
        issues.append("❌ Negative available capital!")
    
    # 2. 仓位一致性
    positions = portfolio.position_manager.get_open_positions()
    for pos in positions:
        if pos.quantity <= 0:
            issues.append(f"❌ Invalid quantity for {pos.symbol}")
        if pos.leverage < 1 or pos.leverage > 40:
            issues.append(f"❌ Invalid leverage for {pos.symbol}")
    
    # 3. 风险检查
    heat = portfolio.risk_manager.calculate_portfolio_heat(positions)
    if heat > 0.20:
        issues.append(f"⚠️ High portfolio heat: {heat:.2%}")
    
    # 4. 保证金检查
    margin = portfolio.get_margin_status()
    if margin["is_critical"]:
        issues.append("⚠️ Critical margin level!")
    
    # 5. 数据库连接
    try:
        await portfolio.position_manager.db.get_session(portfolio.config.session_id)
    except Exception as e:
        issues.append(f"❌ Database error: {e}")
    
    if not issues:
        print("✅ All systems healthy")
    else:
        for issue in issues:
            print(issue)
    
    return len(issues) == 0

# 定期运行
if await health_check(portfolio):
    print("System OK")
```

---

## API 快速参考

### PositionSide (枚举)
```python
from valuecell.agents.tradingview_signal_agent.models import PositionSide

PositionSide.LONG   # 做多
PositionSide.SHORT  # 做空
```

### OperationType (枚举)
```python
from valuecell.agents.tradingview_signal_agent.models import OperationType

OperationType.OPEN    # 开仓
OperationType.CLOSE   # 平仓
OperationType.ADD     # 加仓
OperationType.REDUCE  # 减仓
```

### 平仓原因
```python
EXIT_REASONS = [
    "stop_loss",              # 止损
    "take_profit",            # 止盈
    "invalidation_triggered", # 失效条件触发
    "signal_reverse",         # 信号反转
    "manual",                 # 手动平仓
    "time_stop",              # 时间止损
    "partial_profit",         # 部分止盈
    "rebalance",              # 再平衡
    "close_all"               # 批量平仓
]
```

---

## 性能基准

### 推荐配置 (10K 资金)

| 类型 | 单仓 | 总暴露 | 并发仓位 | 单笔风险 |
|------|------|--------|----------|----------|
| 保守 | 10% | 40% | 3 | 1% |
| 平衡 | 20% | 60% | 5 | 2% |
| 激进 | 30% | 80% | 8 | 3% |

### 预期指标

| 指标 | 初级 | 中级 | 高级 |
|------|------|------|------|
| 月回报 | 2-5% | 5-10% | 10-20% |
| 胜率 | > 40% | > 50% | > 60% |
| 盈利因子 | > 1.2 | > 1.5 | > 2.0 |
| 最大回撤 | < 15% | < 12% | < 10% |
| 夏普比率 | > 1.0 | > 1.5 | > 2.0 |

---

## 相关文档

- [完整架构文档](./POSITION_MANAGEMENT_ARCHITECTURE.md)
- [数据流图](./POSITION_MANAGEMENT_DATAFLOW.md)
- [API 文档](../python/valuecell/agents/tradingview_signal_agent/README.md)

---

*快速参考版本: 1.0*
*最后更新: 2025-10-27*

