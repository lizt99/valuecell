#!/usr/bin/env python3
"""Script to update logger configuration in TradingView Signal Agent modules"""

import os
import re
from pathlib import Path

# Agent directory
AGENT_DIR = Path(__file__).parent.parent / "python" / "valuecell" / "agents" / "tradingview_signal_agent"

# Files to update (exclude logging_config.py itself)
FILES_TO_UPDATE = [
    "decision_engine.py",
    "position_manager.py",
    "webhook_service.py",
    "portfolio_manager.py",
    "technical_analyzer.py",
    "risk_manager.py",
    "indicator_store.py",
    "position_database.py",
    "performance_analytics.py",
    "formatters.py",
]

def update_logger_import(file_path: Path, module_name: str):
    """Update logger configuration in a file"""
    print(f"Updating {file_path.name}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if already updated
    if 'from .logging_config import get_logger' in content:
        print(f"  ✓ {file_path.name} already updated")
        return
    
    # Add import for get_logger after other relative imports
    if 'from .models import' in content:
        content = re.sub(
            r'(from \.models import)',
            r'from .logging_config import get_logger\n\1',
            content,
            count=1
        )
    elif 'from .constants import' in content:
        content = re.sub(
            r'(from \.constants import)',
            r'from .logging_config import get_logger\n\1',
            content,
            count=1
        )
    else:
        # Add after last import
        import_end = 0
        for i, line in enumerate(content.split('\n')):
            if line.startswith('import ') or line.startswith('from '):
                import_end = i
        
        lines = content.split('\n')
        lines.insert(import_end + 1, 'from .logging_config import get_logger')
        content = '\n'.join(lines)
    
    # Replace logger = logging.getLogger(__name__) with logger = get_logger('module_name')
    content = re.sub(
        r'logger = logging\.getLogger\(__name__\)',
        f"logger = get_logger('{module_name}')",
        content
    )
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ Updated {file_path.name}")

def main():
    print("="*80)
    print("Updating TradingView Signal Agent Logger Configuration")
    print("="*80)
    print()
    
    for file_name in FILES_TO_UPDATE:
        file_path = AGENT_DIR / file_name
        if not file_path.exists():
            print(f"  ⚠ {file_name} not found, skipping")
            continue
        
        # Extract module name (without .py)
        module_name = file_name.replace('.py', '')
        
        try:
            update_logger_import(file_path, module_name)
        except Exception as e:
            print(f"  ❌ Error updating {file_name}: {e}")
    
    print()
    print("="*80)
    print("✅ Logger configuration update completed!")
    print("="*80)

if __name__ == "__main__":
    main()


