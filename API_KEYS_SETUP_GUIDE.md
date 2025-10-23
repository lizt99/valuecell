# 🔑 API 密钥配置指南

## 问题: "No auth credentials found"

这个错误表明 **WarrenBuffettAgent** 或其他 Agent 无法找到所需的 API 认证凭据。

---

## ✅ 快速解决方案

### 1. 创建 `.env` 文件

```bash
cd /Users/Doc/code/RSTValueCell/valuecell
cp .env.example .env
```

### 2. 编辑 `.env` 文件并添加 API 密钥

**最少需要配置的密钥：**

```bash
# 至少需要一个 LLM API 密钥
OPENAI_API_KEY=sk-...        # 或
GOOGLE_API_KEY=AIza...       # 或
OPENROUTER_API_KEY=sk-or-... # 或其他

# WarrenBuffettAgent 特别需要
FINANCIAL_DATASETS_API_KEY=...  # 用于获取财务数据

# ResearchAgent 需要
SEC_EMAIL=your-email@example.com  # 用于 SEC 数据访问
```

### 3. 重启应用

```bash
# 停止当前运行的服务
# 然后重新启动
cd /Users/Doc/code/RSTValueCell/valuecell
./start.sh  # 或使用你的启动脚本
```

---

## 📋 详细配置说明

### WarrenBuffettAgent 所需密钥

`WarrenBuffettAgent` 来自 `ai-hedge-fund` 项目，需要以下密钥：

#### 1. **LLM API 密钥**（必需，选择一个）

用于运行 AI 模型进行分析：

| API 提供商 | 环境变量 | 获取地址 | 推荐度 |
|-----------|---------|---------|--------|
| **Google Gemini** | `GOOGLE_API_KEY` | https://makersuite.google.com/app/apikey | ⭐⭐⭐⭐⭐ 免费额度大 |
| **OpenRouter** | `OPENROUTER_API_KEY` | https://openrouter.ai/keys | ⭐⭐⭐⭐⭐ 支持多模型 |
| **OpenAI** | `OPENAI_API_KEY` | https://platform.openai.com/api-keys | ⭐⭐⭐⭐ 质量高但收费 |
| **DeepSeek** | `DEEPSEEK_API_KEY` | https://platform.deepseek.com/api_keys | ⭐⭐⭐⭐ 性价比高 |
| **Groq** | `GROQ_API_KEY` | https://console.groq.com/keys | ⭐⭐⭐⭐ 快速推理 |
| **Anthropic** | `ANTHROPIC_API_KEY` | https://console.anthropic.com/ | ⭐⭐⭐ Claude 系列 |

#### 2. **Financial Datasets API** （WarrenBuffettAgent 专用）

```bash
FINANCIAL_DATASETS_API_KEY=your-key-here
```

- **获取地址:** https://financialdatasets.ai/
- **免费股票:** AAPL, GOOGL, MSFT, NVDA, TSLA （无需 API 密钥）
- **其他股票:** 需要 API 密钥

#### 3. **SEC Email**（ResearchAgent 需要）

```bash
SEC_EMAIL=your-email@example.com
```

- SEC API 要求提供联系邮箱
- 用于合规和速率限制

---

## 🚀 推荐配置（免费方案）

如果你想快速开始且不想花钱，推荐以下配置：

```bash
# 1. Google Gemini (免费额度大，性能好)
GOOGLE_API_KEY=AIza...

# 2. 使用免费支持的股票（无需 Financial Datasets API Key）
# WarrenBuffettAgent 仅查询: AAPL, GOOGL, MSFT, NVDA, TSLA

# 3. SEC Email (任何有效邮箱)
SEC_EMAIL=your-email@gmail.com
```

### 如何获取 Google Gemini API Key（免费）：

1. 访问 https://makersuite.google.com/app/apikey
2. 使用 Google 账号登录
3. 点击 "Create API Key"
4. 复制密钥到 `.env` 文件

---

## 💰 商业配置（付费方案）

如果需要更强大的功能：

```bash
# 1. OpenAI (最佳质量)
OPENAI_API_KEY=sk-proj-...

# 2. Financial Datasets (支持所有股票)
FINANCIAL_DATASETS_API_KEY=fd-...

# 3. SEC Email
SEC_EMAIL=your-email@company.com
```

---

## 🔍 各 Agent 所需密钥汇总

| Agent | LLM API | Financial Data | SEC Email | 其他 |
|-------|---------|----------------|-----------|------|
| **WarrenBuffettAgent** | ✅ 必需 | ✅ 推荐 | ❌ | - |
| **ResearchAgent** | ✅ 必需 | ❌ | ✅ 必需 | - |
| **SECAgent** | ✅ 必需 | ❌ | ✅ 推荐 | - |
| **AutoTradingAgent** | ✅ 必需 | ❌ | ❌ | OpenRouter (可选) |
| **TradingAgents** | ✅ 必需 | ❌ | ❌ | - |

---

## 📝 `.env` 文件示例

```bash
# AI 模型 API (选择一个)
GOOGLE_API_KEY=AIzaSyD...
# 或
OPENAI_API_KEY=sk-proj-...
# 或
OPENROUTER_API_KEY=sk-or-v1-...

# 金融数据 (WarrenBuffettAgent 需要)
FINANCIAL_DATASETS_API_KEY=fd-...

# SEC 数据 (ResearchAgent 需要)
SEC_EMAIL=your-email@example.com

# 可选: 模型配置
RESEARCH_AGENT_MODEL_ID=google/gemini-2.5-flash
TRADING_PARSER_MODEL_ID=deepseek/deepseek-v3.1-terminus
```

---

## ❓ 常见问题

### Q1: 我只想用 WarrenBuffettAgent，需要哪些密钥？

**最少配置：**
```bash
GOOGLE_API_KEY=...  # 免费
# 仅查询: AAPL, GOOGL, MSFT, NVDA, TSLA (无需 FINANCIAL_DATASETS_API_KEY)
```

**完整配置：**
```bash
GOOGLE_API_KEY=...
FINANCIAL_DATASETS_API_KEY=...  # 支持所有股票
```

### Q2: 哪个 LLM API 最便宜/免费？

**免费额度排名：**
1. **Google Gemini** - 最大免费额度
2. **Groq** - 免费但有速率限制
3. **OpenRouter** - 部分模型免费

**性价比排名：**
1. **DeepSeek** - 便宜且性能好
2. **Google Gemini** - 免费额度大
3. **OpenRouter** - 灵活选择模型

### Q3: 为什么需要 SEC_EMAIL？

SEC（美国证券交易委员会）的 API 使用条款要求提供联系邮箱：
- 用于合规
- 速率限制管理
- 可以使用任何有效邮箱

### Q4: Financial Datasets API 免费吗？

**免费：**
- AAPL (Apple)
- GOOGL (Google)
- MSFT (Microsoft)
- NVDA (NVIDIA)
- TSLA (Tesla)

**需要付费：**
- 其他所有股票

### Q5: 如何验证配置是否正确？

```bash
# 1. 检查 .env 文件
cat .env | grep -E "(API_KEY|EMAIL)"

# 2. 运行测试
cd python
uv run python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('LLM API Keys:')
print('  GOOGLE_API_KEY:', '✅ Set' if os.getenv('GOOGLE_API_KEY') else '❌ Missing')
print('  OPENAI_API_KEY:', '✅ Set' if os.getenv('OPENAI_API_KEY') else '❌ Missing')
print('  OPENROUTER_API_KEY:', '✅ Set' if os.getenv('OPENROUTER_API_KEY') else '❌ Missing')
print('Financial Data:')
print('  FINANCIAL_DATASETS_API_KEY:', '✅ Set' if os.getenv('FINANCIAL_DATASETS_API_KEY') else '❌ Missing')
print('SEC Access:')
print('  SEC_EMAIL:', '✅ Set' if os.getenv('SEC_EMAIL') else '❌ Missing')
"

# 3. 重启服务测试
```

---

## 🛠️ 故障排除

### 错误: "No auth credentials found"

**原因：**
- `.env` 文件不存在
- `.env` 文件位置错误
- API 密钥未设置或格式错误

**解决方案：**
1. 确认 `.env` 文件在项目根目录
2. 检查 API 密钥格式正确
3. 重启应用

### 错误: "API Key Error: Please make sure XXX_API_KEY is set"

**原因：**
- 特定 API 密钥缺失

**解决方案：**
根据错误提示添加对应的 API 密钥

### 错误: "HTTP Error 404" 或 "Data not available"

**原因：**
- Financial Datasets API 密钥未设置
- 尝试查询非免费股票

**解决方案：**
1. 添加 `FINANCIAL_DATASETS_API_KEY`
2. 或仅查询免费股票（AAPL, GOOGL, MSFT, NVDA, TSLA）

---

## 📚 相关资源

- [Google Gemini API 文档](https://ai.google.dev/tutorials/setup)
- [OpenAI API 文档](https://platform.openai.com/docs/introduction)
- [OpenRouter 文档](https://openrouter.ai/docs)
- [Financial Datasets 文档](https://financialdatasets.ai/docs)
- [SEC EDGAR API](https://www.sec.gov/edgar/sec-api-documentation)

---

## 🎯 快速检查清单

在使用 WarrenBuffettAgent 前，确保：

- [ ] `.env` 文件已创建
- [ ] 至少有一个 LLM API 密钥
- [ ] 如果查询非免费股票，已设置 `FINANCIAL_DATASETS_API_KEY`
- [ ] 如果使用 ResearchAgent，已设置 `SEC_EMAIL`
- [ ] 应用已重启

---

**配置完成后，WarrenBuffettAgent 应该可以正常工作了！** 🎉

如果还有问题，请检查日志文件获取更详细的错误信息。

