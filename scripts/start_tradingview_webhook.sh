#!/bin/bash
# Start TradingView Webhook Service (Optional)

echo "🌐 Starting TradingView Webhook Service..."

# Set working directory
cd "$(dirname "$0")/../python" || exit 1

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export WEBHOOK_PORT="${WEBHOOK_PORT:-8001}"
export WEBHOOK_HOST="${WEBHOOK_HOST:-0.0.0.0}"
export TRADINGVIEW_WEBHOOK_SECRET="${TRADINGVIEW_WEBHOOK_SECRET:-}"

# Start webhook service
echo "Starting webhook service on http://${WEBHOOK_HOST}:${WEBHOOK_PORT}"
python -m valuecell.agents.tradingview_signal_agent.webhook_service

# Keep the script running
wait

