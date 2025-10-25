#!/usr/bin/env python3
"""Test script for TradingView Signal Agent logging configuration"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "python"))

def test_logging():
    """Test logging configuration"""
    print("\n" + "="*80)
    print("Testing TradingView Signal Agent Logging Configuration")
    print("="*80 + "\n")
    
    # Import logging config directly (avoid importing agent which has dependencies)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "logging_config",
        Path(__file__).parent.parent / "python" / "valuecell" / "agents" / "tradingview_signal_agent" / "logging_config.py"
    )
    logging_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logging_config)
    
    setup_logging = logging_config.setup_logging
    get_logger = logging_config.get_logger
    set_debug_mode = logging_config.set_debug_mode
    
    # Setup logging
    print("1. Setting up logging...")
    log_path = setup_logging(
        log_dir=str(Path(__file__).parent.parent / "logs"),
        log_level=20  # INFO
    )
    print(f"   ✓ Log path: {log_path}")
    
    # Test individual module loggers
    print("\n2. Testing module loggers...")
    
    modules = [
        'agent',
        'decision_engine',
        'position_manager',
        'portfolio_manager',
        'risk_manager',
        'technical_analyzer',
        'performance_analytics',
        'indicator_store',
        'position_database',
        'webhook_service',
        'formatters'
    ]
    
    for module_name in modules:
        logger = get_logger(module_name)
        logger.info(f"Testing {module_name} logger")
        print(f"   ✓ {module_name}: OK")
    
    # Test log levels
    print("\n3. Testing log levels...")
    test_logger = get_logger('test')
    
    test_logger.debug("This is a DEBUG message (may not show)")
    print("   ✓ DEBUG level")
    
    test_logger.info("This is an INFO message")
    print("   ✓ INFO level")
    
    test_logger.warning("This is a WARNING message")
    print("   ✓ WARNING level")
    
    test_logger.error("This is an ERROR message")
    print("   ✓ ERROR level")
    
    # Test debug mode
    print("\n4. Testing debug mode...")
    set_debug_mode()
    test_logger.debug("This DEBUG message should now appear")
    print("   ✓ Debug mode enabled")
    
    # Test error logging
    print("\n5. Testing error logging with traceback...")
    try:
        raise ValueError("Test error for logging")
    except Exception as e:
        test_logger.error(f"Caught test error: {e}", exc_info=True)
        print("   ✓ Error with traceback logged")
    
    # Check log files
    print("\n6. Verifying log files...")
    agent_log = log_path / "tradingview_agent.log"
    error_log = log_path / "tradingview_error.log"
    
    if agent_log.exists():
        size = agent_log.stat().st_size
        print(f"   ✓ Agent log exists: {agent_log} ({size} bytes)")
    else:
        print(f"   ✗ Agent log not found: {agent_log}")
    
    if error_log.exists():
        size = error_log.stat().st_size
        print(f"   ✓ Error log exists: {error_log} ({size} bytes)")
    else:
        print(f"   ✗ Error log not found: {error_log}")
    
    # Display log content summary
    print("\n7. Log content summary...")
    if agent_log.exists():
        with open(agent_log, 'r') as f:
            lines = f.readlines()
            print(f"   - Total lines in agent log: {len(lines)}")
            print(f"   - First line: {lines[0].strip()}")
            if len(lines) > 1:
                print(f"   - Last line: {lines[-1].strip()}")
    
    if error_log.exists():
        with open(error_log, 'r') as f:
            error_lines = f.readlines()
            print(f"   - Total lines in error log: {len(error_lines)}")
            if error_lines:
                print(f"   - Errors captured: {len([l for l in error_lines if 'ERROR' in l])}")
    
    print("\n" + "="*80)
    print("✅ Logging configuration test completed successfully!")
    print("="*80)
    print(f"\nLog directory: {log_path}")
    print("\nView logs:")
    print(f"  tail -f {agent_log}")
    print(f"  tail -f {error_log}")
    print()


if __name__ == "__main__":
    try:
        test_logging()
    except Exception as e:
        print(f"\n❌ Logging test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

