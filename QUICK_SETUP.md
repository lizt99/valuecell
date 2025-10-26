# 🚀 快速配置 Svix API 凭证

**最快的方式启动数据采集！**

---

## ⚡ 方法1: 使用自动配置脚本（推荐）

### 运行配置向导
```bash
cd /Users/Doc/code/RSTValueCell/valuecell
./setup_svix_credentials.sh
```

**配置向导会**:
- ✅ 引导您输入API凭证
- ✅ 自动创建 .env 文件
- ✅ 测试API连接
- ✅ 显示下一步操作

---

## ⚡ 方法2: 一键设置（使用您之前提供的凭证）

### 直接运行以下命令:
```bash
cd /Users/Doc/code/RSTValueCell/valuecell

# 设置环境变量
export SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"  # ⚠️ 如果这是占位符，请替换

# 验证
echo "✓ Token: ${SVIX_API_TOKEN:0:20}..."
echo "✓ Consumer ID: $SVIX_CONSUMER_ID"

# 测试API
curl -s -X GET \
  "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/$SVIX_CONSUMER_ID" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer $SVIX_API_TOKEN" | head -20

# 如果成功，启动服务
./scripts/start_tradingview_polling.sh
```

---

## ⚡ 方法3: 创建 .env 文件

### 一条命令创建配置:
```bash
cd /Users/Doc/code/RSTValueCell/valuecell

cat > .env << 'EOF'
# Svix API 凭证
SVIX_API_TOKEN=sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us
SVIX_CONSUMER_ID=MY_CONSUMER_ID
EOF

# 保护文件权限
chmod 600 .env

# 查看
cat .env
```

⚠️ **重要**: 如果 `MY_CONSUMER_ID` 是占位符，请编辑 .env 替换为实际ID:
```bash
nano .env
# 或
vim .env
# 或
code .env
```

---

## ✅ 验证配置

### 检查环境变量:
```bash
printenv | grep SVIX
```

**应该看到**:
```
SVIX_API_TOKEN=sk_poll_...
SVIX_CONSUMER_ID=...
```

### 测试API连接:
```bash
curl -X GET \
  "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/$SVIX_CONSUMER_ID" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer $SVIX_API_TOKEN"
```

**成功响应** (HTTP 200):
```json
{
  "iterator": "...",
  "data": [...],
  "done": false
}
```

**失败响应**:
- HTTP 401: Token 无效
- HTTP 404: Consumer ID 不存在

---

## 🚀 启动数据采集

### 配置成功后，启动服务:
```bash
cd /Users/Doc/code/RSTValueCell/valuecell

# 方式1: 使用启动脚本
./scripts/start_tradingview_polling.sh

# 方式2: 后台运行
nohup ./scripts/start_tradingview_polling.sh > logs/polling.log 2>&1 &

# 方式3: 直接运行
cd python
python3 -m valuecell.agents.tradingview_signal_agent.polling_service
```

### 监控数据采集:
```bash
# 查看日志
tail -f logs/polling_service.log

# 监控数据库
watch -n 60 "sqlite3 python/tradingview_indicators.db 'SELECT COUNT(*) FROM indicator_data'"

# 查看最新数据
sqlite3 python/tradingview_indicators.db "
SELECT symbol, datetime(timestamp), price, rsi14 
FROM indicator_data 
ORDER BY timestamp DESC 
LIMIT 10;"
```

---

## 🔍 常见问题

### Q1: MY_CONSUMER_ID 是什么？

**A**: 这是一个占位符。您需要：
1. 登录 Svix 控制台
2. 查找您的 Consumer ID
3. 替换配置中的 `MY_CONSUMER_ID`

或者，如果您的API调用中已经包含实际ID，请使用那个。

### Q2: 如何获取实际的 Consumer ID？

**A**: 检查您的 Svix 控制台或 API 文档。通常格式类似：
- `consumer_abc123`
- `usr_xxxxxxxxxxxx`
- 或其他Svix分配的唯一标识符

### Q3: Token 过期了怎么办？

**A**: 重新生成 token 后，更新配置：
```bash
# 更新 .env
nano .env

# 或重新 export
export SVIX_API_TOKEN="new-token"

# 重启服务
pkill -f polling_service
./scripts/start_tradingview_polling.sh
```

### Q4: 如何确认数据正在采集？

**A**: 
```bash
# 1. 检查进程
ps aux | grep polling_service

# 2. 查看日志
tail -20 logs/polling_service.log
# 应该看到: "Fetching data from last 3 minutes..."

# 3. 检查数据库
sqlite3 python/tradingview_indicators.db "
SELECT COUNT(*), MAX(datetime(timestamp)) as latest 
FROM indicator_data;"
# 数量应该每3分钟增加
```

---

## 📞 需要帮助？

1. **查看详细文档**:
   ```bash
   cat SETUP_SVIX_CREDENTIALS.md
   ```

2. **运行诊断**:
   ```bash
   cd python
   python3 diagnose_and_test_phase1.py
   ```

3. **检查 Phase 1 状态**:
   ```bash
   cat valuecell/agents/tradingview_signal_agent/PHASE1_DIAGNOSTIC_REPORT.md
   ```

---

## ✅ 完成清单

配置完成后，确认：

- [ ] ✅ 环境变量已设置 (`printenv | grep SVIX`)
- [ ] ✅ API测试成功 (HTTP 200)
- [ ] ✅ 轮询服务已启动 (`ps aux | grep polling`)
- [ ] ✅ 日志显示正常 (`tail logs/polling_service.log`)
- [ ] ✅ 数据开始采集 (数据库记录增加)

**全部完成？恭喜！Phase 1 数据采集已正常运行！** 🎉

