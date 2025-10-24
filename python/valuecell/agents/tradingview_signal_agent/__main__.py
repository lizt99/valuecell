"""Main entry point for TradingView Signal Agent"""

import asyncio
import logging
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from a2a.types import AgentCard
from valuecell.core.agent.decorator import _serve
from .logging_config import setup_logging, get_logger

# Setup logging
# Check for LOG_DIR environment variable (set by launch.py)
# Otherwise use default logs directory
default_logs_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))),
    "logs"
)
log_dir = os.getenv("VALUECELL_LOG_DIR", default_logs_dir)

log_path = setup_logging(
    log_dir=log_dir,
    log_level=logging.INFO
)

logger = get_logger('main')


# Load agent card
def load_agent_card():
    """Load agent card from JSON file"""
    from valuecell.core.agent.card import find_local_agent_card_by_agent_name
    
    agent_card = find_local_agent_card_by_agent_name("TradingViewSignalAgent")
    if agent_card is None:
        raise RuntimeError("Failed to load TradingViewSignalAgent card. Check that the agent card file exists and is enabled.")
    
    return agent_card


# Serve the agent
async def main():
    """Main entry point"""
    from .agent import TradingViewSignalAgent
    
    logger.info("="*80)
    logger.info("Starting TradingView Signal Agent...")
    logger.info(f"Log path: {log_path}")
    logger.info("="*80)
    
    try:
        # Load agent card
        agent_card = load_agent_card()
        logger.info(f"Loaded agent card: {agent_card.name}")
        logger.info(f"Agent URL: {agent_card.url}")
        
        # Create agent instance with decorator
        @_serve(agent_card)
        class DecoratedTradingViewSignalAgent(TradingViewSignalAgent):
            pass
        
        # Create instance and serve
        agent = DecoratedTradingViewSignalAgent()
        await agent.serve()
        
    except KeyboardInterrupt:
        logger.info("Shutting down gracefully...")
    except Exception as e:
        logger.error(f"Failed to start agent: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

