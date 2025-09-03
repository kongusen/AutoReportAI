#!/bin/bash
# 动态配置时区的脚本

# 设置默认时区
DEFAULT_TZ="Asia/Shanghai"

# 获取时区环境变量，如果未设置则使用默认值
CONTAINER_TZ="${TZ:-${TIMEZONE:-$DEFAULT_TZ}}"

echo "=== 配置容器时区 ==="
echo "目标时区: $CONTAINER_TZ"

# 检查时区文件是否存在
if [ ! -f "/usr/share/zoneinfo/$CONTAINER_TZ" ]; then
    echo "❌ 时区 $CONTAINER_TZ 不存在，使用默认时区 $DEFAULT_TZ"
    CONTAINER_TZ="$DEFAULT_TZ"
fi

# 配置时区
ln -fs "/usr/share/zoneinfo/$CONTAINER_TZ" /etc/localtime
echo "$CONTAINER_TZ" > /etc/timezone

# 验证配置
echo "✅ 时区配置完成"
echo "当前时间: $(date)"
echo "时区文件: $(cat /etc/timezone)"
echo "=========================="