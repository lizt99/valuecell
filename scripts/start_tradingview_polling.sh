#!/bin/bash
# Start TradingView Polling Service
# Replaces the old webhook service with scheduled API polling

echo "🔄 Starting TradingView Polling Service..."

# Set working directory
cd "$(dirname "$0")/../python" || exit 1

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Set environment variables
export SVIX_API_URL="${SVIX_API_URL:-https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6}"
export SVIX_API_TOKEN="${SVIX_API_TOKEN:-sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us}"
export SVIX_CONSUMER_ID="${SVIX_CONSUMER_ID:-MY_CONSUMER_ID}"

echo "Configuration:"
echo "  API URL: ${SVIX_API_URL}"
echo "  Consumer ID: ${SVIX_CONSUMER_ID}"
echo "  Polling Interval: 3 minutes"
echo ""

# Start polling service
echo "Starting polling service..."
python -m valuecell.agents.tradingview_signal_agent.polling_service

# Keep the script running
wait

