"""
Report Quality Checker Service

This service provides comprehensive quality checking for generated reports including:
- Language fluency and readability analysis
- Data consistency validation
- LLM-driven content optimization suggestions
- Quality scoring and feedback mechanisms
"""

import json
import logging
import re
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from sqlalchemy.orm import Session

# 使用React Agent系统和LLM智能选择器
# from app.services.llm.client import LLMServerClient as LLMProviderManager, LLMRequest, LLMResponse
# 使用新的LLM服务
from app.services.infrastructure.ai.llm import select_best_model_for_user, ask_agent_for_user

logger = logging.getLogger(__name__)


class QualityIssueType(Enum):
    """Types of quality issues that can be detected"""

    LANGUAGE_FLUENCY = "language_fluency"
    DATA_INCONSISTENCY = "data_inconsistency"
    FORMATTING_ERROR = "formatting_error"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    MISSING_DATA = "missing_data"
    CALCULATION_ERROR = "calculation_error"


class QualitySeverity(Enum):
    """Severity levels for quality issues"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class QualityIssue:
    """Represents a quality issue found in the report"""

    issue_type: QualityIssueType
    severity: QualitySeverity
    description: str
    location: str  # Where in the report the issue was found
    suggestion: Optional[str] = None
    confidence: float = 0.0
    auto_fixable: bool = False
    original_text: Optional[str] = None
    suggested_text: Optional[str] = None


@dataclass
class QualityMetrics:
    """Quality metrics for a report"""

    overall_score: float  # 0-100
    fluency_score: float
    consistency_score: float
    completeness_score: float
    accuracy_score: float
    readability_score: float

    # Detailed metrics
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float
    complex_words_ratio: float

    # Issue counts by severity
    critical_issues: int = 0
    high_issues: int = 0
    medium_issues: int = 0
    low_issues: int = 0


@dataclass
class QualityCheckResult:
    """Complete quality check result"""

    metrics: QualityMetrics
    issues: List[QualityIssue]
    suggestions: List[str]
    processing_time: float
    timestamp: datetime
    llm_analysis: Optional[Dict[str, Any]] = None


class LanguageAnalyzer:
    """Analyzes language quality and readability"""

    def __init__(self):
        # Chinese punctuation patterns
        self.chinese_punctuation = r'[。！？；：，、""' "（）【】《》〈〉]"
        self.sentence_endings = r"[。！？]"

    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text for language quality metrics"""
        try:
            # Basic text statistics
            word_count = len(text.replace(" ", ""))  # Chinese character count
            sentences = self._split_sentences(text)
            sentence_count = len(sentences)
            paragraphs = text.split("\n\n")
            paragraph_count = len([p for p in paragraphs if p.strip()])

            # Calculate average sentence length
            avg_sentence_length = (
                word_count / sentence_count if sentence_count > 0 else 0
            )

            # Analyze sentence structure
            fluency_issues = self._check_fluency(sentences)

            # Calculate readability score (simplified for Chinese)
            readability_score = self._calculate_readability(text, sentences)

            return {
                "word_count": word_count,
                "sentence_count": sentence_count,
                "paragraph_count": paragraph_count,
                "avg_sentence_length": avg_sentence_length,
                "readability_score": readability_score,
                "fluency_issues": fluency_issues,
                "complex_sentences": self._count_complex_sentences(sentences),
            }

        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return {
                "word_count": 0,
                "sentence_count": 0,
                "paragraph_count": 0,
                "avg_sentence_length": 0,
                "readability_score": 0,
                "fluency_issues": [],
                "complex_sentences": 0,
            }

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        sentences = re.split(self.sentence_endings, text)
        return [s.strip() for s in sentences if s.strip()]

    def _check_fluency(self, sentences: List[str]) -> List[Dict[str, Any]]:
        """Check for fluency issues in sentences"""
        issues = []

        for i, sentence in enumerate(sentences):
            # Check for very short sentences (might be incomplete)
            if len(sentence) < 5:
                issues.append(
                    {
                        "type": "short_sentence",
                        "sentence_index": i,
                        "sentence": sentence,
                        "description": "句子过短，可能不完整",
                    }
                )

            # Check for extremely long sentences (considering modern LLM capabilities)
            # Increased threshold since modern LLMs handle longer contexts well
            if len(sentence) > 200:
                issues.append(
                    {
                        "type": "long_sentence",
                        "sentence_index": i,
                        "sentence": sentence[:50] + "...",
                        "description": "句子极长，可能影响阅读体验",
                    }
                )

            # Check for repeated punctuation
            if re.search(r"[。！？]{2,}", sentence):
                issues.append(
                    {
                        "type": "repeated_punctuation",
                        "sentence_index": i,
                        "sentence": sentence,
                        "description": "重复标点符号",
                    }
                )

        return issues

    def _calculate_readability(self, text: str, sentences: List[str]) -> float:
        """Calculate readability score (0-100, higher is better)"""
        try:
            if not sentences:
                return 0

            # Simple readability calculation for Chinese
            avg_sentence_length = len(text) / len(sentences)

            # Penalty for very long sentences (adjusted for modern LLM capabilities)
            # Increased threshold since modern LLMs handle longer contexts well
            length_penalty = max(0, (avg_sentence_length - 60) * 1.5)

            # Base score
            base_score = 100

            # Apply penalties
            readability_score = max(0, base_score - length_penalty)

            return min(100, readability_score)

        except Exception:
            return 50  # Default score

    def _count_complex_sentences(self, sentences: List[str]) -> int:
        """Count sentences that might be complex"""
        complex_count = 0
        complex_patterns = [
            r"虽然.*但是",  # although...but
            r"不仅.*而且",  # not only...but also
            r"如果.*那么",  # if...then
            r"因为.*所以",  # because...so
        ]

        for sentence in sentences:
            for pattern in complex_patterns:
                if re.search(pattern, sentence):
                    complex_count += 1
                    break

        return complex_count


class DataConsistencyValidator:
    """Validates data consistency in reports"""

    def __init__(self):
        self.number_pattern = r"[\d,]+\.?\d*"
        self.percentage_pattern = r"\d+\.?\d*%"
        self.date_pattern = r"\d{4}年\d{1,2}月|\d{1,2}月\d{1,2}日"

    def validate_report(
        self, report_content: str, source_data: Optional[Dict[str, Any]] = None
    ) -> List[QualityIssue]:
        """Validate data consistency in the report"""
        issues = []

        try:
            # Extract numbers and validate consistency
            numbers = self._extract_numbers(report_content)
            issues.extend(self._check_number_consistency(numbers))

            # Check percentage consistency
            percentages = self._extract_percentages(report_content)
            issues.extend(self._check_percentage_consistency(percentages))

            # Check date consistency
            dates = self._extract_dates(report_content)
            issues.extend(self._check_date_consistency(dates))

            # Validate against source data if provided
            if source_data:
                issues.extend(
                    self._validate_against_source(report_content, source_data)
                )

        except Exception as e:
            logger.error(f"Error validating data consistency: {e}")
            issues.append(
                QualityIssue(
                    issue_type=QualityIssueType.DATA_INCONSISTENCY,
                    severity=QualitySeverity.MEDIUM,
                    description=f"数据一致性检查失败: {str(e)}",
                    location="全文",
                )
            )

        return issues

    def _extract_numbers(self, text: str) -> List[Tuple[str, float, str]]:
        """Extract numbers with context"""
        numbers = []
        for match in re.finditer(self.number_pattern, text):
            try:
                number_str = match.group()
                number_val = float(number_str.replace(",", ""))
                context = text[max(0, match.start() - 20) : match.end() + 20]
                numbers.append((number_str, number_val, context))
            except ValueError:
                continue
        return numbers

    def _extract_percentages(self, text: str) -> List[Tuple[str, float, str]]:
        """Extract percentages with context"""
        percentages = []
        for match in re.finditer(self.percentage_pattern, text):
            try:
                percent_str = match.group()
                percent_val = float(percent_str.replace("%", ""))
                context = text[max(0, match.start() - 20) : match.end() + 20]
                percentages.append((percent_str, percent_val, context))
            except ValueError:
                continue
        return percentages

    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text"""
        dates = []
        for match in re.finditer(self.date_pattern, text):
            dates.append(match.group())
        return dates

    def _check_number_consistency(
        self, numbers: List[Tuple[str, float, str]]
    ) -> List[QualityIssue]:
        """Check for number consistency issues"""
        issues = []

        # Check for suspiciously large numbers
        for num_str, num_val, context in numbers:
            if num_val > 1000000000:  # 10 billion
                issues.append(
                    QualityIssue(
                        issue_type=QualityIssueType.DATA_INCONSISTENCY,
                        severity=QualitySeverity.MEDIUM,
                        description=f"数值异常大: {num_str}",
                        location=context,
                        suggestion="请检查数值是否正确",
                    )
                )

        return issues

    def _check_percentage_consistency(
        self, percentages: List[Tuple[str, float, str]]
    ) -> List[QualityIssue]:
        """Check percentage consistency"""
        issues = []

        for percent_str, percent_val, context in percentages:
            if percent_val > 100:
                issues.append(
                    QualityIssue(
                        issue_type=QualityIssueType.DATA_INCONSISTENCY,
                        severity=QualitySeverity.HIGH,
                        description=f"百分比超过100%: {percent_str}",
                        location=context,
                        suggestion="检查百分比计算是否正确",
                    )
                )
            elif percent_val < 0:
                issues.append(
                    QualityIssue(
                        issue_type=QualityIssueType.DATA_INCONSISTENCY,
                        severity=QualitySeverity.HIGH,
                        description=f"百分比为负数: {percent_str}",
                        location=context,
                        suggestion="检查百分比计算是否正确",
                    )
                )

        return issues

    def _check_date_consistency(self, dates: List[str]) -> List[QualityIssue]:
        """Check date consistency"""
        issues = []

        # Basic date format validation
        for date in dates:
            if "月" in date and "年" in date:
                try:
                    # Extract year and month
                    year_match = re.search(r"(\d{4})年", date)
                    month_match = re.search(r"(\d{1,2})月", date)

                    if year_match and month_match:
                        year = int(year_match.group(1))
                        month = int(month_match.group(1))

                        if year < 1900 or year > 2100:
                            issues.append(
                                QualityIssue(
                                    issue_type=QualityIssueType.DATA_INCONSISTENCY,
                                    severity=QualitySeverity.MEDIUM,
                                    description=f"年份异常: {date}",
                                    location=date,
                                    suggestion="检查年份是否正确",
                                )
                            )

                        if month < 1 or month > 12:
                            issues.append(
                                QualityIssue(
                                    issue_type=QualityIssueType.DATA_INCONSISTENCY,
                                    severity=QualitySeverity.HIGH,
                                    description=f"月份无效: {date}",
                                    location=date,
                                    suggestion="检查月份是否正确",
                                )
                            )
                except ValueError:
                    continue

        return issues

    def _validate_against_source(
        self, report_content: str, source_data: Dict[str, Any]
    ) -> List[QualityIssue]:
        """Validate report data against source data"""
        issues = []

        # This is a simplified validation - in practice, you'd need more sophisticated matching
        try:
            if "expected_values" in source_data:
                for key, expected_value in source_data["expected_values"].items():
                    if str(expected_value) not in report_content:
                        issues.append(
                            QualityIssue(
                                issue_type=QualityIssueType.DATA_INCONSISTENCY,
                                severity=QualitySeverity.MEDIUM,
                                description=f"预期数值未在报告中找到: {key}={expected_value}",
                                location="数据验证",
                                suggestion="检查数据是否正确替换",
                            )
                        )
        except Exception as e:
            logger.error(f"Error validating against source data: {e}")

        return issues


class ReportQualityChecker:
    """Main report quality checker service"""

    def __init__(self, db: Session):
        self.db = db
        self.llm_manager = LLMProviderManager(db)
        self.language_analyzer = LanguageAnalyzer()
        self.data_validator = DataConsistencyValidator()

        # Quality check prompts
        self.quality_check_prompt = """
你是一个专业的报告质量检查专家。请分析以下报告内容的质量，并提供改进建议。

报告内容：
{report_content}

请从以下方面进行分析：
1. 语言流畅性和可读性
2. 逻辑结构和连贯性
3. 数据表述的准确性
4. 格式和排版的规范性
5. 内容的完整性

请以JSON格式返回分析结果，包含：
- overall_assessment: 总体评价
- fluency_score: 流畅性评分 (0-100)
- logic_score: 逻辑性评分 (0-100)
- accuracy_score: 准确性评分 (0-100)
- completeness_score: 完整性评分 (0-100)
- suggestions: 改进建议列表
- issues: 发现的问题列表
"""

        self.optimization_prompt = """
请优化以下报告内容，使其更加专业、流畅和易读：

原始内容：
{original_content}

发现的问题：
{issues}

请提供：
1. 优化后的内容
2. 主要改进点说明
3. 置信度评分 (0-100)

以JSON格式返回结果。
"""

    def check_report_quality(
        self,
        report_content: str,
        source_data: Optional[Dict[str, Any]] = None,
        enable_llm_analysis: bool = True,
    ) -> QualityCheckResult:
        """Perform comprehensive quality check on report"""
        start_time = datetime.now()

        try:
            # Language analysis
            language_analysis = self.language_analyzer.analyze_text(report_content)

            # Data consistency validation
            consistency_issues = self.data_validator.validate_report(
                report_content, source_data
            )

            # LLM-based quality analysis
            llm_analysis = None
            llm_issues = []
            if enable_llm_analysis and self.llm_manager.get_available_providers():
                try:
                    llm_analysis = self._perform_llm_analysis(report_content)
                    llm_issues = self._extract_llm_issues(llm_analysis)
                except Exception as e:
                    logger.error(f"LLM analysis failed: {e}")

            # Combine all issues
            all_issues = consistency_issues + llm_issues

            # Calculate quality metrics
            metrics = self._calculate_quality_metrics(
                language_analysis, all_issues, llm_analysis
            )

            # Generate suggestions
            suggestions = self._generate_suggestions(all_issues, language_analysis)

            processing_time = (datetime.now() - start_time).total_seconds()

            return QualityCheckResult(
                metrics=metrics,
                issues=all_issues,
                suggestions=suggestions,
                processing_time=processing_time,
                timestamp=datetime.now(),
                llm_analysis=llm_analysis,
            )

        except Exception as e:
            logger.error(f"Quality check failed: {e}")
            # Return minimal result on error
            return QualityCheckResult(
                metrics=QualityMetrics(
                    overall_score=0,
                    fluency_score=0,
                    consistency_score=0,
                    completeness_score=0,
                    accuracy_score=0,
                    readability_score=0,
                    word_count=len(report_content),
                    sentence_count=0,
                    paragraph_count=0,
                    avg_sentence_length=0,
                    complex_words_ratio=0,
                ),
                issues=[
                    QualityIssue(
                        issue_type=QualityIssueType.FORMATTING_ERROR,
                        severity=QualitySeverity.HIGH,
                        description=f"质量检查失败: {str(e)}",
                        location="系统错误",
                    )
                ],
                suggestions=["请检查报告内容格式"],
                processing_time=(datetime.now() - start_time).total_seconds(),
                timestamp=datetime.now(),
            )

    def _perform_llm_analysis(self, report_content: str) -> Dict[str, Any]:
        """Perform LLM-based quality analysis"""
        try:
            providers = self.llm_manager.get_available_providers()
            if not providers:
                return {}

            # Use the first available provider
            provider = providers[0]

            request = LLMRequest(
                messages=[
                    {"role": "system", "content": "你是一个专业的报告质量分析专家。"},
                    {
                        "role": "user",
                        "content": self.quality_check_prompt.format(
                            report_content=report_content[:4000]  # Limit content length
                        ),
                    },
                ],
                model="gpt-4" if "openai" in provider else None,
                temperature=0.1,
                max_tokens=2000,
            )

            response = self.llm_manager.call_llm(provider, request)

            # Try to parse JSON response
            try:
                return json.loads(response.content)
            except json.JSONDecodeError:
                # If not valid JSON, return structured response
                return {
                    "overall_assessment": response.content,
                    "fluency_score": 75,
                    "logic_score": 75,
                    "accuracy_score": 75,
                    "completeness_score": 75,
                    "suggestions": ["基于LLM分析的建议"],
                    "issues": [],
                }

        except Exception as e:
            logger.error(f"LLM analysis error: {e}")
            return {}

    def _extract_llm_issues(self, llm_analysis: Dict[str, Any]) -> List[QualityIssue]:
        """Extract quality issues from LLM analysis"""
        issues = []

        try:
            if "issues" in llm_analysis:
                for issue_data in llm_analysis["issues"]:
                    if isinstance(issue_data, dict):
                        issues.append(
                            QualityIssue(
                                issue_type=QualityIssueType.LANGUAGE_FLUENCY,
                                severity=QualitySeverity.MEDIUM,
                                description=issue_data.get("description", ""),
                                location=issue_data.get("location", ""),
                                suggestion=issue_data.get("suggestion", ""),
                                confidence=0.8,
                            )
                        )
                    elif isinstance(issue_data, str):
                        issues.append(
                            QualityIssue(
                                issue_type=QualityIssueType.LANGUAGE_FLUENCY,
                                severity=QualitySeverity.MEDIUM,
                                description=issue_data,
                                location="LLM分析",
                                confidence=0.8,
                            )
                        )
        except Exception as e:
            logger.error(f"Error extracting LLM issues: {e}")

        return issues

    def _calculate_quality_metrics(
        self,
        language_analysis: Dict[str, Any],
        issues: List[QualityIssue],
        llm_analysis: Optional[Dict[str, Any]] = None,
    ) -> QualityMetrics:
        """Calculate comprehensive quality metrics"""

        # Count issues by severity
        critical_count = sum(
            1 for issue in issues if issue.severity == QualitySeverity.CRITICAL
        )
        high_count = sum(
            1 for issue in issues if issue.severity == QualitySeverity.HIGH
        )
        medium_count = sum(
            1 for issue in issues if issue.severity == QualitySeverity.MEDIUM
        )
        low_count = sum(1 for issue in issues if issue.severity == QualitySeverity.LOW)

        # Calculate base scores
        fluency_score = language_analysis.get("readability_score", 75)

        # Adjust scores based on issues
        issue_penalty = (
            (critical_count * 20)
            + (high_count * 10)
            + (medium_count * 5)
            + (low_count * 2)
        )

        # Get LLM scores if available
        llm_fluency = (
            llm_analysis.get("fluency_score", fluency_score)
            if llm_analysis
            else fluency_score
        )
        llm_logic = llm_analysis.get("logic_score", 75) if llm_analysis else 75
        llm_accuracy = llm_analysis.get("accuracy_score", 75) if llm_analysis else 75
        llm_completeness = (
            llm_analysis.get("completeness_score", 75) if llm_analysis else 75
        )

        # Calculate final scores
        final_fluency = max(
            0, min(100, (fluency_score + llm_fluency) / 2 - issue_penalty)
        )
        final_consistency = max(
            0, min(100, 90 - (critical_count * 15) - (high_count * 10))
        )
        final_completeness = max(0, min(100, llm_completeness - issue_penalty))
        final_accuracy = max(0, min(100, llm_accuracy - issue_penalty))
        final_readability = max(0, min(100, fluency_score - (issue_penalty / 2)))

        # Overall score is weighted average
        overall_score = (
            final_fluency * 0.25
            + final_consistency * 0.25
            + final_completeness * 0.2
            + final_accuracy * 0.2
            + final_readability * 0.1
        )

        # Calculate complex words ratio (simplified for Chinese)
        complex_sentences = language_analysis.get("complex_sentences", 0)
        total_sentences = language_analysis.get("sentence_count", 1)
        complex_ratio = (
            complex_sentences / total_sentences if total_sentences > 0 else 0
        )

        return QualityMetrics(
            overall_score=round(overall_score, 2),
            fluency_score=round(final_fluency, 2),
            consistency_score=round(final_consistency, 2),
            completeness_score=round(final_completeness, 2),
            accuracy_score=round(final_accuracy, 2),
            readability_score=round(final_readability, 2),
            word_count=language_analysis.get("word_count", 0),
            sentence_count=language_analysis.get("sentence_count", 0),
            paragraph_count=language_analysis.get("paragraph_count", 0),
            avg_sentence_length=language_analysis.get("avg_sentence_length", 0),
            complex_words_ratio=round(complex_ratio, 3),
            critical_issues=critical_count,
            high_issues=high_count,
            medium_issues=medium_count,
            low_issues=low_count,
        )

    def _generate_suggestions(
        self, issues: List[QualityIssue], language_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate improvement suggestions based on analysis"""
        suggestions = []

        # Add suggestions from issues
        for issue in issues:
            if issue.suggestion:
                suggestions.append(issue.suggestion)

        # Add general suggestions based on language analysis
        avg_length = language_analysis.get("avg_sentence_length", 0)
        if avg_length > 50:
            suggestions.append("建议缩短句子长度，提高可读性")
        elif avg_length < 10:
            suggestions.append("建议增加句子内容，使表达更完整")

        fluency_issues = language_analysis.get("fluency_issues", [])
        if len(fluency_issues) > 5:
            suggestions.append("发现多个语言流畅性问题，建议仔细检查语法和表达")

        # Remove duplicates and limit suggestions
        unique_suggestions = list(set(suggestions))
        return unique_suggestions[:10]  # Limit to 10 suggestions

    def optimize_content(
        self, content: str, issues: List[QualityIssue]
    ) -> Dict[str, Any]:
        """Use LLM to optimize content based on identified issues"""
        try:
            providers = self.llm_manager.get_available_providers()
            if not providers:
                return {
                    "optimized_content": content,
                    "improvements": ["LLM服务不可用，无法进行内容优化"],
                    "confidence": 0,
                }

            provider = providers[0]

            # Format issues for prompt
            issues_text = "\n".join(
                [
                    f"- {issue.description} (位置: {issue.location})"
                    for issue in issues[:5]  # Limit to top 5 issues
                ]
            )

            request = LLMRequest(
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的文档编辑专家，擅长优化报告内容。",
                    },
                    {
                        "role": "user",
                        "content": self.optimization_prompt.format(
                            original_content=content[:3000],  # Limit content length
                            issues=issues_text,
                        ),
                    },
                ],
                model="gpt-4" if "openai" in provider else None,
                temperature=0.2,
                max_tokens=3000,
            )

            response = self.llm_manager.call_llm(provider, request)

            # Try to parse JSON response
            try:
                result = json.loads(response.content)
                return {
                    "optimized_content": result.get("optimized_content", content),
                    "improvements": result.get("improvements", []),
                    "confidence": result.get("confidence", 75),
                }
            except json.JSONDecodeError:
                return {
                    "optimized_content": response.content,
                    "improvements": ["基于LLM的内容优化"],
                    "confidence": 70,
                }

        except Exception as e:
            logger.error(f"Content optimization failed: {e}")
            return {
                "optimized_content": content,
                "improvements": [f"内容优化失败: {str(e)}"],
                "confidence": 0,
            }

    def get_quality_feedback(self, result: QualityCheckResult) -> Dict[str, Any]:
        """Generate structured feedback for the quality check result"""
        feedback = {
            "overall_rating": self._get_rating_from_score(result.metrics.overall_score),
            "summary": self._generate_summary(result),
            "priority_issues": [
                issue
                for issue in result.issues
                if issue.severity in [QualitySeverity.CRITICAL, QualitySeverity.HIGH]
            ][:5],
            "recommendations": result.suggestions[:5],
            "metrics_breakdown": {
                "fluency": result.metrics.fluency_score,
                "consistency": result.metrics.consistency_score,
                "completeness": result.metrics.completeness_score,
                "accuracy": result.metrics.accuracy_score,
                "readability": result.metrics.readability_score,
            },
        }

        return feedback

    def _get_rating_from_score(self, score: float) -> str:
        """Convert numeric score to rating"""
        if score >= 90:
            return "优秀"
        elif score >= 80:
            return "良好"
        elif score >= 70:
            return "一般"
        elif score >= 60:
            return "需要改进"
        else:
            return "较差"

    def _generate_summary(self, result: QualityCheckResult) -> str:
        """Generate a summary of the quality check result"""
        score = result.metrics.overall_score
        issue_count = len(result.issues)
        critical_count = result.metrics.critical_issues

        if score >= 85 and critical_count == 0:
            return f"报告质量优秀（{score:.1f}分），发现{issue_count}个可优化点。"
        elif score >= 70:
            return f"报告质量良好（{score:.1f}分），发现{issue_count}个问题需要关注。"
        elif critical_count > 0:
            return f"报告存在{critical_count}个严重问题，总体质量评分{score:.1f}分，建议优先处理关键问题。"
        else:
            return f"报告质量有待提升（{score:.1f}分），发现{issue_count}个问题，建议进行全面优化。"


# Utility functions for external use
def create_quality_checker(db: Session) -> ReportQualityChecker:
    """Factory function to create a quality checker instance"""
    return ReportQualityChecker(db)


def quick_quality_check(
    report_content: str, db: Session, enable_llm: bool = True
) -> QualityCheckResult:
    """Quick quality check function for simple use cases"""
    checker = create_quality_checker(db)
    return checker.check_report_quality(report_content, enable_llm_analysis=enable_llm)
