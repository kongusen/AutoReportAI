"""
LLM占位符理解服务单元测试

测试占位符语义理解、字段匹配建议生成和ETL指令生成功能。
"""

import json
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest

from app.services.ai_integration.llm_service import LLMResponse
from app.services.intelligent_placeholder.processor import (
    PlaceholderMatch,
    PlaceholderType,
)
from app.services.llm_placeholder_service import (
    ETLInstruction,
    FieldMatchingSuggestion,
    LLMPlaceholderService,
    PlaceholderUnderstanding,
    PlaceholderUnderstandingError,
    understand_placeholder_text,
)


class TestLLMPlaceholderService:
    """LLM占位符理解服务测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return Mock()

    @pytest.fixture
    def mock_ai_service(self):
        """模拟AI服务"""
        ai_service = Mock()
        ai_service.call_llm_unified.return_value = LLMResponse(
            content='{"semantic_meaning": "测试语义", "data_type": "integer", "confidence": 0.9}',
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={"input_tokens": 100, "output_tokens": 50},
            response_time=1.0,
            cost_estimate=0.001,
        )
        return ai_service

    @pytest.fixture
    def mock_placeholder_processor(self):
        """模拟占位符处理器"""
        processor = Mock()
        processor.extract_placeholders.return_value = [
            PlaceholderMatch(
                full_match="{{统计:总投诉件数}}",
                type=PlaceholderType.STATISTIC,
                description="总投诉件数",
                start_pos=0,
                end_pos=10,
                context_before="2024年共受理投诉",
                context_after="件，同比上升8.68%",
                confidence=0.9,
            )
        ]
        return processor

    @pytest.fixture
    def sample_placeholder_match(self):
        """示例占位符匹配"""
        return PlaceholderMatch(
            full_match="{{统计:总投诉件数}}",
            type=PlaceholderType.STATISTIC,
            description="总投诉件数",
            start_pos=0,
            end_pos=10,
            context_before="2024年共受理投诉",
            context_after="件，同比上升8.68%",
            confidence=0.9,
        )

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_service_initialization(
        self, mock_processor_class, mock_ai_service_class, mock_db
    ):
        """测试服务初始化"""
        service = LLMPlaceholderService(mock_db)

        assert service.db == mock_db
        assert service.ai_service is not None
        assert service.placeholder_processor is not None
        assert len(service.prompt_templates) > 0
        assert isinstance(service.understanding_cache, dict)

        # 验证提示模板加载
        assert "semantic_understanding" in service.prompt_templates
        assert "field_matching" in service.prompt_templates
        assert "etl_generation" in service.prompt_templates
        assert "context_analysis" in service.prompt_templates

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_understand_placeholder_success(
        self,
        mock_processor_class,
        mock_ai_service_class,
        mock_db,
        sample_placeholder_match,
    ):
        """测试占位符理解成功"""
        # 设置模拟
        mock_ai_service = Mock()
        mock_ai_service.call_llm_unified.return_value = LLMResponse(
            content=json.dumps(
                {
                    "semantic_meaning": "统计投诉总数量",
                    "data_type": "integer",
                    "field_suggestions": ["complaint_count", "total_complaints"],
                    "calculation_needed": True,
                    "aggregation_type": "count",
                    "confidence": 0.95,
                    "business_context": "投诉数据统计",
                    "validation_rules": ["必须为正整数"],
                }
            ),
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={"input_tokens": 150, "output_tokens": 80},
            response_time=1.2,
            cost_estimate=0.002,
        )
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        # 执行理解
        understanding = service.understand_placeholder(
            sample_placeholder_match,
            available_fields=["complaint_count", "complaint_date", "region"],
            data_source_schema={
                "tables": ["complaints"],
                "columns": ["id", "count", "date"],
            },
        )

        # 验证结果
        assert isinstance(understanding, PlaceholderUnderstanding)
        assert understanding.placeholder == "{{统计:总投诉件数}}"
        assert understanding.type == "统计"
        assert understanding.description == "总投诉件数"
        assert understanding.semantic_meaning == "统计投诉总数量"
        assert understanding.data_type == "integer"
        assert understanding.calculation_needed is True
        assert understanding.aggregation_type == "count"
        assert understanding.confidence == 0.95
        assert len(understanding.field_suggestions) == 2
        assert "complaint_count" in understanding.field_suggestions

        # 验证元数据
        assert understanding.metadata["llm_provider"] == "openai-test"
        assert understanding.metadata["llm_model"] == "gpt-3.5-turbo"
        assert understanding.metadata["cost_estimate"] == 0.002

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_understand_placeholder_with_cache(
        self,
        mock_processor_class,
        mock_ai_service_class,
        mock_db,
        sample_placeholder_match,
    ):
        """测试占位符理解缓存功能"""
        mock_ai_service = Mock()
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        # 预设缓存
        cache_key = (
            f"{sample_placeholder_match.full_match}_{hash(str(['field1', 'field2']))}"
        )
        cached_understanding = PlaceholderUnderstanding(
            placeholder="{{统计:总投诉件数}}",
            type="统计",
            description="总投诉件数",
            semantic_meaning="缓存的理解结果",
            data_type="integer",
            field_suggestions=["cached_field"],
            calculation_needed=True,
            aggregation_type="count",
            confidence=0.8,
            context_analysis={},
            metadata={"source": "cache"},
        )
        service.understanding_cache[cache_key] = cached_understanding

        # 执行理解（应该从缓存获取）
        understanding = service.understand_placeholder(
            sample_placeholder_match, available_fields=["field1", "field2"]
        )

        # 验证使用了缓存
        assert understanding.semantic_meaning == "缓存的理解结果"
        assert understanding.metadata["source"] == "cache"

        # 验证没有调用LLM
        mock_ai_service.call_llm_unified.assert_not_called()

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_understand_placeholder_error_handling(
        self,
        mock_processor_class,
        mock_ai_service_class,
        mock_db,
        sample_placeholder_match,
    ):
        """测试占位符理解错误处理"""
        # 设置LLM调用失败
        mock_ai_service = Mock()
        mock_ai_service.call_llm_unified.side_effect = Exception("LLM调用失败")
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        # 执行理解（应该抛出异常）
        with pytest.raises(PlaceholderUnderstandingError) as exc_info:
            service.understand_placeholder(sample_placeholder_match)

        assert "理解占位符失败" in str(exc_info.value)
        assert sample_placeholder_match.full_match in str(exc_info.value)

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_generate_field_matching_suggestions(
        self, mock_processor_class, mock_ai_service_class, mock_db
    ):
        """测试字段匹配建议生成"""
        # 设置模拟
        mock_ai_service = Mock()
        mock_ai_service.call_llm_unified.return_value = LLMResponse(
            content=json.dumps(
                {
                    "matches": [
                        {
                            "field_name": "complaint_count",
                            "match_score": 0.95,
                            "match_reason": "字段名与语义高度匹配",
                            "data_transformation": None,
                            "validation_rules": ["非负整数"],
                        },
                        {
                            "field_name": "total_complaints",
                            "match_score": 0.85,
                            "match_reason": "语义相似，可作为备选",
                            "data_transformation": "重命名",
                            "validation_rules": ["正整数"],
                        },
                    ],
                    "best_match": "complaint_count",
                    "alternative_matches": ["total_complaints"],
                }
            ),
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={},
            response_time=1.0,
            cost_estimate=0.001,
        )
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        # 创建理解结果
        understanding = PlaceholderUnderstanding(
            placeholder="{{统计:总投诉件数}}",
            type="统计",
            description="总投诉件数",
            semantic_meaning="统计投诉总数量",
            data_type="integer",
            field_suggestions=[],
            calculation_needed=True,
            aggregation_type="count",
            confidence=0.9,
            context_analysis={},
            metadata={},
        )

        # 生成字段匹配建议
        suggestions = service.generate_field_matching_suggestions(
            understanding,
            available_fields=["complaint_count", "total_complaints", "complaint_date"],
            field_metadata={"complaint_count": {"type": "integer"}},
        )

        # 验证结果
        assert len(suggestions) == 2

        # 验证第一个建议
        first_suggestion = suggestions[0]
        assert first_suggestion.suggested_field == "complaint_count"
        assert first_suggestion.match_score == 0.95
        assert "字段名与语义高度匹配" in first_suggestion.match_reason
        assert first_suggestion.data_transformation is None

        # 验证第二个建议
        second_suggestion = suggestions[1]
        assert second_suggestion.suggested_field == "total_complaints"
        assert second_suggestion.match_score == 0.85
        assert second_suggestion.data_transformation == "重命名"

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_generate_etl_instructions(
        self, mock_processor_class, mock_ai_service_class, mock_db
    ):
        """测试ETL指令生成"""
        # 设置模拟
        mock_ai_service = Mock()
        mock_ai_service.call_llm_unified.return_value = LLMResponse(
            content=json.dumps(
                {
                    "query_type": "aggregate",
                    "source_tables": ["complaints"],
                    "target_fields": ["complaint_count"],
                    "filters": [{"column": "year", "operator": "=", "value": 2024}],
                    "aggregations": [
                        {"function": "count", "column": "id", "alias": "total_count"}
                    ],
                    "calculations": [],
                    "transformations": [
                        {"type": "format", "field": "total_count", "format": "integer"}
                    ],
                    "output_format": "scalar",
                    "execution_steps": ["过滤数据", "聚合计算", "格式化输出"],
                }
            ),
            model="gpt-3.5-turbo",
            provider="openai-test",
            usage={},
            response_time=1.5,
            cost_estimate=0.003,
        )
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        # 创建理解结果
        understanding = PlaceholderUnderstanding(
            placeholder="{{统计:总投诉件数}}",
            type="统计",
            description="总投诉件数",
            semantic_meaning="统计投诉总数量",
            data_type="integer",
            field_suggestions=["complaint_count"],
            calculation_needed=True,
            aggregation_type="count",
            confidence=0.9,
            context_analysis={},
            metadata={},
        )

        # 生成ETL指令
        etl_instruction = service.generate_etl_instructions(
            understanding,
            data_source_schema={
                "tables": ["complaints"],
                "columns": ["id", "year", "type"],
            },
            field_mapping={"总投诉件数": "complaint_count"},
        )

        # 验证结果
        assert isinstance(etl_instruction, ETLInstruction)
        assert etl_instruction.query_type == "aggregate"
        assert "complaints" in etl_instruction.source_tables
        assert "complaint_count" in etl_instruction.target_fields
        assert len(etl_instruction.filters) == 1
        assert etl_instruction.filters[0]["column"] == "year"
        assert len(etl_instruction.aggregations) == 1
        assert etl_instruction.aggregations[0]["function"] == "count"
        assert etl_instruction.output_format == "scalar"

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_batch_understand_placeholders(
        self, mock_processor_class, mock_ai_service_class, mock_db
    ):
        """测试批量占位符理解"""
        # 设置模拟
        mock_ai_service = Mock()
        mock_ai_service.call_llm_unified.side_effect = [
            LLMResponse(
                content=json.dumps(
                    {
                        "semantic_meaning": "第一个占位符理解",
                        "data_type": "integer",
                        "confidence": 0.9,
                    }
                ),
                model="gpt-3.5-turbo",
                provider="openai-test",
                usage={},
                response_time=1.0,
                cost_estimate=0.001,
            ),
            LLMResponse(
                content=json.dumps(
                    {
                        "semantic_meaning": "第二个占位符理解",
                        "data_type": "string",
                        "confidence": 0.8,
                    }
                ),
                model="gpt-3.5-turbo",
                provider="openai-test",
                usage={},
                response_time=1.1,
                cost_estimate=0.001,
            ),
        ]
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        # 创建占位符匹配列表
        placeholder_matches = [
            PlaceholderMatch(
                full_match="{{统计:总投诉件数}}",
                type=PlaceholderType.STATISTIC,
                description="总投诉件数",
                start_pos=0,
                end_pos=10,
                context_before="",
                context_after="",
                confidence=0.9,
            ),
            PlaceholderMatch(
                full_match="{{区域:地区名称}}",
                type=PlaceholderType.REGION,
                description="地区名称",
                start_pos=20,
                end_pos=30,
                context_before="",
                context_after="",
                confidence=0.8,
            ),
        ]

        # 批量理解
        understandings = service.batch_understand_placeholders(
            placeholder_matches, available_fields=["field1", "field2"]
        )

        # 验证结果
        assert len(understandings) == 2
        assert understandings[0].semantic_meaning == "第一个占位符理解"
        assert understandings[1].semantic_meaning == "第二个占位符理解"

        # 验证LLM被调用了两次
        assert (
            mock_ai_service.call_llm_unified.call_count == 4
        )  # 每个占位符调用2次（理解+上下文分析）

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_batch_understand_with_errors(
        self, mock_processor_class, mock_ai_service_class, mock_db
    ):
        """测试批量理解中的错误处理"""
        # 设置模拟：第一个成功，第二个失败
        mock_ai_service = Mock()
        mock_ai_service.call_llm_unified.side_effect = [
            LLMResponse(
                content=json.dumps({"semantic_meaning": "成功理解", "confidence": 0.9}),
                model="gpt-3.5-turbo",
                provider="openai-test",
                usage={},
                response_time=1.0,
                cost_estimate=0.001,
            ),
            Exception("第二个占位符理解失败"),
        ]
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        placeholder_matches = [
            PlaceholderMatch(
                full_match="{{统计:成功占位符}}",
                type=PlaceholderType.STATISTIC,
                description="成功占位符",
                start_pos=0,
                end_pos=10,
                context_before="",
                context_after="",
                confidence=0.9,
            ),
            PlaceholderMatch(
                full_match="{{统计:失败占位符}}",
                type=PlaceholderType.STATISTIC,
                description="失败占位符",
                start_pos=20,
                end_pos=30,
                context_before="",
                context_after="",
                confidence=0.8,
            ),
        ]

        # 批量理解（不应该抛出异常）
        understandings = service.batch_understand_placeholders(placeholder_matches)

        # 验证结果
        assert len(understandings) == 2
        assert understandings[0].semantic_meaning == "成功理解"
        assert understandings[1].semantic_meaning == "默认理解: 失败占位符"  # 默认理解
        assert understandings[1].confidence == 0.3  # 默认置信度

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_get_understanding_statistics(
        self, mock_processor_class, mock_ai_service_class, mock_db
    ):
        """测试理解统计信息"""
        mock_ai_service = Mock()
        mock_ai_service.get_llm_usage_stats.return_value = {
            "total_calls": 10,
            "total_cost": 0.05,
            "avg_response_time": 1.2,
        }
        mock_ai_service_class.return_value = mock_ai_service

        service = LLMPlaceholderService(mock_db)

        # 添加一些缓存数据
        service.understanding_cache["test1"] = PlaceholderUnderstanding(
            placeholder="{{统计:测试1}}",
            type="统计",
            description="测试1",
            semantic_meaning="测试",
            data_type="integer",
            field_suggestions=[],
            calculation_needed=False,
            aggregation_type=None,
            confidence=0.9,
            context_analysis={},
            metadata={},
        )
        service.understanding_cache["test2"] = PlaceholderUnderstanding(
            placeholder="{{区域:测试2}}",
            type="区域",
            description="测试2",
            semantic_meaning="测试",
            data_type="string",
            field_suggestions=[],
            calculation_needed=False,
            aggregation_type=None,
            confidence=0.8,
            context_analysis={},
            metadata={},
        )

        # 获取统计
        stats = service.get_understanding_statistics()

        # 验证统计结果
        assert stats["total_understood"] == 2
        assert stats["avg_confidence"] == 0.85  # (0.9 + 0.8) / 2
        assert stats["type_distribution"]["统计"] == 1
        assert stats["type_distribution"]["区域"] == 1
        assert stats["cache_size"] == 2
        assert "llm_usage" in stats

    @patch("app.services.llm_placeholder_service.AIService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_clear_cache(self, mock_processor_class, mock_ai_service_class, mock_db):
        """测试缓存清除"""
        mock_ai_service_class.return_value = Mock()

        service = LLMPlaceholderService(mock_db)

        # 添加缓存数据
        service.understanding_cache["test"] = Mock()
        assert len(service.understanding_cache) == 1

        # 清除缓存
        service.clear_cache()

        # 验证缓存已清除
        assert len(service.understanding_cache) == 0


class TestConvenienceFunctions:
    """便捷函数测试"""

    @patch("app.services.llm_placeholder_service.LLMPlaceholderService")
    @patch("app.services.llm_placeholder_service.PlaceholderProcessor")
    def test_understand_placeholder_text(
        self, mock_processor_class, mock_service_class
    ):
        """测试便捷理解函数"""
        # 设置模拟
        mock_processor = Mock()
        mock_processor.extract_placeholders.return_value = [
            PlaceholderMatch(
                full_match="{{统计:测试}}",
                type=PlaceholderType.STATISTIC,
                description="测试",
                start_pos=0,
                end_pos=8,
                context_before="",
                context_after="",
                confidence=0.9,
            )
        ]
        mock_processor_class.return_value = mock_processor

        mock_service = Mock()
        mock_service.batch_understand_placeholders.return_value = [
            PlaceholderUnderstanding(
                placeholder="{{统计:测试}}",
                type="统计",
                description="测试",
                semantic_meaning="测试理解",
                data_type="integer",
                field_suggestions=[],
                calculation_needed=False,
                aggregation_type=None,
                confidence=0.9,
                context_analysis={},
                metadata={},
            )
        ]
        mock_service_class.return_value = mock_service

        # 调用便捷函数
        mock_db = Mock()
        understandings = understand_placeholder_text(
            "测试文本{{统计:测试}}",
            mock_db,
            available_fields=["field1"],
            data_source_schema={"tables": ["test"]},
        )

        # 验证结果
        assert len(understandings) == 1
        assert understandings[0].placeholder == "{{统计:测试}}"
        assert understandings[0].semantic_meaning == "测试理解"

        # 验证调用
        mock_processor.extract_placeholders.assert_called_once_with(
            "测试文本{{统计:测试}}"
        )
        mock_service.batch_understand_placeholders.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
