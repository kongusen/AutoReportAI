from __future__ import annotations

import re
import logging
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext

logger = logging.getLogger(__name__)


class QualityLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class QualityIssue:
    severity: str  # "high", "medium", "low", "info"
    category: str  # "syntax", "performance", "security", "logic", "style"
    message: str
    suggestion: str
    location: Optional[str] = None
    impact_score: float = 0.0


@dataclass
class QualityReport:
    overall_score: float
    overall_level: QualityLevel
    dimension_scores: Dict[str, float]
    issues: List[QualityIssue]
    suggestions: List[str]
    metadata: Dict[str, Any]


class SQLQualityAssessorAgent(BaseAgent):
    """
SQL质量评估Agent - 多维度评估SQL查询质量
包括语法、性能、安全、逻辑和风格等多个维度
"""
    
    def __init__(self, name: str = "sql_quality_assessor", capabilities: List[str] = None):
        super().__init__(name, capabilities or ["sql_analysis", "quality_assessment", "performance_evaluation"])
        # SQL质量维度权重
        self.dimension_weights = {
            'syntax': 0.25,      # 语法正确性
            'performance': 0.30,  # 性能表现
            'security': 0.20,     # 安全性
            'logic': 0.15,        # 逻辑正确性
            'style': 0.10         # 代码风格
        }
        
    async def validate_preconditions(self, context: EnhancedExecutionContext) -> bool:
        """验证执行前置条件"""
        sql_query = context.request.get('sql_query')
        if not sql_query or not sql_query.strip():
            logger.warning("缺少SQL查询内容")
            return False
        return True
        
    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行SQL质量评估"""
        try:
            sql_query = context.request.get('sql_query', '')
            data_source_context = context.request.get('data_source_context', {})
            semantic_context = context.request.get('semantic_analysis', {})
            
            # 执行全面质量评估
            quality_report = await self._comprehensive_quality_assessment(
                sql_query, data_source_context, semantic_context
            )
            
            logger.info(f"SQL质量评估完成: 总分{quality_report.overall_score:.2f}, 等级{quality_report.overall_level.value}")
            
            return {
                'agent': self.name,
                'type': 'sql_quality_assessment',
                'success': True,
                'data': {
                    'overall_score': quality_report.overall_score,
                    'overall_level': quality_report.overall_level.value,
                    'dimension_scores': quality_report.dimension_scores,
                    'issues': [issue.__dict__ for issue in quality_report.issues],
                    'suggestions': quality_report.suggestions,
                    'total_issues': len(quality_report.issues),
                    'critical_issues': len([i for i in quality_report.issues if i.severity == 'high']),
                    'assessment_summary': self._generate_assessment_summary(quality_report)
                },
                'metadata': {
                    'assessment_timestamp': datetime.now().isoformat(),
                    'sql_query': sql_query,
                    'assessment_method': 'comprehensive_multi_dimensional'
                }
            }
            
        except Exception as e:
            logger.error(f"SQL质量评估失败: {e}")
            return self._generate_fallback_quality_result(context, str(e))
    
    # 以下是详细的评估方法的简化版本
    async def _comprehensive_quality_assessment(
        self, 
        sql_query: str, 
        data_source_context: Dict,
        semantic_context: Dict
    ) -> QualityReport:
        """综合质量评估(简化版)"""
        
        # 基本质量检查
        issues = []
        suggestions = []
        
        # 简化的质量分数计算
        syntax_score = 0.9 if sql_query.strip().upper().startswith('SELECT') else 0.5
        performance_score = 0.8 if 'SELECT *' not in sql_query.upper() else 0.6
        security_score = 0.9 if not any(kw in sql_query.upper() for kw in ['DELETE', 'UPDATE', 'DROP']) else 0.3
        logic_score = 0.8  # 默认逻辑分数
        style_score = 0.7   # 默认风格分数
        
        dimension_scores = {
            'syntax': syntax_score,
            'performance': performance_score,
            'security': security_score,
            'logic': logic_score,
            'style': style_score
        }
        
        # 计算总分
        overall_score = sum(
            score * self.dimension_weights[dim] 
            for dim, score in dimension_scores.items()
        )
        
        # 确定质量等级
        if overall_score >= 0.9:
            overall_level = QualityLevel.EXCELLENT
        elif overall_score >= 0.8:
            overall_level = QualityLevel.GOOD
        elif overall_score >= 0.6:
            overall_level = QualityLevel.FAIR
        elif overall_score >= 0.4:
            overall_level = QualityLevel.POOR
        else:
            overall_level = QualityLevel.CRITICAL
        
        # 添加基本问题检测
        if 'SELECT *' in sql_query.upper():
            issues.append(QualityIssue(
                severity='medium',
                category='performance',
                message='使用SELECT *可能影响性能',
                suggestion='明确指定需要的列名',
                impact_score=0.15
            ))
            suggestions.append('明确指定列名而非SELECT *')
        
        return QualityReport(
            overall_score=overall_score,
            overall_level=overall_level,
            dimension_scores=dimension_scores,
            issues=issues,
            suggestions=suggestions,
            metadata={
                'assessment_timestamp': datetime.now().isoformat(),
                'total_checks': 5,
                'sql_length': len(sql_query),
                'complexity_level': 'simple'
            }
        )
    
    def _generate_assessment_summary(self, quality_report: QualityReport) -> str:
        """生成评估摘要"""
        level_desc = {
            QualityLevel.EXCELLENT: '优秀',
            QualityLevel.GOOD: '良好', 
            QualityLevel.FAIR: '一般',
            QualityLevel.POOR: '较差',
            QualityLevel.CRITICAL: '糟糕'
        }
        
        return f"SQL质量评级: {level_desc[quality_report.overall_level]}({quality_report.overall_score:.2f}分)"
    
    def _generate_fallback_quality_result(self, context: EnhancedExecutionContext, error_msg: str) -> Dict[str, Any]:
        """生成回退质量评估结果"""
        return {
            'agent': self.name,
            'type': 'sql_quality_assessment',
            'success': False,
            'data': {
                'overall_score': 0.1,
                'overall_level': QualityLevel.CRITICAL.value,
                'dimension_scores': {'syntax': 0.1, 'performance': 0.1, 'security': 0.1, 'logic': 0.1, 'style': 0.1},
                'issues': [{
                    'severity': 'high',
                    'category': 'system',
                    'message': f'质量评估失败: {error_msg}',
                    'suggestion': '请手动检查SQL质量'
                }],
                'suggestions': ['手动检查SQL质量'],
                'total_issues': 1,
                'critical_issues': 1,
                'assessment_summary': f'SQL质量评估系统失败: {error_msg}'
            },
            'error': error_msg
        }


