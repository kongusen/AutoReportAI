#!/bin/bash

# AutoReportAI Docker环境字体初始化脚本
# 确保容器中正确配置中文字体支持

set -e

echo "🚀 AutoReportAI 字体初始化脚本"
echo "================================"

# 检查是否为root用户
if [ "$EUID" -eq 0 ]; then
    echo "✅ 以root权限运行"
else
    echo "⚠️  需要root权限来安装字体"
fi

# 更新字体缓存
echo "🔄 更新字体缓存..."
fc-cache -fv

# 验证中文字体安装
echo "🔍 验证中文字体安装..."
CHINESE_FONTS=$(fc-list :lang=zh | wc -l)
echo "📊 检测到 $CHINESE_FONTS 个中文字体"

if [ "$CHINESE_FONTS" -gt 0 ]; then
    echo "✅ 中文字体安装正常"
    
    # 显示主要字体
    echo "📝 主要中文字体:"
    fc-list :lang=zh | head -5 | while read line; do
        font_name=$(echo "$line" | cut -d':' -f2 | cut -d',' -f1 | xargs)
        echo "   🔤 $font_name"
    done
else
    echo "❌ 未检测到中文字体，尝试安装..."
    
    # 尝试安装基础中文字体包
    if command -v apt-get >/dev/null 2>&1; then
        apt-get update
        apt-get install -y --no-install-recommends \
            fonts-noto-cjk \
            fonts-wqy-zenhei \
            fonts-wqy-microhei
        
        # 清理
        rm -rf /var/lib/apt/lists/*
        
        # 重新更新缓存
        fc-cache -fv
    fi
fi

# 设置matplotlib字体缓存目录权限
echo "🎨 配置matplotlib字体缓存..."
MATPLOTLIB_CACHE_DIR="/home/appuser/.cache/matplotlib"
if [ ! -d "$MATPLOTLIB_CACHE_DIR" ]; then
    mkdir -p "$MATPLOTLIB_CACHE_DIR"
fi

# 确保权限正确
if [ "$EUID" -eq 0 ]; then
    chown -R appuser:appuser "$MATPLOTLIB_CACHE_DIR" 2>/dev/null || true
fi

# 创建字体测试脚本
echo "📝 创建字体验证测试..."
cat > /tmp/font_test.py << 'EOF'
#!/usr/bin/env python3
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

print("🔍 matplotlib字体检测...")
fonts = fm.fontManager.ttflist
print(f"总字体数: {len(fonts)}")

chinese_fonts = []
for font in fonts:
    if any(keyword in font.name.lower() for keyword in ['noto', 'cjk', 'han', 'wenquanyi', 'source', 'wqy']):
        chinese_fonts.append(font.name)

chinese_fonts = list(set(chinese_fonts))
if chinese_fonts:
    print(f"✅ 中文字体: {len(chinese_fonts)} 个")
    for font in chinese_fonts[:3]:
        print(f"   🔤 {font}")
else:
    print("⚠️  未检测到专用中文字体")

# 简单测试
try:
    plt.figure(figsize=(6, 4))
    plt.text(0.5, 0.5, "中文测试", fontsize=16, ha='center')
    plt.savefig('/tmp/font_test.png', dpi=100, bbox_inches='tight')
    plt.close()
    print("✅ 图表生成测试成功")
except Exception as e:
    print(f"❌ 图表生成测试失败: {e}")
EOF

# 运行字体测试（如果python可用）
if command -v python3 >/dev/null 2>&1; then
    echo "🧪 运行字体功能测试..."
    python3 /tmp/font_test.py
    
    # 清理测试文件
    rm -f /tmp/font_test.py /tmp/font_test.png
else
    echo "⚠️  Python3不可用，跳过功能测试"
fi

# 创建字体配置文件
echo "⚙️  创建字体配置..."
cat > /etc/fonts/local.conf << 'EOF'
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <!-- 优先使用高质量中文字体 -->
  <alias>
    <family>sans-serif</family>
    <prefer>
      <family>Noto Sans CJK SC</family>
      <family>WenQuanYi Micro Hei</family>
      <family>WenQuanYi Zen Hei</family>
      <family>DejaVu Sans</family>
    </prefer>
  </alias>
  
  <!-- 针对matplotlib的字体映射 -->
  <alias>
    <family>Noto Sans CJK SC</family>
    <default>
      <family>sans-serif</family>
    </default>
  </alias>
</fontconfig>
EOF

# 最终验证
echo "🔍 最终字体配置验证..."
fc-list :lang=zh | wc -l | xargs echo "中文字体总数:"

echo ""
echo "✅ 字体初始化完成!"
echo "📊 AutoReportAI图表生成系统应该能正确显示中文"
echo "================================"