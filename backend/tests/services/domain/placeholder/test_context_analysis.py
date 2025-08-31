"""
上下文分析引擎单元测试
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.services.domain.placeholder.context import (
    ContextAnalysisEngine,
    ParagraphAnalyzer,
    SectionAnalyzer,
    DocumentAnalyzer,
    BusinessRuleAnalyzer
)
from app.services.domain.placeholder.models import (
    PlaceholderSpec,
    DocumentContext,
    BusinessContext,
    TimeContext,
    StatisticalType,
    SyntaxType
)
from app.services.domain.placeholder.weight import WeightComponents

class TestContextAnalysisEngine:
    """上下文分析引擎测试"""
    
    def setup_method(self):
        self.engine = ContextAnalysisEngine()
    
    def test_analyze_comprehensive_context(self):
        """测试综合上下文分析"""
        placeholder = PlaceholderSpec(
            content="monthly_sales",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=10,
            end_position=25
        )
        
        document_context = DocumentContext(
            document_id="doc_001",
            title="月度销售报告",
            content="本月销售情况分析 {{monthly_sales}} 万元",
            metadata={"department": "销售部", "type": "报告"}
        )
        
        business_context = BusinessContext(
            domain="销售分析",
            rules=["销售额必须大于0", "月度数据对比"],
            constraints={"currency": "CNY", "unit": "万元"}
        )
        
        result = self.engine.analyze_comprehensive_context(
            placeholder, document_context, business_context
        )
        
        assert isinstance(result, WeightComponents)
        assert result.document_weight > 0
        assert result.business_weight > 0
        assert result.semantic_weight >= 0
        assert result.position_weight > 0
    
    def test_analyze_without_business_context(self):
        """测试无业务上下文的分析"""
        placeholder = PlaceholderSpec(
            content="total_revenue",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=15
        )
        
        document_context = DocumentContext(
            document_id="doc_002",
            title="收入报表",
            content="总收入 {{total_revenue}} 元",
            metadata={"type": "财务报表"}
        )
        
        result = self.engine.analyze_comprehensive_context(
            placeholder, document_context, None
        )
        
        assert isinstance(result, WeightComponents)
        assert result.document_weight > 0
        assert result.business_weight == 0.5  # 默认值
        assert result.position_weight > 0

class TestParagraphAnalyzer:
    """段落分析器测试"""
    
    def setup_method(self):
        self.analyzer = ParagraphAnalyzer()
    
    def test_analyze_paragraph_context(self):
        """测试段落上下文分析"""
        placeholder = PlaceholderSpec(
            content="sales_growth",
            statistical_type=StatisticalType.TREND,
            syntax_type=SyntaxType.BASIC,
            start_position=20,
            end_position=35
        )
        
        paragraph = "本季度销售增长显著，{{sales_growth}} 表现优异，超过了预期目标。"
        
        weight = self.analyzer.analyze_paragraph_context(placeholder, paragraph)
        
        assert 0.0 <= weight <= 1.0
        # 由于包含积极词汇，权重应该较高
        assert weight > 0.5
    
    def test_analyze_empty_paragraph(self):
        """测试空段落分析"""
        placeholder = PlaceholderSpec(
            content="empty_test",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=10
        )
        
        weight = self.analyzer.analyze_paragraph_context(placeholder, "")
        
        assert weight == 0.5  # 默认权重
    
    def test_analyze_negative_context(self):
        """测试负面上下文"""
        placeholder = PlaceholderSpec(
            content="loss_amount",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=15,
            end_position=28
        )
        
        paragraph = "由于市场下滑，{{loss_amount}} 亏损严重，需要紧急应对。"
        
        weight = self.analyzer.analyze_paragraph_context(placeholder, paragraph)
        
        # 负面词汇应该降低权重
        assert weight < 0.5

class TestSectionAnalyzer:
    """章节分析器测试"""
    
    def setup_method(self):
        self.analyzer = SectionAnalyzer()
    
    def test_analyze_section_importance(self):
        """测试章节重要性分析"""
        section = {
            "title": "关键业绩指标",
            "content": "本节分析关键指标 {{kpi_value}} 的表现情况。",
            "level": 1,
            "position": 0
        }
        
        placeholder = PlaceholderSpec(
            content="kpi_value",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=10,
            end_position=21
        )
        
        weight = self.analyzer.analyze_section_importance(section, placeholder)
        
        assert 0.0 <= weight <= 1.0
        # 关键词在标题中，应该有较高权重
        assert weight > 0.7
    
    def test_analyze_nested_sections(self):
        """测试嵌套章节分析"""
        sections = [
            {
                "title": "财务概况",
                "content": "整体财务状况良好。",
                "level": 1,
                "position": 0
            },
            {
                "title": "收入分析",
                "content": "收入达到 {{total_income}} 万元。",
                "level": 2,
                "position": 1
            }
        ]
        
        placeholder = PlaceholderSpec(
            content="total_income",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=5,
            end_position=18
        )
        
        weight = self.analyzer.analyze_section_hierarchy(sections, placeholder)
        
        assert 0.0 <= weight <= 1.0
        assert weight > 0.5

class TestDocumentAnalyzer:
    """文档分析器测试"""
    
    def setup_method(self):
        self.analyzer = DocumentAnalyzer()
    
    def test_analyze_document_structure(self):
        """测试文档结构分析"""
        sections = [
            {
                "title": "摘要",
                "content": "总销售额 {{total_sales}} 万元",
                "level": 1,
                "position": 0
            },
            {
                "title": "详细分析",
                "content": "各地区销售情况如下...",
                "level": 1,
                "position": 1
            }
        ]
        
        document_context = DocumentContext(
            document_id="doc_003",
            title="销售报告",
            content="完整的销售分析报告",
            metadata={"type": "报告", "priority": "高"}
        )
        
        result = self.analyzer.analyze_document(sections, document_context)
        
        assert isinstance(result, dict)
        assert "document_type" in result
        assert "priority_level" in result
        assert "structure_score" in result
        assert 0.0 <= result["structure_score"] <= 1.0
    
    def test_identify_document_type(self):
        """测试文档类型识别"""
        document_context = DocumentContext(
            document_id="doc_004",
            title="年度财务报表",
            content="财务数据分析报告内容",
            metadata={"category": "财务"}
        )
        
        doc_type = self.analyzer.identify_document_type(document_context)
        
        assert doc_type in ["报告", "报表", "分析", "总结", "其他"]
        # 应该识别为报表类型
        assert doc_type == "报表"

class TestBusinessRuleAnalyzer:
    """业务规则分析器测试"""
    
    def setup_method(self):
        self.analyzer = BusinessRuleAnalyzer()
    
    def test_analyze_business_rules(self):
        """测试业务规则分析"""
        content = "销售额 {{sales_amount}} 必须大于100万，增长率 {{growth_rate}} 应超过10%"
        
        business_context = BusinessContext(
            domain="销售管理",
            rules=[
                "销售额必须为正数",
                "增长率计算基于同期对比",
                "数据精确到万元"
            ],
            constraints={
                "min_sales": 1000000,
                "currency": "CNY",
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
                start_position=25,
                end_position=38
            )
        ]
        
        result = self.analyzer.analyze_business_rules(content, business_context, placeholders)
        
        assert isinstance(result, dict)
        assert "rule_matches" in result
        assert "compliance_score" in result
        assert "violated_constraints" in result
        assert 0.0 <= result["compliance_score"] <= 1.0
    
    def test_validate_constraints(self):
        """测试约束验证"""
        placeholder = PlaceholderSpec(
            content="revenue_amount",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=15
        )
        
        constraints = {
            "data_type": "numeric",
            "unit": "万元",
            "min_value": 0,
            "max_value": 1000000
        }
        
        violations = self.analyzer.validate_constraints(placeholder, constraints)
        
        assert isinstance(violations, list)
        # 对于合理的约束，不应该有违规
        assert len(violations) == 0
    
    def test_detect_rule_conflicts(self):
        """测试规则冲突检测"""
        rules = [
            "销售额必须大于100万",
            "销售额应该小于50万",  # 冲突规则
            "增长率必须为正数"
        ]
        
        conflicts = self.analyzer.detect_rule_conflicts(rules)
        
        assert isinstance(conflicts, list)
        # 应该检测到冲突
        assert len(conflicts) > 0
        assert any("冲突" in str(conflict) for conflict in conflicts)

class TestIntegrationScenarios:
    """集成场景测试"""
    
    def test_comprehensive_context_analysis(self):
        """测试综合上下文分析"""
        # 创建复杂的文档场景
        document_content = """
        # 2023年第四季度业绩报告
        
        ## 财务概况
        本季度总收入达到 {{quarterly_revenue}} 万元，同比增长 {{yoy_growth_rate}}%。
        净利润为 {{net_profit}} 万元，毛利率保持在 {{gross_margin}}% 的较高水平。
        
        ## 市场表现
        各产品线表现如下：
        - 产品A：{{product_a_sales}} 万元
        - 产品B：{{product_b_sales}} 万元
        - 产品C：{{product_c_sales}} 万元
        
        ## 风险评估
        主要风险包括市场波动影响，预计影响金额 {{risk_amount}} 万元。
        
        ## 展望
        预计下季度收入 {{next_quarter_forecast}} 万元。
        """
        
        # 设置上下文
        document_context = DocumentContext(
            document_id="q4_2023_report",
            title="2023年第四季度业绩报告",
            content=document_content,
            metadata={
                "department": "财务部",
                "type": "季度报告",
                "priority": "高",
                "confidentiality": "内部"
            }
        )
        
        business_context = BusinessContext(
            domain="财务分析",
            rules=[
                "收入数据必须准确到万元",
                "增长率保留两位小数",
                "利润率计算基于标准会计准则"
            ],
            constraints={
                "currency": "CNY",
                "unit": "万元",
                "precision": 2,
                "min_growth_rate": -50,
                "max_growth_rate": 200
            }
        )
        
        time_context = TimeContext(
            reference_time=datetime(2023, 12, 31),
            time_range="quarterly",
            fiscal_year=2023,
            period="Q4"
        )
        
        # 创建测试占位符
        test_placeholder = PlaceholderSpec(
            content="quarterly_revenue",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=50,
            end_position=68
        )
        
        # 执行综合分析
        engine = ContextAnalysisEngine()
        result = engine.analyze_comprehensive_context(
            test_placeholder, document_context, business_context
        )
        
        # 验证分析结果
        assert isinstance(result, WeightComponents)
        assert result.document_weight > 0.7  # 重要文档应该有高权重
        assert result.business_weight > 0.6   # 业务相关性高
        assert result.position_weight > 0.5   # 在重要位置
        assert result.temporal_weight > 0.0   # 有时间上下文
    
    def test_multi_language_context(self):
        """测试多语言上下文分析"""
        # 中英文混合内容
        mixed_content = """
        Sales Performance Analysis
        销售业绩分析
        
        Q4 Revenue: {{q4_revenue}} 万元 (Million CNY)
        Growth Rate: {{growth_rate}}% 增长率
        """
        
        document_context = DocumentContext(
            document_id="mixed_lang_report",
            title="Sales Performance Analysis 销售业绩分析",
            content=mixed_content,
            metadata={"language": "zh-en", "type": "analysis"}
        )
        
        placeholder = PlaceholderSpec(
            content="q4_revenue",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=15,
            end_position=26
        )
        
        engine = ContextAnalysisEngine()
        result = engine.analyze_comprehensive_context(
            placeholder, document_context, None
        )
        
        # 多语言内容应该能正常分析
        assert isinstance(result, WeightComponents)
        assert result.document_weight > 0
    
    def test_error_handling_and_resilience(self):
        """测试错误处理和容错性"""
        # 测试空或无效数据的处理
        engine = ContextAnalysisEngine()
        
        # 空占位符
        empty_placeholder = PlaceholderSpec(
            content="",
            statistical_type=StatisticalType.STATISTICAL,
            syntax_type=SyntaxType.BASIC,
            start_position=0,
            end_position=0
        )
        
        # 空文档上下文
        empty_document = DocumentContext(
            document_id="",
            title="",
            content="",
            metadata={}
        )
        
        # 应该能处理而不抛出异常
        result = engine.analyze_comprehensive_context(
            empty_placeholder, empty_document, None
        )
        
        assert isinstance(result, WeightComponents)
        # 默认权重应该被应用
        assert 0.0 <= result.document_weight <= 1.0
        assert 0.0 <= result.business_weight <= 1.0