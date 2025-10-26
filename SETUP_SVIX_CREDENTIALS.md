# 设置 Svix API 凭证指南

**目的**: 配置Svix API凭证以启用数据采集

---

## 📋 所需信息

根据您提供的API调用信息，需要以下凭证：

### 1. API Token
```
sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us
```

### 2. Consumer ID
```
MY_CONSUMER_ID
```
⚠️ **注意**: 如果这是占位符，请替换为您的实际Consumer ID

### 3. API URL（已在代码中配置）
```
https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6
```

---

## 🔧 配置方法

### 方法1: 使用 .env 文件（推荐）

#### 步骤1: 创建或编辑 .env 文件
```bash
cd /Users/Doc/code/RSTValueCell/valuecell
nano .env
# 或使用其他编辑器
# vim .env
# code .env
```

#### 步骤2: 添加以下内容
```bash
# Svix API 凭证
SVIX_API_TOKEN=sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us
SVIX_CONSUMER_ID=MY_CONSUMER_ID

# 可选：覆盖默认API URL
# SVIX_API_URL=https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6
```

⚠️ **重要**: 
- 如果 `MY_CONSUMER_ID` 是占位符，请替换为实际的Consumer ID
- 保存文件后确保没有多余的空格

#### 步骤3: 验证 .env 文件
```bash
cat .env | grep SVIX
```

应该看到：
```
SVIX_API_TOKEN=sk_poll_...
SVIX_CONSUMER_ID=MY_CONSUMER_ID
```

---

### 方法2: 直接 export（临时，当前会话）

```bash
# 在终端中直接设置
export SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"

# 验证
echo $SVIX_API_TOKEN
echo $SVIX_CONSUMER_ID
```

⚠️ **注意**: 此方法只在当前终端会话有效，关闭终端后失效

---

### 方法3: 添加到 shell 配置文件（永久）

#### 对于 zsh (macOS 默认):
```bash
# 编辑 ~/.zshrc
nano ~/.zshrc

# 添加以下内容
export SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"

# 保存后重新加载
source ~/.zshrc
```

#### 对于 bash:
```bash
# 编辑 ~/.bashrc 或 ~/.bash_profile
nano ~/.bashrc

# 添加同样的内容
export SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"

# 重新加载
source ~/.bashrc
```

---

## ✅ 验证配置

### 步骤1: 检查环境变量
```bash
# 检查是否设置
printenv | grep SVIX

# 或分别检查
echo "Token: $SVIX_API_TOKEN"
echo "Consumer ID: $SVIX_CONSUMER_ID"
```

**预期输出**:
```
SVIX_API_TOKEN=sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us
SVIX_CONSUMER_ID=MY_CONSUMER_ID
```

### 步骤2: 测试 API 连接
```bash
# 手动测试API调用
curl -X GET \
  "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/$SVIX_CONSUMER_ID" \
  -H 'Accept: application/json' \
  -H "Authorization: Bearer $SVIX_API_TOKEN"
```

**成功响应示例**:
```json
{
  "iterator": "eyJvZmZzZXQiOi05MjIzMzc",
  "data": [...],
  "done": false
}
```

**错误响应示例**:
```json
{
  "error": "Invalid token"
}
```
或
```json
{
  "error": "Consumer not found"
}
```

---

## 🚀 启动轮询服务

配置完成后，启动服务：

### 使用启动脚本
```bash
cd /Users/Doc/code/RSTValueCell/valuecell
./scripts/start_tradingview_polling.sh
```

### 或直接运行
```bash
cd /Users/Doc/code/RSTValueCell/valuecell/python
python3 -m valuecell.agents.tradingview_signal_agent.polling_service
```

### 后台运行
```bash
cd /Users/Doc/code/RSTValueCell/valuecell
nohup ./scripts/start_tradingview_polling.sh > logs/polling.log 2>&1 &

# 查看进程
ps aux | grep polling_service

# 查看日志
tail -f logs/polling.log
```

---

## 🔍 故障排查

### 问题1: 环境变量未加载

**症状**: 
```bash
$ echo $SVIX_API_TOKEN
# (空输出)
```

**解决**:
```bash
# 重新加载配置
source ~/.zshrc  # 或 source ~/.bashrc

# 或重新export
export SVIX_API_TOKEN="sk_poll_..."
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"
```

### 问题2: .env 文件未被读取

**检查**:
```bash
# 确认文件存在
ls -la /Users/Doc/code/RSTValueCell/valuecell/.env

# 检查内容
cat /Users/Doc/code/RSTValueCell/valuecell/.env
```

**注意**: 
- Python脚本需要使用 `python-dotenv` 库来读取 .env 文件
- 或者在启动脚本中手动加载

### 问题3: API Token 无效

**症状**:
```json
{"error": "Invalid token"}
```

**解决**:
1. 检查token是否完整（包括 `.us` 后缀）
2. 检查是否有多余空格
3. 确认token前面没有 "Bearer " 前缀（代码会自动添加）

### 问题4: Consumer ID 错误

**症状**:
```json
{"error": "Consumer not found"}
```

**解决**:
1. 确认 `MY_CONSUMER_ID` 不是占位符
2. 检查实际的Consumer ID
3. 联系Svix支持获取正确的Consumer ID

---

## 📝 检查清单

配置完成后，验证以下项目：

- [ ] ✅ 环境变量已设置
  ```bash
  printenv | grep SVIX
  ```

- [ ] ✅ API Token 正确
  ```bash
  echo $SVIX_API_TOKEN
  # 应该输出: sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us
  ```

- [ ] ✅ Consumer ID 正确
  ```bash
  echo $SVIX_CONSUMER_ID
  # 应该输出实际的ID，不是 MY_CONSUMER_ID
  ```

- [ ] ✅ API测试成功
  ```bash
  curl -X GET "..." -H "Authorization: Bearer $SVIX_API_TOKEN"
  # 应该返回JSON数据
  ```

- [ ] ✅ 轮询服务启动
  ```bash
  ps aux | grep polling_service
  # 应该看到进程
  ```

- [ ] ✅ 数据开始采集
  ```bash
  sqlite3 python/tradingview_indicators.db "SELECT COUNT(*) FROM indicator_data"
  # 应该看到数量增加
  ```

---

## 🎯 完整配置示例

### 创建环境配置脚本
```bash
# 创建 setup_env.sh
cat > /Users/Doc/code/RSTValueCell/valuecell/setup_env.sh << 'EOF'
#!/bin/bash

# Svix API 凭证配置

# 请替换为实际的凭证
export SVIX_API_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
export SVIX_CONSUMER_ID="MY_CONSUMER_ID"  # 替换为实际ID

# 验证
echo "✓ Svix API Token: ${SVIX_API_TOKEN:0:20}..."
echo "✓ Consumer ID: $SVIX_CONSUMER_ID"

# 测试连接
echo ""
echo "Testing API connection..."
curl -s -X GET \
  "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/$SVIX_CONSUMER_ID" \
  -H 'Accept: application/json' \
  -H "Authorization: Bearer $SVIX_API_TOKEN" | jq -r '.done // "ERROR"'

EOF

# 使脚本可执行
chmod +x /Users/Doc/code/RSTValueCell/valuecell/setup_env.sh

# 运行
source /Users/Doc/code/RSTValueCell/valuecell/setup_env.sh
```

---

## 🔐 安全建议

1. **不要提交凭证到Git**
   ```bash
   # 确保 .env 在 .gitignore 中
   echo ".env" >> .gitignore
   ```

2. **限制文件权限**
   ```bash
   chmod 600 /Users/Doc/code/RSTValueCell/valuecell/.env
   ```

3. **定期轮换Token**
   - 建议定期更新API token
   - 记录token的创建和过期时间

4. **使用环境特定的凭证**
   - 开发环境: `.env.development`
   - 生产环境: `.env.production`

---

## 📞 获取帮助

如果仍有问题：

1. **查看Svix文档**: https://docs.svix.com/
2. **检查API状态**: https://status.svix.com/
3. **联系支持**: 通过Svix控制台获取支持

---

## ✅ 完成

配置完成后，您应该能够：
- ✅ 环境变量正确设置
- ✅ API连接测试成功
- ✅ 轮询服务正常运行
- ✅ 数据开始自动采集

**下一步**: 启动轮询服务，开始数据采集！

