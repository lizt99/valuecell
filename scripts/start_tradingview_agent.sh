#!/bin/bash
# Start TradingView Signal Agent

echo "🚀 Starting TradingView Signal Agent..."

# Set working directory
cd "$(dirname "$0")/../python" || exit 1

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "⚠️  Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Set environment variables (optional)
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
export TV_DECISION_MODEL="${TV_DECISION_MODEL:-anthropic/claude-sonnet-4.5}"
export TRADINGVIEW_WEBHOOK_SECRET="${TRADINGVIEW_WEBHOOK_SECRET:-}"

# Start the agent
echo "Starting agent on http://localhost:10005"
python -m valuecell.agents.tradingview_signal_agent

# Keep the script running
wait

