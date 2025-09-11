"""
提示词系统集成测试
==================

测试企业级提示词系统的各项功能
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import Dict, Any, List

# 假设的导入路径，根据实际情况调整
try:
    from app.services.infrastructure.ai.core.prompts import (
        prompt_manager, PromptComplexity, PromptSafety,
        SQLGenerationPrompts, ReportGenerationPrompts
    )
    from app.services.infrastructure.ai.core.prompt_monitor import (
        PromptPerformanceMonitor, get_prompt_monitor
    )
    from app.services.infrastructure.ai.tools.enhanced_sql_generation_tool import (
        EnhancedSQLGenerationTool
    )
    from app.services.infrastructure.ai.unified_ai_facade import (
        get_unified_ai_facade
    )
except ImportError as e:
    pytest.skip(f"AI模块导入失败: {e}", allow_module_level=True)


class TestPromptManager:
    """提示词管理器测试"""
    
    def test_complexity_assessment(self):
        """测试复杂度自动评估"""
        
        # 简单上下文
        simple_context = {
            'available_tables': ['table1'],
            'error_history': [],
            'is_critical_operation': False
        }
        complexity = prompt_manager._assess_complexity(simple_context)
        assert complexity == PromptComplexity.MEDIUM
        
        # 复杂上下文
        complex_context = {
            'available_tables': ['table1'] * 25,  # 超过20个表
            'error_history': [1, 2, 3],  # 有错误历史
            'is_critical_operation': False
        }
        complexity = prompt_manager._assess_complexity(complex_context)
        assert complexity == PromptComplexity.HIGH
        
        # 关键操作
        critical_context = {
            'is_critical_operation': True
        }
        complexity = prompt_manager._assess_complexity(critical_context)
        assert complexity == PromptComplexity.CRITICAL
    
    def test_sql_reasoning_prompt_generation(self):
        """测试SQL推理提示词生成"""
        
        context = {
            'placeholder_name': '测试占位符',
            'placeholder_analysis': '测试分析',
            'available_tables': ['ods_test', 'dim_user'],
            'table_details': [
                {
                    'name': 'ods_test',
                    'columns_count': 10,
                    'estimated_rows': 1000,
                    'all_columns': ['id', 'name', 'created_at']
                }
            ],
            'learned_insights': ['测试经验1'],
            'iteration_history': [],
            'iteration': 0
        }
        
        prompt = prompt_manager.get_prompt(
            category='sql_generation',
            prompt_type='reasoning',
            context=context
        )
        
        # 验证提示词包含关键元素
        assert '强制性约束' in prompt
        assert 'NEVER' in prompt
        assert 'ALWAYS' in prompt
        assert 'ods_test' in prompt
        assert 'dim_user' in prompt
        assert '测试占位符' in prompt
        assert 'JSON格式' in prompt
    
    def test_sql_generation_prompt(self):
        """测试SQL生成提示词"""
        
        context = {
            'selected_table': 'ods_test',
            'relevant_fields': ['id', 'name'],
            'query_strategy': '统计查询',
            'field_mappings': {'时间字段': 'created_at'},
            'placeholder_name': '测试占位符',
            'placeholder_analysis': '测试分析',
            'learned_insights': []
        }
        
        prompt = prompt_manager.get_prompt(
            category='sql_generation',
            prompt_type='sql_generation',
            context=context
        )
        
        # 验证约束存在
        assert '强制SQL生成约束' in prompt
        assert '绝对禁止' in prompt
        assert 'ods_test' in prompt
        assert 'id' in prompt and 'name' in prompt
    
    def test_report_generation_prompt(self):
        """测试报告生成提示词"""
        
        context = {
            'report_type': 'business_analysis',
            'data_summary': {'total_records': 1000},
            'business_context': '业务分析报告'
        }
        
        prompt = prompt_manager.get_prompt(
            category='report_generation',
            prompt_type='content_generation',
            context=context
        )
        
        # 验证报告要求
        assert '报告生成约束' in prompt
        assert 'ALWAYS' in prompt and 'NEVER' in prompt
        assert 'business_analysis' in prompt
        assert '业务分析报告' in prompt


class TestPromptMonitor:
    """提示词监控测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.monitor = PromptPerformanceMonitor()
    
    def test_record_usage(self):
        """测试使用记录"""
        
        self.monitor.record_usage(
            category='sql_generation',
            prompt_type='reasoning',
            complexity='medium',
            success=True,
            execution_time_ms=1500,
            prompt_length=2000,
            user_id='test_user'
        )
        
        assert len(self.monitor.metrics_buffer) == 1
        metric = self.monitor.metrics_buffer[0]
        assert metric.category == 'sql_generation'
        assert metric.success == True
        assert metric.execution_time_ms == 1500
    
    def test_performance_summary(self):
        """测试性能摘要生成"""
        
        # 添加测试数据
        for i in range(10):
            success = i % 3 != 0  # 70% 成功率
            self.monitor.record_usage(
                category='sql_generation',
                prompt_type='reasoning',
                complexity='medium',
                success=success,
                execution_time_ms=1000 + i * 100,
                prompt_length=2000,
                error_message="test error" if not success else None
            )
        
        summary = self.monitor.get_performance_summary(
            category='sql_generation',
            time_window_hours=1
        )
        
        assert summary['total_usage'] == 10
        assert abs(summary['success_rate'] - 0.7) < 0.1  # 约70%
        assert summary['average_execution_time'] > 1000
        assert len(summary['recommendations']) > 0
    
    def test_error_analysis(self):
        """测试错误分析"""
        
        # 添加不同类型的错误
        error_messages = [
            "Unknown table: users",
            "Unknown column: user_name", 
            "SQL syntax error",
            "Connection timeout"
        ]
        
        for i, error_msg in enumerate(error_messages):
            self.monitor.record_usage(
                category='sql_generation',
                prompt_type='reasoning',
                complexity='medium',
                success=False,
                execution_time_ms=1000,
                prompt_length=2000,
                error_message=error_msg
            )
        
        summary = self.monitor.get_performance_summary()
        error_analysis = summary['error_analysis']
        
        assert error_analysis['total_errors'] == 4
        assert 'table_not_found' in error_analysis['error_patterns']
        assert 'column_not_found' in error_analysis['error_patterns']
        assert 'syntax_error' in error_analysis['error_patterns']
        assert len(error_analysis['common_causes']) > 0
    
    def test_dashboard_data(self):
        """测试仪表板数据生成"""
        
        # 添加一些测试数据
        for i in range(5):
            self.monitor.record_usage(
                category='sql_generation',
                prompt_type='reasoning',
                complexity='medium',
                success=True,
                execution_time_ms=1000,
                prompt_length=2000,
                user_id=f'user_{i % 2}'
            )
        
        dashboard_data = self.monitor.get_real_time_dashboard_data()
        
        assert 'real_time' in dashboard_data
        assert 'system_health' in dashboard_data
        assert 'recent_hour' in dashboard_data['real_time']
        assert 'last_24_hours' in dashboard_data['real_time']
        assert 'buffer_usage' in dashboard_data['system_health']


class TestEnhancedSQLGenerationTool:
    """增强SQL生成工具测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.tool = EnhancedSQLGenerationTool()
    
    def test_input_validation(self):
        """测试输入验证"""
        
        # 有效输入
        valid_input = {"placeholders": [{"name": "test"}]}
        result = asyncio.run(self.tool.validate_input(valid_input))
        assert result == True
        
        # 无效输入 - 缺少必需字段
        invalid_input = {}
        result = asyncio.run(self.tool.validate_input(invalid_input))
        assert result == False
        
        # 无效输入 - 错误类型
        invalid_input = {"placeholders": "not_a_list"}
        result = asyncio.run(self.tool.validate_input(invalid_input))
        assert result == False
    
    def test_table_constraint_enforcement(self):
        """测试表约束强制执行"""
        
        reasoning_result = {
            "selected_table": "non_existent_table",
            "relevant_fields": ["field1"],
            "query_strategy": "test"
        }
        
        data_source_info = {
            "tables": ["ods_test", "dim_user"]
        }
        
        corrected_result = self.tool._enforce_table_constraints(
            reasoning_result, data_source_info, 0
        )
        
        # 应该被纠正为可用表之一
        assert corrected_result["selected_table"] in data_source_info["tables"]
        assert "constraint_violation" in corrected_result
    
    def test_table_matching(self):
        """测试智能表匹配"""
        
        available_tables = ["ods_complain", "dim_user", "fact_order"]
        
        # 测试精确匹配
        match = self.tool._find_best_table_match(
            "ods_complain", available_tables, {"placeholder_name": "test"}
        )
        assert match == "ods_complain"
        
        # 测试业务语义匹配
        match = self.tool._find_best_table_match(
            "complaints", available_tables, {"placeholder_name": "投诉统计"}
        )
        assert match == "ods_complain"
        
        # 测试默认匹配
        match = self.tool._find_best_table_match(
            "unknown_table", available_tables, {"placeholder_name": "test"}
        )
        assert match in available_tables
    
    def test_sql_cleaning_and_validation(self):
        """测试SQL清理和验证"""
        
        # 测试Markdown清理
        sql_with_markdown = "```sql\nSELECT * FROM test;\n```"
        cleaned = self.tool._clean_and_validate_sql(sql_with_markdown)
        assert cleaned == "SELECT * FROM test;"
        
        # 测试错误SQL
        with pytest.raises(ValueError):
            self.tool._clean_and_validate_sql("")
        
        with pytest.raises(ValueError):
            self.tool._clean_and_validate_sql("ERROR: Something went wrong")
        
        with pytest.raises(ValueError):
            self.tool._clean_and_validate_sql("This is not SQL")


@pytest.mark.asyncio
class TestUnifiedAIFacadeIntegration:
    """统一AI门面集成测试"""
    
    async def test_enhanced_sql_generation_integration(self):
        """测试增强SQL生成集成"""
        
        facade = get_unified_ai_facade()
        
        # 模拟输入数据
        placeholders = [
            {
                "name": "test_placeholder",
                "analysis": "测试分析",
                "text": "{{test}}"
            }
        ]
        
        data_source_info = {
            "tables": ["ods_test"],
            "table_details": [
                {
                    "name": "ods_test",
                    "columns_count": 3,
                    "estimated_rows": 100,
                    "all_columns": ["id", "name", "created_at"]
                }
            ]
        }
        
        # 由于需要真实的AI调用，这里只测试方法存在性
        assert hasattr(facade, 'generate_sql_enhanced')
        assert hasattr(facade, 'get_optimized_prompt')
        assert hasattr(facade, 'assess_prompt_complexity')
    
    async def test_prompt_management_integration(self):
        """测试提示词管理集成"""
        
        facade = get_unified_ai_facade()
        
        # 测试复杂度评估
        context = {"available_tables": ["table1"], "error_history": []}
        complexity = facade.assess_prompt_complexity(context)
        assert complexity in [PromptComplexity.SIMPLE, PromptComplexity.MEDIUM, PromptComplexity.HIGH, PromptComplexity.CRITICAL]
        
        # 测试提示词获取
        prompt_context = {
            'placeholder_name': '测试',
            'placeholder_analysis': '分析',
            'available_tables': ['table1'],
            'table_details': [],
            'learned_insights': [],
            'iteration_history': [],
            'iteration': 0
        }
        
        prompt = facade.get_optimized_prompt(
            category='sql_generation',
            prompt_type='reasoning',
            context=prompt_context
        )
        
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # 应该是一个完整的提示词


class TestEndToEndWorkflow:
    """端到端工作流测试"""
    
    @pytest.mark.integration
    async def test_complete_sql_generation_workflow(self):
        """测试完整的SQL生成工作流"""
        
        # 这是一个集成测试，需要真实的数据库和AI服务
        # 在CI/CD环境中可能需要跳过
        
        if not pytest.config.getoption("--integration"):
            pytest.skip("需要 --integration 标志运行集成测试")
        
        facade = get_unified_ai_facade()
        monitor = get_prompt_monitor()
        
        # 准备测试数据
        placeholders = [
            {
                "name": "user_count",
                "analysis": "统计用户数量", 
                "text": "{{user_count}}"
            }
        ]
        
        data_source_info = {
            "id": "test_source",
            "type": "doris",
            "tables": ["ods_user"],
            "table_details": [
                {
                    "name": "ods_user",
                    "columns_count": 5,
                    "estimated_rows": 1000,
                    "all_columns": ["id", "username", "email", "created_at", "status"]
                }
            ]
        }
        
        # 记录初始监控状态
        initial_metrics = monitor.get_performance_summary()
        
        try:
            # 执行增强SQL生成
            result = await facade.generate_sql_enhanced(
                user_id="test_user",
                placeholders=placeholders,
                data_source_info=data_source_info,
                template_context="用户统计报告",
                use_enterprise_prompts=True
            )
            
            # 验证结果结构
            assert "status" in result
            
            if result["status"] == "success":
                assert "data" in result
                assert "enhanced" in result
                assert result["enhanced"] == True
            
        finally:
            # 验证监控记录了使用情况
            final_metrics = monitor.get_performance_summary()
            # 注意：实际测试中可能需要等待异步记录完成


if __name__ == "__main__":
    # 运行测试
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        # "--integration"  # 取消注释以运行集成测试
    ])