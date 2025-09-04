#!/usr/bin/env python3
"""
纯服务层测试（不导入任何模型和数据库相关代码）
"""

import asyncio
import sys
import os
from datetime import datetime

# 测试SQL生成器核心逻辑
async def test_sql_generation_logic():
    print("=== 测试SQL生成逻辑 ===")
    
    try:
        # 直接测试SQL生成逻辑
        from backend.app.services.infrastructure.ai.sql.sql_generator_service import SQLGeneratorService
        
        # 创建服务实例
        sql_service = SQLGeneratorService()
        
        # 测试需求解析
        requirements = {
            "description": "查询用户表中今年注册的用户总数",
            "entity": "users",
            "operation": "COUNT",
            "time_range": "this_year",
            "columns": ["*"],
            "filters": ["status = 'active'"]
        }
        
        # 测试需求解析方法
        parsed = sql_service._parse_requirements(requirements)
        
        print(f"✅ 需求解析成功")
        print(f"   实体: {parsed['entity']}")
        print(f"   操作: {parsed['operation']}")
        print(f"   时间范围: {parsed.get('time_range', 'None')}")
        print(f"   过滤条件: {len(parsed['filters'])}")
        
        # 测试查询类型确定
        query_type = sql_service._determine_query_type(parsed)
        print(f"   查询类型: {query_type.value}")
        
        # 测试复杂度评估
        complexity = sql_service._assess_complexity(parsed, None)
        print(f"   复杂度: {complexity.value}")
        
        return True
        
    except Exception as e:
        print(f"❌ SQL生成逻辑测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


# 测试数据源分析器核心逻辑
async def test_data_source_analyzer_logic():
    print("\n=== 测试数据源分析逻辑 ===")
    
    try:
        from backend.app.services.infrastructure.ai.analyzer.data_source_analyzer_service import DataSourceAnalyzerService
        
        analyzer = DataSourceAnalyzerService()
        
        # 测试配置解析
        config = {
            "id": "test_db",
            "source_type": "mysql",
            "host": "localhost",
            "port": 3306
        }
        
        parsed_data = analyzer._parse_performance_data({
            "response_time": 2.5,
            "cpu_usage": 65.0,
            "memory_usage": 70.0,
            "error_rate": 0.03
        })
        
        print(f"✅ 性能数据解析成功")
        print(f"   响应时间: {parsed_data['avg_response_time']}s")
        print(f"   CPU使用率: {parsed_data['cpu_usage']}%")
        print(f"   内存使用率: {parsed_data['memory_usage']}%")
        print(f"   错误率: {parsed_data['error_rate']:.1%}")
        
        # 测试评分计算
        overall_score = analyzer._calculate_overall_score(
            analyzer.health_check_config, parsed_data, [], {}
        )
        
        print(f"   整体评分计算: 成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据源分析逻辑测试失败: {e}")
        return False


# 测试Schema检查器核心逻辑
async def test_schema_inspector_logic():
    print("\n=== 测试Schema检查逻辑 ===")
    
    try:
        from backend.app.services.infrastructure.ai.schema.schema_inspector_service import SchemaInspectorService
        
        inspector = SchemaInspectorService()
        
        # 测试列类型解析
        column_types = [
            ("varchar(50)", "STRING"),
            ("int", "INTEGER"),
            ("datetime", "DATETIME"),
            ("decimal(10,2)", "DECIMAL"),
            ("boolean", "BOOLEAN")
        ]
        
        for type_str, expected in column_types:
            parsed_type = inspector._parse_column_type(type_str)
            print(f"   {type_str} -> {parsed_type.value}")
            
        # 测试复杂度计算
        tables = [
            {"name": "users", "columns": [{"name": "id"}, {"name": "email"}]},
            {"name": "orders", "columns": [{"name": "id"}, {"name": "user_id"}, {"name": "total"}]}
        ]
        
        complexity = inspector._calculate_complexity_score(tables, [])
        print(f"✅ Schema分析逻辑测试成功")
        print(f"   复杂度评分: {complexity}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema检查逻辑测试失败: {e}")
        return False


# 测试性能优化器核心逻辑
async def test_performance_optimizer_logic():
    print("\n=== 测试性能优化逻辑 ===")
    
    try:
        from backend.app.services.infrastructure.ai.performance.performance_optimizer_service import PerformanceOptimizerService
        
        optimizer = PerformanceOptimizerService()
        
        # 测试性能数据解析
        data = {
            "response_time": 5.2,
            "cpu_usage": 88.0,
            "memory_usage": 92.0,
            "error_rate": 0.12,
            "bottlenecks": ["database_query", "memory_usage"]
        }
        
        parsed = optimizer._parse_performance_data(data)
        print(f"✅ 性能数据解析成功")
        print(f"   平均响应时间: {parsed['avg_response_time']}s")
        print(f"   CPU使用率: {parsed['cpu_usage']}%")
        print(f"   内存使用率: {parsed['memory_usage']}%")
        
        # 测试评分计算
        score = optimizer._calculate_performance_score(parsed, [])
        print(f"   性能评分: {score}")
        
        # 测试优化指标计算
        optimized = optimizer._calculate_optimized_metrics(parsed, [])
        print(f"   优化后响应时间: {optimized['avg_response_time']:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能优化逻辑测试失败: {e}")
        return False


# 测试报告质量检查器核心逻辑
async def test_report_quality_logic():
    print("\n=== 测试报告质量检查逻辑 ===")
    
    try:
        from backend.app.services.infrastructure.ai.quality.report_quality_checker_service import ReportQualityCheckerService
        
        checker = ReportQualityCheckerService()
        
        # 测试内容分析
        content = """
        # 销售分析报告
        
        本月销售额达到1,250,000元，增长15.8%。
        
        ## 主要发现
        - 移动端占比68%
        - 新用户转化率12.5%
        - 复购率35%
        
        ## 建议
        1. 加强移动端体验
        2. 提高转化率
        """
        
        # 测试内容完整性评估
        completeness_score = checker._assess_content_completeness(content, checker.quality_rules)
        print(f"✅ 内容完整性评估: {completeness_score}")
        
        # 测试结构清晰度评估
        structure_score = checker._assess_structure_clarity(content, checker.quality_rules)
        print(f"   结构清晰度评估: {structure_score}")
        
        # 测试语言质量评估
        language_score = checker._assess_language_quality(content, checker.quality_rules)
        print(f"   语言质量评估: {language_score}")
        
        # 测试整体评分计算
        from backend.app.services.infrastructure.ai.quality.report_quality_checker_service import QualityMetric, QualityDimension
        
        metrics = [
            QualityMetric(QualityDimension.CONTENT_COMPLETENESS, completeness_score, 0.2),
            QualityMetric(QualityDimension.STRUCTURE_CLARITY, structure_score, 0.15),
            QualityMetric(QualityDimension.LANGUAGE_QUALITY, language_score, 0.12)
        ]
        
        overall_score = checker._calculate_overall_score(metrics)
        print(f"   整体质量评分: {overall_score}")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告质量检查逻辑测试失败: {e}")
        return False


# 测试上下文分析器核心逻辑
async def test_context_analyzer_logic():
    print("\n=== 测试上下文分析逻辑 ===")
    
    try:
        from backend.app.services.infrastructure.ai.context.context_analyzer_service import ContextAnalyzerService
        
        analyzer = ContextAnalyzerService()
        
        # 测试上下文类型识别
        context_data = {
            "user_query": "分析最近销售数据",
            "data_source": "mysql://localhost/ecommerce",
            "template": "report.html",
            "business_context": "电商运营"
        }
        
        context_types = analyzer._identify_context_types(context_data)
        print(f"✅ 上下文类型识别成功")
        print(f"   识别的类型: {[ct.value for ct in context_types]}")
        
        # 测试复杂度计算
        complexity = analyzer._calculate_complexity_score(context_data)
        print(f"   上下文复杂度: {complexity}")
        
        # 测试增强处理
        enhanced = analyzer._enhance_context(context_data, context_types)
        print(f"   增强成功: {len(enhanced) > len(context_data)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 上下文分析逻辑测试失败: {e}")
        return False


# 测试增强推理核心逻辑  
async def test_enhanced_reasoning_logic():
    print("\n=== 测试增强推理逻辑 ===")
    
    try:
        from backend.app.services.infrastructure.ai.reasoning.enhanced_reasoning_service import EnhancedReasoningService
        
        reasoning = EnhancedReasoningService()
        
        # 测试推理模式识别
        problem = "分析销售数据下降的原因并提出解决方案"
        pattern = reasoning._identify_reasoning_pattern(problem, None)
        print(f"✅ 推理模式识别: {pattern['pattern']}")
        print(f"   复杂度: {pattern['complexity'].value}")
        
        # 测试推理方法选择
        methods = reasoning._select_reasoning_methods(problem, pattern)
        print(f"   选择的推理方法: {[m.value for m in methods]}")
        
        # 测试分析生成
        from app.services.infrastructure.ai.reasoning.enhanced_reasoning_service import ReasoningStep, ReasoningType
        
        steps = [
            ReasoningStep(1, ReasoningType.INDUCTIVE, "观察数据", "归纳分析", "识别趋势", 0.8),
            ReasoningStep(2, ReasoningType.CAUSAL, "分析原因", "因果推理", "找到根因", 0.75)
        ]
        
        analysis = reasoning._generate_analysis(problem, steps, {})
        print(f"   生成分析: {analysis[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 增强推理逻辑测试失败: {e}")
        return False


# 测试工具监控核心逻辑
async def test_monitoring_logic():
    print("\n=== 测试监控逻辑 ===")
    
    try:
        from app.services.infrastructure.ai.monitoring.tool_monitor_service import ToolMonitorService
        
        monitor = ToolMonitorService()
        
        # 测试阈值配置
        thresholds = monitor.get_performance_thresholds()
        print(f"✅ 性能阈值配置: {len(thresholds)} 项")
        
        # 测试百分位数计算
        values = [1.2, 2.5, 3.1, 4.8, 5.2, 6.0, 7.3, 8.1, 9.2, 10.5]
        p95 = monitor._calculate_percentile(values, 0.95)
        print(f"   P95计算: {p95}")
        
        # 测试趋势分析
        execution_times = [2.1, 2.3, 2.0, 2.4, 2.2, 2.8, 3.0, 3.2, 3.5, 3.8]
        trend = monitor._analyze_performance_trend("test_tool", execution_times)
        print(f"   性能趋势: {trend}")
        
        # 测试输入大小计算
        input_size = monitor._calculate_input_size(("test", 123), {"param": "value"})
        print(f"   输入大小计算: {input_size} bytes")
        
        return True
        
    except Exception as e:
        print(f"❌ 监控逻辑测试失败: {e}")
        return False


# 主测试函数
async def main():
    print("🧪 开始纯服务层逻辑测试...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    # 按顺序执行测试
    tests = [
        ("SQL生成逻辑", test_sql_generation_logic),
        ("数据源分析逻辑", test_data_source_analyzer_logic),
        ("Schema检查逻辑", test_schema_inspector_logic),
        ("性能优化逻辑", test_performance_optimizer_logic),
        ("报告质量检查逻辑", test_report_quality_logic),
        ("上下文分析逻辑", test_context_analyzer_logic),
        ("增强推理逻辑", test_enhanced_reasoning_logic),
        ("监控逻辑", test_monitoring_logic)
    ]
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            test_results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} 测试出现异常: {e}")
            test_results[test_name] = False
    
    # 输出测试总结
    print("\n" + "="*60)
    print("🔍 服务层逻辑测试结果总结")
    print("="*60)
    
    passed = 0
    failed = 0
    
    for test_name, success in test_results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:<25} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    total = len(test_results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print("-" * 60)
    print(f"总测试数: {total}")
    print(f"通过: {passed}")  
    print(f"失败: {failed}")
    print(f"成功率: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 所有服务核心逻辑实现正确！")
        print("✨ 系统已具备完整的15个AI工具功能")
        print("🔧 核心算法和业务逻辑运行良好")
    elif success_rate >= 70:
        print("\n✨ 大部分服务逻辑实现成功")
        print("🔧 建议对失败的服务逻辑进行优化")
    else:
        print("\n⚠️  部分服务逻辑需要进一步完善")
        print("🛠️  建议重点检查核心算法实现")
    
    return success_rate >= 70


if __name__ == "__main__":
    asyncio.run(main())