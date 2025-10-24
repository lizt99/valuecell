# TradingView Signal Agent - 市场列表集成指南

## 问题描述

TradingView Signal Agent 在 `http://localhost:1420/market` 页面的 agent 列表中不显示。

## 根本原因

ValueCell 框架使用 **两个独立的 Agent 发现机制**：

### 1. 数据库层 (agents 表)
- **用途**: 前端 `/market` 列表显示
- **数据源**: `init_db.py` 从 JSON 加载到 SQLite
- **更新方式**: 运行 `init_db.py --force`

### 2. RemoteConnections (运行时)
- **用途**: Orchestrator 执行任务时连接 agents
- **数据源**: 直接从 `configs/agent_cards/*.json` 读取
- **更新方式**: 重启后端服务

**关键问题**: 数据库更新后，`RemoteConnections` 不会自动重新加载！

## 数据流

### 前端列表显示流程
```
配置文件 (tradingview_signal_agent.json)
    ↓
数据库初始化 (init_db.py --force)
    ↓
SQLite agents 表
    ↓
AgentService.get_all_agents()
    ↓
/api/v1/agents REST API
    ↓
前端 /market 列表
```

### Orchestrator 执行流程
```
配置文件 (tradingview_signal_agent.json)
    ↓
后端启动 → RemoteConnections._load_remote_contexts()
    ↓
内存中的 _contexts 字典 {agent_name: AgentContext}
    ↓
AgentOrchestrator → start_agent(agent_name)
    ↓
连接到 agent URL (http://localhost:10005)
    ↓
执行 agent 任务
```

⚠️ **注意**: 这两个流程是独立的！数据库更新不会影响 RemoteConnections！

## 解决方案

### 步骤 1: 确保 Agent Card 存在且正确

```bash
# 检查文件是否存在
ls python/configs/agent_cards/tradingview_signal_agent.json

# 验证 JSON 格式
cat python/configs/agent_cards/tradingview_signal_agent.json | python3 -m json.tool
```

关键字段：
- `name`: "TradingViewSignalAgent" (必须匹配类名)
- `display_name`: 前端显示的名称
- `enabled`: true
- `url`: "http://localhost:10005"

### 步骤 2: 初始化/更新数据库

```bash
cd python
uv run --env-file ../.env python -m valuecell.server.db.init_db --force
```

这会：
1. 读取所有 `agent_cards/*.json` 文件
2. 将配置写入 SQLite `agents` 表
3. 新 agents 会被插入，已存在的会被更新

### 步骤 3: 验证数据库

```bash
# 检查数据库中是否有 TradingView Agent
cd python
sqlite3 ../valuecell.db "SELECT name, display_name, enabled FROM agents WHERE name='TradingViewSignalAgent';"
```

预期输出：
```
TradingViewSignalAgent|TradingView Signal Agent with Position Management|1
```

### 步骤 4: 重启后端服务 ⭐

**重要**: 数据库更新后，必须重启后端以重新加载 RemoteConnections！

```bash
# 停止后端
lsof -ti:8000 | xargs kill -9

# 重启后端（会重新加载所有 agent cards）
cd python
nohup uv run --env-file ../.env -m valuecell.server.main > ../logs/backend.log 2>&1 &
```

为什么需要重启？
- `RemoteConnections` 在后端启动时从 JSON 文件加载 agent cards
- 它不会自动重新加载，即使数据库更新了
- 重启后端会触发 `_load_remote_contexts()` 重新读取所有 JSON 配置

### 步骤 5: 验证 API

```bash
# 测试 API 端点
curl -s 'http://localhost:8000/api/v1/agents?enabled_only=true' | python3 -m json.tool | grep -A 5 "TradingView"

# 直接获取 agent 信息
curl -s 'http://localhost:8000/api/v1/agents/by-name/TradingViewSignalAgent' | python3 -m json.tool
```

### 步骤 6: 刷新前端

访问 `http://localhost:1420/market` 并刷新页面，应该看到 TradingView Agent。

## 重要提示

⚠️ **每次新增或修改 agent card 后，必须执行以下步骤：**

```bash
# 新增 agent - 完整流程
1. 创建 configs/agent_cards/new_agent.json
2. 运行 init_db.py --force  ← 更新数据库！
3. 重启后端服务            ← 重新加载 RemoteConnections！
4. 启动 agent 服务          ← 确保 agent 运行！
5. 前端才能看到并使用

# 修改 agent 配置
1. 编辑 configs/agent_cards/existing_agent.json
2. 运行 init_db.py --force  ← 更新数据库！
3. 重启后端服务            ← 重新加载 RemoteConnections！
4. 前端才会显示更新
```

## 框架规范对比

### ✅ 正确的实现方式

按照 ResearchAgent 和 AutoTradingAgent 的模式：

1. **Agent Card** (`tradingview_signal_agent.json`):
   ```json
   {
     "name": "TradingViewSignalAgent",
     "display_name": "TradingView Signal Agent with Position Management",
     "url": "http://localhost:10005",
     "enabled": true,
     "metadata": { ... },
     "skills": [ ... ]
   }
   ```

2. **Agent 实现** (`agent.py`):
   ```python
   class TradingViewSignalAgent(BaseAgent):
       async def stream(self, query, session_id, task_id, dependencies):
           # 实现 stream 方法
   ```

3. **启动入口** (`__main__.py`):
   ```python
   from valuecell.core.agent.decorator import create_wrapped_agent
   from .agent import TradingViewSignalAgent

   if __name__ == "__main__":
       agent = create_wrapped_agent(TradingViewSignalAgent)
       asyncio.run(agent.serve())
   ```

4. **数据库同步**:
   ```bash
   uv run --env-file ../.env python -m valuecell.server.db.init_db --force
   ```

5. **launch.py 集成**:
   ```python
   TRADINGVIEW_SIGNAL_AGENT_NAME = "TradingViewSignalAgent"
   AGENTS = [..., TRADINGVIEW_SIGNAL_AGENT_NAME]
   MAP_NAME_COMMAND[TRADINGVIEW_SIGNAL_AGENT_NAME] = (
       f"uv run --env-file {ENV_PATH_STR} -m valuecell.agents.tradingview_signal_agent"
   )
   ```

## 验证清单

- [x] Agent card JSON 文件存在且格式正确
- [x] Agent 类实现 BaseAgent 接口
- [x] __main__.py 使用 create_wrapped_agent()
- [x] 数据库已初始化（agents 表有记录）
- [x] API 返回 agent 信息
- [x] 前端列表显示 agent
- [x] launch.py 包含 agent 配置
- [x] agent 服务在正确端口运行

## 常见问题

### Q: 为什么我添加了 JSON 文件但前端看不到？

A: 必须运行 `init_db.py --force` 将配置同步到数据库。

### Q: 为什么要用数据库而不是直接读 JSON？

A: 数据库提供：
- 运行时性能（无需重复解析 JSON）
- 动态启用/禁用功能
- 统计信息（enabled_count 等）
- 扩展字段（created_at, updated_at 等）

### Q: 我可以只更新数据库而不修改 JSON 吗？

A: 不推荐。JSON 是"源of truth"，数据库是缓存。
   始终先修改 JSON，然后运行 init_db.py。

## 总结

TradingView Agent 现已完全集成到 ValueCell 框架：

✅ Agent Card 配置正确
✅ 数据库同步完成
✅ API 端点可访问
✅ 前端列表可见
✅ 自动启动集成
✅ 日志管理统一

访问 http://localhost:1420/market 即可看到 TradingView Signal Agent！
