# 如何获取 Svix Consumer ID

**问题**: 在配置中看到 `MY_CONSUMER_ID`，这是什么？如何获取？

---

## 📋 什么是 Consumer ID？

**Consumer ID** 是您为 Svix Polling Endpoint 创建的**自定义标识符**。

- 🔑 **作用**: 唯一标识您的轮询客户端
- 💾 **服务器追踪**: Svix服务器使用它来记住您的iterator位置
- 🔄 **断点续传**: 服务重启后可以从上次位置继续

---

## 🎯 获取方法

### 方法1: 自定义创建（推荐）✨

**Consumer ID 是您自己定义的**，Svix允许您使用任何字符串作为consumer_id。

#### 推荐格式：
```bash
# 格式1: 应用名-环境-标识
export SVIX_CONSUMER_ID="valuecell-prod-001"

# 格式2: 项目-用途
export SVIX_CONSUMER_ID="tradingview-poller"

# 格式3: 简单标识
export SVIX_CONSUMER_ID="my-app-consumer"

# 格式4: UUID风格（推荐用于生产）
export SVIX_CONSUMER_ID="valuecell-$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -d'-' -f1)"
# 例如: valuecell-a3f2b1c4
```

#### 命名规则：
- ✅ 字母、数字、下划线、连字符
- ✅ 建议有意义的名称
- ✅ 同一个consumer_id会保持iterator状态
- ⚠️  不同consumer_id会有独立的iterator

---

### 方法2: 从 Svix 控制台获取

如果您在Svix控制台已经创建了Consumer：

#### 步骤1: 登录 Svix
```
https://dashboard.svix.com/
```

#### 步骤2: 进入您的应用
```
Applications → app_34c45yl2FOypajxyz2UPrmsYl06
```

#### 步骤3: 查找 Polling 设置
```
Settings → Polling Endpoints → poll_xo6
```

#### 步骤4: 查看或创建 Consumer
```
Consumers → [您的Consumer列表]
```

如果已经创建过，会看到类似：
```
consumer_id: my-valuecell-consumer
status: active
last_poll: 2025-10-27 12:00:00
```

---

### 方法3: 从 API 响应获取

如果您之前已经使用过某个consumer_id，可以通过API查询：

```bash
# 列出所有consumers（如果API支持）
curl -X GET \
  "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumers" \
  -H "Authorization: Bearer $SVIX_API_TOKEN"
```

---

## 🔧 如何设置 Consumer ID

### 快速设置（选择其一）

#### 选项A: 使用自定义ID
```bash
export SVIX_CONSUMER_ID="valuecell-prod-001"
```

#### 选项B: 生成UUID风格ID
```bash
export SVIX_CONSUMER_ID="valuecell-$(date +%s)"
# 例如: valuecell-1698412800
```

#### 选项C: 使用机器名
```bash
export SVIX_CONSUMER_ID="valuecell-$(hostname | cut -d'.' -f1)"
# 例如: valuecell-macbook-pro
```

### 永久保存到 .env

```bash
cd /Users/Doc/code/RSTValueCell/valuecell

# 编辑 .env
nano .env

# 添加或修改
SVIX_CONSUMER_ID=valuecell-prod-001

# 保存并退出
```

---

## ✅ 验证 Consumer ID

### 测试API连接

```bash
# 替换为您的consumer_id
export SVIX_CONSUMER_ID="valuecell-prod-001"

# 测试
curl -X GET \
  "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/$SVIX_CONSUMER_ID" \
  -H 'Accept: application/json' \
  -H "Authorization: Bearer $SVIX_API_TOKEN"
```

**成功响应** (HTTP 200):
```json
{
  "iterator": "eyJvZmZzZXQi...",
  "data": [],
  "done": false
}
```

**注意**: 首次使用新的consumer_id时，会自动初始化。

---

## 🎯 推荐配置

### 生产环境推荐

```bash
# 1. 生成唯一ID
UNIQUE_ID=$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -d'-' -f1)

# 2. 设置consumer_id
export SVIX_CONSUMER_ID="valuecell-${UNIQUE_ID}"

# 3. 保存到 .env
echo "SVIX_CONSUMER_ID=valuecell-${UNIQUE_ID}" >> .env

# 4. 验证
echo "Consumer ID: $SVIX_CONSUMER_ID"
```

### 开发环境推荐

```bash
# 简单易记的ID
export SVIX_CONSUMER_ID="valuecell-dev"

# 或者
export SVIX_CONSUMER_ID="valuecell-test"
```

---

## 🔄 Consumer ID 的作用

### 1. 追踪轮询状态
```
Consumer: valuecell-prod-001
  ↓
Svix服务器记住:
  - last_iterator: "eyJvZmZz..."
  - last_poll_time: 2025-10-27 12:00:00
  - messages_delivered: 1523
```

### 2. 多客户端支持
```
不同的consumer_id = 独立的轮询状态

valuecell-prod-001  → Iterator A
valuecell-prod-002  → Iterator B
valuecell-dev       → Iterator C
```

### 3. 断点续传
```
服务重启:
  ↓
使用相同consumer_id
  ↓
从上次iterator继续
  ↓
不丢失数据
```

---

## ⚠️ 重要说明

### 1. Consumer ID 的唯一性

**相同 consumer_id**:
- ✅ 共享iterator状态
- ✅ 适合单实例部署
- ⚠️  多实例会冲突（竞争同一iterator）

**不同 consumer_id**:
- ✅ 独立iterator状态
- ✅ 适合多实例部署
- ⚠️  会收到重复数据（每个consumer独立接收）

### 2. 更换 Consumer ID

**更换consumer_id = 从头开始**:
```
旧ID: valuecell-001 (iterator在第1000条)
  ↓
换成新ID: valuecell-002
  ↓
新ID从第1条开始！
```

**如何保持连续**:
- 不要随意更换consumer_id
- 如需更换，先清空旧数据或做好去重

---

## 📝 快速配置脚本

```bash
#!/bin/bash
# setup_consumer_id.sh

cd /Users/Doc/code/RSTValueCell/valuecell

# 1. 检查是否已有consumer_id
if grep -q "SVIX_CONSUMER_ID" .env 2>/dev/null; then
    CURRENT_ID=$(grep "SVIX_CONSUMER_ID" .env | cut -d'=' -f2)
    echo "✓ 已有 Consumer ID: $CURRENT_ID"
    echo ""
    echo "是否继续使用? (y/n)"
    read -r CONTINUE
    
    if [ "$CONTINUE" = "n" ]; then
        # 生成新ID
        NEW_ID="valuecell-$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -d'-' -f1)"
        sed -i.bak "s/SVIX_CONSUMER_ID=.*/SVIX_CONSUMER_ID=$NEW_ID/" .env
        echo "✓ 已更新为: $NEW_ID"
    fi
else
    # 创建新ID
    echo "生成新的 Consumer ID..."
    NEW_ID="valuecell-$(uuidgen | tr '[:upper:]' '[:lower:]' | cut -d'-' -f1)"
    echo "SVIX_CONSUMER_ID=$NEW_ID" >> .env
    echo "✓ Consumer ID: $NEW_ID"
fi

# 2. 导出环境变量
source <(grep SVIX .env | sed 's/^/export /')

# 3. 测试连接
echo ""
echo "测试API连接..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/$SVIX_CONSUMER_ID" \
    -H "Authorization: Bearer $SVIX_API_TOKEN")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ API连接成功 (HTTP $HTTP_CODE)"
else
    echo "✗ API连接失败 (HTTP $HTTP_CODE)"
fi

echo ""
echo "配置完成！"
echo "Consumer ID: $SVIX_CONSUMER_ID"
```

保存后运行：
```bash
chmod +x setup_consumer_id.sh
./setup_consumer_id.sh
```

---

## 🎓 最佳实践

### 1. 命名约定
```
[项目]-[环境]-[编号]
valuecell-prod-001
valuecell-staging-001
valuecell-dev-001
```

### 2. 单实例部署
```bash
# 使用固定的consumer_id
SVIX_CONSUMER_ID=valuecell-prod-main
```

### 3. 多实例部署
```bash
# 每个实例不同的consumer_id
# 实例1
SVIX_CONSUMER_ID=valuecell-prod-001

# 实例2
SVIX_CONSUMER_ID=valuecell-prod-002
```

### 4. 开发/测试
```bash
# 使用dev后缀
SVIX_CONSUMER_ID=valuecell-dev

# 或使用开发者名字
SVIX_CONSUMER_ID=valuecell-zhang-dev
```

---

## 🔍 故障排查

### 问题1: 找不到Consumer

**症状**: HTTP 404 Not Found

**原因**: Consumer ID不存在（首次使用）

**解决**: 首次使用会自动创建，继续即可

### 问题2: Iterator冲突

**症状**: 数据重复或跳过

**原因**: 多个进程使用相同consumer_id

**解决**: 
- 单实例: 确保只运行一个轮询服务
- 多实例: 每个实例使用不同consumer_id

### 问题3: 从头开始

**症状**: 想重新开始轮询

**解决**:
```bash
# 方法1: 换一个新的consumer_id
export SVIX_CONSUMER_ID="valuecell-new-$(date +%s)"

# 方法2: 清除本地iterator状态
sqlite3 python/tradingview_indicators.db "DELETE FROM polling_state;"
```

---

## ✅ 检查清单

配置完成后验证：

- [ ] Consumer ID 已设置
  ```bash
  echo $SVIX_CONSUMER_ID
  ```

- [ ] Consumer ID 已保存到 .env
  ```bash
  grep SVIX_CONSUMER_ID .env
  ```

- [ ] API连接测试成功
  ```bash
  curl -s -o /dev/null -w "%{http_code}" \
    "https://api.us.svix.com/.../consumer/$SVIX_CONSUMER_ID" \
    -H "Authorization: Bearer $SVIX_API_TOKEN"
  # 应返回: 200
  ```

- [ ] 轮询服务可以启动
  ```bash
  ./scripts/start_tradingview_polling.sh
  ```

---

## 📞 还有问题？

### 查看当前配置
```bash
cd /Users/Doc/code/RSTValueCell/valuecell
cat .env | grep SVIX
```

### 使用推荐ID
```bash
# 如果不确定，使用这个：
export SVIX_CONSUMER_ID="valuecell-prod-001"

# 更新 .env
echo "SVIX_CONSUMER_ID=valuecell-prod-001" >> .env
```

### 立即测试
```bash
source <(grep SVIX .env | sed 's/^/export /')
./scripts/start_tradingview_polling.sh
```

---

## 🎉 总结

**Consumer ID 就是您自己定义的标识符！**

推荐做法：
1. 使用有意义的名称: `valuecell-prod-001`
2. 保存到 .env 文件
3. 不要随意更改（保持iterator连续性）
4. 单实例用一个ID，多实例用不同ID

**现在就设置**:
```bash
export SVIX_CONSUMER_ID="valuecell-prod-001"
echo "SVIX_CONSUMER_ID=valuecell-prod-001" >> .env
```

