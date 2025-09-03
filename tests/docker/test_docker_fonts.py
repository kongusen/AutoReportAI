#!/usr/bin/env python3
"""
Docker环境中文字体测试脚本
验证容器中的中文字体支持和图表生成功能
"""

import os
import sys
import json
import subprocess
import platform
from pathlib import Path

# 添加backend路径
sys.path.append('/Users/shan/work/me/AutoReportAI/backend')

def check_docker_environment():
    """检查是否在Docker环境中"""
    print("🐳 Docker环境检测...")
    
    is_docker = os.path.exists('/.dockerenv') or os.path.exists('/proc/1/cgroup')
    
    if is_docker:
        print("✅ 检测到Docker环境")
        
        # 检查容器信息
        if os.path.exists('/proc/1/cgroup'):
            try:
                with open('/proc/1/cgroup', 'r') as f:
                    content = f.read()
                    if 'docker' in content:
                        print("   📋 确认运行在Docker容器中")
            except Exception:
                pass
    else:
        print("⚠️  当前不在Docker环境中")
        print("   📝 注意: 这是Docker字体测试脚本，建议在容器中运行")
    
    print(f"   🖥️  操作系统: {platform.system()} {platform.release()}")
    print(f"   🐍 Python版本: {sys.version.split()[0]}")
    
    return is_docker

def check_system_fonts():
    """检查系统中文字体安装情况"""
    print("\n📝 系统字体检查...")
    
    # 检查字体配置工具
    try:
        result = subprocess.run(['fc-list', '--version'], 
                               capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ fontconfig 可用")
        else:
            print("❌ fontconfig 不可用")
    except Exception as e:
        print(f"❌ fontconfig 检查失败: {e}")
    
    # 列出中文字体
    try:
        result = subprocess.run(['fc-list', ':lang=zh'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            chinese_fonts = result.stdout.strip().split('\n')
            chinese_fonts = [f for f in chinese_fonts if f.strip()]
            
            print(f"📊 检测到 {len(chinese_fonts)} 个中文字体:")
            
            # 分析字体类型
            noto_fonts = [f for f in chinese_fonts if 'noto' in f.lower()]
            wqy_fonts = [f for f in chinese_fonts if 'wenquanyi' in f.lower() or 'wqy' in f.lower()]
            source_fonts = [f for f in chinese_fonts if 'source' in f.lower()]
            
            if noto_fonts:
                print(f"   🎨 Noto字体: {len(noto_fonts)} 个")
                print(f"      {noto_fonts[0].split(':')[0] if noto_fonts else ''}")
            
            if wqy_fonts:
                print(f"   🎨 文泉驿字体: {len(wqy_fonts)} 个")
                print(f"      {wqy_fonts[0].split(':')[0] if wqy_fonts else ''}")
            
            if source_fonts:
                print(f"   🎨 思源字体: {len(source_fonts)} 个")
                print(f"      {source_fonts[0].split(':')[0] if source_fonts else ''}")
            
            assert len(chinese_fonts) > 0, "应该检测到中文字体"
        else:
            print("❌ 无法列出中文字体")
            assert False, "无法列出中文字体"
            
    except Exception as e:
        print(f"❌ 字体检查失败: {e}")
        assert False, f"字体检查失败: {e}"

def test_matplotlib_fonts():
    """测试matplotlib字体支持"""
    print("\n📊 matplotlib字体测试...")
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
        
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        
        # 检查matplotlib字体
        font_list = fm.fontManager.ttflist
        print(f"✅ matplotlib检测到 {len(font_list)} 个字体")
        
        # 查找中文字体
        chinese_fonts = []
        for font in font_list:
            font_name = font.name.lower()
            if any(keyword in font_name for keyword in [
                'noto', 'cjk', 'han', 'wenquanyi', 'source', 'wqy'
            ]):
                chinese_fonts.append(font.name)
        
        chinese_fonts = list(set(chinese_fonts))  # 去重
        
        if chinese_fonts:
            print(f"✅ matplotlib中文字体: {len(chinese_fonts)} 个")
            for font in chinese_fonts[:5]:  # 显示前5个
                print(f"   🔤 {font}")
            assert True, "应该检测到matplotlib中文字体"
        else:
            print("⚠️  matplotlib未检测到标准中文字体")
            print("   但可能仍支持中文显示（通过系统字体后备）")
            assert False, "应该检测到matplotlib中文字体"
            
    except Exception as e:
        print(f"❌ matplotlib测试失败: {e}")
        assert False, f"matplotlib测试失败: {e}"

def test_chart_generation():
    """测试图表生成功能"""
    print("\n🎨 Docker环境图表生成测试...")
    
    try:
        from app.services.infrastructure.ai.tools.chart_generator_tool import ChartGeneratorTool
        
        generator = ChartGeneratorTool()
        
        # 测试中文图表
        chart_data = {
            "title": "Docker环境中文字体测试",
            "x_data": ["北京", "上海", "深圳", "广州"],
            "y_data": [95000, 108000, 87000, 102000],
            "x_label": "城市",
            "y_label": "销售额（元）"
        }
        
        result = generator.generate_bar_chart(chart_data)
        
        if result["success"]:
            print("✅ Docker环境图表生成成功")
            print(f"   📄 文件: {result['filename']}")
            print(f"   📍 路径: {result['filepath']}")
            
            if 'font_used' in result:
                print(f"   🔤 使用字体: {result['font_used']}")
            
            # 检查文件大小
            if os.path.exists(result['filepath']):
                file_size = os.path.getsize(result['filepath'])
                print(f"   💾 文件大小: {file_size:,} bytes")
                
                if file_size > 10000:  # 大于10KB说明生成正常
                    print("✅ 文件大小正常，可能包含正确的图表内容")
                    assert True, "图表生成应该成功"
                else:
                    print("⚠️  文件过小，可能生成异常")
                    assert False, "图表文件应该足够大"
            else:
                print("❌ 图表文件未找到")
                assert False, "图表文件应该存在"
        else:
            print(f"❌ 图表生成失败: {result.get('error', '未知错误')}")
            assert False, f"图表生成应该成功: {result.get('error', '未知错误')}"
            
    except Exception as e:
        print(f"❌ 图表生成测试异常: {e}")
        assert False, f"图表生成测试异常: {e}"

def test_agent_tool_integration():
    """测试Agent工具集成"""
    print("\n🤖 Agent工具集成测试...")
    
    try:
        from app.services.infrastructure.ai.tools.chart_generator_tool import generate_chart
        
        # 测试Agent工具调用
        agent_config = {
            "type": "pie",
            "title": "Docker容器资源分布",
            "labels": ["CPU使用", "内存占用", "磁盘空间", "网络IO", "其他"],
            "sizes": [25, 35, 20, 15, 5]
        }
        
        result_json = generate_chart(json.dumps(agent_config, ensure_ascii=False))
        result = json.loads(result_json)
        
        if result["success"]:
            print("✅ Agent工具调用成功")
            print(f"   📄 文件: {result['filename']}")
            print(f"   📊 类型: {result['chart_type']}")
            assert True, "Agent工具调用应该成功"
        else:
            print(f"❌ Agent工具调用失败: {result.get('error', '未知错误')}")
            assert False, f"Agent工具调用应该成功: {result.get('error', '未知错误')}"
            
    except Exception as e:
        print(f"❌ Agent工具测试异常: {e}")
        assert False, f"Agent工具测试异常: {e}"

def create_docker_font_fix_guide():
    """创建Docker字体修复指南"""
    guide_content = """
# Docker环境中文字体支持指南

## 1. Dockerfile字体支持配置

```dockerfile
# 安装中文字体和相关依赖
RUN apt-get update && apt-get install -y --no-install-recommends \\
    fontconfig \\
    fonts-dejavu \\
    fonts-liberation \\
    fonts-noto-cjk \\
    fonts-wqy-zenhei \\
    fonts-wqy-microhei \\
    libfreetype6-dev \\
    libpng-dev \\
    && fc-cache -fv \\
    && rm -rf /var/lib/apt/lists/*
```

## 2. 字体优先级（推荐）

1. **Noto Sans CJK SC** - Google开源CJK字体，质量最高
2. **WenQuanYi Micro Hei** - 文泉驿微米黑，Docker环境常用
3. **WenQuanYi Zen Hei** - 文泉驿正黑，轻量级选择

## 3. 验证字体安装

```bash
# 在容器中运行
fc-list :lang=zh
fc-cache -fv
```

## 4. matplotlib配置

确保matplotlib能识别系统字体：
- 清除matplotlib字体缓存
- 重建字体索引
- 使用字体后备机制

## 5. 故障排除

如果中文显示为方块：
1. 检查字体是否正确安装
2. 验证字体缓存是否更新
3. 确认matplotlib后端设置
4. 使用字体文件路径直接指定
"""
    
    guide_path = "docker_font_guide.md"
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"\n📖 Docker字体支持指南已保存到: {guide_path}")

def main():
    """主函数"""
    print("🚀 AutoReportAI - Docker环境中文字体支持测试")
    print("=" * 60)
    print("验证Docker容器中的中文字体配置和图表生成功能")
    
    results = []
    
    # 1. 环境检测
    is_docker = check_docker_environment()
    results.append(("Docker环境", is_docker))
    
    # 2. 系统字体检查
    fonts_ok = check_system_fonts()
    results.append(("系统字体", fonts_ok))
    
    # 3. matplotlib字体测试
    mpl_fonts_ok = test_matplotlib_fonts()
    results.append(("matplotlib字体", mpl_fonts_ok))
    
    # 4. 图表生成测试
    chart_ok = test_chart_generation()
    results.append(("图表生成", chart_ok))
    
    # 5. Agent工具测试
    agent_ok = test_agent_tool_integration()
    results.append(("Agent工具", agent_ok))
    
    # 结果总结
    print("\n" + "=" * 60)
    print("📋 Docker中文字体支持测试结果:")
    
    success_count = sum(1 for _, success in results if success)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"   {name}: {status}")
    
    print(f"\n🎯 总体成功率: {success_count}/{len(results)} ({success_count/len(results)*100:.0f}%)")
    
    # 建议
    if success_count == len(results):
        print("\n🎉 恭喜! Docker环境中文字体支持完全正常")
        print("✅ 可以在容器中生成高质量的中文图表")
    elif success_count >= 3:
        print("\n✅ Docker环境基本支持中文图表生成")
        print("🔧 可能需要调整部分配置以获得最佳效果")
    else:
        print("\n⚠️  Docker环境中文支持需要改进")
        print("📝 请参考生成的字体支持指南进行配置")
        create_docker_font_fix_guide()
    
    return success_count >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)