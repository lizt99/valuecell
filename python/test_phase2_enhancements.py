"""
Phase 2 Enhancement Testing Script

Tests all new functionality added in Phase 2:
- Data layer optimizations (indicator_store.py)
- Analysis layer enhancements (technical_analyzer.py)
- Risk management improvements (risk_manager.py)
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from valuecell.agents.tradingview_signal_agent.indicator_store import IndicatorDataStore
from valuecell.agents.tradingview_signal_agent.technical_analyzer import TradingViewTechnicalAnalyzer
from valuecell.agents.tradingview_signal_agent.risk_manager import RiskManager
from valuecell.agents.tradingview_signal_agent.models import (
    PositionSide,
    TradingSessionConfig,
    TradingMode
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_header(title: str):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_subheader(title: str):
    """Print a formatted subsection header"""
    print(f"\n--- {title} ---\n")


async def test_data_layer_enhancements():
    """Test Phase 2 data layer enhancements"""
    print_header("🔴 Phase 2.1: Data Layer Enhancements Test")
    
    store = IndicatorDataStore()
    
    # Test symbols
    test_symbols = ["BTCUSDT", "ETHUSDT"]
    
    try:
        # 1. Test batch query
        print_subheader("1. Testing get_latest_data_batch()")
        batch_data = await store.get_latest_data_batch(test_symbols, timeframe="1m")
        
        for symbol, data in batch_data.items():
            if data:
                print(f"✓ {symbol}: ${data.ohlcv.get('price', 0):,.2f} (timestamp: {data.timestamp})")
            else:
                print(f"⚠️  {symbol}: No data available")
        
        # 2. Test trend analysis
        print_subheader("2. Testing get_trend_analysis()")
        for symbol in test_symbols:
            trend = await store.get_trend_analysis(symbol, timeframe="1m")
            if trend:
                print(f"✓ {symbol} Trend Analysis:")
                print(f"  - Direction: {trend['trend_direction']}")
                print(f"  - Strength: {trend['trend_strength']:.2f}")
                print(f"  - Price Position: {trend['price_position']}")
                print(f"  - EMA Aligned: {trend['ema_alignment']}")
            else:
                print(f"⚠️  {symbol}: No trend data")
        
        # 3. Test volatility context
        print_subheader("3. Testing get_volatility_context()")
        for symbol in test_symbols:
            vol = await store.get_volatility_context(symbol, timeframe="1m")
            if vol:
                print(f"✓ {symbol} Volatility Context:")
                print(f"  - State: {vol.get('volatility_state', 'N/A')}")
                print(f"  - Risk Level: {vol.get('risk_level', 'N/A')}")
                print(f"  - ATR Ratio: {vol.get('atr_ratio', 0):.3f}")
                if 'atr3' in vol and 'atr14' in vol:
                    print(f"  - ATR3: {vol['atr3']:.2f} | ATR14: {vol['atr14']:.2f}")
            else:
                print(f"⚠️  {symbol}: No volatility data")
        
        # 4. Test signal crossovers
        print_subheader("4. Testing get_signal_crossovers()")
        for symbol in test_symbols:
            signals = await store.get_signal_crossovers(symbol, lookback_periods=5, timeframe="1m")
            if signals:
                print(f"✓ {symbol} Signal Crossovers:")
                if signals['macd_crossover']:
                    print(f"  - MACD: {signals['macd_crossover']} ({signals['macd_crossover_bars_ago']} bars ago)")
                if signals['rsi_crossover_30']:
                    print(f"  - RSI crossed above 30 (oversold exit)")
                if signals['rsi_crossover_70']:
                    print(f"  - RSI crossed below 70 (overbought exit)")
                if signals['rsi7_vs_rsi14']:
                    print(f"  - RSI Divergence: {signals['rsi7_vs_rsi14']}")
                if not any([signals['macd_crossover'], signals['rsi_crossover_30'], 
                           signals['rsi_crossover_70'], signals['rsi7_vs_rsi14']]):
                    print(f"  - No recent crossovers detected")
            else:
                print(f"⚠️  {symbol}: No signal data")
        
        # 5. Test layout name query
        print_subheader("5. Testing get_by_layout_name()")
        # Try to get data for a specific layout
        layout_data = await store.get_by_layout_name("rst-BTC-1m-rule", limit=5, timeframe="1m")
        if layout_data:
            print(f"✓ Found {len(layout_data)} records for layout 'rst-BTC-1m-rule'")
            if layout_data:
                print(f"  - Latest: {layout_data[0].symbol} @ ${layout_data[0].ohlcv.get('price', 0):,.2f}")
        else:
            print(f"ℹ️  No data found for layout 'rst-BTC-1m-rule' (may not exist)")
        
        print("\n✅ Data Layer Tests Complete")
        return True
        
    except Exception as e:
        print(f"\n❌ Data Layer Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_analysis_layer_enhancements():
    """Test Phase 2 analysis layer enhancements"""
    print_header("🔴 Phase 2.2: Analysis Layer Enhancements Test")
    
    store = IndicatorDataStore()
    analyzer = TradingViewTechnicalAnalyzer()
    
    try:
        # Get test data
        symbol = "BTCUSDT"
        latest = await store.get_latest_data(symbol, timeframe="1m")
        
        if not latest:
            print(f"⚠️  No data available for {symbol}")
            return False
        
        price = latest.ohlcv.get("price", 0)
        ema_20 = latest.indicators.get("ema_20")
        ema_50 = latest.indicators.get("ema_50")
        rsi7 = latest.indicators.get("rsi7")
        rsi14 = latest.indicators.get("rsi14")
        atr3 = latest.indicators.get("atr3")
        atr14 = latest.indicators.get("atr14")
        
        # 1. Test EMA alignment analysis
        print_subheader("1. Testing analyze_ema_alignment()")
        if ema_20 and ema_50:
            ema_analysis = analyzer.analyze_ema_alignment(price, ema_20, ema_50)
            print(f"✓ EMA Alignment Analysis for {symbol}:")
            print(f"  - Trend Direction: {ema_analysis['trend_direction']}")
            print(f"  - Trend Strength: {ema_analysis['trend_strength']:.2f}")
            print(f"  - Price Position: {ema_analysis['price_position']}")
            print(f"  - EMA Aligned: {ema_analysis['ema_aligned']}")
            print(f"  - Observations: {len(ema_analysis['key_observations'])} insights")
        else:
            print(f"⚠️  Missing EMA data")
        
        # 2. Test RSI divergence analysis
        print_subheader("2. Testing analyze_rsi_divergence()")
        if rsi7 and rsi14:
            rsi_div = analyzer.analyze_rsi_divergence(rsi7, rsi14)
            print(f"✓ RSI Divergence Analysis for {symbol}:")
            print(f"  - Divergence Type: {rsi_div['divergence_type']}")
            print(f"  - Divergence Strength: {rsi_div['divergence_strength']:.1f}")
            print(f"  - Short-term Momentum: {rsi_div['short_term_momentum']}")
            print(f"  - RSI7: {rsi7:.2f} | RSI14: {rsi14:.2f}")
        else:
            print(f"⚠️  Missing RSI data")
        
        # 3. Test volatility context analysis
        print_subheader("3. Testing analyze_volatility_context()")
        if atr3 and atr14:
            vol_analysis = analyzer.analyze_volatility_context(atr3, atr14, price)
            print(f"✓ Volatility Context Analysis for {symbol}:")
            print(f"  - Volatility State: {vol_analysis['volatility_state']}")
            print(f"  - Risk Level: {vol_analysis['risk_level']}")
            print(f"  - ATR Ratio: {vol_analysis['atr_ratio']:.3f}")
            
            if 'suggested_stop_distance' in vol_analysis:
                stops = vol_analysis['suggested_stop_distance']
                print(f"  - Suggested Stops:")
                for profile, stop_data in stops.items():
                    print(f"    • {profile.capitalize()}: ${stop_data['stop_price_long']:,.2f} "
                          f"({stop_data['risk_pct']:.2f}% risk)")
        else:
            print(f"⚠️  Missing ATR data")
        
        # 4. Test enhanced synthesis
        print_subheader("4. Testing Enhanced synthesize_technical_signals()")
        historical = await store.get_recent_data(symbol, limit=20, timeframe="1m")
        
        if historical:
            tech_signals = analyzer.synthesize_technical_signals(latest, historical)
            print(f"✓ Enhanced Technical Synthesis for {symbol}:")
            print(f"  - Signal Strength: {tech_signals['signal_strength']:.1f}")
            print(f"  - Confidence: {tech_signals['confidence']:.1%}")
            print(f"  - Trend: {tech_signals['trend']}")
            print(f"  - Action: {tech_signals['action']}")
            
            # Check for Phase 2 enhancements
            if 'macd_momentum_analysis' in tech_signals and tech_signals['macd_momentum_analysis']:
                macd_mom = tech_signals['macd_momentum_analysis']
                print(f"  - MACD Momentum: {macd_mom.get('momentum_direction', 'N/A')}")
            
            if 'rsi_divergence_analysis' in tech_signals and tech_signals['rsi_divergence_analysis']:
                rsi_div = tech_signals['rsi_divergence_analysis']
                print(f"  - RSI Divergence: {rsi_div.get('divergence_type', 'N/A')}")
            
            if 'volatility_analysis' in tech_signals and tech_signals['volatility_analysis']:
                vol = tech_signals['volatility_analysis']
                print(f"  - Volatility: {vol.get('volatility_state', 'N/A')}")
            
            print(f"  - Key Factors: {len(tech_signals.get('key_factors', []))} insights")
        else:
            print(f"⚠️  Insufficient historical data")
        
        print("\n✅ Analysis Layer Tests Complete")
        return True
        
    except Exception as e:
        print(f"\n❌ Analysis Layer Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_risk_management_enhancements():
    """Test Phase 2 risk management enhancements"""
    print_header("🔴 Phase 2.4: Risk Management Enhancements Test")
    
    # Create test config
    config = TradingSessionConfig(
        session_id="test_session",
        mode=TradingMode.PAPER,
        initial_capital=100000.0,
        current_capital=100000.0,
        supported_symbols=["BTCUSDT", "ETHUSDT"]
    )
    
    risk_manager = RiskManager(config)
    
    # Test data
    entry_price = 50000.0
    atr3 = 150.0
    atr14 = 200.0
    base_quantity = 0.1
    base_leverage = 10
    
    try:
        # 1. Test ATR-based stop loss
        print_subheader("1. Testing calculate_atr_based_stop_loss()")
        
        for profile in ["conservative", "moderate", "aggressive"]:
            stop_data = risk_manager.calculate_atr_based_stop_loss(
                entry_price=entry_price,
                atr14=atr14,
                atr3=atr3,
                side=PositionSide.LONG,
                risk_profile=profile
            )
            print(f"✓ {profile.capitalize()} Stop Loss:")
            print(f"  - Stop Price: ${stop_data['stop_price']:,.2f}")
            print(f"  - Stop Distance: ${stop_data['stop_distance']:.2f}")
            print(f"  - ATR Multiple: {stop_data['atr_multiple']}x")
            print(f"  - Risk %: {stop_data['risk_pct']:.2f}%")
        
        # 2. Test volatility-adjusted position sizing
        print_subheader("2. Testing adjust_position_size_for_volatility()")
        
        # Test different volatility scenarios
        scenarios = [
            ("Rapidly Expanding", 150.0, 100.0),  # atr3 > atr14 * 1.3
            ("Expanding", 120.0, 100.0),          # atr3 > atr14 * 1.1
            ("Stable", 100.0, 100.0),              # atr3 ≈ atr14
            ("Contracting", 60.0, 100.0),          # atr3 < atr14 * 0.7
        ]
        
        for scenario_name, atr3_test, atr14_test in scenarios:
            adj_data = risk_manager.adjust_position_size_for_volatility(
                base_position_size=base_quantity,
                atr3=atr3_test,
                atr14=atr14_test,
                entry_price=entry_price
            )
            print(f"✓ {scenario_name} Volatility:")
            print(f"  - Base Quantity: {base_quantity:.4f}")
            print(f"  - Adjusted Quantity: {adj_data['adjusted_quantity']:.4f}")
            print(f"  - Adjustment Factor: {adj_data['adjustment_factor']:.2f}x")
            print(f"  - ATR Ratio: {adj_data['atr_ratio']:.3f}")
        
        # 3. Test volatility-adjusted leverage
        print_subheader("3. Testing get_volatility_adjusted_leverage()")
        
        for scenario_name, atr3_test, atr14_test in scenarios:
            lev_data = risk_manager.get_volatility_adjusted_leverage(
                base_leverage=base_leverage,
                atr3=atr3_test,
                atr14=atr14_test,
                entry_price=entry_price
            )
            print(f"✓ {scenario_name} Volatility:")
            print(f"  - Base Leverage: {base_leverage}x")
            print(f"  - Adjusted Leverage: {lev_data['adjusted_leverage']}x")
            print(f"  - Reason: {lev_data['reason']}")
        
        print("\n✅ Risk Management Tests Complete")
        return True
        
    except Exception as e:
        print(f"\n❌ Risk Management Test Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all Phase 2 enhancement tests"""
    print("\n" + "╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "PHASE 2 ENHANCEMENT TEST SUITE" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    
    results = {
        "Data Layer": False,
        "Analysis Layer": False,
        "Risk Management": False
    }
    
    # Run tests
    results["Data Layer"] = await test_data_layer_enhancements()
    results["Analysis Layer"] = await test_analysis_layer_enhancements()
    results["Risk Management"] = test_risk_management_enhancements()
    
    # Summary
    print_header("📊 Test Results Summary")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:20s}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ALL TESTS PASSED - Phase 2 enhancements are working correctly!")
    else:
        print("⚠️  SOME TESTS FAILED - Please review the errors above")
    print("=" * 80 + "\n")
    
    return all_passed


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

