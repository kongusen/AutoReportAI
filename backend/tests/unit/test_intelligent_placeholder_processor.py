"""
智能占位符处理器单元测试

测试占位符解析、上下文提取、错误处理和恢复机制。
"""

import json
import os
import tempfile
from typing import List

import pytest

from app.services.intelligent_placeholder import (
    PlaceholderMatch,
    PlaceholderProcessor,
    PlaceholderType,
)
from app.services.intelligent_placeholder.processor import (
    ProcessingError,
    extract_placeholders_from_text,
    validate_placeholder_text,
)


class TestPlaceholderProcessor:
    """占位符处理器测试类"""

    def setup_method(self):
        """测试前准备"""
        self.processor = PlaceholderProcessor()

        # 测试文本样本
        self.sample_text = """
        2024年昆明市文化和旅游市场投诉数据分析报告
        
        一、基本情况
        系统全量统计情况：{{周期:统计开始日期}}—{{周期:统计结束日期}}，{{区域:地区名称}}共受理投诉{{统计:总投诉件数}}件，
        较上年同期{{统计:上年同期投诉件数}}件，同比{{统计:同比变化方向}}{{统计:同比变化百分比}}%。
        
        其中"游云南"微信小程序{{统计:微信小程序投诉件数}}件，占总投诉的{{统计:微信小程序占比}}%。
        
        二、数据可视化
        {{图表:投诉趋势折线图}}
        {{图表:投诉来源饼图}}
        {{图表:投诉类型柱状图}}
        """

    def test_extract_basic_placeholders(self):
        """测试基本占位符提取"""
        placeholders = self.processor.extract_placeholders(self.sample_text)

        # 验证提取数量
        assert len(placeholders) > 0

        # 验证包含各种类型
        types_found = {p.type for p in placeholders}
        expected_types = {
            PlaceholderType.PERIOD,
            PlaceholderType.REGION,
            PlaceholderType.STATISTIC,
            PlaceholderType.CHART,
        }
        assert expected_types.issubset(types_found)

        # 验证具体占位符
        placeholder_texts = [p.full_match for p in placeholders]
        assert "{{周期:统计开始日期}}" in placeholder_texts
        assert "{{统计:总投诉件数}}" in placeholder_texts
        assert "{{图表:投诉趋势折线图}}" in placeholder_texts

    def test_placeholder_types_parsing(self):
        """测试占位符类型解析"""
        test_cases = [
            ("{{周期:报告年份}}", PlaceholderType.PERIOD, "报告年份"),
            ("{{区域:地区名称}}", PlaceholderType.REGION, "地区名称"),
            ("{{统计:总投诉件数}}", PlaceholderType.STATISTIC, "总投诉件数"),
            ("{{图表:趋势图}}", PlaceholderType.CHART, "趋势图"),
        ]

        for text, expected_type, expected_desc in test_cases:
            placeholders = self.processor.extract_placeholders(text)
            assert len(placeholders) == 1

            placeholder = placeholders[0]
            assert placeholder.type == expected_type
            assert placeholder.description == expected_desc
            assert placeholder.full_match == text

    def test_context_extraction(self):
        """测试上下文提取"""
        text = "第一句话。第二句话。第三句话。{{统计:测试数据}}第四句话。第五句话。第六句话。"
        placeholders = self.processor.extract_placeholders(text)

        assert len(placeholders) == 1
        placeholder = placeholders[0]

        # 验证上下文包含前后句子
        assert (
            "第一句话" in placeholder.context_before
            or "第二句话" in placeholder.context_before
        )
        assert (
            "第四句话" in placeholder.context_after
            or "第五句话" in placeholder.context_after
        )

    def test_confidence_calculation(self):
        """测试置信度计算"""
        # 高置信度案例
        high_confidence_text = "统计数据显示：{{统计:总投诉件数}}件投诉已处理完成。"
        placeholders = self.processor.extract_placeholders(high_confidence_text)
        assert len(placeholders) == 1
        assert placeholders[0].confidence > 0.6

        # 低置信度案例
        low_confidence_text = "{{统计:x}}测试"
        placeholders = self.processor.extract_placeholders(low_confidence_text)
        assert len(placeholders) == 1
        assert placeholders[0].confidence < 0.6

    def test_invalid_placeholder_types(self):
        """测试无效占位符类型处理"""
        invalid_text = "{{无效类型:测试描述}}"
        placeholders = self.processor.extract_placeholders(invalid_text)

        # 应该没有提取到有效占位符
        assert len(placeholders) == 0

        # 应该有错误记录
        assert len(self.processor.processing_errors) > 0
        error = self.processor.processing_errors[0]
        assert error.error_type == "invalid_type"
        assert "无效类型" in error.message

    def test_empty_description_handling(self):
        """测试空描述处理"""
        empty_desc_text = "{{统计:}}"
        placeholders = self.processor.extract_placeholders(empty_desc_text)

        # 应该没有提取到有效占位符
        assert len(placeholders) == 0

        # 应该有错误记录
        assert len(self.processor.processing_errors) > 0
        error = self.processor.processing_errors[0]
        assert error.error_type == "empty_description"

    def test_malformed_placeholder_recovery(self):
        """测试格式错误恢复"""
        malformed_cases = [
            # 缺少冒号
            ("{{统计总投诉件数}}", "{{统计:总投诉件数}}"),
            # 多余空格
            ("{{ 统计 : 总投诉件数 }}", "{{统计:总投诉件数}}"),
            # 中文括号
            ("｛｛统计:总投诉件数｝｝", "{{统计:总投诉件数}}"),
            # 不完整括号
            ("{{统计:总投诉件数}", "{{统计:总投诉件数}}"),
        ]

        for malformed, expected in malformed_cases:
            recovered = self.processor.recover_from_errors(malformed)
            assert expected in recovered

    def test_validation_results(self):
        """测试验证结果"""
        placeholders = self.processor.extract_placeholders(self.sample_text)
        validation = self.processor.validate_placeholders(placeholders)

        # 验证基本结构
        assert "is_valid" in validation
        assert "total_count" in validation
        assert "type_distribution" in validation
        assert "errors" in validation

        # 验证类型分布
        assert validation["total_count"] > 0
        assert len(validation["type_distribution"]) > 0

    def test_sentence_splitting(self):
        """测试句子分割"""
        text = "第一句。第二句！第三句？第四句；第五句。"
        sentences = self.processor._split_sentences(text)

        # 应该正确分割句子
        assert len(sentences) >= 4
        assert any("第一句" in s for s in sentences)
        assert any("第二句" in s for s in sentences)

    def test_processing_summary(self):
        """测试处理摘要"""
        # 处理包含错误的文本
        error_text = "{{无效:测试}}{{统计:}}{{正常:测试数据}}"
        self.processor.extract_placeholders(error_text)

        summary = self.processor.get_processing_summary()

        assert "total_errors" in summary
        assert "error_by_severity" in summary
        assert "supported_types" in summary
        assert summary["total_errors"] > 0

    def test_custom_type_definitions(self):
        """测试自定义类型定义"""
        # 创建临时类型定义文件
        custom_types = {
            "placeholder_types": {
                "周期": {"description": "自定义周期类型"},
                "区域": {"description": "自定义区域类型"},
                "统计": {"description": "自定义统计类型"},
                "图表": {"description": "自定义图表类型"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(custom_types, f, ensure_ascii=False)
            temp_file = f.name

        try:
            # 使用自定义类型定义创建处理器
            custom_processor = PlaceholderProcessor(temp_file)
            assert custom_processor.type_definitions == custom_types

            # 测试正常工作
            placeholders = custom_processor.extract_placeholders("{{统计:测试}}")
            assert len(placeholders) == 1

        finally:
            os.unlink(temp_file)

    def test_edge_cases(self):
        """测试边界情况"""
        edge_cases = [
            "",  # 空文本
            "没有占位符的文本",  # 无占位符
            "{{}}",  # 空占位符
            "{{统计}}",  # 缺少描述
            "{{:描述}}",  # 缺少类型
            "{{统计:描述}}{{区域:名称}}",  # 连续占位符
            "嵌套{{统计:{{区域:测试}}}}占位符",  # 嵌套情况
        ]

        for case in edge_cases:
            # 不应该抛出异常
            try:
                placeholders = self.processor.extract_placeholders(case)
                validation = self.processor.validate_placeholders(placeholders)
                assert isinstance(placeholders, list)
                assert isinstance(validation, dict)
            except Exception as e:
                pytest.fail(f"边界情况处理失败: {case}, 错误: {e}")


class TestConvenienceFunctions:
    """便捷函数测试"""

    def test_extract_placeholders_from_text(self):
        """测试便捷提取函数"""
        text = "{{统计:测试数据}}和{{区域:测试区域}}"
        placeholders = extract_placeholders_from_text(text)

        assert len(placeholders) == 2
        assert placeholders[0].type == PlaceholderType.STATISTIC
        assert placeholders[1].type == PlaceholderType.REGION

    def test_validate_placeholder_text(self):
        """测试便捷验证函数"""
        text = "{{统计:测试数据}}"
        validation = validate_placeholder_text(text)

        assert "is_valid" in validation
        assert "total_count" in validation
        assert validation["total_count"] == 1


class TestRealWorldScenarios:
    """真实场景测试"""

    def test_complaint_report_template(self):
        """测试投诉报告模板"""
        template_text = """
        {{周期:报告年份}}年{{区域:地区名称}}投诉数据分析报告
        
        一、基本情况
        {{周期:统计开始日期}}—{{周期:统计结束日期}}期间，
        {{区域:地区名称}}共受理投诉{{统计:总投诉件数}}件，
        同比{{统计:同比变化方向}}{{统计:同比变化百分比}}%。
        
        二、数据分析
        {{图表:投诉趋势折线图}}
        {{图表:投诉来源分布饼图}}
        
        三、处理效率
        平均响应时长{{统计:平均响应时长分钟}}分钟，
        24小时办结率{{统计:24小时办结率}}%。
        """

        processor = PlaceholderProcessor()
        placeholders = processor.extract_placeholders(template_text)
        validation = processor.validate_placeholders(placeholders)

        # 验证提取结果
        assert len(placeholders) >= 8  # 至少8个占位符
        assert validation["is_valid"]

        # 验证类型分布
        type_dist = validation["type_distribution"]
        assert "周期" in type_dist
        assert "区域" in type_dist
        assert "统计" in type_dist
        assert "图表" in type_dist

        # 验证具体占位符
        descriptions = [p.description for p in placeholders]
        assert "报告年份" in descriptions
        assert "总投诉件数" in descriptions
        assert "投诉趋势折线图" in descriptions

    def test_mixed_content_with_errors(self):
        """测试包含错误的混合内容"""
        mixed_text = """
        正常占位符：{{统计:正常数据}}
        错误类型：{{错误类型:测试}}
        空描述：{{统计:}}
        格式错误：{{ 统计 : 格式错误数据 }}
        中文括号：｛｛区域:中文括号｝｝
        不完整：{{统计:不完整
        """

        processor = PlaceholderProcessor()

        # 先尝试错误恢复
        recovered_text = processor.recover_from_errors(mixed_text)
        placeholders = processor.extract_placeholders(recovered_text)

        # 应该能提取到一些有效占位符
        valid_placeholders = [p for p in placeholders if p.confidence > 0.5]
        assert len(valid_placeholders) > 0

        # 应该有错误记录
        assert len(processor.processing_errors) > 0

        # 验证错误类型
        error_types = {e.error_type for e in processor.processing_errors}
        expected_error_types = {"invalid_type", "empty_description"}
        assert len(expected_error_types.intersection(error_types)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
