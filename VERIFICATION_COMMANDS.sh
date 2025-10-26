#!/bin/bash
# 验证第一阶段功能的快速命令集
# 使用方法: bash VERIFICATION_COMMANDS.sh

echo "🔍 第一阶段验证命令集"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. 检查服务进程
echo -e "${YELLOW}1. 检查服务进程${NC}"
ps aux | grep polling_service | grep -v grep
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 服务进程运行中${NC}"
else
    echo -e "${RED}❌ 服务未运行${NC}"
fi
echo ""

# 2. 检查最新日志
echo -e "${YELLOW}2. 最新日志（最后20行）${NC}"
tail -20 logs/polling_service.log
echo ""

# 3. 检查数据库统计
echo -e "${YELLOW}3. 数据库统计${NC}"
sqlite3 python/tradingview_indicators.db "
SELECT 
    'Total Records' as metric,
    COUNT(*) as value
FROM indicator_data
UNION ALL
SELECT 
    'Unique Symbols' as metric,
    COUNT(DISTINCT symbol) as value
FROM indicator_data
UNION ALL
SELECT 
    'Empty Symbols' as metric,
    COUNT(*) as value
FROM indicator_data
WHERE symbol IS NULL OR symbol = ''
UNION ALL
SELECT 
    'Valid Prices' as metric,
    COUNT(*) as value
FROM indicator_data
WHERE price > 0;
"
echo ""

# 4. 检查最新数据
echo -e "${YELLOW}4. 最新10条数据${NC}"
sqlite3 python/tradingview_indicators.db "
SELECT 
    symbol,
    datetime(timestamp) as time,
    price,
    volume,
    rsi14,
    layout_name
FROM indicator_data
ORDER BY timestamp DESC
LIMIT 10;
"
echo ""

# 5. 检查polling状态
echo -e "${YELLOW}5. Polling状态${NC}"
sqlite3 python/tradingview_indicators.db "
SELECT 
    consumer_id,
    datetime(last_poll_time) as last_poll,
    total_messages_fetched as total_messages,
    last_message_count as last_batch,
    substr(last_iterator, 1, 30) || '...' as iterator
FROM polling_state;
"
echo ""

# 6. 检查每个symbol的数据分布
echo -e "${YELLOW}6. Symbol数据分布${NC}"
sqlite3 python/tradingview_indicators.db "
SELECT 
    symbol,
    COUNT(*) as count,
    MIN(datetime(timestamp)) as earliest,
    MAX(datetime(timestamp)) as latest
FROM indicator_data
GROUP BY symbol;
"
echo ""

# 7. 检查最近5分钟的新数据
echo -e "${YELLOW}7. 最近5分钟的新数据${NC}"
sqlite3 python/tradingview_indicators.db "
SELECT 
    COUNT(*) as new_records,
    COUNT(DISTINCT symbol) as symbols,
    MIN(datetime(created_at)) as first_insert,
    MAX(datetime(created_at)) as last_insert
FROM indicator_data
WHERE created_at > datetime('now', '-5 minutes');
"
echo ""

# 8. 数据完整性检查
echo -e "${YELLOW}8. 数据完整性检查${NC}"
sqlite3 python/tradingview_indicators.db "
SELECT 
    'symbol' as field,
    COUNT(*) as null_count
FROM indicator_data
WHERE symbol IS NULL OR symbol = ''
UNION ALL
SELECT 
    'timestamp' as field,
    COUNT(*) as null_count
FROM indicator_data
WHERE timestamp IS NULL
UNION ALL
SELECT 
    'price' as field,
    COUNT(*) as null_count
FROM indicator_data
WHERE price IS NULL OR price = 0
UNION ALL
SELECT 
    'volume' as field,
    COUNT(*) as null_count
FROM indicator_data
WHERE volume IS NULL;
"
echo ""

# 9. 检查环境变量
echo -e "${YELLOW}9. 环境变量配置${NC}"
if [ -f .env ]; then
    grep SVIX .env
    echo -e "${GREEN}✅ .env文件存在${NC}"
else
    echo -e "${RED}❌ .env文件不存在${NC}"
fi
echo ""

# 10. 服务健康摘要
echo -e "${YELLOW}10. 服务健康摘要${NC}"
echo "================================"

# 检查进程
if ps aux | grep polling_service | grep -v grep > /dev/null; then
    echo -e "进程状态: ${GREEN}✅ 运行中${NC}"
else
    echo -e "进程状态: ${RED}❌ 未运行${NC}"
fi

# 检查最近是否有轮询
last_poll=$(sqlite3 python/tradingview_indicators.db "SELECT datetime(last_poll_time) FROM polling_state LIMIT 1")
if [ -n "$last_poll" ]; then
    echo -e "最后轮询: ${GREEN}$last_poll${NC}"
else
    echo -e "最后轮询: ${YELLOW}未开始${NC}"
fi

# 检查数据量
record_count=$(sqlite3 python/tradingview_indicators.db "SELECT COUNT(*) FROM indicator_data")
echo -e "数据记录: ${GREEN}$record_count 条${NC}"

# 检查错误数据
empty_symbols=$(sqlite3 python/tradingview_indicators.db "SELECT COUNT(*) FROM indicator_data WHERE symbol IS NULL OR symbol = ''")
if [ "$empty_symbols" -eq 0 ]; then
    echo -e "数据质量: ${GREEN}✅ 无空symbol${NC}"
else
    echo -e "数据质量: ${RED}❌ 发现 $empty_symbols 条空symbol${NC}"
fi

echo ""
echo "================================"
echo "验证完成！"
echo ""
echo "💡 提示:"
echo "  - 实时日志: tail -f logs/polling_service.log"
echo "  - 停止服务: kill -15 \$(ps aux | grep polling_service | grep -v grep | awk '{print \$2}')"
echo "  - 启动服务: cd python && nohup python3 -m valuecell.agents.tradingview_signal_agent.polling_service > ../logs/polling_service.log 2>&1 &"

