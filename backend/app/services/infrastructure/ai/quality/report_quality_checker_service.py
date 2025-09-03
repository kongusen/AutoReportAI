"""
报告质量检查器服务

负责检查和评估报告内容质量，提供改进建议
"""

import logging
import re
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QualityDimension(Enum):
    """质量维度"""
    CONTENT_COMPLETENESS = "content_completeness"   # 内容完整性
    DATA_ACCURACY = "data_accuracy"                 # 数据准确性
    STRUCTURE_CLARITY = "structure_clarity"         # 结构清晰度
    LANGUAGE_QUALITY = "language_quality"           # 语言质量
    VISUAL_PRESENTATION = "visual_presentation"     # 视觉呈现
    LOGICAL_CONSISTENCY = "logical_consistency"     # 逻辑一致性
    TIMELINESS = "timeliness"                       # 时效性
    ACTIONABILITY = "actionability"                 # 可操作性


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = 5   # 优秀
    GOOD = 4        # 良好
    FAIR = 3        # 中等
    POOR = 2        # 较差
    CRITICAL = 1    # 严重问题


class IssueSeverity(Enum):
    """问题严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityIssue:
    """质量问题"""
    dimension: QualityDimension
    severity: IssueSeverity
    description: str
    location: Optional[str] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False
    impact_score: float = 0.0


@dataclass
class QualityMetric:
    """质量指标"""
    dimension: QualityDimension
    score: float        # 0.0-1.0
    weight: float       # 权重
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityAssessmentResult:
    """质量评估结果"""
    overall_score: float
    quality_level: QualityLevel
    metrics: List[QualityMetric]
    issues: List[QualityIssue]
    suggestions: List[str]
    auto_improvements: List[str]
    metadata: Dict[str, Any]


class ReportQualityCheckerService:
    """报告质量检查器服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 质量检查规则
        self.quality_rules = {
            "content_length": {
                "min_length": 200,      # 最小长度
                "optimal_length": 1000,  # 理想长度
                "max_length": 10000     # 最大长度
            },
            "structure": {
                "required_sections": ["标题", "摘要", "分析", "结论"],
                "section_patterns": [
                    r"^#+\s*.+$",           # Markdown标题
                    r"^\d+\.\s*.+$",        # 数字序号
                    r"^[一二三四五六七八九十]+[、.]\s*.+$"  # 中文序号
                ],
                "paragraph_min_length": 50
            },
            "data_presentation": {
                "number_format_patterns": [
                    r"\d{1,3}(,\d{3})*",     # 千位分隔符
                    r"\d+\.\d+%",            # 百分比
                    r"\d+\.\d{2}",           # 两位小数
                ],
                "chart_indicators": ["图", "表", "chart", "graph", "visualization"],
                "data_source_indicators": ["数据来源", "source", "来源于"]
            },
            "language": {
                "professional_terms": ["分析", "显示", "表明", "指出", "建议", "推荐"],
                "avoid_terms": ["可能", "也许", "大概", "估计"],  # 不确定性词汇
                "conjunction_words": ["因此", "所以", "但是", "然而", "另外"],
                "passive_voice_limit": 0.3  # 被动语态使用限制
            }
        }
        
        # 维度权重配置
        self.dimension_weights = {
            QualityDimension.CONTENT_COMPLETENESS: 0.20,
            QualityDimension.DATA_ACCURACY: 0.18,
            QualityDimension.STRUCTURE_CLARITY: 0.15,
            QualityDimension.LANGUAGE_QUALITY: 0.12,
            QualityDimension.LOGICAL_CONSISTENCY: 0.12,
            QualityDimension.VISUAL_PRESENTATION: 0.10,
            QualityDimension.TIMELINESS: 0.08,
            QualityDimension.ACTIONABILITY: 0.05
        }

    async def check_report_quality(
        self, 
        report_content: str, 
        quality_criteria: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        检查和评估报告质量
        
        Args:
            report_content: 报告内容
            quality_criteria: 质量检查标准
            
        Returns:
            质量评估结果字典
        """
        try:
            self.logger.info(f"开始报告质量检查，内容长度: {len(report_content)}")
            
            # 更新检查规则（如果提供了自定义标准）
            effective_criteria = self._merge_quality_criteria(quality_criteria)
            
            # 执行各维度质量检查
            quality_metrics = await self._assess_all_dimensions(
                report_content, effective_criteria
            )
            
            # 识别质量问题
            quality_issues = self._identify_quality_issues(
                report_content, quality_metrics, effective_criteria
            )
            
            # 计算综合评分
            overall_score = self._calculate_overall_score(quality_metrics)
            
            # 确定质量等级
            quality_level = self._determine_quality_level(overall_score)
            
            # 生成改进建议
            suggestions = self._generate_improvement_suggestions(
                quality_issues, quality_metrics
            )
            
            # 识别自动改进机会
            auto_improvements = self._identify_auto_improvements(quality_issues)
            
            # 生成详细分析报告
            analysis_details = self._generate_analysis_details(
                report_content, quality_metrics, quality_issues
            )
            
            result = {
                "overall_score": overall_score,
                "quality_level": quality_level.name,
                "quality_grade": self._score_to_grade(overall_score),
                "dimension_scores": {
                    metric.dimension.value: metric.score for metric in quality_metrics
                },
                "weighted_scores": {
                    metric.dimension.value: metric.score * metric.weight 
                    for metric in quality_metrics
                },
                "issues": [self._issue_to_dict(issue) for issue in quality_issues],
                "suggestions": suggestions,
                "auto_improvements": auto_improvements,
                "content_analysis": analysis_details,
                "is_acceptable": overall_score >= 0.6,
                "requires_revision": overall_score < 0.7,
                "checked_at": datetime.now().isoformat(),
                "metadata": {
                    "content_length": len(report_content),
                    "word_count": len(report_content.split()),
                    "paragraph_count": len([p for p in report_content.split('\n\n') if p.strip()]),
                    "issues_found": len(quality_issues),
                    "critical_issues": len([i for i in quality_issues if i.severity == IssueSeverity.CRITICAL]),
                    "auto_fixable_issues": len([i for i in quality_issues if i.auto_fixable]),
                    "assessment_complete": True
                }
            }
            
            self.logger.info(
                f"质量检查完成: 评分={overall_score:.2f}, 等级={quality_level.name}, "
                f"问题={len(quality_issues)}, 建议={len(suggestions)}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"报告质量检查失败: {e}")
            raise ValueError(f"报告质量检查失败: {str(e)}")

    def _merge_quality_criteria(self, custom_criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """合并质量检查标准"""
        effective_criteria = self.quality_rules.copy()
        
        if custom_criteria:
            for category, criteria in custom_criteria.items():
                if category in effective_criteria:
                    effective_criteria[category].update(criteria)
                else:
                    effective_criteria[category] = criteria
        
        return effective_criteria

    async def _assess_all_dimensions(
        self, 
        content: str, 
        criteria: Dict[str, Any]
    ) -> List[QualityMetric]:
        """评估所有质量维度"""
        
        metrics = []
        
        # 内容完整性
        completeness_score = self._assess_content_completeness(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.CONTENT_COMPLETENESS,
            score=completeness_score,
            weight=self.dimension_weights[QualityDimension.CONTENT_COMPLETENESS],
            details={"length_score": completeness_score, "structure_score": completeness_score}
        ))
        
        # 数据准确性
        accuracy_score = self._assess_data_accuracy(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.DATA_ACCURACY,
            score=accuracy_score,
            weight=self.dimension_weights[QualityDimension.DATA_ACCURACY],
            details={"number_format_score": accuracy_score, "source_citation_score": accuracy_score}
        ))
        
        # 结构清晰度
        structure_score = self._assess_structure_clarity(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.STRUCTURE_CLARITY,
            score=structure_score,
            weight=self.dimension_weights[QualityDimension.STRUCTURE_CLARITY],
            details={"heading_score": structure_score, "flow_score": structure_score}
        ))
        
        # 语言质量
        language_score = self._assess_language_quality(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.LANGUAGE_QUALITY,
            score=language_score,
            weight=self.dimension_weights[QualityDimension.LANGUAGE_QUALITY],
            details={"grammar_score": language_score, "terminology_score": language_score}
        ))
        
        # 逻辑一致性
        consistency_score = self._assess_logical_consistency(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.LOGICAL_CONSISTENCY,
            score=consistency_score,
            weight=self.dimension_weights[QualityDimension.LOGICAL_CONSISTENCY],
            details={"argument_flow": consistency_score, "conclusion_support": consistency_score}
        ))
        
        # 视觉呈现
        visual_score = self._assess_visual_presentation(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.VISUAL_PRESENTATION,
            score=visual_score,
            weight=self.dimension_weights[QualityDimension.VISUAL_PRESENTATION],
            details={"formatting_score": visual_score, "chart_integration": visual_score}
        ))
        
        # 时效性
        timeliness_score = self._assess_timeliness(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.TIMELINESS,
            score=timeliness_score,
            weight=self.dimension_weights[QualityDimension.TIMELINESS],
            details={"data_freshness": timeliness_score, "relevance_score": timeliness_score}
        ))
        
        # 可操作性
        actionability_score = self._assess_actionability(content, criteria)
        metrics.append(QualityMetric(
            dimension=QualityDimension.ACTIONABILITY,
            score=actionability_score,
            weight=self.dimension_weights[QualityDimension.ACTIONABILITY],
            details={"recommendations_present": actionability_score, "specificity_score": actionability_score}
        ))
        
        return metrics

    def _assess_content_completeness(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估内容完整性"""
        score = 1.0
        length_rules = criteria.get("content_length", self.quality_rules["content_length"])
        
        content_length = len(content)
        
        # 长度评分
        if content_length < length_rules["min_length"]:
            score *= 0.3  # 内容过短
        elif content_length > length_rules["max_length"]:
            score *= 0.7  # 内容过长
        elif content_length < length_rules["optimal_length"]:
            score *= 0.8  # 长度不够理想
        
        # 检查必要部分
        required_sections = criteria.get("structure", {}).get("required_sections", [])
        found_sections = 0
        for section in required_sections:
            if section in content or section.lower() in content.lower():
                found_sections += 1
        
        if required_sections:
            section_score = found_sections / len(required_sections)
            score *= (0.5 + section_score * 0.5)  # 结构完整性权重50%
        
        # 检查占位符处理
        if "{{" in content or "}}" in content:
            score *= 0.4  # 未处理占位符严重影响质量
        
        return round(max(score, 0.1), 2)

    def _assess_data_accuracy(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估数据准确性"""
        score = 1.0
        data_rules = criteria.get("data_presentation", self.quality_rules["data_presentation"])
        
        # 检查数字格式规范性
        numbers = re.findall(r'\d+(?:\.\d+)?(?:%|万|千|亿)?', content)
        if numbers:
            formatted_numbers = 0
            for pattern in data_rules["number_format_patterns"]:
                formatted_numbers += len(re.findall(pattern, content))
            
            if len(numbers) > 0:
                format_ratio = min(formatted_numbers / len(numbers), 1.0)
                score *= (0.7 + format_ratio * 0.3)
        
        # 检查数据来源标注
        source_indicators = data_rules.get("data_source_indicators", [])
        has_data_source = any(indicator in content for indicator in source_indicators)
        if not has_data_source and len(numbers) > 3:  # 数据较多但缺少来源
            score *= 0.8
        
        # 检查异常数值
        large_numbers = re.findall(r'\d{10,}', content)  # 检查异常大的数字
        if large_numbers:
            score *= 0.9  # 可能存在数据错误
        
        return round(max(score, 0.2), 2)

    def _assess_structure_clarity(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估结构清晰度"""
        score = 1.0
        structure_rules = criteria.get("structure", self.quality_rules["structure"])
        
        # 检查标题结构
        heading_count = 0
        for pattern in structure_rules["section_patterns"]:
            headings = re.findall(pattern, content, re.MULTILINE)
            heading_count += len(headings)
        
        word_count = len(content.split())
        if word_count > 200:  # 长内容需要更多结构
            expected_headings = max(word_count // 300, 2)
            if heading_count < expected_headings:
                score *= 0.7
        
        # 检查段落结构
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        short_paragraphs = [p for p in paragraphs if len(p) < structure_rules["paragraph_min_length"]]
        
        if paragraphs:
            long_paragraph_ratio = (len(paragraphs) - len(short_paragraphs)) / len(paragraphs)
            score *= (0.6 + long_paragraph_ratio * 0.4)
        
        # 检查逻辑连接词
        conjunction_words = criteria.get("language", {}).get("conjunction_words", [])
        conjunction_count = sum(content.count(word) for word in conjunction_words)
        if conjunction_count < word_count // 200:  # 逻辑连接词比例
            score *= 0.85
        
        return round(max(score, 0.3), 2)

    def _assess_language_quality(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估语言质量"""
        score = 1.0
        language_rules = criteria.get("language", self.quality_rules["language"])
        
        # 检查专业术语使用
        professional_terms = language_rules.get("professional_terms", [])
        professional_count = sum(content.count(term) for term in professional_terms)
        word_count = len(content.split())
        
        if word_count > 100:
            professional_ratio = professional_count / word_count
            if professional_ratio < 0.02:  # 专业性不足
                score *= 0.8
            elif professional_ratio > 0.1:  # 过度使用
                score *= 0.9
        
        # 检查不确定性词汇
        avoid_terms = language_rules.get("avoid_terms", [])
        uncertainty_count = sum(content.count(term) for term in avoid_terms)
        if uncertainty_count > word_count // 100:  # 不确定性词汇过多
            score *= 0.7
        
        # 检查重复词汇
        words = content.split()
        if words:
            unique_words = set(words)
            repetition_ratio = len(words) / len(unique_words)
            if repetition_ratio > 3.0:  # 词汇重复度过高
                score *= 0.85
        
        # 语法和拼写检查（简化版）
        grammar_issues = self._check_basic_grammar(content)
        if grammar_issues > word_count // 200:
            score *= 0.9
        
        return round(max(score, 0.4), 2)

    def _assess_logical_consistency(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估逻辑一致性"""
        score = 1.0
        
        # 检查逻辑流程
        logical_indicators = ["首先", "其次", "然后", "最后", "因此", "所以", "由于"]
        logical_count = sum(content.count(indicator) for indicator in logical_indicators)
        
        paragraphs = len([p for p in content.split('\n\n') if p.strip()])
        if paragraphs > 3 and logical_count < paragraphs // 2:
            score *= 0.8  # 缺乏逻辑连接
        
        # 检查矛盾表述
        contradictions = self._detect_contradictions(content)
        if contradictions:
            score *= (1.0 - len(contradictions) * 0.1)
        
        # 检查结论支撑
        has_conclusion = any(kw in content for kw in ["结论", "总结", "综上", "总而言之"])
        has_evidence = any(kw in content for kw in ["数据显示", "分析表明", "结果表明"])
        
        if has_conclusion and not has_evidence:
            score *= 0.7  # 结论缺乏支撑
        
        return round(max(score, 0.3), 2)

    def _assess_visual_presentation(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估视觉呈现"""
        score = 1.0
        data_rules = criteria.get("data_presentation", self.quality_rules["data_presentation"])
        
        # 检查图表集成
        chart_indicators = data_rules.get("chart_indicators", [])
        has_charts = any(indicator in content for indicator in chart_indicators)
        
        word_count = len(content.split())
        if word_count > 500 and not has_charts:
            score *= 0.7  # 长报告缺少图表
        
        # 检查格式化
        has_formatting = any(marker in content for marker in ['**', '*', '#', '##', '###'])
        if not has_formatting and word_count > 300:
            score *= 0.8  # 缺少格式化
        
        # 检查列表使用
        has_lists = any(marker in content for marker in ['-', '*', '•', '1.', '2.'])
        if not has_lists and word_count > 400:
            score *= 0.85  # 建议使用列表提高可读性
        
        # 检查表格
        has_tables = '|' in content or 'table' in content.lower() or '表格' in content
        if word_count > 800 and not has_tables and not has_charts:
            score *= 0.75  # 复杂数据缺少表格展示
        
        return round(max(score, 0.4), 2)

    def _assess_timeliness(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估时效性"""
        score = 1.0
        
        # 检查时间引用
        time_references = re.findall(
            r'\d{4}年|\d{1,2}月|\d{1,2}日|今天|昨天|本月|上月|今年|去年|最新|当前',
            content
        )
        
        if not time_references:
            score *= 0.6  # 缺少时间上下文
        
        # 检查数据时效性指标
        freshness_indicators = ["最新数据", "实时", "当前", "截止", "updated", "latest"]
        has_freshness = any(indicator in content.lower() for indicator in freshness_indicators)
        
        if not has_freshness and len(time_references) == 0:
            score *= 0.7  # 数据时效性不明
        
        # 检查过时信息
        old_references = re.findall(r'20[01]\d年', content)  # 检查是否有很久远的年份
        if old_references:
            current_year = datetime.now().year
            oldest_year = min(int(ref.replace('年', '')) for ref in old_references)
            if current_year - oldest_year > 5:
                score *= 0.8  # 数据较为陈旧
        
        return round(max(score, 0.5), 2)

    def _assess_actionability(self, content: str, criteria: Dict[str, Any]) -> float:
        """评估可操作性"""
        score = 1.0
        
        # 检查建议和推荐
        actionable_keywords = [
            "建议", "推荐", "应该", "需要", "可以", "考虑",
            "recommend", "suggest", "should", "need", "consider"
        ]
        actionable_count = sum(content.lower().count(kw) for kw in actionable_keywords)
        
        word_count = len(content.split())
        if word_count > 300:
            expected_actions = max(word_count // 200, 1)
            if actionable_count < expected_actions:
                score *= 0.7
        
        # 检查具体步骤
        step_indicators = ["步骤", "方法", "措施", "计划", "策略"]
        has_specific_steps = any(indicator in content for indicator in step_indicators)
        
        if actionable_count > 0 and not has_specific_steps:
            score *= 0.8  # 有建议但不够具体
        
        # 检查量化目标
        quantified_goals = re.findall(r'\d+%|\d+倍|提高\d+|降低\d+|增加\d+', content)
        if actionable_count > 2 and not quantified_goals:
            score *= 0.85  # 建议缺少量化目标
        
        return round(max(score, 0.4), 2)

    def _check_basic_grammar(self, content: str) -> int:
        """基础语法检查"""
        issues = 0
        
        # 检查常见语法问题
        grammar_patterns = [
            r'([。！？])\s*([a-z])',  # 句号后小写字母
            r'(\w)\s{2,}(\w)',        # 多余空格
            r'([，。！？])\1+',       # 重复标点
            r'\d+\s+%',               # 数字和百分号之间有空格
        ]
        
        for pattern in grammar_patterns:
            matches = re.findall(pattern, content)
            issues += len(matches)
        
        return issues

    def _detect_contradictions(self, content: str) -> List[str]:
        """检测矛盾表述"""
        contradictions = []
        content_lower = content.lower()
        
        # 简单矛盾检测
        contradiction_pairs = [
            (["增长", "提高", "上升"], ["下降", "降低", "减少"]),
            (["改善", "优化", "提升"], ["恶化", "降级", "退步"]),
            (["成功", "有效"], ["失败", "无效"])
        ]
        
        for positive_words, negative_words in contradiction_pairs:
            has_positive = any(word in content_lower for word in positive_words)
            has_negative = any(word in content_lower for word in negative_words)
            
            if has_positive and has_negative:
                contradictions.append(f"内容中同时出现正面和负面描述")
        
        return contradictions

    def _identify_quality_issues(
        self, 
        content: str, 
        metrics: List[QualityMetric], 
        criteria: Dict[str, Any]
    ) -> List[QualityIssue]:
        """识别质量问题"""
        issues = []
        
        for metric in metrics:
            if metric.score < 0.6:
                issues.append(QualityIssue(
                    dimension=metric.dimension,
                    severity=IssueSeverity.HIGH if metric.score < 0.4 else IssueSeverity.MEDIUM,
                    description=f"{metric.dimension.value} 评分较低: {metric.score:.1%}",
                    suggestion=self._get_dimension_improvement_suggestion(metric.dimension),
                    impact_score=metric.weight * (1 - metric.score)
                ))
        
        # 特定问题检查
        if "{{" in content:
            issues.append(QualityIssue(
                dimension=QualityDimension.CONTENT_COMPLETENESS,
                severity=IssueSeverity.CRITICAL,
                description="发现未处理的占位符",
                location="模板处理阶段",
                suggestion="确保所有占位符都被正确替换",
                auto_fixable=True,
                impact_score=0.5
            ))
        
        if len(content) < 100:
            issues.append(QualityIssue(
                dimension=QualityDimension.CONTENT_COMPLETENESS,
                severity=IssueSeverity.HIGH,
                description="报告内容过短",
                suggestion="增加详细分析和数据支撑",
                impact_score=0.3
            ))
        
        # 检查空白内容
        if not content.strip():
            issues.append(QualityIssue(
                dimension=QualityDimension.CONTENT_COMPLETENESS,
                severity=IssueSeverity.CRITICAL,
                description="报告内容为空",
                suggestion="生成有意义的报告内容",
                impact_score=1.0
            ))
        
        return issues

    def _get_dimension_improvement_suggestion(self, dimension: QualityDimension) -> str:
        """获取维度改进建议"""
        suggestions = {
            QualityDimension.CONTENT_COMPLETENESS: "增加内容深度和广度，确保涵盖所有必要信息",
            QualityDimension.DATA_ACCURACY: "验证数据准确性，规范数字格式，标注数据来源",
            QualityDimension.STRUCTURE_CLARITY: "改善文档结构，添加标题和段落，使用列表和图表",
            QualityDimension.LANGUAGE_QUALITY: "提高语言专业性，减少不确定性表述，改善语法",
            QualityDimension.LOGICAL_CONSISTENCY: "加强逻辑论证，确保论据支撑结论，避免矛盾表述",
            QualityDimension.VISUAL_PRESENTATION: "改善视觉呈现，添加图表和格式化，提高可读性",
            QualityDimension.TIMELINESS: "更新数据时间范围，明确时效性，使用最新信息",
            QualityDimension.ACTIONABILITY: "增加具体建议和行动方案，提供可操作的指导"
        }
        return suggestions.get(dimension, "改善该维度的质量表现")

    def _calculate_overall_score(self, metrics: List[QualityMetric]) -> float:
        """计算综合评分"""
        if not metrics:
            return 0.0
        
        weighted_sum = sum(metric.score * metric.weight for metric in metrics)
        total_weight = sum(metric.weight for metric in metrics)
        
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        return round(max(min(overall_score, 1.0), 0.0), 2)

    def _determine_quality_level(self, score: float) -> QualityLevel:
        """确定质量等级"""
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.8:
            return QualityLevel.GOOD
        elif score >= 0.6:
            return QualityLevel.FAIR
        elif score >= 0.4:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL

    def _score_to_grade(self, score: float) -> str:
        """评分转换为等级"""
        if score >= 0.95:
            return "A+"
        elif score >= 0.9:
            return "A"
        elif score >= 0.85:
            return "A-"
        elif score >= 0.8:
            return "B+"
        elif score >= 0.75:
            return "B"
        elif score >= 0.7:
            return "B-"
        elif score >= 0.6:
            return "C"
        elif score >= 0.5:
            return "D"
        else:
            return "F"

    def _generate_improvement_suggestions(
        self, 
        issues: List[QualityIssue], 
        metrics: List[QualityMetric]
    ) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于问题生成建议
        critical_issues = [i for i in issues if i.severity == IssueSeverity.CRITICAL]
        high_issues = [i for i in issues if i.severity == IssueSeverity.HIGH]
        
        if critical_issues:
            suggestions.append(f"紧急处理 {len(critical_issues)} 个关键质量问题")
        
        if high_issues:
            suggestions.append(f"优先解决 {len(high_issues)} 个高优先级问题")
        
        # 基于评分生成建议
        low_score_metrics = [m for m in metrics if m.score < 0.7]
        for metric in low_score_metrics:
            suggestions.append(self._get_dimension_improvement_suggestion(metric.dimension))
        
        # 综合建议
        overall_score = self._calculate_overall_score(metrics)
        if overall_score < 0.6:
            suggestions.append("建议全面修订报告内容和结构")
        elif overall_score < 0.8:
            suggestions.append("建议重点改善薄弱环节，提升整体质量")
        
        return list(set(suggestions))  # 去重

    def _identify_auto_improvements(self, issues: List[QualityIssue]) -> List[str]:
        """识别自动改进机会"""
        auto_improvements = []
        
        auto_fixable_issues = [i for i in issues if i.auto_fixable]
        for issue in auto_fixable_issues:
            auto_improvements.append(f"自动修复: {issue.description}")
        
        # 其他可自动改进的项目
        auto_improvements.extend([
            "自动格式化数字显示",
            "自动添加段落分隔",
            "自动优化标点符号使用",
            "自动调整文本格式"
        ])
        
        return auto_improvements

    def _generate_analysis_details(
        self, 
        content: str, 
        metrics: List[QualityMetric], 
        issues: List[QualityIssue]
    ) -> Dict[str, Any]:
        """生成详细分析信息"""
        
        return {
            "readability_analysis": {
                "avg_sentence_length": self._calculate_avg_sentence_length(content),
                "paragraph_count": len([p for p in content.split('\n\n') if p.strip()]),
                "complex_sentences": self._count_complex_sentences(content),
                "readability_score": self._calculate_readability_score(content)
            },
            "content_structure": {
                "has_introduction": "介绍" in content or "概述" in content,
                "has_body": len(content.split('\n\n')) > 2,
                "has_conclusion": "结论" in content or "总结" in content,
                "heading_levels": self._count_heading_levels(content)
            },
            "data_elements": {
                "number_count": len(re.findall(r'\d+', content)),
                "percentage_count": len(re.findall(r'\d+%', content)),
                "date_references": len(re.findall(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}', content)),
                "chart_references": content.lower().count('图') + content.lower().count('chart')
            },
            "language_metrics": {
                "word_diversity": self._calculate_word_diversity(content),
                "sentence_variety": self._calculate_sentence_variety(content),
                "technical_term_ratio": self._calculate_technical_ratio(content)
            }
        }

    def _calculate_avg_sentence_length(self, content: str) -> float:
        """计算平均句子长度"""
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            return sum(len(s) for s in sentences) / len(sentences)
        return 0.0

    def _count_complex_sentences(self, content: str) -> int:
        """统计复杂句子"""
        sentences = re.split(r'[。！？.!?]', content)
        complex_count = 0
        
        for sentence in sentences:
            if len(sentence) > 50 or sentence.count('，') > 3:
                complex_count += 1
        
        return complex_count

    def _calculate_readability_score(self, content: str) -> float:
        """计算可读性评分"""
        avg_sentence_length = self._calculate_avg_sentence_length(content)
        
        # 简化的可读性评分
        if avg_sentence_length < 10:
            return 0.9
        elif avg_sentence_length < 20:
            return 0.8
        elif avg_sentence_length < 30:
            return 0.7
        else:
            return 0.6

    def _count_heading_levels(self, content: str) -> Dict[str, int]:
        """统计标题层级"""
        return {
            "h1": content.count('# '),
            "h2": content.count('## '),
            "h3": content.count('### '),
            "numbered": len(re.findall(r'^\d+\.', content, re.MULTILINE))
        }

    def _calculate_word_diversity(self, content: str) -> float:
        """计算词汇多样性"""
        words = content.split()
        if not words:
            return 0.0
        
        unique_words = set(words)
        return len(unique_words) / len(words)

    def _calculate_sentence_variety(self, content: str) -> float:
        """计算句子多样性"""
        sentences = re.split(r'[。！？.!?]', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return 0.0
        
        sentence_lengths = [len(s) for s in sentences]
        if not sentence_lengths:
            return 0.0
        
        # 基于长度变异系数评估多样性
        avg_length = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((l - avg_length) ** 2 for l in sentence_lengths) / len(sentence_lengths)
        std_dev = variance ** 0.5
        
        # 变异系数越大，多样性越高
        coefficient_of_variation = std_dev / avg_length if avg_length > 0 else 0
        return min(coefficient_of_variation, 1.0)

    def _calculate_technical_ratio(self, content: str) -> float:
        """计算专业术语比例"""
        technical_terms = [
            "分析", "数据", "指标", "趋势", "统计", "比率", "增长率", "占比",
            "analysis", "data", "metric", "trend", "statistics", "ratio", "growth"
        ]
        
        words = content.split()
        if not words:
            return 0.0
        
        technical_count = sum(content.lower().count(term) for term in technical_terms)
        return min(technical_count / len(words), 1.0)

    def _issue_to_dict(self, issue: QualityIssue) -> Dict[str, Any]:
        """将问题对象转换为字典"""
        return {
            "dimension": issue.dimension.value,
            "severity": issue.severity.value,
            "description": issue.description,
            "location": issue.location,
            "suggestion": issue.suggestion,
            "auto_fixable": issue.auto_fixable,
            "impact_score": issue.impact_score
        }

    def get_quality_rules(self) -> Dict[str, Any]:
        """获取质量检查规则"""
        return self.quality_rules.copy()

    def update_quality_rules(self, new_rules: Dict[str, Any]) -> None:
        """更新质量检查规则"""
        for category, rules in new_rules.items():
            if category in self.quality_rules:
                self.quality_rules[category].update(rules)
            else:
                self.quality_rules[category] = rules
        
        self.logger.info(f"质量检查规则已更新: {list(new_rules.keys())}")


# 全局实例
report_quality_checker_service = ReportQualityCheckerService()