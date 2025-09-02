#!/bin/bash

# 简单的Docker环境字体测试脚本
# 快速验证Docker镜像中的中文字体支持

echo "🚀 AutoReportAI Docker字体快速测试"
echo "================================"

# 检查Docker是否可用
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装或不可用"
    exit 1
fi

echo "✅ Docker可用"

# 构建测试镜像
echo "🔨 构建Docker测试镜像..."
docker build --target development -t autoreport-font-test ./backend

if [ $? -eq 0 ]; then
    echo "✅ 镜像构建成功"
else
    echo "❌ 镜像构建失败"
    exit 1
fi

# 运行字体测试容器
echo "🧪 运行字体测试容器..."
docker run --rm -it \
    -v $(pwd)/backend:/app:ro \
    -v $(pwd)/test_docker_fonts.py:/app/test_docker_fonts.py:ro \
    -w /app \
    autoreport-font-test \
    bash -c "
        echo '🐳 容器启动成功' &&
        echo '检查系统字体...' &&
        fc-list :lang=zh | head -3 &&
        echo '运行Python字体测试...' &&
        python test_docker_fonts.py
    "

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Docker字体测试完成"
    echo "📊 检查生成的图表文件:"
    ls -la storage/reports/*chart*.png 2>/dev/null | tail -3
else
    echo ""
    echo "❌ Docker字体测试失败"
    echo "请检查Dockerfile配置和字体安装"
fi

echo "================================"
echo "测试完成"