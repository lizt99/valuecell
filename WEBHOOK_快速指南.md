# TradingView Webhook 快速指南

## 🚀 快速验证

运行自动化验证脚本：
```bash
./scripts/verify_tradingview_webhook.sh
```

所有测试通过 ✅ 表示服务运行正常！

---

## 📋 服务状态

| 服务 | 端口 | 状态 |
|------|------|------|
| Webhook服务 | 8001 | ✅ 运行中 |
| Signal Agent | 10005 | ✅ 运行中 |
| Backend API | 8000 | ✅ 运行中 |

---

## 🔌 API端点

### 1. 健康检查
```bash
curl http://localhost:8001/health
```

### 2. 接收Webhook
```bash
curl -X POST http://localhost:8001/api/webhook/tradingview \
  -H "Content-Type: application/json" \
  -d @webhook_payload.json
```

### 3. 查询指标数据
```bash
curl "http://localhost:8001/api/indicators/BTCUSDT?limit=10"
```

---

## 📊 Webhook数据格式

```json
{
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-24T15:20:00Z",
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
}
```

---

## ⚙️ 服务管理

### 启动服务
```bash
./scripts/start_tradingview_webhook.sh
```

### 检查服务状态
```bash
# 查看进程
ps aux | grep webhook_service

# 查看端口
lsof -i :8001

# 查看日志
tail -f logs/webhook_service.log
```

### 停止服务
```bash
pkill -f webhook_service
```

---

## 🔐 安全配置

### 设置Webhook密钥（推荐）
```bash
export TRADINGVIEW_WEBHOOK_SECRET="your-secure-secret-key"
```

### 配置端口（可选）
```bash
export WEBHOOK_PORT=8001
export WEBHOOK_HOST=0.0.0.0
```

---

## 📈 TradingView配置

### 1. Webhook URL
```
http://your-server-ip:8001/api/webhook/tradingview
```

### 2. Alert消息模板
```javascript
{
  "symbol": "{{ticker}}",
  "timestamp": "{{time}}",
  "timeframe": "{{interval}}",
  "price": {{close}},
  "open": {{open}},
  "high": {{high}},
  "low": {{low}},
  "close": {{close}},
  "volume": {{volume}},
  "macd": {
    "macd_line": {{plot("MACD")}},
    "signal_line": {{plot("Signal")}},
    "histogram": {{plot("Histogram")}}
  },
  "rsi": {
    "value": {{plot("RSI")}}
  }
}
```

### 3. TradingView设置步骤
1. 创建Alert
2. 选择"Webhook URL"
3. 填入上述URL
4. 粘贴消息模板
5. 保存并激活

---

## 🗄️ 数据库

### 查看数据
```bash
sqlite3 python/tradingview_indicators.db \
  "SELECT * FROM indicator_data ORDER BY timestamp DESC LIMIT 10;"
```

### 统计信息
```bash
sqlite3 python/tradingview_indicators.db \
  "SELECT symbol, COUNT(*) as count FROM indicator_data GROUP BY symbol;"
```

### 清理旧数据（保留最近1000条）
```bash
sqlite3 python/tradingview_indicators.db \
  "DELETE FROM indicator_data WHERE id NOT IN (SELECT id FROM indicator_data ORDER BY timestamp DESC LIMIT 1000);"
```

---

## 🐛 故障排查

### 问题1: 端口被占用
```bash
# 查找并终止占用进程
lsof -i :8001
kill -9 <PID>
```

### 问题2: Webhook接收失败
1. 检查服务是否运行: `lsof -i :8001`
2. 查看日志: `tail -f logs/webhook_service.log`
3. 验证数据格式是否正确

### 问题3: 数据未保存
1. 检查数据库文件: `ls -lh python/tradingview_indicators.db`
2. 查看数据库日志
3. 验证时间周期是否匹配（默认查询15m）

---

## 📝 验证结果

### 最近验证时间
2025-10-24 15:10:00

### 验证结果
- ✅ 健康检查端点
- ✅ Webhook接收功能
- ✅ 数据持久化
- ✅ 查询API
- ✅ 数据库完整性
- ✅ Agent连接

### 测试数据
- BTCUSDT: 1条记录
- ETHUSDT: 1条记录
- 总计: 3条记录

---

## 📚 相关文档

- 完整验证报告: `WEBHOOK_SERVICE_VERIFICATION.md`
- Agent设置指南: `docs/TRADINGVIEW_AGENT_SETUP.md`
- 日志配置: `python/valuecell/agents/tradingview_signal_agent/LOGGING.md`
- 数据库设置: `python/valuecell/agents/tradingview_signal_agent/DATABASE_AND_LOGGING_SETUP.md`

---

## 💡 性能优化建议

### 1. 生产环境
- 使用Nginx反向代理
- 启用HTTPS/SSL
- 配置速率限制
- 设置IP白名单

### 2. 监控
- 配置Prometheus指标
- 设置告警规则
- 启用日志聚合

### 3. 高可用
- 配置systemd自动重启
- 定期数据库备份
- 实现故障转移

---

## ✅ 验证清单

- [x] Webhook服务运行正常
- [x] 健康检查端点可访问
- [x] Webhook接收功能正常
- [x] 数据正确保存到数据库
- [x] 查询API返回正确数据
- [x] Signal Agent连接正常

**状态: 所有功能正常 ✅**

---

**更新时间**: 2025-10-24  
**版本**: 1.0


