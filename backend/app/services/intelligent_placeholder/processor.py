"""
智能占位符处理器核心模块

处理 {{类型:描述}} 格式的占位符，提供上下文提取、语义分析和错误恢复功能。
支持四种占位符类型：周期、区域、统计、图表。
"""

import json
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from app.core.logging_config import get_module_logger, get_performance_logger

# Get module-specific logger
logger = get_module_logger('intelligent_placeholder')
perf_logger = get_performance_logger()


class PlaceholderType(Enum):
    """占位符类型枚举"""

    PERIOD = "周期"  # 时间周期相关
    REGION = "区域"  # 地理区域相关
    STATISTIC = "统计"  # 统计数据相关
    CHART = "图表"  # 图表可视化相关


@dataclass
class PlaceholderMatch:
    """占位符匹配结果"""

    full_match: str  # 完整匹配文本，如 "{{统计:总投诉件数}}"
    type: PlaceholderType  # 占位符类型
    description: str  # 描述部分，如 "总投诉件数"
    start_pos: int  # 在文档中的开始位置
    end_pos: int  # 在文档中的结束位置
    context_before: str  # 前置上下文（前3句话）
    context_after: str  # 后置上下文（后3句话）
    confidence: float  # 匹配置信度 (0.0-1.0)


@dataclass
class ProcessingError:
    """处理错误信息"""

    error_type: str  # 错误类型
    message: str  # 错误消息
    position: int  # 错误位置
    placeholder: str  # 相关占位符
    severity: str  # 严重程度: 'warning', 'error', 'critical'
    suggestion: Optional[str] = None  # 修复建议


class PlaceholderProcessor:
    """智能占位符处理器"""

    # 占位符正则表达式模式
    PLACEHOLDER_PATTERN = r"\{\{([^:]+):([^}]+)\}\}"

    # 句子分割模式（中文句号、问号、感叹号）
    SENTENCE_PATTERN = r"[。！？；]+"

    # 支持的占位符类型
    SUPPORTED_TYPES = {
        "周期": PlaceholderType.PERIOD,
        "区域": PlaceholderType.REGION,
        "统计": PlaceholderType.STATISTIC,
        "图表": PlaceholderType.CHART,
        "分析": PlaceholderType.STATISTIC,  # 分析类型映射到统计类型
    }

    def __init__(self, type_definitions_path: Optional[str] = None):
        """
        初始化占位符处理器

        Args:
            type_definitions_path: 类型定义文件路径
        """
        self.type_definitions = {}
        self.processing_errors: List[ProcessingError] = []

        # 加载类型定义
        if type_definitions_path:
            self._load_type_definitions(type_definitions_path)
        else:
            # 使用默认类型定义
            self._load_default_type_definitions()

    def _load_type_definitions(self, file_path: str) -> None:
        """加载占位符类型定义"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.type_definitions = json.load(f)
            logger.info(f"成功加载类型定义文件: {file_path}")
        except Exception as e:
            logger.error(f"加载类型定义文件失败: {e}")
            self._load_default_type_definitions()

    def _load_default_type_definitions(self) -> None:
        """加载默认类型定义"""
        self.type_definitions = {
            "placeholder_types": {
                "周期": {
                    "description": "时间周期相关占位符",
                    "auto_calculation": True,
                    "depends_on": "task_execution_time",
                },
                "区域": {
                    "description": "地理区域相关占位符",
                    "auto_calculation": False,
                    "depends_on": "data_source_configuration",
                },
                "统计": {
                    "description": "统计数据占位符",
                    "auto_calculation": True,
                    "depends_on": "data_source_data",
                },
                "图表": {
                    "description": "图表占位符",
                    "auto_calculation": True,
                    "depends_on": "chart_data_and_config",
                },
            }
        }

    def extract_placeholders(self, text: str) -> List[PlaceholderMatch]:
        """
        从文本中提取所有占位符

        Args:
            text: 输入文本

        Returns:
            占位符匹配结果列表
        """
        start_time = time.time()
        self.processing_errors.clear()
        placeholders = []

        try:
            logger.info("开始提取占位符", text_length=len(text))
            
            # 使用正则表达式查找所有占位符
            matches = re.finditer(self.PLACEHOLDER_PATTERN, text)

            for match in matches:
                try:
                    placeholder = self._process_single_match(match, text)
                    if placeholder:
                        placeholders.append(placeholder)
                except Exception as e:
                    self._add_error(
                        error_type="parsing_error",
                        message=f"处理占位符时出错: {str(e)}",
                        position=match.start(),
                        placeholder=match.group(0),
                        severity="error",
                    )

            duration = time.time() - start_time
            logger.info(
                "占位符提取完成",
                placeholder_count=len(placeholders),
                text_length=len(text),
                duration=duration
            )
            
            # Log performance metrics
            perf_logger.info(
                "占位符提取性能",
                operation="extract_placeholders",
                duration=duration,
                text_length=len(text),
                placeholder_count=len(placeholders),
                processing_rate=len(text) / duration if duration > 0 else 0
            )
            
            return placeholders

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "占位符提取失败",
                error=str(e),
                duration=duration,
                text_length=len(text),
                exc_info=True
            )
            self._add_error(
                error_type="extraction_error",
                message=f"占位符提取过程出错: {str(e)}",
                position=0,
                placeholder="",
                severity="critical",
            )
            return []

    def _process_single_match(
        self, match: re.Match, text: str
    ) -> Optional[PlaceholderMatch]:
        """
        处理单个占位符匹配

        Args:
            match: 正则匹配对象
            text: 完整文本

        Returns:
            占位符匹配结果或None
        """
        full_match = match.group(0)
        type_str = match.group(1).strip()
        description = match.group(2).strip()

        # 验证占位符类型
        if type_str not in self.SUPPORTED_TYPES:
            self._add_error(
                error_type="invalid_type",
                message=f"不支持的占位符类型: {type_str}",
                position=match.start(),
                placeholder=full_match,
                severity="error",
                suggestion=f"支持的类型: {', '.join(self.SUPPORTED_TYPES.keys())}",
            )
            return None

        # 验证描述部分
        if not description or len(description.strip()) == 0:
            self._add_error(
                error_type="empty_description",
                message="占位符描述不能为空",
                position=match.start(),
                placeholder=full_match,
                severity="error",
                suggestion="请提供有意义的描述，如：{{统计:总投诉件数}}",
            )
            return None

        # 提取上下文
        context_before, context_after = self._extract_context(
            text, match.start(), match.end()
        )

        # 计算置信度
        confidence = self._calculate_confidence(
            type_str, description, context_before, context_after
        )

        return PlaceholderMatch(
            full_match=full_match,
            type=self.SUPPORTED_TYPES[type_str],
            description=description,
            start_pos=match.start(),
            end_pos=match.end(),
            context_before=context_before,
            context_after=context_after,
            confidence=confidence,
        )

    def _extract_context(
        self, text: str, start_pos: int, end_pos: int
    ) -> Tuple[str, str]:
        """
        提取占位符的上下文（前后各3句话）

        Args:
            text: 完整文本
            start_pos: 占位符开始位置
            end_pos: 占位符结束位置

        Returns:
            (前置上下文, 后置上下文)
        """
        try:
            # 提取前置文本和后置文本
            before_text = text[:start_pos]
            after_text = text[end_pos:]

            # 分割句子
            before_sentences = self._split_sentences(before_text)
            after_sentences = self._split_sentences(after_text)

            # 取前3句和后3句
            context_before = "".join(before_sentences[-3:]) if before_sentences else ""
            context_after = "".join(after_sentences[:3]) if after_sentences else ""

            return context_before.strip(), context_after.strip()

        except Exception as e:
            logger.warning(f"上下文提取失败: {e}")
            return "", ""

    def _split_sentences(self, text: str) -> List[str]:
        """
        分割句子

        Args:
            text: 输入文本

        Returns:
            句子列表
        """
        if not text:
            return []

        # 使用正则表达式分割句子
        sentences = re.split(self.SENTENCE_PATTERN, text)

        # 过滤空句子并保留标点符号
        result = []
        parts = re.split(f"({self.SENTENCE_PATTERN})", text)

        sentence = ""
        for part in parts:
            if re.match(self.SENTENCE_PATTERN, part):
                if sentence.strip():
                    result.append(sentence + part)
                    sentence = ""
            else:
                sentence += part

        # 添加最后一个句子（如果有）
        if sentence.strip():
            result.append(sentence)

        return [s for s in result if s.strip()]

    def _calculate_confidence(
        self, type_str: str, description: str, context_before: str, context_after: str
    ) -> float:
        """
        计算占位符匹配的置信度

        Args:
            type_str: 占位符类型
            description: 描述
            context_before: 前置上下文
            context_after: 后置上下文

        Returns:
            置信度分数 (0.0-1.0)
        """
        confidence = 0.5  # 基础置信度

        try:
            # 类型匹配度
            if type_str in self.SUPPORTED_TYPES:
                confidence += 0.2

            # 描述质量评估
            if len(description) >= 3:  # 描述长度合理
                confidence += 0.1
            if any(
                keyword in description
                for keyword in ["数量", "件数", "比例", "率", "时间", "日期"]
            ):
                confidence += 0.1  # 包含常见统计关键词

            # 上下文相关性
            context_keywords = {
                "周期": ["年", "月", "日", "时间", "期间", "统计"],
                "区域": ["省", "市", "县", "区", "地区", "区域"],
                "统计": ["件", "个", "次", "率", "比", "数量", "总计"],
                "图表": ["图", "表", "趋势", "分布", "对比"],
            }

            if type_str in context_keywords:
                keywords = context_keywords[type_str]
                context_text = context_before + context_after
                if any(keyword in context_text for keyword in keywords):
                    confidence += 0.1

            # 确保置信度在合理范围内
            confidence = max(0.0, min(1.0, confidence))

        except Exception as e:
            logger.warning(f"置信度计算失败: {e}")
            confidence = 0.5

        return confidence

    def _add_error(
        self,
        error_type: str,
        message: str,
        position: int,
        placeholder: str,
        severity: str,
        suggestion: Optional[str] = None,
    ) -> None:
        """添加处理错误"""
        error = ProcessingError(
            error_type=error_type,
            message=message,
            position=position,
            placeholder=placeholder,
            severity=severity,
            suggestion=suggestion,
        )
        self.processing_errors.append(error)

        # 记录日志
        log_level = {
            "warning": logger.warning,
            "error": logger.error,
            "critical": logger.critical,
        }.get(severity, logger.info)

        log_level(
            f"占位符处理错误: {message} (位置: {position}, 占位符: {placeholder})"
        )

    def validate_placeholders(
        self, placeholders: List[PlaceholderMatch]
    ) -> Dict[str, Any]:
        """
        验证占位符的有效性

        Args:
            placeholders: 占位符列表

        Returns:
            验证结果
        """
        validation_result = {
            "is_valid": True,
            "total_count": len(placeholders),
            "type_distribution": {},
            "low_confidence_count": 0,
            "errors": self.processing_errors,
            "warnings": [],
        }

        # 统计类型分布
        for placeholder in placeholders:
            type_name = placeholder.type.value
            validation_result["type_distribution"][type_name] = (
                validation_result["type_distribution"].get(type_name, 0) + 1
            )

            # 检查低置信度占位符
            if placeholder.confidence < 0.6:
                validation_result["low_confidence_count"] += 1
                validation_result["warnings"].append(
                    f"占位符 '{placeholder.full_match}' 置信度较低 ({placeholder.confidence:.2f})"
                )

        # 检查是否有严重错误
        critical_errors = [
            e for e in self.processing_errors if e.severity == "critical"
        ]
        if critical_errors:
            validation_result["is_valid"] = False

        return validation_result

    def get_processing_summary(self) -> Dict[str, Any]:
        """获取处理摘要"""
        return {
            "total_errors": len(self.processing_errors),
            "error_by_severity": {
                "warning": len(
                    [e for e in self.processing_errors if e.severity == "warning"]
                ),
                "error": len(
                    [e for e in self.processing_errors if e.severity == "error"]
                ),
                "critical": len(
                    [e for e in self.processing_errors if e.severity == "critical"]
                ),
            },
            "supported_types": list(self.SUPPORTED_TYPES.keys()),
            "type_definitions_loaded": bool(self.type_definitions),
        }

    def recover_from_errors(self, text: str) -> str:
        """
        从错误中恢复，尝试修复常见的占位符格式问题

        Args:
            text: 原始文本

        Returns:
            修复后的文本
        """
        recovered_text = text

        try:
            # 修复常见格式错误

            # 1. 修复缺少冒号的情况：{{统计总投诉件数}} -> {{统计:总投诉件数}}
            recovered_text = re.sub(
                r"\{\{(周期|区域|统计|图表)([^:}]+)\}\}", r"{{\1:\2}}", recovered_text
            )

            # 2. 修复多余空格：{{ 统计 : 总投诉件数 }} -> {{统计:总投诉件数}}
            recovered_text = re.sub(
                r"\{\{\s*([^:]+?)\s*:\s*([^}]+?)\s*\}\}", r"{{\1:\2}}", recovered_text
            )

            # 3. 修复中英文括号混用：｛｛统计:总投诉件数｝｝ -> {{统计:总投诉件数}}
            recovered_text = recovered_text.replace("｛", "{").replace("｝", "}")

            # 4. 修复不完整的占位符：{{统计:总投诉件数} -> {{统计:总投诉件数}}
            recovered_text = re.sub(
                r"\{\{([^:]+:[^}]+)(?!\}\})", r"{{\1}}", recovered_text
            )

            logger.info("占位符格式错误恢复完成")

        except Exception as e:
            logger.error(f"错误恢复失败: {e}")

        return recovered_text


# 便捷函数
def extract_placeholders_from_text(
    text: str, type_definitions_path: Optional[str] = None
) -> List[PlaceholderMatch]:
    """
    从文本中提取占位符的便捷函数

    Args:
        text: 输入文本
        type_definitions_path: 类型定义文件路径

    Returns:
        占位符匹配结果列表
    """
    processor = PlaceholderProcessor(type_definitions_path)
    return processor.extract_placeholders(text)


def validate_placeholder_text(
    text: str, type_definitions_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    验证文本中占位符的便捷函数

    Args:
        text: 输入文本
        type_definitions_path: 类型定义文件路径

    Returns:
        验证结果
    """
    processor = PlaceholderProcessor(type_definitions_path)
    placeholders = processor.extract_placeholders(text)
    return processor.validate_placeholders(placeholders)

# Create a default instance for easy import
intelligent_placeholder_processor = PlaceholderProcessor()