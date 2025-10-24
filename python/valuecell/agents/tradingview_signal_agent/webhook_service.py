"""
TradingView Webhook Service (Optional)

This is a standalone FastAPI service that receives TradingView webhooks.
Run separately from the main agent.
"""

import hmac
import hashlib
import logging
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from .indicator_store import IndicatorDataStore
from .models import TradingViewWebhookPayload

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="TradingView Webhook Service", version="1.0.0")

# Webhook secret for security
WEBHOOK_SECRET = os.getenv("TRADINGVIEW_WEBHOOK_SECRET", "")

# Indicator store
indicator_store = IndicatorDataStore()


def verify_signature(payload: str, signature: str) -> bool:
    """Verify webhook signature"""
    if not WEBHOOK_SECRET:
        logger.warning("No webhook secret configured, skipping verification")
        return True
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "tradingview-webhook"}


@app.post("/api/webhook/tradingview")
async def receive_webhook(
    payload: TradingViewWebhookPayload,
    background_tasks: BackgroundTasks,
    x_tradingview_signature: Optional[str] = Header(None)
):
    """
    Receive TradingView webhook data
    
    Security:
    - HMAC signature verification
    - Rate limiting (handled by reverse proxy)
    - IP whitelist (optional, handled by firewall)
    """
    try:
        # Verify signature if provided
        if x_tradingview_signature:
            if not verify_signature(payload.json(), x_tradingview_signature):
                raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Process in background to avoid blocking webhook response
        background_tasks.add_task(process_webhook_data, payload)
        
        logger.info(f"Received webhook for {payload.symbol} at {payload.timestamp}")
        
        return {
            "status": "received",
            "symbol": payload.symbol,
            "timestamp": payload.timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_webhook_data(payload: TradingViewWebhookPayload):
    """Process webhook data in background"""
    try:
        # Save to indicator store
        await indicator_store.save_indicator_data(payload)
        
        logger.info(
            f"Saved indicator data for {payload.symbol}: "
            f"Price=${payload.price:.2f}, RSI={payload.rsi.value:.2f}, "
            f"MACD={payload.macd.macd_line:.3f}"
        )
        
        # Optional: Trigger analysis notification
        # This could notify the main agent to analyze new data
        # For now, the agent will fetch data on demand
        
    except Exception as e:
        logger.error(f"Failed to process webhook data: {e}")


@app.get("/api/indicators/{symbol}")
async def get_indicators(symbol: str, limit: int = 100):
    """Get recent indicators for a symbol (for testing)"""
    try:
        data = await indicator_store.get_recent_data(symbol, limit=limit)
        return {
            "symbol": symbol,
            "count": len(data),
            "data": [d.dict() for d in data]
        }
    except Exception as e:
        logger.error(f"Error fetching indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    # Run webhook service
    port = int(os.getenv("WEBHOOK_PORT", 8001))
    host = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    
    logger.info(f"Starting TradingView Webhook Service on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )

