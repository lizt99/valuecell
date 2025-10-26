#!/bin/bash
# Svix API 凭证配置脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Svix API 凭证配置向导                                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# 从您之前提供的API调用中提取的默认值
DEFAULT_TOKEN="sk_poll_yHiqZ0QyAqCWsR5BfIkrI7He3xUPbe8z.us"
DEFAULT_CONSUMER_ID="MY_CONSUMER_ID"

# 获取API Token
echo -e "${YELLOW}步骤 1/2: 设置 API Token${NC}"
echo -e "默认 Token: ${DEFAULT_TOKEN}"
echo -n "按 Enter 使用默认值，或输入新的 Token: "
read INPUT_TOKEN

if [ -z "$INPUT_TOKEN" ]; then
    SVIX_API_TOKEN="$DEFAULT_TOKEN"
    echo -e "${GREEN}✓ 使用默认 Token${NC}"
else
    SVIX_API_TOKEN="$INPUT_TOKEN"
    echo -e "${GREEN}✓ 使用自定义 Token${NC}"
fi

echo ""

# 获取Consumer ID
echo -e "${YELLOW}步骤 2/2: 设置 Consumer ID${NC}"
echo -e "默认 ID: ${DEFAULT_CONSUMER_ID}"
echo -e "${RED}⚠️  注意: 如果这是占位符，请输入实际的 Consumer ID${NC}"
echo -n "按 Enter 使用默认值，或输入 Consumer ID: "
read INPUT_CONSUMER_ID

if [ -z "$INPUT_CONSUMER_ID" ]; then
    SVIX_CONSUMER_ID="$DEFAULT_CONSUMER_ID"
    echo -e "${YELLOW}⚠️  使用默认 Consumer ID (可能需要替换)${NC}"
else
    SVIX_CONSUMER_ID="$INPUT_CONSUMER_ID"
    echo -e "${GREEN}✓ 使用自定义 Consumer ID${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# 显示配置
echo -e "${GREEN}配置信息:${NC}"
echo -e "  API Token: ${SVIX_API_TOKEN:0:20}...${SVIX_API_TOKEN: -5}"
echo -e "  Consumer ID: $SVIX_CONSUMER_ID"
echo ""

# 选择配置方法
echo -e "${YELLOW}选择配置方法:${NC}"
echo "  1) 创建/更新 .env 文件 (推荐)"
echo "  2) 导出到当前 shell (临时)"
echo "  3) 添加到 ~/.zshrc (永久)"
echo "  4) 仅显示命令，不执行"
echo -n "请选择 [1-4]: "
read CHOICE

echo ""

case $CHOICE in
    1)
        # 方法1: .env 文件
        ENV_FILE=".env"
        
        echo -e "${BLUE}创建/更新 $ENV_FILE 文件...${NC}"
        
        # 备份现有文件
        if [ -f "$ENV_FILE" ]; then
            cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
            echo -e "${GREEN}✓ 已备份现有 .env 文件${NC}"
        fi
        
        # 移除旧的SVIX变量
        if [ -f "$ENV_FILE" ]; then
            sed -i.tmp '/^SVIX_/d' "$ENV_FILE"
            rm -f "${ENV_FILE}.tmp"
        fi
        
        # 添加新配置
        cat >> "$ENV_FILE" << EOF

# Svix API 凭证 (自动生成 $(date))
SVIX_API_TOKEN=$SVIX_API_TOKEN
SVIX_CONSUMER_ID=$SVIX_CONSUMER_ID
EOF
        
        chmod 600 "$ENV_FILE"
        echo -e "${GREEN}✓ .env 文件已更新${NC}"
        echo -e "${BLUE}位置: $(pwd)/$ENV_FILE${NC}"
        
        # 导出到当前shell
        export SVIX_API_TOKEN="$SVIX_API_TOKEN"
        export SVIX_CONSUMER_ID="$SVIX_CONSUMER_ID"
        echo -e "${GREEN}✓ 已导出到当前 shell${NC}"
        ;;
        
    2)
        # 方法2: 导出到当前shell
        echo -e "${BLUE}导出环境变量到当前 shell...${NC}"
        export SVIX_API_TOKEN="$SVIX_API_TOKEN"
        export SVIX_CONSUMER_ID="$SVIX_CONSUMER_ID"
        echo -e "${GREEN}✓ 已导出${NC}"
        echo -e "${YELLOW}⚠️  注意: 关闭终端后失效${NC}"
        ;;
        
    3)
        # 方法3: 添加到 ~/.zshrc
        SHELL_RC="$HOME/.zshrc"
        
        echo -e "${BLUE}添加到 $SHELL_RC...${NC}"
        
        # 备份
        cp "$SHELL_RC" "${SHELL_RC}.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✓ 已备份 shell 配置${NC}"
        
        # 移除旧配置
        sed -i.tmp '/^export SVIX_/d' "$SHELL_RC"
        rm -f "${SHELL_RC}.tmp"
        
        # 添加新配置
        cat >> "$SHELL_RC" << EOF

# Svix API 凭证 (自动添加 $(date))
export SVIX_API_TOKEN="$SVIX_API_TOKEN"
export SVIX_CONSUMER_ID="$SVIX_CONSUMER_ID"
EOF
        
        echo -e "${GREEN}✓ 已添加到 $SHELL_RC${NC}"
        
        # 重新加载
        source "$SHELL_RC"
        echo -e "${GREEN}✓ 已重新加载配置${NC}"
        ;;
        
    4)
        # 方法4: 仅显示
        echo -e "${BLUE}手动配置命令:${NC}"
        echo ""
        echo -e "${YELLOW}# 方法1: 导出到当前 shell${NC}"
        echo "export SVIX_API_TOKEN=\"$SVIX_API_TOKEN\""
        echo "export SVIX_CONSUMER_ID=\"$SVIX_CONSUMER_ID\""
        echo ""
        echo -e "${YELLOW}# 方法2: 添加到 .env 文件${NC}"
        echo "cat >> .env << 'EOF'"
        echo "SVIX_API_TOKEN=$SVIX_API_TOKEN"
        echo "SVIX_CONSUMER_ID=$SVIX_CONSUMER_ID"
        echo "EOF"
        exit 0
        ;;
        
    *)
        echo -e "${RED}无效选择${NC}"
        exit 1
        ;;
esac

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# 验证配置
echo -e "${GREEN}验证配置...${NC}"
echo ""

# 检查环境变量
if [ -n "$SVIX_API_TOKEN" ]; then
    echo -e "${GREEN}✓ SVIX_API_TOKEN: ${SVIX_API_TOKEN:0:20}...${NC}"
else
    echo -e "${RED}✗ SVIX_API_TOKEN 未设置${NC}"
fi

if [ -n "$SVIX_CONSUMER_ID" ]; then
    echo -e "${GREEN}✓ SVIX_CONSUMER_ID: $SVIX_CONSUMER_ID${NC}"
else
    echo -e "${RED}✗ SVIX_CONSUMER_ID 未设置${NC}"
fi

echo ""

# 测试API连接
echo -e "${YELLOW}测试 API 连接...${NC}"

API_URL="https://api.us.svix.com/api/v1/app/app_34c45yl2FOypajxyz2UPrmsYl06/poller/poll_xo6/consumer/$SVIX_CONSUMER_ID"

HTTP_CODE=$(curl -s -o /tmp/svix_test.json -w "%{http_code}" \
    -X GET "$API_URL" \
    -H "Accept: application/json" \
    -H "Authorization: Bearer $SVIX_API_TOKEN")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ API 连接成功 (HTTP $HTTP_CODE)${NC}"
    
    # 显示响应预览
    if command -v jq &> /dev/null; then
        echo -e "\n${BLUE}响应预览:${NC}"
        cat /tmp/svix_test.json | jq -r '{done, data_count: (.data | length)}'
    fi
elif [ "$HTTP_CODE" = "401" ]; then
    echo -e "${RED}✗ API Token 无效 (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}请检查 SVIX_API_TOKEN 是否正确${NC}"
elif [ "$HTTP_CODE" = "404" ]; then
    echo -e "${RED}✗ Consumer ID 未找到 (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}请检查 SVIX_CONSUMER_ID 是否正确${NC}"
else
    echo -e "${YELLOW}⚠️  API 返回 HTTP $HTTP_CODE${NC}"
    echo -e "${BLUE}响应内容:${NC}"
    cat /tmp/svix_test.json
fi

# 清理
rm -f /tmp/svix_test.json

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

# 后续步骤
if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✅ 配置完成！${NC}"
    echo ""
    echo -e "${YELLOW}下一步:${NC}"
    echo "  1. 启动轮询服务:"
    echo "     ${BLUE}./scripts/start_tradingview_polling.sh${NC}"
    echo ""
    echo "  2. 查看日志:"
    echo "     ${BLUE}tail -f logs/polling_service.log${NC}"
    echo ""
    echo "  3. 监控数据库:"
    echo "     ${BLUE}watch -n 60 \"sqlite3 python/tradingview_indicators.db 'SELECT COUNT(*) FROM indicator_data'\"${NC}"
else
    echo -e "${YELLOW}配置已保存，但 API 连接测试失败${NC}"
    echo ""
    echo -e "${RED}请检查:${NC}"
    echo "  1. API Token 是否正确"
    echo "  2. Consumer ID 是否正确"
    echo "  3. 网络连接是否正常"
    echo ""
    echo -e "${BLUE}查看完整文档:${NC}"
    echo "  cat SETUP_SVIX_CREDENTIALS.md"
fi

echo ""

