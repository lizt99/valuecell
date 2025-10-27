# 仓位管理系统架构与数据流

## 概述

ValueCell 仓位管理系统负责管理交易仓位、资金、风险控制和绩效分析。系统支持两种交易代理模式：

1. **TradingView Signal Agent** - 基于信号的交易系统
2. **Auto Trading Agent** - 自动化交易系统

## 核心架构

### 1. 系统架构分层

```
┌─────────────────────────────────────────────────────────┐
│                  PortfolioManager                       │
│         (组合级别协调器 - 顶层管理)                      │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
┌───────▼──────────┐    ┌────────▼─────────┐
│ PositionManager  │    │   RiskManager    │
│  (仓位管理)      │    │   (风险管理)     │
└───────┬──────────┘    └────────┬─────────┘
        │                         │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │ PerformanceAnalytics    │
        │    (绩效分析)           │
        └────────────┬────────────┘
                     │
        ┌────────────▼────────────┐
        │  PositionDatabase       │
        │    (持久化存储)         │
        └─────────────────────────┘
```

---

## 数据模型

### 1. Position (仓位)

**位置**: `python/valuecell/agents/tradingview_signal_agent/models.py`

```python
class Position(BaseModel):
    # 基本信息
    position_id: str              # 唯一标识
    session_id: str               # 会话ID
    symbol: str                   # 交易标的
    side: PositionSide           # LONG/SHORT
    
    # 仓位大小
    quantity: float              # 数量
    notional_value: float        # 名义价值
    leverage: int                # 杠杆倍数 (1-40)
    
    # 价格信息
    entry_price: float           # 入场价格
    current_price: float         # 当前价格
    
    # 退出策略
    profit_target: float         # 盈利目标
    stop_loss_price: float       # 止损价格
    take_profit_targets: List    # 多级止盈目标
    invalidation_condition       # 失效条件
    
    # 风险指标
    risk_usd: float              # 风险金额(USD)
    risk_amount: float           # 风险数量
    reward_potential: float      # 潜在收益
    risk_reward_ratio: float     # 风险收益比
    confidence: float            # 信心水平 (0-1)
    
    # 盈亏信息
    unrealized_pnl: float        # 未实现盈亏
    unrealized_pnl_pct: float    # 未实现盈亏百分比
    
    # 时间信息
    opened_at: datetime          # 开仓时间
    last_updated: datetime       # 最后更新时间
```

**关键方法**:
- `calculate_unrealized_pnl(current_price)` - 计算未实现盈亏
- `check_invalidation(recent_candles)` - 检查失效条件

### 2. ClosedPosition (已平仓位)

```python
class ClosedPosition(BaseModel):
    position_id: str
    session_id: str
    symbol: str
    side: PositionSide
    
    # 仓位信息
    quantity: float
    entry_price: float
    exit_price: float
    
    # 已实现盈亏
    realized_pnl: float          # 已实现盈亏
    realized_pnl_pct: float      # 已实现盈亏百分比
    
    # 时间
    opened_at: datetime
    closed_at: datetime
    holding_duration: float      # 持仓时长(小时)
    
    # 原因
    exit_reason: str             # 平仓原因
    exit_signal_id: str          # 信号ID
```

### 3. PortfolioSnapshot (组合快照)

```python
class PortfolioSnapshot(BaseModel):
    session_id: str
    timestamp: datetime
    
    # 资金状态
    total_capital: float         # 总资金
    available_capital: float     # 可用资金
    used_capital: float          # 已使用资金
    
    # 仓位状态
    open_positions_count: int    # 开仓数量
    total_position_value: float  # 总仓位价值
    
    # 盈亏
    unrealized_pnl: float        # 未实现盈亏
    realized_pnl: float          # 已实现盈亏
    total_pnl: float             # 总盈亏
    total_return_pct: float      # 总回报率
    
    # 风险指标
    portfolio_heat: float        # 组合热度(总风险暴露)
    exposure_pct: float          # 暴露百分比
    
    # 绩效指标
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
```

### 4. TradingSessionConfig (交易会话配置)

```python
class TradingSessionConfig(BaseModel):
    session_id: str
    user_id: str
    
    # 资金配置
    initial_capital: float       # 初始资金
    current_capital: float       # 当前资金
    
    # 风险参数
    max_position_size_pct: float = 0.20      # 单仓最大占比 20%
    max_total_exposure_pct: float = 0.60     # 总仓位最大占比 60%
    max_concurrent_positions: int = 5        # 最大并发仓位数
    risk_per_trade_pct: float = 0.02         # 单笔风险比例 2%
    
    # 交易规则
    allow_pyramiding: bool = False           # 是否允许加仓
    allow_hedging: bool = False              # 是否允许对冲
    max_leverage: int = 20                   # 最大杠杆
    default_leverage: int = 10               # 默认杠杆
    leverage_by_confidence: Dict             # 基于信心的杠杆配置
        # high: 10-20x
        # medium: 5-10x
        # low: 2-5x
```

---

## 核心组件详解

### 1. PositionManager (仓位管理器)

**位置**: `python/valuecell/agents/tradingview_signal_agent/position_manager.py`

**职责**:
- 开仓、平仓、加仓、减仓
- 更新仓位状态
- 检查止损和止盈
- 检查失效条件
- 维护仓位历史

#### 主要方法流程

##### 1.1 开仓 (open_position)

```
输入参数:
  - symbol: 交易标的
  - side: LONG/SHORT
  - quantity: 数量
  - entry_price: 入场价格
  - profit_target: 盈利目标
  - stop_loss: 止损价格
  - invalidation_condition: 失效条件
  - leverage: 杠杆
  - confidence: 信心水平
  - risk_usd: 风险金额

处理流程:
  1. 生成 position_id (UUID)
  2. 计算仓位指标:
     - notional_value = quantity × entry_price
     - risk_amount = quantity × |entry_price - stop_loss|
     - reward_potential = quantity × |profit_target - entry_price|
     - risk_reward_ratio = reward_potential / risk_amount
  3. 创建 Position 对象
  4. 添加到 positions 字典 {symbol: Position}
  5. 更新可用资金:
     - margin_required = notional_value / leverage
     - current_capital -= margin_required
  6. 记录交易历史 (_record_trade)
  7. 保存到数据库 (db.save_position)

输出: Position 对象
```

##### 1.2 平仓 (close_position)

```
输入参数:
  - symbol: 交易标的
  - exit_price: 退出价格
  - exit_reason: 平仓原因
  - signal_id: 信号ID (可选)

处理流程:
  1. 查找仓位
  2. 计算已实现盈亏:
     LONG: realized_pnl = (exit_price - entry_price) × quantity
     SHORT: realized_pnl = (entry_price - exit_price) × quantity
  3. 计算已实现盈亏百分比:
     realized_pnl_pct = (realized_pnl / notional_value) × 100
  4. 计算持仓时长:
     holding_duration = (closed_at - opened_at).hours
  5. 创建 ClosedPosition 对象
  6. 更新可用资金:
     - margin_returned = notional_value / leverage
     - current_capital += margin_returned + realized_pnl
  7. 从 positions 字典移除
  8. 添加到 closed_positions 列表
  9. 记录交易历史
  10. 保存到数据库 (db.save_closed_position)

输出: ClosedPosition 对象
```

##### 1.3 加仓 (add_to_position)

```
前提条件: allow_pyramiding = True

处理流程:
  1. 检查加仓权限
  2. 查找现有仓位
  3. 计算新的平均入场价格:
     total_cost = (old_quantity × old_price) + (add_quantity × new_price)
     new_avg_price = total_cost / (old_quantity + add_quantity)
  4. 更新仓位数量和价格
  5. 更新名义价值
  6. 扣除额外保证金
  7. 记录交易并更新数据库

输出: 更新后的 Position
```

##### 1.4 减仓 (reduce_position)

```
处理流程:
  1. 查找仓位
  2. 检查减仓数量:
     - 如果 >= 总数量，则全部平仓
     - 否则部分平仓
  3. 计算部分盈亏
  4. 更新仓位数量和价值
  5. 返还部分保证金 + 部分盈亏
  6. 记录交易并更新数据库

输出: (更新后的Position, 部分盈亏)
```

##### 1.5 更新仓位 (update_positions)

```
输入: current_prices (Dict[symbol, price])

处理流程:
  对每个仓位:
    1. 获取当前价格
    2. 计算未实现盈亏 (calculate_unrealized_pnl)
    3. 检查止损和止盈 (_check_stop_loss_take_profit)
       - LONG: 价格 <= 止损价 → 平仓
       - SHORT: 价格 >= 止损价 → 平仓
       - LONG: 价格 >= 止盈价 → 平仓
       - SHORT: 价格 <= 止盈价 → 平仓

实时监控: 自动触发平仓条件
```

##### 1.6 检查失效条件 (check_invalidation_conditions)

```
输入: 
  - symbol: 交易标的
  - recent_candles: 最近的K线数据

处理流程:
  1. 获取仓位
  2. 调用 position.check_invalidation(candles)
  3. 如果触发失效条件:
     - 记录警告日志
     - 立即平仓
     - 平仓原因: "invalidation_triggered"

用途: 处理技术失效场景
```

---

### 2. RiskManager (风险管理器)

**位置**: `python/valuecell/agents/tradingview_signal_agent/risk_manager.py`

**职责**:
- 计算仓位大小
- 管理杠杆
- 计算组合热度
- 评估交易风险
- 计算止损和止盈

#### 主要方法

##### 2.1 计算仓位大小 (calculate_position_size)

```
输入:
  - symbol: 交易标的
  - entry_price: 入场价格
  - stop_loss_price: 止损价格
  - available_capital: 可用资金
  - confidence: 信心水平

计算公式:
  1. 计算风险金额:
     risk_amount = available_capital × risk_per_trade_pct
     
  2. 计算价格风险:
     price_risk = |entry_price - stop_loss_price|
     
  3. 计算数量:
     quantity = risk_amount / price_risk
     
  4. 计算名义价值:
     notional_value = quantity × entry_price
     
  5. 检查限制:
     max_notional = available_capital × max_position_size_pct
     if notional_value > max_notional:
       quantity = max_notional / entry_price
       notional_value = max_notional
       
  6. 检查资金:
     if notional_value > available_capital:
       quantity = available_capital / entry_price
       notional_value = available_capital

输出:
  {
    "quantity": 计算的数量,
    "notional_value": 名义价值,
    "capital_usage_pct": 资金使用百分比,
    "actual_risk_amount": 实际风险金额,
    "actual_risk_pct": 实际风险百分比,
    "recommended_leverage": 推荐杠杆
  }
```

##### 2.2 杠杆管理 (_get_leverage_for_confidence)

```
信心水平映射:
  - confidence >= 0.75 → 高杠杆 (10-20x)
  - confidence >= 0.65 → 中杠杆 (5-10x)
  - confidence < 0.65  → 低杠杆 (2-5x)

目的: 根据信心调整风险暴露
```

##### 2.3 计算组合热度 (calculate_portfolio_heat)

```
输入: positions (List[Position])

计算公式:
  total_risk = Σ(position.risk_usd)
  total_capital = current_capital + Σ(position.notional_value)
  portfolio_heat = total_risk / total_capital

解释:
  - Portfolio Heat 表示总资金的风险暴露百分比
  - 例如: heat = 0.10 表示总资金的10%处于风险中

警告级别:
  - > 0.10 (10%) → 高风险警告
  - > max_total_exposure_pct → 拒绝新仓位
```

##### 2.4 评估交易风险 (assess_trade_risk)

```
输入:
  - symbol, action, quantity, entry_price, stop_loss
  - current_positions: 当前仓位列表
  - available_capital: 可用资金

检查项:
  1. 仓位大小限制:
     notional_value <= available_capital × max_position_size_pct
     
  2. 组合热度限制:
     new_portfolio_heat <= max_total_exposure_pct
     
  3. 并发仓位限制:
     len(positions) < max_concurrent_positions
     
  4. 可用资金:
     notional_value <= available_capital

输出:
  {
    "is_acceptable": True/False,
    "risks": [风险列表],
    "warnings": [警告列表],
    "metrics": {
      "position_risk_pct": 仓位风险百分比,
      "new_portfolio_heat": 新组合热度,
      "capital_usage_pct": 资金使用百分比,
      "total_exposure_after": 总暴露金额
    }
  }
```

##### 2.5 止损止盈计算

```
止损 (calculate_stop_loss):
  方法1 - ATR基础:
    LONG: stop_loss = entry_price - (ATR × multiplier)
    SHORT: stop_loss = entry_price + (ATR × multiplier)
    默认 multiplier = 2.0
    
  方法2 - 百分比基础:
    LONG: stop_loss = entry_price × (1 - percentage)
    SHORT: stop_loss = entry_price × (1 + percentage)
    默认 percentage = 0.02 (2%)

止盈目标 (calculate_take_profit_targets):
  输入: 风险回报比列表 [2.0, 3.0, 4.0]
  
  对每个比率:
    risk = |entry_price - stop_loss|
    reward = risk × rr_ratio
    
    LONG: tp_price = entry_price + reward
    SHORT: tp_price = entry_price - reward
    
  输出: [
    {"price": TP1, "qty_pct": 50, "risk_reward_ratio": 2.0},
    {"price": TP2, "qty_pct": 30, "risk_reward_ratio": 3.0},
    {"price": TP3, "qty_pct": 20, "risk_reward_ratio": 4.0}
  ]
  
  策略: 分批止盈 (50% + 30% + 20%)
```

##### 2.6 保证金检查 (check_margin_requirements)

```
计算:
  total_notional = Σ(position.notional_value)
  total_margin_used = Σ(position.notional_value / position.leverage)
  margin_usage_pct = (total_margin_used / available_capital) × 100

级别:
  - > 80% → 警告
  - > 90% → 严重

输出:
  {
    "total_margin_used": 已使用保证金,
    "available_margin": 可用保证金,
    "margin_usage_pct": 使用百分比,
    "is_warning": 是否警告,
    "is_critical": 是否严重
  }
```

---

### 3. PortfolioManager (组合管理器)

**位置**: `python/valuecell/agents/tradingview_signal_agent/portfolio_manager.py`

**职责**:
- 协调 PositionManager 和 RiskManager
- 生成组合级别分析和报告
- 检查交易约束
- 保存组合快照

#### 主要方法

##### 3.1 获取组合摘要 (get_portfolio_summary)

```
处理流程:
  1. 获取所有开仓 (position_manager.get_open_positions())
  
  2. 计算资金:
     - total_position_value = Σ(position.notional_value)
     - available_capital = config.current_capital
     - total_capital = available_capital + total_position_value
     
  3. 计算盈亏:
     - unrealized_pnl = Σ(position.unrealized_pnl)
     - realized_pnl = position_manager.get_total_realized_pnl()
     - total_pnl = unrealized_pnl + realized_pnl
     
  4. 计算风险指标:
     - portfolio_heat = risk_manager.calculate_portfolio_heat(positions)
     - exposure_pct = (total_position_value / total_capital) × 100
     
  5. 获取绩效统计:
     - stats = performance_analytics.calculate_statistics()
     
  6. 构建 PortfolioSnapshot

输出: PortfolioSnapshot 对象
```

##### 3.2 检查能否开新仓 (can_open_new_position)

```
输入:
  - symbol: 交易标的
  - position_size_usd: 仓位大小(USD)

检查流程:
  1. 检查最大仓位数:
     if len(positions) >= max_concurrent_positions:
       return False, "达到最大仓位数"
       
  2. 检查单仓大小限制:
     max_size = current_capital × max_position_size_pct
     if position_size_usd > max_size:
       return False, "超过单仓限制"
       
  3. 检查可用资金:
     if position_size_usd > current_capital:
       return False, "资金不足"
       
  4. 检查总暴露:
     total_exposure = risk_manager.get_total_exposure(positions)
     new_exposure_pct = (total_exposure + position_size_usd) / 
                        (current_capital + total_exposure)
     if new_exposure_pct > max_total_exposure_pct:
       return False, "总暴露超限"
       
  5. 检查是否已有该标的仓位:
     if has_position(symbol) and not allow_pyramiding:
       return False, "已有仓位且不允许加仓"

输出: (bool, str) - (是否可以, 原因)
```

##### 3.3 更新所有仓位 (update_all_positions)

```
输入: current_prices (Dict[symbol, price])

流程:
  1. 调用 position_manager.update_positions(prices)
  2. 自动触发止损/止盈检查
  3. 更新所有未实现盈亏

用途: 定期更新（例如每分钟）
```

##### 3.4 检查所有失效条件 (check_all_invalidations)

```
输入: market_data (Dict[symbol, List[candles]])

流程:
  对每个持仓标的:
    1. 获取K线数据
    2. 调用 position_manager.check_invalidation_conditions
    3. 如果触发，自动平仓

用途: 技术失效监控
```

---

### 4. PerformanceAnalytics (绩效分析)

**位置**: `python/valuecell/agents/tradingview_signal_agent/performance_analytics.py`

**职责**:
- 计算交易统计
- 计算最大回撤
- 计算夏普比率
- 生成绩效报告

#### 主要指标

##### 4.1 交易统计 (calculate_statistics)

```
基础指标:
  - total_trades: 总交易次数
  - winning_trades: 盈利交易数
  - losing_trades: 亏损交易数
  - win_rate: 胜率 = winning / total

平均盈亏:
  - avg_win: 平均盈利 = Σ(win_pnl) / win_count
  - avg_loss: 平均亏损 = Σ(loss_pnl) / loss_count

极值:
  - largest_win: 最大单笔盈利
  - largest_loss: 最大单笔亏损

盈利因子:
  - total_wins = Σ(winning_pnl)
  - total_losses = Σ(losing_pnl)
  - profit_factor = total_wins / |total_losses|
  
  解释:
    > 1.0 → 系统盈利
    < 1.0 → 系统亏损
    > 2.0 → 优秀系统

时间指标:
  - avg_holding_time: 平均持仓时长(小时)
```

##### 4.2 最大回撤 (calculate_max_drawdown)

```
输入: equity_curve (List[float]) - 资金曲线

算法:
  peak = equity_curve[0]
  max_dd = 0
  max_dd_pct = 0
  
  for value in equity_curve:
    if value > peak:
      peak = value
    
    dd = peak - value
    dd_pct = (dd / peak) × 100
    
    if dd > max_dd:
      max_dd = dd
      max_dd_pct = dd_pct

输出: (max_dd, max_dd_pct)
  - max_dd: 最大回撤金额
  - max_dd_pct: 最大回撤百分比

解释: 从峰值到谷底的最大损失
```

##### 4.3 夏普比率 (calculate_sharpe_ratio)

```
输入:
  - returns: 收益率列表
  - risk_free_rate: 无风险利率 (默认 0.02)

计算:
  avg_return = mean(returns)
  std_return = stdev(returns)
  
  sharpe_ratio = (avg_return - risk_free_rate) / std_return

解释:
  > 1.0 → 可接受
  > 2.0 → 良好
  > 3.0 → 优秀

含义: 每单位风险的超额收益
```

---

### 5. PositionDatabase (数据持久化)

**位置**: `python/valuecell/agents/tradingview_signal_agent/position_database.py`

**数据库**: SQLite

#### 表结构

##### 5.1 trading_sessions (交易会话)

```sql
CREATE TABLE trading_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    initial_capital REAL NOT NULL,
    current_capital REAL NOT NULL,
    config_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
)
```

##### 5.2 positions (开仓)

```sql
CREATE TABLE positions (
    position_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    leverage INTEGER NOT NULL,
    profit_target REAL NOT NULL,
    stop_loss_price REAL NOT NULL,
    invalidation_condition TEXT NOT NULL,
    risk_usd REAL NOT NULL,
    confidence REAL NOT NULL,
    take_profit_targets TEXT,
    funding_rate REAL,
    opened_at TIMESTAMP NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'open',
    FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
)

-- 索引
CREATE INDEX idx_positions_session_symbol ON positions(session_id, symbol);
CREATE INDEX idx_positions_status ON positions(status);
```

##### 5.3 closed_positions (平仓)

```sql
CREATE TABLE closed_positions (
    position_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    realized_pnl_pct REAL NOT NULL,
    opened_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP NOT NULL,
    holding_duration REAL NOT NULL,
    exit_reason TEXT NOT NULL,
    exit_signal_id TEXT,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
)

-- 索引
CREATE INDEX idx_closed_positions_session 
ON closed_positions(session_id, closed_at DESC);
```

##### 5.4 portfolio_snapshots (组合快照)

```sql
CREATE TABLE portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    total_capital REAL NOT NULL,
    available_capital REAL NOT NULL,
    unrealized_pnl REAL NOT NULL,
    realized_pnl REAL NOT NULL,
    total_pnl REAL NOT NULL,
    total_return_pct REAL NOT NULL,
    snapshot_json TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id),
    UNIQUE(session_id, timestamp)
)

-- 索引
CREATE INDEX idx_snapshots_session_time 
ON portfolio_snapshots(session_id, timestamp DESC);
```

##### 5.5 trade_records (交易记录)

```sql
CREATE TABLE trade_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    position_id TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    action TEXT NOT NULL,          -- OPEN, CLOSE, ADD, REDUCE
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity REAL NOT NULL,
    price REAL NOT NULL,
    pnl REAL,
    record_json TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
)
```

##### 5.6 recommendations (推荐)

```sql
CREATE TABLE recommendations (
    recommendation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    operation TEXT NOT NULL,       -- OPEN, CLOSE, ADD, HOLD
    confidence REAL NOT NULL,
    recommendation_json TEXT NOT NULL,
    executed BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(session_id)
)
```

#### 主要操作

```
Session:
  - save_session()
  - get_session()

Position:
  - save_position()
  - update_position()
  - save_closed_position()
  - get_closed_positions()

Snapshot:
  - save_snapshot()
  - get_snapshots()

Trade:
  - save_trade_record()

Recommendation:
  - save_recommendation()
```

---

## 完整数据流

### 1. 开仓流程

```
1. TradingView Signal → DecisionEngine
   - 接收交易信号
   - 分析市场条件
   - 生成交易决策

2. DecisionEngine → PortfolioManager.can_open_new_position()
   - 检查是否可以开新仓
   - 检查各项限制

3. PortfolioManager → RiskManager.calculate_position_size()
   - 计算推荐仓位大小
   - 根据风险参数计算数量

4. PortfolioManager → RiskManager.assess_trade_risk()
   - 评估交易风险
   - 检查风险指标

5. 如果通过所有检查 → PositionManager.open_position()
   a. 创建 Position 对象
   b. 计算仓位指标
   c. 更新可用资金
   d. 保存到 positions 字典
   e. 记录交易历史
   f. 保存到数据库

6. PositionDatabase.save_position()
   - 持久化到 SQLite

7. 返回成功 → 通知用户/前端
```

### 2. 仓位监控流程

```
定时任务 (例如每分钟):

1. 获取当前价格
   - 从交易所/数据源获取实时价格

2. PortfolioManager.update_all_positions(prices)
   ↓
   PositionManager.update_positions(prices)
   
   对每个仓位:
     a. 更新 current_price
     b. 计算 unrealized_pnl
     c. 检查止损条件
     d. 检查止盈条件
     e. 如果触发 → 自动平仓

3. PortfolioManager.check_all_invalidations(market_data)
   ↓
   PositionManager.check_invalidation_conditions()
   
   对每个仓位:
     a. 获取最近K线数据
     b. 检查失效条件
     c. 如果触发 → 自动平仓

4. 生成组合快照
   PortfolioManager.get_portfolio_summary()
   ↓
   PortfolioManager.save_snapshot()
   - 保存当前状态到历史记录
```

### 3. 平仓流程

```
触发条件:
  - 止损触发
  - 止盈触发
  - 失效条件触发
  - 反向信号
  - 手动平仓

流程:

1. 触发平仓 → PositionManager.close_position()
   a. 查找仓位
   b. 获取当前价格
   c. 计算已实现盈亏
   d. 创建 ClosedPosition 对象
   e. 更新可用资金（返还保证金 + 盈亏）
   f. 从 positions 移除
   g. 添加到 closed_positions
   h. 记录交易历史

2. PositionDatabase.save_closed_position()
   - 保存到 closed_positions 表
   - 更新 positions 表状态为 'closed'

3. PerformanceAnalytics.add_closed_position()
   - 更新绩效统计

4. 生成组合快照
   - 更新组合状态

5. 通知用户/前端
```

### 4. 加仓/减仓流程

```
加仓 (Pyramiding):
  前提: allow_pyramiding = True
  
  1. 检查权限
  2. PositionManager.add_to_position()
     - 计算新的平均入场价
     - 更新数量和价值
     - 扣除额外保证金
  3. 保存更新

减仓 (Partial Close):
  1. PositionManager.reduce_position()
     - 计算部分盈亏
     - 更新剩余仓位
     - 返还部分保证金
  2. 保存更新
```

---

## 风险控制机制

### 1. 资金管理

```
层级1 - 单笔交易风险:
  - 默认每笔交易风险 2% 的资金
  - risk_amount = total_capital × risk_per_trade_pct

层级2 - 单仓大小限制:
  - 默认单仓不超过总资金 20%
  - max_position_size = total_capital × max_position_size_pct

层级3 - 总暴露限制:
  - 默认总仓位不超过总资金 60%
  - max_exposure = total_capital × max_total_exposure_pct

层级4 - 并发仓位数:
  - 默认最多 5 个并发仓位
  - max_concurrent_positions = 5
```

### 2. 组合热度监控

```
Portfolio Heat = Σ(position_risk) / total_capital

含义: 总资金的风险暴露百分比

警戒级别:
  - < 5%: 安全
  - 5-10%: 正常
  - 10-15%: 警告
  - > 15%: 危险
```

### 3. 保证金管理

```
保证金计算:
  margin_required = notional_value / leverage

保证金监控:
  - 80% 使用率 → 警告
  - 90% 使用率 → 严重警告
  - 100% → 拒绝新仓位
```

### 4. 止损机制

```
硬止损 (Hard Stop):
  - 价格触及止损价格 → 立即平仓
  - 由 update_positions() 自动检查

技术失效止损:
  - 失效条件触发 → 立即平仓
  - 例如: 关键支撑位跌破

时间止损:
  - 可设置最大持仓时长
  - 超时自动平仓
```

---

## 绩效评估

### 关键指标

```
盈利能力:
  - Total P&L: 总盈亏
  - Total Return %: 总回报率
  - Profit Factor: 盈利因子 (>2.0 优秀)
  - Win Rate: 胜率

风险控制:
  - Max Drawdown: 最大回撤
  - Max Drawdown %: 最大回撤百分比
  - Sharpe Ratio: 夏普比率 (>2.0 良好)
  - Portfolio Heat: 组合热度

效率:
  - Avg Win: 平均盈利
  - Avg Loss: 平均亏损
  - Avg Win/Loss Ratio: 盈亏比
  - Avg Holding Time: 平均持仓时长

一致性:
  - Winning Streak: 连胜记录
  - Losing Streak: 连亏记录
  - Consistency Score: 一致性评分
```

### 报告生成

```
日报:
  - 当日交易汇总
  - 盈亏统计
  - 当前持仓

周报:
  - 周度绩效
  - 最佳/最差交易
  - 风险分析

月报:
  - 月度总结
  - 策略表现
  - 改进建议
```

---

## Auto Trading Agent 差异

**位置**: `python/valuecell/agents/auto_trading_agent/position_manager.py`

### 主要差异

```
1. 资金管理:
   - 使用 CashManagement 模型
   - 区分 available_cash 和 cash_in_trades
   - 更简单的现金流跟踪

2. 仓位模型:
   - 使用 TradeType (LONG/SHORT)
   - 不使用杠杆
   - 简化的 P&L 计算

3. 方法:
   - allocate_cash(): 分配资金
   - release_cash(): 释放资金
   - snapshot_positions(): 定期快照
   - snapshot_portfolio(): 组合快照

4. 特点:
   - 更适合股票交易
   - 不支持杠杆
   - 更简单的风险模型
```

---

## API 端点

### 服务端 API

**位置**: `python/valuecell/server/`

```
GET /api/portfolio/summary
  - 获取组合摘要

GET /api/portfolio/positions
  - 获取所有开仓

GET /api/portfolio/closed-positions
  - 获取历史平仓

GET /api/portfolio/snapshots
  - 获取历史快照

POST /api/portfolio/position/open
  - 开仓

POST /api/portfolio/position/close
  - 平仓

POST /api/portfolio/position/update
  - 更新仓位

GET /api/performance/statistics
  - 获取绩效统计

GET /api/risk/assessment
  - 风险评估
```

---

## 最佳实践

### 1. 开仓前检查

```python
# 1. 检查能否开仓
can_open, reason = await portfolio_manager.can_open_new_position(
    symbol=symbol,
    position_size_usd=position_size
)

if not can_open:
    logger.warning(f"Cannot open position: {reason}")
    return

# 2. 计算仓位大小
sizing = risk_manager.calculate_position_size(
    symbol=symbol,
    entry_price=entry_price,
    stop_loss_price=stop_loss,
    available_capital=config.current_capital,
    confidence=confidence
)

# 3. 评估风险
risk_assessment = risk_manager.assess_trade_risk(
    symbol=symbol,
    action=OperationType.OPEN,
    quantity=sizing["quantity"],
    entry_price=entry_price,
    stop_loss=stop_loss,
    current_positions=portfolio_manager.position_manager.get_open_positions(),
    available_capital=config.current_capital
)

if not risk_assessment["is_acceptable"]:
    logger.warning(f"Trade risk not acceptable: {risk_assessment['risks']}")
    return

# 4. 开仓
position = await position_manager.open_position(
    symbol=symbol,
    side=side,
    quantity=sizing["quantity"],
    entry_price=entry_price,
    profit_target=profit_target,
    stop_loss=stop_loss,
    invalidation_condition=invalidation,
    leverage=sizing["recommended_leverage"],
    confidence=confidence,
    risk_usd=sizing["actual_risk_amount"]
)
```

### 2. 定期监控

```python
import asyncio

async def monitor_positions():
    """定期监控仓位"""
    while True:
        # 1. 获取当前价格
        prices = await get_current_prices()
        
        # 2. 更新所有仓位
        await portfolio_manager.update_all_positions(prices)
        
        # 3. 检查失效条件
        market_data = await get_market_data()
        await portfolio_manager.check_all_invalidations(market_data)
        
        # 4. 生成快照
        await portfolio_manager.save_snapshot()
        
        # 5. 检查保证金
        margin_status = portfolio_manager.get_margin_status()
        if margin_status["is_critical"]:
            logger.error("Critical margin level!")
            # 采取行动
        
        # 等待下一次检查
        await asyncio.sleep(60)  # 每分钟检查一次
```

### 3. 平仓策略

```python
async def check_exit_conditions(position: Position, current_price: float):
    """检查退出条件"""
    
    # 1. 止损
    if position.side == PositionSide.LONG and current_price <= position.stop_loss_price:
        await position_manager.close_position(position.symbol, current_price, "stop_loss")
        return
    
    # 2. 止盈
    if position.side == PositionSide.LONG and current_price >= position.profit_target:
        await position_manager.close_position(position.symbol, current_price, "take_profit")
        return
    
    # 3. 分批止盈
    for tp_target in position.take_profit_targets:
        if current_price >= tp_target["price"] and not tp_target.get("executed"):
            reduce_qty = position.quantity * (tp_target["qty_pct"] / 100)
            await position_manager.reduce_position(
                symbol=position.symbol,
                reduce_quantity=reduce_qty,
                exit_price=current_price,
                reason="partial_profit"
            )
            tp_target["executed"] = True
    
    # 4. 时间止损
    holding_hours = (datetime.now() - position.opened_at).total_seconds() / 3600
    if holding_hours > MAX_HOLDING_HOURS:
        await position_manager.close_position(position.symbol, current_price, "time_stop")
```

### 4. 组合再平衡

```python
async def rebalance_portfolio():
    """组合再平衡"""
    positions = portfolio_manager.position_manager.get_open_positions()
    
    # 计算每个仓位的暴露
    total_value = sum(p.notional_value for p in positions)
    
    for position in positions:
        exposure_pct = position.notional_value / total_value
        
        # 如果某个仓位占比过大
        if exposure_pct > 0.30:  # 超过30%
            # 减仓到目标比例
            target_value = total_value * 0.25
            reduce_value = position.notional_value - target_value
            reduce_qty = reduce_value / position.current_price
            
            await position_manager.reduce_position(
                symbol=position.symbol,
                reduce_quantity=reduce_qty,
                exit_price=position.current_price,
                reason="rebalance"
            )
```

---

## 配置示例

### 保守配置

```python
conservative_config = TradingSessionConfig(
    session_id="conservative_001",
    initial_capital=10000.0,
    current_capital=10000.0,
    
    # 风险参数 - 保守
    max_position_size_pct=0.10,          # 单仓最大10%
    max_total_exposure_pct=0.40,         # 总暴露40%
    max_concurrent_positions=3,           # 最多3个仓位
    risk_per_trade_pct=0.01,             # 单笔风险1%
    
    # 交易规则
    allow_pyramiding=False,
    allow_hedging=False,
    max_leverage=5,
    default_leverage=2,
    leverage_by_confidence={
        "high": 5,
        "medium": 3,
        "low": 2
    }
)
```

### 激进配置

```python
aggressive_config = TradingSessionConfig(
    session_id="aggressive_001",
    initial_capital=10000.0,
    current_capital=10000.0,
    
    # 风险参数 - 激进
    max_position_size_pct=0.30,          # 单仓最大30%
    max_total_exposure_pct=0.80,         # 总暴露80%
    max_concurrent_positions=8,           # 最多8个仓位
    risk_per_trade_pct=0.03,             # 单笔风险3%
    
    # 交易规则
    allow_pyramiding=True,
    allow_hedging=True,
    max_leverage=20,
    default_leverage=10,
    leverage_by_confidence={
        "high": 20,
        "medium": 10,
        "low": 5
    }
)
```

---

## 总结

### 核心优势

1. **多层风险控制**
   - 单笔风险限制
   - 单仓大小限制
   - 总暴露限制
   - 组合热度监控

2. **自动化管理**
   - 自动止损止盈
   - 自动失效检查
   - 自动仓位更新
   - 自动快照保存

3. **完整记录**
   - 所有交易记录
   - 仓位历史
   - 组合快照
   - 绩效统计

4. **灵活配置**
   - 可调整风险参数
   - 多种交易模式
   - 自定义策略

### 改进方向

1. **实时性能**
   - WebSocket 实时价格推送
   - 事件驱动架构
   - 异步处理优化

2. **高级功能**
   - 期权仓位管理
   - 多账户管理
   - 智能路由
   - 算法执行

3. **分析增强**
   - 归因分析
   - 因子暴露分析
   - 压力测试
   - 情景分析

4. **UI/UX**
   - 实时仪表盘
   - 交互式图表
   - 移动端支持
   - 警报通知

---

## 相关文件

### Python Backend

```
python/valuecell/agents/tradingview_signal_agent/
  ├── position_manager.py          # 仓位管理器
  ├── portfolio_manager.py         # 组合管理器
  ├── risk_manager.py              # 风险管理器
  ├── performance_analytics.py     # 绩效分析
  ├── position_database.py         # 数据库
  ├── models.py                    # 数据模型
  ├── decision_engine.py           # 决策引擎
  └── agent.py                     # 主代理

python/valuecell/agents/auto_trading_agent/
  ├── position_manager.py          # 简化版仓位管理
  ├── trading_executor.py          # 交易执行
  └── models.py                    # 数据模型

python/valuecell/server/
  └── routes/                      # API路由
```

### Database

```
valuecell.db                       # 主数据库
tradingview_signal_agent.db        # 信号代理数据库
```

---

*最后更新: 2025-10-27*
*版本: 1.0*

