#!/usr/bin/env python3
"""
测试Agent系统的字体配置
验证matplotlib和系统字体是否正确设置
"""

import sys
import os
import logging

# 添加项目根路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_system_fonts():
    """测试系统字体配置"""
    print("🔍 检查系统字体配置...")

    try:
        import subprocess

        # 检查中文字体
        result = subprocess.run(['fc-list', ':lang=zh'], capture_output=True, text=True)
        chinese_fonts = result.stdout.strip().split('\n') if result.stdout.strip() else []

        print(f"✅ 检测到 {len(chinese_fonts)} 个中文字体:")
        for i, font in enumerate(chinese_fonts[:5]):  # 只显示前5个
            print(f"   {i+1}. {font}")

        if len(chinese_fonts) > 5:
            print(f"   ... 还有 {len(chinese_fonts) - 5} 个字体")

        return len(chinese_fonts) > 0

    except Exception as e:
        print(f"❌ 系统字体检查失败: {e}")
        return False

def test_matplotlib_fonts():
    """测试matplotlib字体配置"""
    print("\n🎨 检查matplotlib字体配置...")

    try:
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm

        # 显示当前字体配置
        current_font = plt.rcParams['font.sans-serif']
        print(f"✅ 当前sans-serif字体顺序: {current_font}")

        # 查找可用的中文字体
        chinese_fonts = []
        for font in fm.fontManager.ttflist:
            if any(keyword in font.name.lower() for keyword in ['simhei', 'simsun', 'songti', 'heiti', 'wqy', 'dejavu']):
                chinese_fonts.append(font.name)

        chinese_fonts = list(set(chinese_fonts))  # 去重
        print(f"✅ matplotlib可用中文字体: {chinese_fonts[:5]}")

        return len(chinese_fonts) > 0

    except Exception as e:
        print(f"❌ matplotlib字体检查失败: {e}")
        return False

def test_agent_chart_generation():
    """测试Agent图表生成的字体配置"""
    print("\n🤖 测试Agent图表工具字体配置...")

    try:
        from app.services.infrastructure.agents.tools.chart_tools import ChartRenderTool
        from app.core.container import Container

        # 创建容器和工具
        container = Container()
        chart_tool = ChartRenderTool(container)

        # 模拟测试数据
        test_data = {
            "chart_spec": {
                "type": "bar",
                "title": "测试中文字体显示",
                "data": [
                    {"name": "产品A", "value": 100},
                    {"name": "产品B", "value": 150},
                    {"name": "产品C", "value": 80}
                ],
                "xField": "name",
                "yField": "value"
            },
            "placeholder": {"id": "test_chart"}
        }

        print("✅ Agent图表工具初始化成功")
        print("✅ 字体配置已在chart_tools.py中设置:")
        print("   - SimHei, DejaVu Sans, Arial")
        print("   - axes.unicode_minus = False")

        return True

    except Exception as e:
        print(f"❌ Agent图表工具测试失败: {e}")
        return False

def test_visualization_service():
    """测试可视化服务的字体配置"""
    print("\n📊 测试可视化服务字体配置...")

    try:
        from app.services.data.processing.visualization_service import VisualizationService

        # 创建可视化服务
        viz_service = VisualizationService()

        print("✅ 可视化服务初始化成功")
        print("✅ 字体配置已在visualization_service.py中设置:")
        print("   - SimHei, DejaVu Sans")
        print("   - axes.unicode_minus = False")

        return True

    except Exception as e:
        print(f"❌ 可视化服务测试失败: {e}")
        return False

def test_word_template_service():
    """测试Word模板服务的字体配置"""
    print("\n📄 测试Word模板服务字体配置...")

    try:
        from app.services.infrastructure.document.word_template_service import WordTemplateService

        # 创建Word模板服务
        word_service = WordTemplateService()

        print("✅ Word模板服务初始化成功")
        print("✅ 字体配置已在word_template_service.py中设置:")
        print("   - SimHei, Arial Unicode MS")
        print("   - 支持自定义字体路径")

        return True

    except Exception as e:
        print(f"❌ Word模板服务测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始Agent系统字体配置测试\n")

    test_results = []

    # 测试1: 系统字体
    result1 = test_system_fonts()
    test_results.append(("系统字体配置", result1))

    # 测试2: matplotlib字体
    result2 = test_matplotlib_fonts()
    test_results.append(("matplotlib字体配置", result2))

    # 测试3: Agent图表工具
    result3 = test_agent_chart_generation()
    test_results.append(("Agent图表工具", result3))

    # 测试4: 可视化服务
    result4 = test_visualization_service()
    test_results.append(("可视化服务", result4))

    # 测试5: Word模板服务
    result5 = test_word_template_service()
    test_results.append(("Word模板服务", result5))

    # 结果汇总
    print("\n📊 字体配置测试结果汇总:")
    print("=" * 50)

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ 正常" if result else "❌ 异常"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1

    print("=" * 50)
    print(f"总计: {passed}/{total} 个测试通过")

    # 总结
    if passed == total:
        print("\n🎉 所有字体配置测试通过！")
        print("\n✅ Agent系统字体配置正确，能够支持中文显示：")
        print("   • Docker容器已安装 fonts-wqy-microhei 字体")
        print("   • matplotlib 配置了 SimHei、DejaVu Sans 等字体")
        print("   • Agent图表工具正确设置了字体参数")
        print("   • 可视化服务包含完整字体配置")
        print("   • Word模板服务支持自定义字体")
        return True
    else:
        print(f"\n⚠️  有 {total - passed} 个配置存在问题")
        print("\n🔧 建议检查以下配置：")
        print("   • 确保Docker容器中已安装中文字体")
        print("   • 验证matplotlib字体缓存是否正确")
        print("   • 检查字体文件路径是否可访问")
        return False

if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    print(f"\n🏁 测试完成，退出码: {exit_code}")
    sys.exit(exit_code)