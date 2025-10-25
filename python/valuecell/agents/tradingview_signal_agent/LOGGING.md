# TradingView Signal Agent - Logging Documentation

## 📋 概述

TradingView Signal Agent使用完善的分层日志系统，提供详细的运行时信息、错误追踪和性能监控。

## 🏗️ 日志架构

### 日志级别

- **DEBUG**: 详细的调试信息（开发模式）
- **INFO**: 一般运行信息（默认）
- **WARNING**: 警告信息
- **ERROR**: 错误信息
- **CRITICAL**: 严重错误

### 日志输出

1. **控制台输出** - 实时查看运行状态
2. **文件输出** - 持久化存储，方便事后分析
   - `tradingview_agent.log` - 所有日志（INFO及以上）
   - `tradingview_error.log` - 仅错误日志（ERROR及以上）

### 日志目录结构

```
logs/
└── 20251023205830/          # 时间戳目录 (YYYYMMDDHHmmss)
    ├── tradingview_agent.log
    └── tradingview_error.log
```

## 🚀 使用方法

### 启动Agent

```bash
# 启动agent (自动配置日志)
python -m valuecell.agents.tradingview_signal_agent

# 或使用启动脚本
./scripts/start_tradingview_agent.sh
```

### 启动Webhook服务

```bash
# 启动webhook服务 (独立日志)
python -m valuecell.agents.tradingview_signal_agent.webhook_service

# 或使用启动脚本
./scripts/start_tradingview_webhook.sh
```

## 📊 日志内容示例

### Agent启动日志

```
2025-10-23 20:58:30 - INFO - ================================================================================
2025-10-23 20:58:30 - INFO - TradingView Signal Agent - Logging Initialized
2025-10-23 20:58:30 - INFO - Log directory: /Users/Doc/code/RSTValueCell/valuecell/logs/20251023205830
2025-10-23 20:58:30 - INFO - Agent log: /path/to/tradingview_agent.log
2025-10-23 20:58:30 - INFO - Error log: /path/to/tradingview_error.log
2025-10-23 20:58:30 - INFO - Log level: INFO
2025-10-23 20:58:30 - INFO - ================================================================================
```

### 交易决策日志

```
2025-10-23 21:00:15 - valuecell.agents.tradingview_signal_agent.agent - INFO - [agent.py:156] - Processing analyze request for BTCUSDT
2025-10-23 21:00:15 - valuecell.agents.tradingview_signal_agent.technical_analyzer - INFO - [technical_analyzer.py:45] - Analyzing MACD: bullish crossover detected
2025-10-23 21:00:15 - valuecell.agents.tradingview_signal_agent.decision_engine - INFO - [decision_engine.py:89] - Starting COT decision making for 1 symbols
2025-10-23 21:00:16 - valuecell.agents.tradingview_signal_agent.position_manager - INFO - [position_manager.py:123] - Opening new position: BTCUSDT LONG, quantity=0.12
```

### Webhook接收日志

```
2025-10-23 21:00:00 - valuecell.agents.tradingview_signal_agent.webhook_service - INFO - [webhook_service.py:67] - Received webhook from TradingView for BTCUSDT
2025-10-23 21:00:00 - valuecell.agents.tradingview_signal_agent.indicator_store - INFO - [indicator_store.py:45] - Saved indicator data for BTCUSDT at 2025-10-23 21:00:00
```

### 错误日志

```
2025-10-23 21:05:30 - valuecell.agents.tradingview_signal_agent.decision_engine - ERROR - [decision_engine.py:234] - Failed to parse COT response: Invalid JSON
Traceback (most recent call last):
  File "/path/to/decision_engine.py", line 234, in _parse_cot_to_decisions
    decisions = json.loads(response)
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

## 🔧 配置选项

### 环境变量

```bash
# 设置日志级别
export TRADINGVIEW_LOG_LEVEL=DEBUG

# 设置日志目录
export TRADINGVIEW_LOG_DIR=/custom/log/path
```

### 代码配置

```python
from valuecell.agents.tradingview_signal_agent.logging_config import setup_logging, set_debug_mode

# 自定义日志配置
setup_logging(
    log_dir="custom_logs",
    log_level=logging.DEBUG,
    max_bytes=20 * 1024 * 1024,  # 20MB
    backup_count=10
)

# 启用调试模式
set_debug_mode()
```

## 📂 模块级日志

每个模块都有独立的logger，方便追踪问题：

| 模块 | Logger名称 |
|-----|-----------|
| Agent主模块 | `agent` |
| 决策引擎 | `decision_engine` |
| 仓位管理 | `position_manager` |
| 投资组合管理 | `portfolio_manager` |
| 风险管理 | `risk_manager` |
| 技术分析 | `technical_analyzer` |
| 性能分析 | `performance_analytics` |
| 指标存储 | `indicator_store` |
| 数据库 | `position_database` |
| Webhook服务 | `webhook_service` |

## 🔍 日志查询

### 查看最新日志

```bash
# 查看最新的agent日志
tail -f logs/$(ls -t logs | head -1)/tradingview_agent.log

# 查看最新的错误日志
tail -f logs/$(ls -t logs | head -1)/tradingview_error.log
```

### 搜索特定交易

```bash
# 搜索BTCUSDT相关日志
grep "BTCUSDT" logs/20251023205830/tradingview_agent.log

# 搜索错误
grep "ERROR" logs/20251023205830/tradingview_agent.log

# 搜索特定仓位
grep "position_id=abc123" logs/20251023205830/tradingview_agent.log
```

### 分析交易决策流程

```bash
# 查看完整的决策过程
grep -A 10 "Starting COT decision" logs/20251023205830/tradingview_agent.log

# 查看开仓记录
grep "Opening new position" logs/20251023205830/tradingview_agent.log

# 查看平仓记录
grep "Closing position" logs/20251023205830/tradingview_agent.log
```

## 🐛 故障排查

### 常见问题

1. **日志文件过大**
   - 调整 `max_bytes` 参数
   - 增加 `backup_count` 自动轮换

2. **日志级别太高/太低**
   ```python
   # 临时调整日志级别
   import logging
   logging.getLogger('valuecell.agents.tradingview_signal_agent').setLevel(logging.DEBUG)
   ```

3. **查找特定错误**
   ```bash
   # 按时间排序错误
   grep "ERROR" logs/*/tradingview_error.log | sort
   
   # 统计错误类型
   grep "ERROR" logs/*/tradingview_error.log | cut -d':' -f4 | sort | uniq -c
   ```

## 📈 性能监控

### 关键指标日志

```bash
# 交易执行时间
grep "execution_time" logs/20251023205830/tradingview_agent.log

# API调用延迟
grep "api_latency" logs/20251023205830/tradingview_agent.log

# 决策引擎响应时间
grep "COT decision took" logs/20251023205830/tradingview_agent.log
```

## 🔒 生产环境配置

### 推荐设置

```python
# 生产环境配置
from valuecell.agents.tradingview_signal_agent.logging_config import setup_logging, set_production_mode

setup_logging(
    log_dir="/var/log/tradingview_agent",
    log_level=logging.WARNING,  # 只记录警告和错误
    max_bytes=50 * 1024 * 1024,  # 50MB
    backup_count=20  # 保留20个备份文件
)

set_production_mode()
```

### 日志轮换

```bash
# 使用logrotate管理日志
cat > /etc/logrotate.d/tradingview-agent <<EOF
/var/log/tradingview_agent/*/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    missingok
}
EOF
```

## 📚 最佳实践

1. **定期检查日志** - 每天检查error日志
2. **监控磁盘空间** - 确保日志目录有足够空间
3. **备份重要日志** - 定期备份到远程存储
4. **设置告警** - 监控ERROR和CRITICAL日志，及时通知
5. **分析交易行为** - 定期分析决策日志，优化策略

## 🆘 支持

如果遇到日志相关问题，请提供：
- 完整的错误日志
- 时间戳
- 日志目录路径
- Agent版本信息


