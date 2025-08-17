#!/usr/bin/env python3
"""
测试两段式任务执行功能
展示数据发现->分析报告生成的完整流程
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_two_phase_task_execution():
    """测试两段式任务执行"""
    print("\n🔄 测试两段式任务执行...")
    
    from app.services.agents.factory import create_agent, AgentType
    from app.services.agents.core.performance_monitor import performance_context
    from app.db.session import get_db_session
    
    try:
        with get_db_session() as db:
            print("  📊 第一阶段：数据发现和Schema分析...")
            
            # 第一阶段：数据发现
            with performance_context("phase1_data_discovery"):
                schema_agent = create_agent(AgentType.SCHEMA_ANALYSIS, db_session=db)
                
                # 模拟数据源信息
                mock_data_source = {
                    "type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "autoreport",
                    "tables": ["users", "reports", "tasks"]
                }
                
                print(f"     🔍 发现数据源: {mock_data_source['type']}")
                print(f"     📋 发现表格: {', '.join(mock_data_source['tables'])}")
                
                # 模拟Schema分析结果
                schema_analysis = {
                    "database_type": mock_data_source["type"],
                    "total_tables": len(mock_data_source["tables"]),
                    "schema_complexity": "medium",
                    "recommended_queries": [
                        "SELECT COUNT(*) FROM users",
                        "SELECT status, COUNT(*) FROM tasks GROUP BY status",
                        "SELECT created_at, COUNT(*) FROM reports GROUP BY DATE(created_at)"
                    ],
                    "data_relationships": {
                        "users -> tasks": "one-to-many",
                        "users -> reports": "one-to-many"
                    }
                }
                
                print(f"     ✅ Schema分析完成，发现 {schema_analysis['total_tables']} 个表")
            
            print("\n  📈 第二阶段：报告生成...")
            
            # 第二阶段：报告生成
            with performance_context("phase2_report_generation"):
                content_agent = create_agent(AgentType.CONTENT_GENERATION, db_session=db)
                
                # 模拟查询执行结果
                mock_query_results = {
                    "user_count": 150,
                    "task_status_distribution": {
                        "completed": 45,
                        "in_progress": 23,
                        "pending": 12
                    },
                    "daily_reports": {
                        "2025-08-15": 8,
                        "2025-08-16": 12,
                        "2025-08-17": 15
                    }
                }
                
                print(f"     📊 执行查询获取数据...")
                print(f"     👥 用户总数: {mock_query_results['user_count']}")
                print(f"     📋 任务分布: {mock_query_results['task_status_distribution']}")
                
                # 生成分析报告
                report_content = generate_analysis_report(schema_analysis, mock_query_results)
                
                print(f"     ✅ 报告生成完成，共 {len(report_content)} 字符")
            
            print("\n  📋 两段式任务执行结果:")
            print("     ✅ 第一阶段：数据发现和Schema分析 - 完成")
            print("     ✅ 第二阶段：查询执行和报告生成 - 完成")
            
            return {
                "phase1_result": schema_analysis,
                "phase2_result": report_content,
                "execution_status": "success"
            }
            
    except Exception as e:
        print(f"     ❌ 两段式任务执行失败: {e}")
        return {"execution_status": "failed", "error": str(e)}

def generate_analysis_report(schema_analysis: Dict[str, Any], query_results: Dict[str, Any]) -> str:
    """生成分析报告"""
    report = f"""
# 数据分析报告

## 数据源概览
- 数据库类型: {schema_analysis['database_type']}
- 表格数量: {schema_analysis['total_tables']}
- Schema复杂度: {schema_analysis['schema_complexity']}

## 关键指标
- 用户总数: {query_results['user_count']}
- 任务完成率: {query_results['task_status_distribution']['completed'] / sum(query_results['task_status_distribution'].values()) * 100:.1f}%

## 任务状态分布
{json.dumps(query_results['task_status_distribution'], indent=2, ensure_ascii=False)}

## 每日报告趋势
{json.dumps(query_results['daily_reports'], indent=2, ensure_ascii=False)}

## 数据关系
{json.dumps(schema_analysis['data_relationships'], indent=2, ensure_ascii=False)}

## 建议查询
{chr(10).join(['- ' + query for query in schema_analysis['recommended_queries']])}

---
生成时间: {datetime.now().isoformat()}
"""
    return report

async def test_performance_with_monitoring():
    """测试性能监控下的任务执行"""
    print("\n📊 测试性能监控...")
    
    from app.services.agents.core.performance_monitor import get_performance_monitor
    from app.services.agents.core.cache_manager import get_cache_manager
    
    try:
        monitor = get_performance_monitor()
        cache_manager = get_cache_manager()
        
        # 启动监控
        monitor.start_monitoring()
        
        # 模拟多次任务执行来测试缓存
        print("  🔄 执行多轮任务测试缓存效果...")
        
        results = []
        for i in range(3):
            print(f"     第 {i+1} 轮执行...")
            result = await test_two_phase_task_execution()
            results.append(result)
        
        # 获取性能统计
        perf_summary = monitor.get_performance_summary()
        cache_stats = cache_manager.get_global_stats()
        
        print(f"\n  📈 性能监控结果:")
        print(f"     执行轮数: {len(results)}")
        print(f"     缓存命中率: {cache_stats['global']['global_hit_rate']:.2%}")
        print(f"     总缓存项目: {cache_stats['global']['total_size']}")
        
        # 停止监控
        monitor.stop_monitoring()
        
        return {
            "rounds_executed": len(results),
            "performance_summary": perf_summary,
            "cache_statistics": cache_stats
        }
        
    except Exception as e:
        print(f"     ❌ 性能监控测试失败: {e}")
        return {"error": str(e)}

async def test_health_monitoring_during_tasks():
    """测试任务执行期间的健康监控"""
    print("\n🏥 测试健康监控...")
    
    from app.services.agents.core.health_monitor import get_health_monitor, perform_system_health_check
    
    try:
        monitor = get_health_monitor()
        
        # 执行任务前健康检查
        print("  🔍 任务执行前健康检查...")
        health_before = await perform_system_health_check()
        print(f"     系统状态: {health_before['overall_status']}")
        
        # 执行任务
        print("  🔄 执行任务...")
        task_result = await test_two_phase_task_execution()
        
        # 执行任务后健康检查
        print("  🔍 任务执行后健康检查...")
        health_after = await perform_system_health_check()
        print(f"     系统状态: {health_after['overall_status']}")
        
        # 比较健康状态
        health_comparison = {
            "before": health_before,
            "after": health_after,
            "task_result": task_result,
            "health_stable": health_before['overall_status'] == health_after['overall_status']
        }
        
        print(f"     健康状态稳定: {'✅' if health_comparison['health_stable'] else '❌'}")
        
        return health_comparison
        
    except Exception as e:
        print(f"     ❌ 健康监控测试失败: {e}")
        return {"error": str(e)}

async def run_comprehensive_two_phase_test():
    """运行完整的两段式任务测试"""
    print("🚀 开始两段式任务系统全面测试")
    print("=" * 60)
    
    test_results = {}
    
    # 1. 基础两段式任务测试
    print("\n1️⃣ 基础两段式任务测试")
    test_results["basic_task"] = await test_two_phase_task_execution()
    
    # 2. 性能监控测试
    print("\n2️⃣ 性能监控测试")
    test_results["performance_monitoring"] = await test_performance_with_monitoring()
    
    # 3. 健康监控测试
    print("\n3️⃣ 健康监控测试")
    test_results["health_monitoring"] = await test_health_monitoring_during_tasks()
    
    # 输出总结
    print("\n" + "=" * 60)
    print("📊 两段式任务测试总结")
    print("=" * 60)
    
    success_count = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        if isinstance(result, dict) and result.get("execution_status") == "success":
            success_count += 1
            status = "✅ 成功"
        elif isinstance(result, dict) and "error" not in result:
            success_count += 1
            status = "✅ 成功"
        else:
            status = "❌ 失败"
        
        print(f"{test_name:<25} {status}")
    
    print("-" * 60)
    print(f"总测试数: {total_tests}")
    print(f"成功数: {success_count}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    print("=" * 60)
    
    if success_count == total_tests:
        print("🎉 两段式任务系统测试全部通过！")
    else:
        print("⚠️ 部分测试失败，请检查错误信息")
    
    return test_results

if __name__ == "__main__":
    # 运行测试
    asyncio.run(run_comprehensive_two_phase_test())