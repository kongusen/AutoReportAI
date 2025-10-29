#!/usr/bin/env python3
"""
测试Doris SQL生成提示词更新

验证提示词模板是否正确包含Doris规范和时间占位符要求
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.infrastructure.agents.prompts.templates import PromptTemplateManager
from app.services.infrastructure.agents.prompts.system import SystemPromptBuilder
from app.services.infrastructure.agents.config.stage_config import StageConfigManager


def test_sql_generation_template():
    """测试SQL生成模板"""
    print("🧪 测试SQL生成模板...")
    
    template_manager = PromptTemplateManager()
    sql_template = template_manager.get_template("sql_generation")
    
    # 测试模板渲染
    rendered = sql_template.format(
        placeholder="统计昨日销售数据",
        schema_info="sales_table (id, amount, sale_date, customer_id)",
        additional_requirements="需要按客户分组统计"
    )
    
    print("✅ SQL生成模板渲染成功")
    
    # 检查关键内容
    checks = [
        ("Doris", "Doris" in rendered),
        ("{{start_date}}", "{{start_date}}" in rendered),
        ("{{end_date}}", "{{end_date}}" in rendered),
        ("禁止硬编码", "禁止硬编码" in rendered),
        ("时间占位符", "时间占位符" in rendered),
        ("质量检查清单", "质量检查清单" in rendered)
    ]
    
    print("📋 模板内容检查:")
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}: {'通过' if result else '失败'}")
    
    # 检查是否包含Doris示例
    if "SELECT COUNT(*) AS total_count" in rendered or "SELECT COUNT(*) as total_count" in rendered:
        print("✅ 包含Doris SQL示例")
    else:
        print("❌ 缺少Doris SQL示例")
        print(f"   实际内容片段: {rendered[500:800]}...")
    
    return all(result for _, result in checks)


def test_system_prompt():
    """测试系统提示词"""
    print("\n🧪 测试系统提示词...")
    
    system_builder = SystemPromptBuilder()
    base_prompt = system_builder._build_base_prompt()
    
    # 检查关键内容
    checks = [
        ("Doris", "Doris" in base_prompt),
        ("{{start_date}}", "{{start_date}}" in base_prompt),
        ("{{end_date}}", "{{end_date}}" in base_prompt),
        ("禁止硬编码", "禁止硬编码" in base_prompt)
    ]
    
    print("📋 系统提示词检查:")
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}: {'通过' if result else '失败'}")
    
    return all(result for _, result in checks)


def test_sql_stage_prompt():
    """测试SQL阶段提示词"""
    print("\n🧪 测试SQL阶段提示词...")
    
    stage_manager = StageConfigManager()
    sql_prompt = stage_manager._get_sql_stage_prompt()
    
    # 检查关键内容
    checks = [
        ("Doris", "Doris" in sql_prompt),
        ("{{start_date}}", "{{start_date}}" in sql_prompt),
        ("{{end_date}}", "{{end_date}}" in sql_prompt),
        ("禁止硬编码", "禁止硬编码" in sql_prompt),
        ("时间占位符优先", "时间占位符优先" in sql_prompt),
        ("Doris SQL示例", "Doris SQL示例" in sql_prompt)
    ]
    
    print("📋 SQL阶段提示词检查:")
    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}: {'通过' if result else '失败'}")
    
    return all(result for _, result in checks)


def test_prompt_consistency():
    """测试提示词一致性"""
    print("\n🧪 测试提示词一致性...")
    
    template_manager = PromptTemplateManager()
    system_builder = SystemPromptBuilder()
    stage_manager = StageConfigManager()
    
    # 获取所有相关提示词
    sql_template = template_manager.get_template("sql_generation").format(
        placeholder="test",
        schema_info="test",
        additional_requirements=""
    )
    base_prompt = system_builder._build_base_prompt()
    sql_stage_prompt = stage_manager._get_sql_stage_prompt()
    
    # 检查一致性
    consistency_checks = [
        ("模板和系统提示词都包含Doris", 
         "Doris" in sql_template and "Doris" in base_prompt),
        ("模板和阶段提示词都包含时间占位符", 
         "{{start_date}}" in sql_template and "{{start_date}}" in sql_stage_prompt),
        ("所有提示词都禁止硬编码", 
         "禁止硬编码" in sql_template and "禁止硬编码" in base_prompt and "禁止硬编码" in sql_stage_prompt)
    ]
    
    print("📋 一致性检查:")
    for check_name, result in consistency_checks:
        status = "✅" if result else "❌"
        print(f"   {status} {check_name}: {'通过' if result else '失败'}")
    
    return all(result for _, result in consistency_checks)


def main():
    """主测试函数"""
    print("🚀 开始Doris SQL生成提示词测试\n")
    
    try:
        results = []
        
        # 运行各项测试
        results.append(test_sql_generation_template())
        results.append(test_system_prompt())
        results.append(test_sql_stage_prompt())
        results.append(test_prompt_consistency())
        
        # 总结结果
        passed = sum(results)
        total = len(results)
        
        print(f"\n📊 测试结果: {passed}/{total} 通过")
        
        if passed == total:
            print("🎉 所有测试通过！Doris SQL生成提示词更新成功")
            print("\n📝 更新内容总结:")
            print("   ✅ SQL生成模板包含Doris规范")
            print("   ✅ 强制要求使用 {{start_date}} 和 {{end_date}} 占位符")
            print("   ✅ 禁止硬编码日期值")
            print("   ✅ 包含Doris SQL示例和最佳实践")
            print("   ✅ 系统提示词和阶段提示词保持一致")
        else:
            print("❌ 部分测试失败，请检查提示词更新")
            sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
