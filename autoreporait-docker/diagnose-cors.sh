#!/bin/bash

# AutoReportAI CORS 诊断脚本
# 用于检查和诊断跨域配置问题

echo "🔍 AutoReportAI CORS 配置诊断"
echo "================================"

# 检查环境文件
if [ -f ".env" ]; then
    echo "✅ .env 文件存在"
    
    # 检查CORS配置
    if grep -q "CORS_ORIGINS" .env; then
        CORS_ORIGINS=$(grep "CORS_ORIGINS" .env | cut -d'=' -f2 | head -1)
        echo "📋 当前CORS配置: $CORS_ORIGINS"
    else
        echo "❌ 未找到CORS_ORIGINS配置"
    fi
    
    # 检查正则表达式配置
    if grep -q "CORS_ORIGIN_REGEX" .env; then
        CORS_REGEX=$(grep "CORS_ORIGIN_REGEX" .env | cut -d'=' -f2 | head -1)
        if [ ! -z "$CORS_REGEX" ]; then
            echo "🔧 CORS正则表达式: $CORS_REGEX"
        fi
    fi
else
    echo "❌ .env 文件不存在"
fi

echo ""
echo "🌐 网络信息检查"
echo "----------------"

# 获取本机IP
echo "🖥️  本机IP地址:"
hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^$' | head -3

echo ""
echo "🐳 Docker 容器状态检查"
echo "----------------------"

# 检查容器是否运行
if docker ps --filter "name=autoreport" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -q "autoreport"; then
    echo "✅ AutoReportAI 容器正在运行:"
    docker ps --filter "name=autoreport" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo "❌ AutoReportAI 容器未运行"
fi

echo ""
echo "🧪 CORS 测试建议"
echo "----------------"
echo "1. 浏览器访问前端时，检查开发者工具的Console和Network选项卡"
echo "2. 查看是否有CORS相关的错误信息"
echo "3. 确认前端访问的URL与CORS_ORIGINS配置匹配"

echo ""
echo "⚙️  常见解决方案:"
echo "----------------"
echo "1. 开发环境: 添加你的服务器IP到CORS_ORIGINS"
echo "   CORS_ORIGINS=http://localhost:3000,http://your-server-ip:3000"
echo ""
echo "2. 生产环境: 使用域名"
echo "   CORS_ORIGINS=https://your-domain.com"
echo ""
echo "3. 临时测试: 允许所有来源（不安全）"
echo "   CORS_ORIGINS=*"
echo ""
echo "4. 使用正则表达式: 更灵活的配置"
echo "   CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1|your-server-ip)(:\d+)?$"

echo ""
echo "📝 修改配置后，请重启容器:"
echo "docker-compose down && docker-compose up -d"

echo ""
echo "🔗 测试CORS的方法:"
echo "curl -H \"Origin: http://your-frontend-url\" \\"
echo "     -H \"Access-Control-Request-Method: POST\" \\"
echo "     -H \"Access-Control-Request-Headers: X-Requested-With\" \\"
echo "     -X OPTIONS \\"
echo "     http://your-server:8000/api/v1/health"