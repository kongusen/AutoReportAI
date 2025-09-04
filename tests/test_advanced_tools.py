#!/usr/bin/env python3
"""
测试高级AI工具实现
"""

import asyncio
import json
from datetime import datetime

# 测试SQL生成器
async def test_sql_generator():
    print("=== 测试SQL生成器 ===")
    
    try:
        from backend.app.services.infrastructure.ai.sql.sql_generator_service import sql_generator_service
        
        # 测试基础查询生成
        requirements = {
            "description": "查询用户表中今年注册的用户总数",
            "entity": "users",
            "operation": "COUNT",
            "time_range": "this_year",
            "columns": ["*"]
        }
        
        schema_info = {
            "database_type": "mysql",
            "tables": [
                {
                    "name": "users",
                    "columns": [
                        {"name": "id", "type": "int"},
                        {"name": "username", "type": "varchar"},
                        {"name": "email", "type": "varchar"},
                        {"name": "created_at", "type": "datetime"}
                    ]
                }
            ]
        }
        
        result = await sql_generator_service.generate_query(requirements, schema_info)
        
        print(f"✅ SQL生成成功")
        print(f"   生成的SQL: {result['sql'][:100]}...")
        print(f"   查询类型: {result['query_type']}")
        print(f"   复杂度: {result['complexity']}")
        print(f"   预估成本: {result['estimated_cost']}")
        print(f"   性能提示数量: {len(result['performance_hints'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ SQL生成器测试失败: {e}")
        return False


# 测试数据源分析器
async def test_data_source_analyzer():
    print("\n=== 测试数据源分析器 ===")
    
    try:
        from backend.app.services.infrastructure.ai.analyzer.data_source_analyzer_service import data_source_analyzer_service
        
        # 测试数据源分析
        data_source_config = {
            "id": "test_mysql_db",
            "source_type": "mysql", 
            "host": "localhost",
            "port": 3306,
            "database": "test_db",
            "estimated_tables": 15,
            "version": "8.0.25"
        }
        
        result = await data_source_analyzer_service.analyze_data_source(data_source_config)
        
        print(f"✅ 数据源分析成功")
        print(f"   整体健康状态: {result['overall_health']}")
        print(f"   性能评分: {result['performance_score']}")
        print(f"   响应时间: {result['health_check']['response_time']:.3f}s")
        print(f"   建议数量: {len(result['recommendations'])}")
        print(f"   问题数量: {len(result['issues'])}")
        print(f"   数据质量评分: {result['data_quality']['overall_score']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 数据源分析器测试失败: {e}")
        return False


# 测试Schema检查器
async def test_schema_inspector():
    print("\n=== 测试Schema检查器 ===")
    
    try:
        from backend.app.services.infrastructure.ai.schema.schema_inspector_service import schema_inspector_service
        
        # 测试Schema分析
        schema_info = {
            "schema_name": "ecommerce",
            "database_type": "mysql",
            "tables": [
                {
                    "name": "users",
                    "row_count": 50000,
                    "size_kb": 2048,
                    "columns": [
                        {"name": "id", "type": "int", "is_primary_key": True},
                        {"name": "username", "type": "varchar", "max_length": 50},
                        {"name": "email", "type": "varchar", "max_length": 100},
                        {"name": "created_at", "type": "datetime"}
                    ],
                    "indexes": [
                        {"name": "PRIMARY", "type": "primary", "columns": ["id"]},
                        {"name": "idx_email", "type": "unique", "columns": ["email"]}
                    ]
                },
                {
                    "name": "orders",
                    "row_count": 100000,
                    "size_kb": 5120,
                    "columns": [
                        {"name": "id", "type": "int", "is_primary_key": True},
                        {"name": "user_id", "type": "int", "is_foreign_key": True, "foreign_table": "users"},
                        {"name": "total_amount", "type": "decimal"},
                        {"name": "status", "type": "varchar"},
                        {"name": "created_at", "type": "datetime"}
                    ],
                    "indexes": [
                        {"name": "PRIMARY", "type": "primary", "columns": ["id"]},
                        {"name": "idx_user_id", "type": "index", "columns": ["user_id"]}
                    ]
                }
            ]
        }
        
        result = await schema_inspector_service.inspect_schema(schema_info)
        
        print(f"✅ Schema检查成功")
        print(f"   整体健康评分: {result['overall_health_score']}")
        print(f"   复杂度评分: {result['complexity_score']}")
        print(f"   表数量: {result['table_count']}")
        print(f"   关系数量: {result['relationship_count']}")
        print(f"   优化机会: {len(result['optimization_opportunities'])}")
        print(f"   潜在问题: {len(result['potential_issues'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Schema检查器测试失败: {e}")
        return False


# 测试性能优化器
async def test_performance_optimizer():
    print("\n=== 测试性能优化器 ===")
    
    try:
        from backend.app.services.infrastructure.ai.performance.performance_optimizer_service import performance_optimizer_service
        
        # 测试性能优化
        performance_data = {
            "response_time": 3.5,
            "cpu_usage": 85.0,
            "memory_usage": 75.0,
            "error_rate": 0.08,
            "throughput": 150.0,
            "connection_pool_usage": 0.9,
            "cache_hit_rate": 0.65,
            "bottlenecks": ["database_query", "memory_usage"]
        }
        
        result = await performance_optimizer_service.optimize_performance(performance_data)
        
        print(f"✅ 性能优化分析成功")
        print(f"   整体性能评分: {result['overall_score']}")
        print(f"   当前响应时间: {result['current_performance']['response_time']}s")
        print(f"   优化后响应时间: {result['optimized_performance']['avg_response_time']:.2f}s")
        print(f"   检测到瓶颈: {len(result['bottlenecks'])}")
        print(f"   优化建议: {len(result['optimization_recommendations'])}")
        print(f"   快速改进机会: {len(result['quick_wins'])}")
        print(f"   改进潜力: {result['improvement_potential']['overall']:.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 性能优化器测试失败: {e}")
        return False


# 测试报告质量检查器
async def test_report_quality_checker():
    print("\n=== 测试报告质量检查器 ===")
    
    try:
        from backend.app.services.infrastructure.ai.quality.report_quality_checker_service import report_quality_checker_service
        
        # 测试报告质量检查
        report_content = """
        # 电商平台月度销售分析报告
        
        ## 摘要
        本月电商平台总销售额达到了1,250,000元，相比上月增长了15.8%。
        订单数量为8,500单，平均订单价值为147.06元。
        
        ## 详细分析
        
        ### 销售趋势
        根据数据显示，本月销售呈现稳定上升趋势。其中：
        - 手机类产品销售额占比35%，达到437,500元
        - 服装类产品销售额占比28%，达到350,000元
        - 家电类产品销售额占比22%，达到275,000元
        
        ### 用户行为分析
        通过分析用户购买行为，发现以下特点：
        1. 移动端购买占比达到68%
        2. 新用户转化率为12.5%
        3. 复购率达到35%
        
        ## 结论和建议
        基于以上分析，建议：
        1. 继续加强手机类产品的推广力度
        2. 优化移动端购买体验
        3. 实施新用户激励计划，提高转化率
        4. 通过个性化推荐提升复购率
        
        数据来源：电商平台业务系统
        """
        
        result = await report_quality_checker_service.check_report_quality(report_content)
        
        print(f"✅ 报告质量检查成功")
        print(f"   整体评分: {result['overall_score']}")
        print(f"   质量等级: {result['quality_level']}")
        print(f"   质量评级: {result['quality_grade']}")
        print(f"   是否可接受: {result['is_acceptable']}")
        print(f"   是否需要修订: {result['requires_revision']}")
        print(f"   发现问题: {len(result['issues'])}")
        print(f"   改进建议: {len(result['suggestions'])}")
        print(f"   自动改进机会: {len(result['auto_improvements'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 报告质量检查器测试失败: {e}")
        return False


# 测试上下文分析器
async def test_context_analyzer():
    print("\n=== 测试上下文分析器 ===")
    
    try:
        from backend.app.services.infrastructure.ai.context.context_analyzer_service import context_analyzer_service
        
        # 测试上下文分析
        context_data = {
            "user_query": "分析最近一个月的销售数据，特别关注手机产品的表现",
            "data_source": "mysql://localhost/ecommerce",
            "template": "monthly_sales_report.html",
            "business_context": "电商平台运营分析",
            "time_range": "last_month",
            "analysis_depth": "deep"
        }
        
        result = context_analyzer_service.analyze_context(context_data)
        
        print(f"✅ 上下文分析成功")
        print(f"   识别的上下文类型: {len(result['metadata']['context_types'])}")
        print(f"   生成的洞察: {len(result['insights'])}")
        print(f"   置信度提升: {result['confidence_improvement']:.2f}")
        print(f"   分析完成: {result['analysis_complete']}")
        print(f"   增强应用: {result['metadata']['enhancement_applied']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 上下文分析器测试失败: {e}")
        return False


# 测试增强推理
async def test_enhanced_reasoning():
    print("\n=== 测试增强推理 ===")
    
    try:
        from backend.app.services.infrastructure.ai.reasoning.enhanced_reasoning_service import enhanced_reasoning_service
        
        # 测试增强推理
        problem = "分析电商平台销售数据下降的可能原因，并提出解决方案"
        context = {
            "data": "sales_decline_analysis",
            "business_domain": "ecommerce",
            "time_period": "last_quarter",
            "stakeholders": ["marketing_team", "product_team", "management"]
        }
        
        result = await enhanced_reasoning_service.perform_reasoning(problem, context)
        
        print(f"✅ 增强推理成功")
        print(f"   推理步骤: {len(result['reasoning_steps'])}")
        print(f"   整体置信度: {result['confidence']}")
        print(f"   生成建议: {len(result['recommendations'])}")
        print(f"   推理模式: {result['metadata']['reasoning_pattern']}")
        print(f"   复杂度: {result['metadata']['complexity']}")
        print(f"   使用方法: {', '.join(result['metadata']['reasoning_methods'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 增强推理测试失败: {e}")
        return False


# 测试工具监控
async def test_tool_monitoring():
    print("\n=== 测试工具监控 ===")
    
    try:
        from backend.app.services.infrastructure.ai.monitoring.tool_monitor_service import tool_monitor_service
        
        # 启动监控
        tool_monitor_service.start_monitoring()
        
        # 模拟工具执行监控
        async def mock_tool_execution():
            await asyncio.sleep(0.1)  # 模拟工具执行
            return {"result": "success", "data": [1, 2, 3]}
        
        # 监控工具执行
        result = await tool_monitor_service.monitor_tool_execution(
            "test_tool",
            mock_tool_execution
        )
        
        # 获取系统概览
        overview = await tool_monitor_service.get_system_overview()
        
        print(f"✅ 工具监控成功")
        print(f"   监控状态: {'激活' if overview['monitoring_active'] else '未激活'}")
        print(f"   监控级别: {overview['monitoring_level']}")
        print(f"   监控工具数: {overview['total_tools_monitored']}")
        print(f"   总执行次数: {overview['total_executions']}")
        print(f"   整体成功率: {overview['overall_success_rate']:.1%}")
        
        # 获取工具性能报告
        report = await tool_monitor_service.get_tool_performance_report("test_tool")
        if report:
            print(f"   测试工具执行时间: {report.avg_execution_time:.3f}s")
            print(f"   测试工具成功率: {report.success_rate:.1%}")
        
        return True
        
    except Exception as e:
        print(f"❌ 工具监控测试失败: {e}")
        return False


# 主测试函数
async def main():
    print("🚀 开始测试高级AI工具实现...")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    # 按顺序执行测试
    tests = [
        ("SQL生成器", test_sql_generator),
        ("数据源分析器", test_data_source_analyzer), 
        ("Schema检查器", test_schema_inspector),
        ("性能优化器", test_performance_optimizer),
        ("报告质量检查器", test_report_quality_checker),
        ("上下文分析器", test_context_analyzer),
        ("增强推理", test_enhanced_reasoning),
        ("工具监控", test_tool_monitoring)
    ]
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            test_results[test_name] = success
        except Exception as e:
            print(f"❌ {test_name} 测试出现异常: {e}")
            test_results[test_name] = False
    
    # 输出测试总结
    print("\n" + "="*50)
    print("📊 测试结果总结")
    print("="*50)
    
    passed = 0
    failed = 0
    
    for test_name, success in test_results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{test_name:<20} {status}")
        if success:
            passed += 1
        else:
            failed += 1
    
    total = len(test_results)
    success_rate = (passed / total) * 100 if total > 0 else 0
    
    print("-" * 50)
    print(f"总测试数: {total}")
    print(f"通过: {passed}")  
    print(f"失败: {failed}")
    print(f"成功率: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 所有工具实现质量良好！")
    elif success_rate >= 70:
        print("\n✨ 大部分工具实现成功，少数需要调整")
    else:
        print("\n⚠️  部分工具需要进一步优化")
    
    return success_rate >= 70


if __name__ == "__main__":
    asyncio.run(main())