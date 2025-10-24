# TradingView Signal Agent with Position Management

A comprehensive trading agent that combines TradingView technical indicators with intelligent position management and COT-style AI reasoning.

## Features

- 📊 **Real-time TradingView Integration**: Receives technical indicators via webhook every 15 minutes
- 🤖 **AI-Powered Analysis**: Uses Chain-of-Thought (COT) reasoning with Claude/GPT models
- 💼 **Position Management**: Tracks holdings, calculates P&L, manages risk exposure
- ⚖️ **Risk Control**: Automatic position sizing, stop-loss, and portfolio heat monitoring
- 🎮 **Paper Trading**: Simulate trading without real capital
- 📈 **Performance Analytics**: Track win rate, profit factor, and trade history

## Supported Indicators

- **MACD** (12/26/9): Trend direction and momentum
- **RSI** (14): Overbought/oversold conditions
- **Chart Prime**: Custom indicator suite from TradingView
- **EMA** (20/50/200): Moving average alignment
- **Funding Rate**: Crypto perpetual futures funding (optional)

## Installation

```bash
cd /Users/Doc/code/RSTValueCell/valuecell/python
# Install dependencies (if needed)
pip install agno pydantic
```

## Quick Start

### 1. Start the Agent

```bash
python -m valuecell.agents.tradingview_signal_agent
```

The agent will start on `http://localhost:10004`

### 2. Setup Trading Session

```
Setup trading with $100,000 for BTCUSDT and ETHUSDT
```

This creates a paper trading session with:
- Initial capital: $100,000
- Supported symbols: BTCUSDT, ETHUSDT
- Max position size: 20% per trade
- Risk per trade: 2%
- Max concurrent positions: 5

### 3. Analyze Signals

```
Analyze BTCUSDT
```

The agent will:
1. Fetch latest TradingView indicator data
2. Perform technical analysis
3. Check current positions
4. Generate AI-powered recommendation using COT reasoning
5. Provide specific trade instructions

### 4. Check Portfolio

```
Portfolio status
```

Shows:
- Total capital and P&L
- Open positions
- Risk metrics
- Performance statistics

### 5. Close Position

```
Close BTCUSDT
```

## TradingView Webhook Setup

### Configure Alert in TradingView

1. Create an alert on your chart
2. Set webhook URL: `http://your-server:8001/api/webhook/tradingview`
3. Configure alert to trigger every 15 minutes
4. Set message format (JSON):

```json
{
  "symbol": "{{ticker}}",
  "timestamp": "{{time}}",
  "timeframe": "15m",
  "price": {{close}},
  "open": {{open}},
  "high": {{high}},
  "low": {{low}},
  "close": {{close}},
  "volume": {{volume}},
  "macd": {
    "macd_line": {{macd}},
    "signal_line": {{macd_signal}},
    "histogram": {{macd_histogram}}
  },
  "rsi": {
    "value": {{rsi}}
  },
  "ema_20": {{ema(20)}},
  "ema_50": {{ema(50)}}
}
```

## Architecture

```
┌─────────────────┐
│  TradingView    │
│   (Webhooks)    │
└────────┬────────┘
         │ 15min intervals
         ▼
┌─────────────────────────────────┐
│   Indicator Data Store          │
│   (SQLite)                      │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Technical Analyzer            │
│   - MACD, RSI, Chart Prime      │
│   - EMA alignment               │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   COT Decision Engine           │
│   - Chain-of-Thought reasoning  │
│   - Position-aware decisions    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│   Portfolio Manager             │
│   - Position tracking           │
│   - Risk management             │
│   - P&L calculation             │
└─────────────────────────────────┘
```

## Data Models

### Key Models

- **TradingSessionConfig**: Session configuration with capital and risk params
- **Position**: Open position with entry, targets, stop-loss
- **InvalidationCondition**: Complex exit conditions (e.g., "price closes below X on 3m candle")
- **PortfolioSnapshot**: Portfolio state at a point in time
- **TradingRecommendation**: AI-generated trading advice

### Position States

- Entry → Open → (Add/Reduce) → Close
- Invalidation checks every update
- Automatic stop-loss and take-profit execution

## Risk Management

### Position Sizing

- Based on fixed risk per trade (default 2%)
- Considers stop-loss distance
- Respects max position size limits
- Accounts for leverage

### Portfolio Limits

- Max position size: 20% of capital
- Max concurrent positions: 5
- Max total exposure: 60%
- Portfolio heat monitoring (total risk)

### Leverage Management

Confidence-based leverage:
- High confidence (>0.75): 15x
- Medium confidence (>0.65): 10x
- Low confidence: 5x

## COT Reasoning

The agent uses Chain-of-Thought (COT) reasoning to make decisions:

1. **Check Existing Positions**:
   - Is invalidation condition triggered?
   - Current P&L status
   - Technical indicator signals

2. **Analyze Market Context**:
   - RSI overbought/oversold
   - MACD trend
   - EMA alignment
   - Funding rate

3. **Make Decision**:
   - HOLD: Conditions still favorable
   - CLOSE: Exit criteria met
   - ENTRY: Strong new opportunity

4. **Size Position**:
   - Calculate quantity based on risk
   - Set stop-loss and take-profit
   - Apply leverage based on confidence

## Examples

### Example Session

```
> Setup trading with $100,000 for BTCUSDT and ETHUSDT
✅ Trading Session Created
Initial Capital: $100,000
Mode: Paper Trading

> Analyze BTCUSDT
🔍 Analyzing BTCUSDT...
💹 Current Price: $67,432.50
📈 Running technical analysis...
🧠 Generating AI-powered recommendation...

🟢 OPEN Signal - BTCUSDT (Confidence: 78%)
Action: OPEN LONG
Quantity: 0.148 BTC ($10,000)
Entry: $67,400
Stop Loss: $65,800 (-2.4%)
Take Profit: $70,500 / $72,800 / $75,000
Leverage: 10x
Risk: $2,000

Reasoning: MACD bullish crossover, RSI at 62 showing strength,
EMA20 support confirmed. Strong uptrend momentum.

> Portfolio status
📊 Portfolio Status
Total Capital: $100,000
Open Positions: 1 (BTCUSDT)
Unrealized P&L: +$445 (+0.45%)
```

## Performance Analytics

Track your trading performance:

- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Total wins / Total losses
- **Average Win/Loss**: Mean P&L per trade
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns

## Troubleshooting

### No Data Available

- Ensure TradingView webhooks are configured
- Check webhook endpoint is accessible
- Verify JSON format matches expected structure

### Positions Not Updating

- Check if indicator data is being received every 15 minutes
- Review logs for errors
- Verify database is writable

### AI Reasoning Failed

- Check OpenRouter API key is set
- Verify model name is correct
- Review rate limits

## Configuration

Environment variables:

```bash
# OpenRouter API key for AI decisions
export OPENROUTER_API_KEY="your-key"

# Optional: Override default model
export TV_DECISION_MODEL="anthropic/claude-sonnet-4.5"

# Optional: Webhook secret for security
export TRADINGVIEW_WEBHOOK_SECRET="your-secret"
```

## Database

The agent uses SQLite databases:

- `tradingview_indicators.db`: Indicator history
- `tradingview_signal_agent.db`: Positions, trades, snapshots

Location: Current working directory

## License

Part of the ValueCell project.

## Support

For issues or questions, please refer to the main ValueCell documentation.

