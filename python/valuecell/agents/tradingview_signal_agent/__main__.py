"""Main entry point for TradingView Signal Agent"""

import asyncio

from valuecell.core.agent.decorator import create_wrapped_agent

from .agent import TradingViewSignalAgent

if __name__ == "__main__":
    agent = create_wrapped_agent(TradingViewSignalAgent)
    asyncio.run(agent.serve())
