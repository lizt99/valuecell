#!/usr/bin/env python3
"""测试 YFinance 和 AKShare 数据适配器"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "python"))

from datetime import datetime, timedelta
from valuecell.adapters.assets.manager import get_adapter_manager
from valuecell.adapters.assets.types import AssetSearchQuery, AssetType, DataSource


def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_health_check():
    """测试适配器健康检查"""
    print_section("1. 健康检查")
    
    manager = get_adapter_manager()
    health_status = manager.health_check()
    
    for source, status in health_status.items():
        print(f"\n📊 {source.value.upper()} 适配器:")
        print(f"   状态: {status.get('status', 'unknown')}")
        if 'details' in status:
            print(f"   详情: {status['details']}")
        if 'error' in status:
            print(f"   ❌ 错误: {status['error']}")
        if 'timestamp' in status:
            print(f"   时间: {status['timestamp']}")


def test_search_assets():
    """测试资产搜索"""
    print_section("2. 资产搜索测试")
    
    manager = get_adapter_manager()
    
    test_queries = [
        ("AAPL", "美股搜索 - Apple"),
        ("600519", "A股搜索 - 贵州茅台"),
        ("00700", "港股搜索 - 腾讯"),
        ("BTC", "加密货币搜索"),
    ]
    
    for query, description in test_queries:
        print(f"\n🔍 测试: {description} (查询: {query})")
        
        search_query = AssetSearchQuery(
            query=query,
            limit=3,
            language="zh-Hans"
        )
        
        try:
            results = manager.search_assets(search_query)
            print(f"   ✅ 找到 {len(results)} 个结果")
            
            for i, result in enumerate(results[:2], 1):
                print(f"   {i}. {result.ticker}")
                print(f"      名称: {result.get_display_name('zh-Hans')}")
                print(f"      类型: {result.asset_type.value}")
                print(f"      交易所: {result.exchange}")
                print(f"      相关度: {result.relevance_score:.2f}")
                
        except Exception as e:
            print(f"   ❌ 搜索失败: {e}")


def test_asset_info():
    """测试获取资产信息"""
    print_section("3. 资产信息测试")
    
    manager = get_adapter_manager()
    
    test_tickers = [
        ("NASDAQ:AAPL", "Apple Inc."),
        ("SSE:600519", "贵州茅台"),
        ("CRYPTO:BTC", "Bitcoin"),
    ]
    
    for ticker, name in test_tickers:
        print(f"\n📋 测试: {name} ({ticker})")
        
        try:
            asset = manager.get_asset_info(ticker)
            
            if asset:
                print(f"   ✅ 成功获取信息")
                print(f"   Ticker: {asset.ticker}")
                print(f"   类型: {asset.asset_type.value}")
                print(f"   交易所: {asset.market_info.exchange}")
                print(f"   货币: {asset.market_info.currency}")
                print(f"   国家: {asset.market_info.country}")
                
                # 显示一些属性
                if asset.properties:
                    props_to_show = ['sector', 'industry', 'market_cap', 'pe_ratio']
                    for prop in props_to_show:
                        if prop in asset.properties:
                            print(f"   {prop}: {asset.properties[prop]}")
            else:
                print(f"   ⚠️  未找到资产信息")
                
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")


def test_real_time_price():
    """测试实时价格获取"""
    print_section("4. 实时价格测试")
    
    manager = get_adapter_manager()
    
    test_tickers = [
        ("NASDAQ:AAPL", "Apple"),
        ("SSE:600519", "贵州茅台"),
        ("CRYPTO:BTC", "Bitcoin"),
    ]
    
    for ticker, name in test_tickers:
        print(f"\n💰 测试: {name} ({ticker})")
        
        try:
            price_data = manager.get_real_time_price(ticker)
            
            if price_data:
                print(f"   ✅ 成功获取价格")
                print(f"   当前价: {price_data.price} {price_data.currency}")
                if price_data.change:
                    print(f"   涨跌: {price_data.change:+.2f} ({price_data.change_percent:+.2f}%)")
                if price_data.volume:
                    print(f"   成交量: {price_data.volume:,.0f}")
                print(f"   开盘: {price_data.open_price}")
                print(f"   最高: {price_data.high_price}")
                print(f"   最低: {price_data.low_price}")
                print(f"   时间: {price_data.timestamp}")
                print(f"   数据源: {price_data.source.value if price_data.source else 'N/A'}")
            else:
                print(f"   ⚠️  未获取到价格数据")
                
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")


def test_historical_prices():
    """测试历史价格获取"""
    print_section("5. 历史价格测试")
    
    manager = get_adapter_manager()
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=7)
    
    test_cases = [
        ("NASDAQ:AAPL", "Apple - 最近7天日线", "1d"),
        ("SSE:600519", "贵州茅台 - 最近7天日线", "1d"),
    ]
    
    for ticker, description, interval in test_cases:
        print(f"\n📈 测试: {description}")
        
        try:
            prices = manager.get_historical_prices(
                ticker, start_date, end_date, interval
            )
            
            if prices:
                print(f"   ✅ 成功获取 {len(prices)} 个数据点")
                
                # 显示最近3个数据点
                for price_data in prices[-3:]:
                    print(f"   {price_data.timestamp.strftime('%Y-%m-%d')}: "
                          f"{price_data.close_price} {price_data.currency} "
                          f"(成交量: {price_data.volume:,.0f})")
            else:
                print(f"   ⚠️  未获取到历史数据")
                
        except Exception as e:
            print(f"   ❌ 获取失败: {e}")


def test_multiple_prices():
    """测试批量价格获取"""
    print_section("6. 批量价格获取测试")
    
    manager = get_adapter_manager()
    
    tickers = [
        "NASDAQ:AAPL",
        "NASDAQ:GOOGL",
        "NASDAQ:MSFT",
    ]
    
    print(f"\n📊 批量获取 {len(tickers)} 个股票价格...")
    print(f"   {', '.join(tickers)}")
    
    try:
        prices = manager.get_multiple_prices(tickers)
        
        print(f"\n   ✅ 成功获取 {len([p for p in prices.values() if p])} / {len(tickers)} 个价格")
        
        for ticker, price_data in prices.items():
            if price_data:
                print(f"\n   {ticker}:")
                print(f"      价格: {price_data.price} {price_data.currency}")
                if price_data.change_percent:
                    print(f"      涨跌幅: {price_data.change_percent:+.2f}%")
                print(f"      数据源: {price_data.source.value}")
            else:
                print(f"\n   {ticker}: ⚠️ 未获取到数据")
                
    except Exception as e:
        print(f"   ❌ 批量获取失败: {e}")


def test_adapter_priority():
    """测试适配器优先级"""
    print_section("7. 适配器优先级测试")
    
    manager = get_adapter_manager()
    
    print("\n当前配置的适配器优先级:")
    
    for asset_type in [AssetType.STOCK, AssetType.ETF, AssetType.CRYPTO, AssetType.INDEX]:
        adapters = manager.get_adapters_for_asset_type(asset_type)
        adapter_names = [a.source.value for a in adapters]
        print(f"   {asset_type.value}: {' → '.join(adapter_names)}")


def main():
    """运行所有测试"""
    print("=" * 80)
    print("  ValueCell 数据适配器测试")
    print("=" * 80)
    print("\n开始测试 YFinance 和 AKShare 适配器...")
    
    try:
        # 初始化适配器管理器
        manager = get_adapter_manager()
        manager.configure_yfinance()
        manager.configure_akshare()
        
        print(f"\n✅ 适配器管理器初始化成功")
        print(f"   可用适配器: {', '.join([s.value for s in manager.get_available_adapters()])}")
        
        # 运行测试
        test_health_check()
        test_search_assets()
        test_asset_info()
        test_real_time_price()
        test_historical_prices()
        test_multiple_prices()
        test_adapter_priority()
        
        print_section("测试完成")
        print("\n✅ 所有测试已完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

