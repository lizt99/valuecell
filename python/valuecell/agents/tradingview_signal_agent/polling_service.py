"""
TradingView Data Polling Service

Replaces webhook service with scheduled polling from Svix API.
Runs every 3 minutes starting from :00 seconds.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .indicator_store import IndicatorDataStore
from .models import SvixIndicatorData

logger = logging.getLogger(__name__)


class SvixPollingService:
    """Service to poll TradingView indicator data from Svix API"""
    
    def __init__(
        self,
        api_url: str = None,
        api_token: str = None,
        consumer_id: str = None,
        poll_interval_minutes: int = 3,
    ):
        """
        Initialize polling service
        
        Args:
            api_url: Svix API base URL
            api_token: Svix API authentication token
            consumer_id: Consumer ID for polling
            poll_interval_minutes: Polling interval in minutes (default: 3)
        """
        # API configuration
        self.api_url = api_url or os.getenv(
            "SVIX_API_URL",
            "https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6"
        )
        self.api_token = api_token or os.getenv(
            "SVIX_API_TOKEN",
            "sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
        )
        self.consumer_id = consumer_id or os.getenv("SVIX_CONSUMER_ID", "MY_CONSUMER_ID")
        
        # Polling configuration
        self.poll_interval = poll_interval_minutes
        self.is_running = False
        
        # Components
        self.indicator_store = IndicatorDataStore()
        self.scheduler = AsyncIOScheduler()
        self.http_client: Optional[httpx.AsyncClient] = None
        
        logger.info(
            f"Initialized SvixPollingService: "
            f"interval={poll_interval_minutes}min, consumer={self.consumer_id}"
        )
    
    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for Svix API"""
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_token}"
        }
    
    def _get_poll_url(self) -> str:
        """Get full polling URL"""
        return f"{self.api_url}/consumer/{self.consumer_id}"
    
    async def _init_http_client(self):
        """Initialize HTTP client"""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(
                timeout=30.0,
                headers=self._get_headers()
            )
            logger.info("HTTP client initialized")
    
    async def _close_http_client(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
            self.http_client = None
            logger.info("HTTP client closed")
    
    async def fetch_indicator_data(self) -> List[SvixIndicatorData]:
        """
        Fetch indicator data from Svix API using iterator for incremental polling
        
        Uses iterator to get only new messages since last poll.
        Server remembers the last iterator for each Consumer ID.
        
        Real API response format:
        {
            "iterator": "eyJvZmZzZXQiOi05MjIzMzc",
            "data": [...],  # List of indicator items (only new ones)
            "done": false   # Whether there are more pages
        }
        
        Returns:
            List of indicator data items (incremental, no filtering needed)
        """
        all_indicators = []
        max_pages = 10  # Safety limit to prevent infinite loops
        page_count = 0
        
        # 1. Get last saved iterator (resume from where we left off)
        last_iterator = await self.indicator_store.get_last_iterator(
            self.consumer_id
        )
        
        if last_iterator:
            logger.info(f"Resuming from iterator: {last_iterator[:20]}...")
        else:
            logger.info("First poll - no iterator yet (will initialize)")
        
        current_iterator = last_iterator
        
        try:
            total_fetched = 0
            
            while page_count < max_pages:
                # 2. Build URL with iterator (if we have one)
                url = self._get_poll_url()
                if current_iterator:
                    url = f"{url}?iterator={current_iterator}"
                
                logger.info(f"Polling Svix API (page {page_count + 1})")
                logger.debug(f"URL: {url}")
                
                response = await self.http_client.get(url)
                response.raise_for_status()
                
                response_data = response.json()
                
                # 3. Extract pagination info
                new_iterator = response_data.get("iterator")
                items = response_data.get("data", [])
                done = response_data.get("done", True)
                
                logger.info(
                    f"Page {page_count + 1}: {len(items)} new items, "
                    f"done={done}, iterator={new_iterator[:20] if new_iterator else 'None'}..."
                )
                
                total_fetched += len(items)
                
                # 4. Parse items (NO filtering needed - all are new!)
                for item in items:
                    try:
                        # Extract payload from Svix event structure
                        # API returns: {"eventId": "...", "payload": {...}, ...}
                        payload = item.get("payload", {})
                        if not payload:
                            logger.warning(f"Empty payload in item: {item.get('eventId', 'unknown')}")
                            continue
                        
                        indicator = SvixIndicatorData.from_api_response(payload)
                        all_indicators.append(indicator)
                    except Exception as e:
                        logger.error(
                            f"Failed to parse indicator item: {e}\n"
                            f"Item: {item}"
                        )
                
                page_count += 1
                
                # 5. Save iterator after each page (for fault tolerance)
                if new_iterator:
                    await self.indicator_store.save_iterator(
                        self.consumer_id,
                        new_iterator,
                        len(items)
                    )
                    current_iterator = new_iterator
                
                # 6. Check if we're done
                if done:
                    logger.info(f"Pagination complete: fetched {page_count} pages")
                    break
            
            if page_count >= max_pages:
                logger.warning(f"Reached max page limit ({max_pages}), may have more data")
            
            logger.info(
                f"✓ Fetch complete: {total_fetched} new messages "
                f"(incremental, no filtering needed)"
            )
            
            # Log stats
            stats = await self.indicator_store.get_polling_stats(self.consumer_id)
            if stats:
                logger.info(
                    f"Polling stats: {stats['total_messages_fetched']} total messages, "
                    f"last poll: {stats['last_poll_time']}"
                )
            
            return all_indicators
            
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error fetching data: {e.response.status_code}\n"
                f"Response: {e.response.text}"
            )
            return all_indicators  # Return what we have so far
        except httpx.RequestError as e:
            logger.error(f"Request error fetching data: {e}")
            return all_indicators
        except Exception as e:
            logger.error(f"Unexpected error fetching data: {e}", exc_info=True)
            return all_indicators
    
    async def process_and_store_data(self, indicators: List[SvixIndicatorData]):
        """
        Process and store indicator data
        
        Args:
            indicators: List of indicator data from Svix
        """
        if not indicators:
            logger.info("No data to process")
            return
        
        stored_count = 0
        error_count = 0
        
        for indicator in indicators:
            try:
                # Store in database
                await self.indicator_store.save_svix_indicator_data(indicator)
                stored_count += 1
                
                logger.debug(
                    f"Stored indicator: {indicator.symbol} @ {indicator.timestamp}, "
                    f"price=${indicator.price:.2f}"
                )
                
            except Exception as e:
                error_count += 1
                logger.error(
                    f"Failed to store indicator {indicator.symbol}: {e}",
                    exc_info=True
                )
        
        logger.info(
            f"Batch complete: {stored_count} stored, {error_count} errors, "
            f"total {len(indicators)} items"
        )
    
    async def poll_task(self):
        """Main polling task - executed on schedule"""
        try:
            logger.info("=" * 60)
            logger.info(f"Starting polling task at {datetime.now(timezone.utc).isoformat()}")
            
            # Fetch data
            indicators = await self.fetch_indicator_data()
            
            # Process and store
            await self.process_and_store_data(indicators)
            
            logger.info(f"Polling task completed successfully")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error in polling task: {e}", exc_info=True)
    
    def start(self):
        """Start the polling service"""
        if self.is_running:
            logger.warning("Polling service is already running")
            return
        
        logger.info("Starting TradingView Polling Service...")
        
        # Initialize HTTP client (run in event loop)
        asyncio.create_task(self._init_http_client())
        
        # Schedule polling task
        # Run every N minutes at :00 seconds
        trigger = CronTrigger(
            minute=f"*/{self.poll_interval}",
            second=0
        )
        
        self.scheduler.add_job(
            self.poll_task,
            trigger=trigger,
            id="poll_tradingview_data",
            name="Poll TradingView Data from Svix",
            replace_existing=True
        )
        
        # Start scheduler
        self.scheduler.start()
        self.is_running = True
        
        logger.info(
            f"✅ Polling service started - running every {self.poll_interval} minutes at :00"
        )
    
    def stop(self):
        """Stop the polling service"""
        if not self.is_running:
            logger.warning("Polling service is not running")
            return
        
        logger.info("Stopping polling service...")
        
        # Stop scheduler
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
        
        # Close HTTP client (run in event loop)
        asyncio.create_task(self._close_http_client())
        
        self.is_running = False
        logger.info("✅ Polling service stopped")
    
    async def run_once(self):
        """Run polling task once (for testing)"""
        logger.info("Running polling task once (manual trigger)...")
        await self._init_http_client()
        await self.poll_task()
        await self._close_http_client()


async def main():
    """Main entry point for standalone service"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Create service
    service = SvixPollingService()
    
    # Initialize HTTP client
    await service._init_http_client()
    
    # Start polling
    service.start()
    
    logger.info("Service is running. Press Ctrl+C to stop.")
    
    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        service.stop()
        await service._close_http_client()
        logger.info("Service shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())

