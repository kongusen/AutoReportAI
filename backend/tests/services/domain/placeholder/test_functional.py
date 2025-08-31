"""
占位符系统功能验证测试
测试各类统计类型和语法类型的处理功能
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any, List

from app.services.domain.placeholder.parsers import ParserFactory
from app.services.domain.placeholder.orchestrator import PlaceholderOrchestrator
from app.services.domain.placeholder.models import (
    PlaceholderSpec,
    DocumentContext, 
    BusinessContext,
    TimeContext,
    StatisticalType,
    SyntaxType
)


class TestStatisticalTypeFunctionality:
    """统计类型功能测试"""
    
    @pytest.fixture
    def parser_factory(self):
        """解析器工厂"""
        return ParserFactory()
    
    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        return Mock()
    
    @pytest.fixture
    def orchestrator(self, mock_db_session):
        """占位符编排器"""
        return PlaceholderOrchestrator(db_session=mock_db_session)

    def test_statistical_type_identification(self, parser_factory):
        """测试统计类型识别"""
        test_cases = [
            # 基础统计类型
            ("总销售额：{{total_sales}} 万元", StatisticalType.STATISTICAL),
            ("平均收入：{{avg_revenue}} 元", StatisticalType.STATISTICAL), 
            ("客户数量：{{customer_count}} 人", StatisticalType.STATISTICAL),
            ("最高销量：{{max_sales}} 件", StatisticalType.STATISTICAL),
            
            # 趋势类型
            ("增长率：{{growth_rate}} %", StatisticalType.TREND),
            ("同比增长：{{yoy_growth}} %", StatisticalType.TREND),
            ("月度变化：{{monthly_change}} %", StatisticalType.TREND),
            ("趋势分析：{{trend_analysis}}", StatisticalType.TREND),
            
            # 对比类型
            ("本年vs去年：{{current_vs_last_year}}", StatisticalType.COMPARISON),
            ("产品A对比产品B：{{product_a_vs_b}}", StatisticalType.COMPARISON),
            ("实际vs预算：{{actual_vs_budget}}", StatisticalType.COMPARISON),
            
            # 排名类型
            ("销售排名：{{sales_ranking}}", StatisticalType.RANKING),
            ("TOP5客户：{{top5_customers}}", StatisticalType.RANKING),
            ("地区排行：{{region_ranking}}", StatisticalType.RANKING),
            
            # 预测类型
            ("下季度预测：{{next_quarter_forecast}}", StatisticalType.FORECAST),
            ("年末预计：{{year_end_prediction}}", StatisticalType.FORECAST),
            ("趋势预测：{{trend_prediction}}", StatisticalType.FORECAST),
            
            # 分布类型
            ("年龄分布：{{age_distribution}}", StatisticalType.DISTRIBUTION),
            ("地区分布：{{regional_distribution}}", StatisticalType.DISTRIBUTION),
            ("收入分布：{{income_distribution}}", StatisticalType.DISTRIBUTION),
            
            # 占比类型
            ("市场占有率：{{market_share}} %", StatisticalType.PROPORTION),
            ("成本占比：{{cost_ratio}} %", StatisticalType.PROPORTION),
            ("完成度：{{completion_rate}} %", StatisticalType.PROPORTION),
        ]
        
        for content, expected_type in test_cases:
            placeholders = parser_factory.parse_with_auto_detection(content)
            
            assert len(placeholders) == 1, f"内容'{content}'应该解析出1个占位符"
            placeholder = placeholders[0]
            
            # 验证统计类型识别
            assert placeholder.statistical_type == expected_type, \
                f"内容'{content}'的统计类型应该是{expected_type.value}，实际是{placeholder.statistical_type.value}"

    def test_syntax_type_identification(self, parser_factory):
        """测试语法类型识别"""
        test_cases = [
            # 基础语法
            ("{{simple_placeholder}}", SyntaxType.BASIC),
            ("{{sales_total}}", SyntaxType.BASIC),
            
            # 参数化语法
            ("{{revenue(region='北京', year=2023)}}", SyntaxType.PARAMETERIZED),
            ("{{sales(product='手机', quarter='Q1')}}", SyntaxType.PARAMETERIZED),
            ("{{growth(period='monthly', type='yoy')}}", SyntaxType.PARAMETERIZED),
            
            # 复合语法
            ("{{sum(sales_q1, sales_q2, sales_q3, sales_q4)}}", SyntaxType.COMPOSITE),
            ("{{avg(revenue_jan, revenue_feb, revenue_mar)}}", SyntaxType.COMPOSITE),
            ("{{(current_sales - last_year_sales) / last_year_sales * 100}}", SyntaxType.COMPOSITE),
            
            # 条件语法
            ("{{if sales > target then '达标' else '未达标'}}", SyntaxType.CONDITIONAL),
            ("{{if growth_rate > 10 then '优秀' else if growth_rate > 0 then '良好' else '需改进'}}", SyntaxType.CONDITIONAL),
            ("{{case when revenue > 1000000 then '大客户' when revenue > 100000 then '中客户' else '小客户' end}}", SyntaxType.CONDITIONAL),
        ]
        
        for content, expected_type in test_cases:
            placeholders = parser_factory.parse_with_auto_detection(content)
            
            assert len(placeholders) >= 1, f"内容'{content}'应该解析出至少1个占位符"
            
            # 找到主要的占位符（通常是第一个或最复杂的那个）
            main_placeholder = placeholders[0]
            
            assert main_placeholder.syntax_type == expected_type, \
                f"内容'{content}'的语法类型应该是{expected_type.value}，实际是{main_placeholder.syntax_type.value}"

    @pytest.mark.asyncio
    async def test_statistical_sql_generation(self, orchestrator):
        """测试统计类型的SQL生成功能"""
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            
            # 模拟不同统计类型的SQL生成结果
            def mock_sql_generation(placeholders, context=None):
                results = []
                for placeholder in placeholders:
                    content = placeholder.get("content", "")
                    
                    if "total" in content or "sum" in content:
                        sql = f"SELECT SUM(amount) FROM sales WHERE conditions"
                    elif "avg" in content or "average" in content:
                        sql = f"SELECT AVG(amount) FROM sales WHERE conditions"
                    elif "count" in content:
                        sql = f"SELECT COUNT(*) FROM sales WHERE conditions"
                    elif "max" in content:
                        sql = f"SELECT MAX(amount) FROM sales WHERE conditions"
                    elif "min" in content:
                        sql = f"SELECT MIN(amount) FROM sales WHERE conditions"
                    elif "growth" in content or "rate" in content:
                        sql = f"SELECT (current.amount - previous.amount) / previous.amount * 100 FROM sales current JOIN sales previous WHERE conditions"
                    elif "ranking" in content or "top" in content:
                        sql = f"SELECT *, ROW_NUMBER() OVER (ORDER BY amount DESC) as ranking FROM sales WHERE conditions"
                    elif "distribution" in content:
                        sql = f"SELECT category, COUNT(*), percentage FROM sales GROUP BY category WHERE conditions"
                    else:
                        sql = f"SELECT amount FROM sales WHERE conditions"
                    
                    results.append({
                        "content": content,
                        "statistical_type": placeholder.get("statistical_type", "STATISTICAL"),
                        "generated_sql": sql,
                        "confidence_score": 0.9
                    })
                
                return {
                    "success": True,
                    "placeholders": results
                }
            
            mock_agent_service.analyze_placeholders.side_effect = mock_sql_generation
            mock_agents.return_value = mock_agent_service
            
            # 测试各种统计类型的SQL生成
            test_contents = [
                "总销售额：{{total_sales}} 万元",
                "平均收入：{{average_revenue}} 元", 
                "客户总数：{{customer_count}} 人",
                "最高销量：{{max_sales}} 件",
                "增长率：{{growth_rate}} %",
                "销售排名：{{sales_ranking}}",
                "地区分布：{{region_distribution}}",
            ]
            
            for content in test_contents:
                document_context = DocumentContext(
                    document_id="sql_test",
                    title="SQL生成测试",
                    content=content,
                    metadata={"type": "功能测试"}
                )
                
                result = await orchestrator.process_document_placeholders(
                    content=content,
                    document_context=document_context,
                    business_context=None
                )
                
                # 验证SQL生成结果
                assert result["success"] is True
                assert len(result["placeholders"]) == 1
                
                placeholder_result = result["placeholders"][0]
                assert "generated_sql" in placeholder_result
                assert placeholder_result["generated_sql"] is not None
                assert len(placeholder_result["generated_sql"]) > 0
                
                # 验证SQL包含相应的关键词
                sql = placeholder_result["generated_sql"].upper()
                content_lower = content.lower()
                
                if "total" in content_lower or "sum" in content_lower:
                    assert "SUM" in sql
                elif "average" in content_lower or "avg" in content_lower:
                    assert "AVG" in sql
                elif "count" in content_lower:
                    assert "COUNT" in sql
                elif "max" in content_lower:
                    assert "MAX" in sql
                elif "growth" in content_lower or "rate" in content_lower:
                    assert "JOIN" in sql or "OVER" in sql
                elif "ranking" in content_lower or "top" in content_lower:
                    assert "ROW_NUMBER" in sql or "RANK" in sql
                elif "distribution" in content_lower:
                    assert "GROUP BY" in sql

class TestComplexPlaceholderFunctionality:
    """复杂占位符功能测试"""
    
    @pytest.fixture
    def orchestrator(self):
        """占位符编排器"""
        return PlaceholderOrchestrator(db_session=Mock())

    @pytest.mark.asyncio
    async def test_parameterized_placeholder_processing(self, orchestrator):
        """测试参数化占位符处理功能"""
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            
            def mock_parameterized_sql(placeholders, context=None):
                results = []
                for placeholder in placeholders:
                    content = placeholder.get("content", "")
                    parameters = placeholder.get("parameters", {})
                    
                    # 解析参数化占位符的参数
                    if "region=" in content and "year=" in content:
                        sql = f"SELECT SUM(amount) FROM sales WHERE region = 'extracted_region' AND year = extracted_year"
                    elif "product=" in content:
                        sql = f"SELECT amount FROM sales WHERE product = 'extracted_product'"
                    else:
                        sql = f"SELECT amount FROM sales WHERE conditions_from_parameters"
                    
                    results.append({
                        "content": content,
                        "generated_sql": sql,
                        "parameters": parameters,
                        "confidence_score": 0.85
                    })
                
                return {
                    "success": True,
                    "placeholders": results
                }
            
            mock_agent_service.analyze_placeholders.side_effect = mock_parameterized_sql
            mock_agents.return_value = mock_agent_service
            
            # 测试参数化占位符
            test_cases = [
                "北京地区销售额：{{sales(region='北京', year=2023)}} 万元",
                "手机产品收入：{{revenue(product='手机', quarter='Q1')}} 元",
                "华东区增长率：{{growth_rate(region='华东', period='monthly')}} %",
            ]
            
            for content in test_cases:
                document_context = DocumentContext(
                    document_id="param_test",
                    title="参数化测试",
                    content=content,
                    metadata={"type": "参数化测试"}
                )
                
                result = await orchestrator.process_document_placeholders(
                    content=content,
                    document_context=document_context
                )
                
                assert result["success"] is True
                assert len(result["placeholders"]) == 1
                
                placeholder_result = result["placeholders"][0]
                assert "generated_sql" in placeholder_result
                assert placeholder_result["generated_sql"] is not None

    @pytest.mark.asyncio  
    async def test_composite_placeholder_processing(self, orchestrator):
        """测试复合占位符处理功能"""
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            
            def mock_composite_sql(placeholders, context=None):
                results = []
                for placeholder in placeholders:
                    content = placeholder.get("content", "")
                    
                    if "sum(" in content:
                        sql = f"SELECT (SELECT amount FROM table1) + (SELECT amount FROM table2) + (SELECT amount FROM table3)"
                    elif "/" in content and "*" in content:
                        sql = f"SELECT (current_value - previous_value) / previous_value * 100"
                    elif "avg(" in content:
                        sql = f"SELECT AVG(sub_values) FROM (subquery)"
                    else:
                        sql = f"SELECT complex_calculation"
                    
                    results.append({
                        "content": content,
                        "generated_sql": sql,
                        "confidence_score": 0.8
                    })
                
                return {
                    "success": True,
                    "placeholders": results
                }
            
            mock_agent_service.analyze_placeholders.side_effect = mock_composite_sql
            mock_agents.return_value = mock_agent_service
            
            # 测试复合占位符
            test_cases = [
                "年度总销售额：{{sum(q1_sales, q2_sales, q3_sales, q4_sales)}} 万元",
                "增长率计算：{{(current_sales - last_year_sales) / last_year_sales * 100}} %",
                "平均季度收入：{{avg(q1_revenue, q2_revenue, q3_revenue, q4_revenue)}} 元",
            ]
            
            for content in test_cases:
                document_context = DocumentContext(
                    document_id="composite_test",
                    title="复合占位符测试",
                    content=content,
                    metadata={"type": "复合测试"}
                )
                
                result = await orchestrator.process_document_placeholders(
                    content=content,
                    document_context=document_context
                )
                
                assert result["success"] is True
                assert len(result["placeholders"]) >= 1
                
                # 验证复合占位符的SQL生成
                for placeholder_result in result["placeholders"]:
                    if "sum(" in placeholder_result["content"]:
                        assert "+" in placeholder_result["generated_sql"] or "SUM" in placeholder_result["generated_sql"].upper()
                    elif "/" in placeholder_result["content"] and "*" in placeholder_result["content"]:
                        assert "/" in placeholder_result["generated_sql"] and "*" in placeholder_result["generated_sql"]

    @pytest.mark.asyncio
    async def test_conditional_placeholder_processing(self, orchestrator):
        """测试条件占位符处理功能"""
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            
            def mock_conditional_sql(placeholders, context=None):
                results = []
                for placeholder in placeholders:
                    content = placeholder.get("content", "")
                    
                    if "if" in content and "then" in content and "else" in content:
                        sql = f"SELECT CASE WHEN condition THEN 'value1' ELSE 'value2' END"
                    elif "case when" in content:
                        sql = f"SELECT CASE WHEN condition1 THEN 'value1' WHEN condition2 THEN 'value2' ELSE 'default' END"
                    else:
                        sql = f"SELECT conditional_logic"
                    
                    results.append({
                        "content": content,
                        "generated_sql": sql,
                        "confidence_score": 0.75
                    })
                
                return {
                    "success": True,
                    "placeholders": results
                }
            
            mock_agent_service.analyze_placeholders.side_effect = mock_conditional_sql
            mock_agents.return_value = mock_agent_service
            
            # 测试条件占位符
            test_cases = [
                "完成状态：{{if sales > target then '超额完成' else '未达标'}}",
                "业绩等级：{{if performance > 90 then '优秀' else if performance > 70 then '良好' else '需改进'}}",
                "客户分类：{{case when revenue > 1000000 then '大客户' when revenue > 100000 then '中客户' else '小客户' end}}",
            ]
            
            for content in test_cases:
                document_context = DocumentContext(
                    document_id="conditional_test",
                    title="条件占位符测试", 
                    content=content,
                    metadata={"type": "条件测试"}
                )
                
                result = await orchestrator.process_document_placeholders(
                    content=content,
                    document_context=document_context
                )
                
                assert result["success"] is True
                assert len(result["placeholders"]) >= 1
                
                # 验证条件占位符的SQL生成
                for placeholder_result in result["placeholders"]:
                    if "if" in placeholder_result["content"] or "case" in placeholder_result["content"]:
                        sql = placeholder_result["generated_sql"].upper()
                        assert "CASE" in sql and ("WHEN" in sql or "IF" in sql)

class TestBusinessContextFunctionality:
    """业务上下文功能测试"""
    
    @pytest.mark.asyncio
    async def test_business_rule_validation(self):
        """测试业务规则验证功能"""
        from app.services.domain.placeholder.context import BusinessRuleAnalyzer
        
        analyzer = BusinessRuleAnalyzer()
        
        # 测试业务规则验证
        content = "销售额 {{sales_amount}} 增长率 {{growth_rate}} 必须符合业务规则"
        
        business_context = BusinessContext(
            domain="销售分析",
            rules=[
                "销售额必须大于0",
                "增长率范围在-50%到500%之间",
                "数据精确到万元",
                "同比数据必须基于相同周期"
            ],
            constraints={
                "min_sales": 0,
                "max_growth_rate": 500,
                "min_growth_rate": -50,
                "currency": "CNY",
                "unit": "万元",
                "precision": 10000
            }
        )
        
        placeholders = [
            PlaceholderSpec(
                content="sales_amount",
                statistical_type=StatisticalType.STATISTICAL,
                syntax_type=SyntaxType.BASIC,
                start_position=3,
                end_position=16
            ),
            PlaceholderSpec(
                content="growth_rate", 
                statistical_type=StatisticalType.TREND,
                syntax_type=SyntaxType.BASIC,
                start_position=20,
                end_position=32
            )
        ]
        
        # 执行业务规则分析
        result = analyzer.analyze_business_rules(content, business_context, placeholders)
        
        # 验证分析结果
        assert isinstance(result, dict)
        assert "rule_matches" in result
        assert "compliance_score" in result
        assert "violated_constraints" in result
        assert 0.0 <= result["compliance_score"] <= 1.0
        
        # 验证规则匹配
        assert len(result["rule_matches"]) > 0

    @pytest.mark.asyncio
    async def test_time_context_processing(self):
        """测试时间上下文处理功能"""
        from app.services.domain.placeholder.context import ContextAnalysisEngine
        
        engine = ContextAnalysisEngine()
        
        # 测试时间相关的占位符
        placeholder = PlaceholderSpec(
            content="quarterly_revenue",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=18
        )
        
        document_context = DocumentContext(
            document_id="time_test",
            title="季度收入报告",
            content="Q4季度收入 {{quarterly_revenue}} 万元",
            metadata={"period": "Q4", "year": 2023}
        )
        
        business_context = BusinessContext(
            domain="财务分析",
            rules=["季度数据统计", "年度对比分析"],
            constraints={"fiscal_year": 2023, "quarter": "Q4"}
        )
        
        time_context = TimeContext(
            reference_time=datetime(2023, 12, 31),
            time_range="quarterly", 
            fiscal_year=2023,
            period="Q4"
        )
        
        # 执行上下文分析
        result = engine.analyze_comprehensive_context(
            placeholder, document_context, business_context
        )
        
        # 验证时间权重
        assert result.temporal_weight > 0.0
        assert result.document_weight > 0.0

class TestErrorHandlingFunctionality:
    """错误处理功能测试"""
    
    @pytest.fixture
    def orchestrator(self):
        """占位符编排器"""
        return PlaceholderOrchestrator(db_session=Mock())

    @pytest.mark.asyncio
    async def test_malformed_placeholder_handling(self, orchestrator):
        """测试格式错误占位符处理"""
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            mock_agent_service.analyze_placeholders.side_effect = Exception("解析错误：占位符格式不正确")
            mock_agents.return_value = mock_agent_service
            
            # 测试格式错误的占位符
            malformed_content = """
            格式错误的占位符：
            - {{unclosed_placeholder 
            - }}closed_without_open{{
            - {{nested_{{inner}}_placeholder}}
            - {{special@#$%characters}}
            """
            
            document_context = DocumentContext(
                document_id="error_test",
                title="错误处理测试",
                content=malformed_content,
                metadata={"type": "错误测试"}
            )
            
            result = await orchestrator.process_document_placeholders(
                content=malformed_content,
                document_context=document_context
            )
            
            # 验证错误处理
            assert result["success"] is False
            assert "error" in result
            assert "解析错误" in result["error"]

    @pytest.mark.asyncio
    async def test_empty_content_handling(self, orchestrator):
        """测试空内容处理"""
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            mock_agent_service.analyze_placeholders.return_value = {
                "success": True,
                "placeholders": []
            }
            mock_agents.return_value = mock_agent_service
            
            # 测试各种空内容情况
            test_cases = [
                "",  # 完全空白
                "   ",  # 只有空格
                "\n\n\n",  # 只有换行
                "没有占位符的普通文本",  # 无占位符
            ]
            
            for empty_content in test_cases:
                document_context = DocumentContext(
                    document_id="empty_test",
                    title="空内容测试",
                    content=empty_content,
                    metadata={"type": "空内容测试"}
                )
                
                result = await orchestrator.process_document_placeholders(
                    content=empty_content,
                    document_context=document_context
                )
                
                # 验证空内容处理
                assert result["success"] is True
                assert isinstance(result["placeholders"], list)
                assert len(result["placeholders"]) == 0

    @pytest.mark.asyncio
    async def test_invalid_context_handling(self, orchestrator):
        """测试无效上下文处理"""
        
        with patch.object(orchestrator, '_get_agents_integration') as mock_agents:
            mock_agent_service = AsyncMock()
            mock_agent_service.analyze_placeholders.return_value = {
                "success": True,
                "placeholders": [
                    {
                        "content": "test_placeholder",
                        "generated_sql": "SELECT 1",
                        "confidence_score": 0.8
                    }
                ]
            }
            mock_agents.return_value = mock_agent_service
            
            # 测试无效的文档上下文
            invalid_document = DocumentContext(
                document_id="",  # 空ID
                title="",  # 空标题
                content="",  # 空内容
                metadata={}  # 空元数据
            )
            
            result = await orchestrator.process_document_placeholders(
                content="测试占位符：{{test_placeholder}}",
                document_context=invalid_document,
                business_context=None
            )
            
            # 应该能处理无效上下文而不抛出异常
            assert isinstance(result, dict)
            assert "success" in result

if __name__ == "__main__":
    pytest.main([__file__, "-v"])