#!/bin/bash

# AutoReportAI 局域网访问测试脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🌐 AutoReportAI 局域网访问测试${NC}"
echo ""

# 获取本机IP地址
get_local_ip() {
    local ip=$(ip route get 8.8.8.8 2>/dev/null | grep -oE 'src [0-9]{1,3}(\.[0-9]{1,3}){3}' | awk '{print $2}')
    if [ -z "$ip" ]; then
        ip=$(ifconfig 2>/dev/null | grep -E 'inet [0-9]' | grep -v 'inet 127.0.0.1' | head -1 | awk '{print $2}')
    fi
    if [ -z "$ip" ]; then
        ip="localhost"
    fi
    echo "$ip"
}

local_ip=$(get_local_ip)

echo -e "${YELLOW}检测到本机IP: ${GREEN}$local_ip${NC}"
echo ""

# 检查环境配置文件
echo -e "${YELLOW}检查环境配置...${NC}"

if [ -f ".env" ]; then
    echo -e "${GREEN}✓ .env 文件存在${NC}"
    
    # 检查SERVER_IP配置
    server_ip=$(grep "SERVER_IP=" .env | cut -d'=' -f2)
    echo -e "  SERVER_IP: ${BLUE}$server_ip${NC}"
    
    # 检查前端API配置
    api_url=$(grep "NEXT_PUBLIC_API_URL=" .env | cut -d'=' -f2)
    echo -e "  API URL: ${BLUE}$api_url${NC}"
    
    # 检查CORS配置
    cors_origins=$(grep "ALLOWED_ORIGINS=" .env | cut -d'=' -f2)
    echo -e "  CORS Origins: ${BLUE}$cors_origins${NC}"
    
else
    echo -e "${RED}✗ .env 文件不存在，请先运行启动脚本${NC}"
    exit 1
fi

echo ""

# 检查服务状态
echo -e "${YELLOW}检查服务状态...${NC}"

if command -v docker-compose &> /dev/null; then
    if docker-compose ps | grep -q "Up"; then
        echo -e "${GREEN}✓ Docker服务正在运行${NC}"
        
        # 显示运行中的服务
        echo -e "${BLUE}运行中的服务:${NC}"
        docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
        
    else
        echo -e "${YELLOW}⚠ Docker服务未运行，请先启动服务${NC}"
    fi
else
    echo -e "${RED}✗ Docker Compose 未安装${NC}"
fi

echo ""

# 显示访问地址
echo -e "${YELLOW}局域网访问地址:${NC}"
echo -e "  • 前端: ${GREEN}http://$local_ip:3000${NC}"
echo -e "  • 后端API: ${GREEN}http://$local_ip:8000${NC}"
echo -e "  • API文档: ${GREEN}http://$local_ip:8000/docs${NC}"
echo -e "  • Minio控制台: ${GREEN}http://$local_ip:9001${NC}"

echo ""

# 网络连通性测试
echo -e "${YELLOW}测试网络连通性...${NC}"

# 测试后端API
if curl -s --connect-timeout 3 "http://$local_ip:8000/api/v1/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 后端API可访问${NC}"
else
    echo -e "${RED}✗ 后端API不可访问${NC}"
fi

# 测试前端服务
if curl -s --connect-timeout 3 "http://$local_ip:3000" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ 前端服务可访问${NC}"
else
    echo -e "${RED}✗ 前端服务不可访问${NC}"
fi

echo ""

# 局域网设备访问指南
echo -e "${BLUE}📱 局域网设备访问指南:${NC}"
echo -e "  1. 确保设备与服务器在同一局域网"
echo -e "  2. 在设备浏览器中访问: ${GREEN}http://$local_ip:3000${NC}"
echo -e "  3. 如果无法访问，检查防火墙设置"
echo -e "  4. 确保端口3000和8000未被占用"

echo ""
echo -e "${GREEN}测试完成！${NC}"