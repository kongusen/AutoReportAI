"""
SQL质量评估器 - 改进SQL生成质量评估机制

多维度评估SQL质量，包括语法、性能、安全、业务逻辑等
"""

import logging
import re
import ast
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import sqlparse
from sqlparse import sql, tokens
from sqlparse.engine import FilterStack
from sqlalchemy import text, create_engine
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SQLQualityDimension(Enum):
    """SQL质量评估维度"""
    SYNTAX = "syntax"                   # 语法正确性
    PERFORMANCE = "performance"         # 性能优化
    SECURITY = "security"               # 安全性
    BUSINESS_LOGIC = "business_logic"   # 业务逻辑正确性
    MAINTAINABILITY = "maintainability" # 可维护性
    SEMANTIC_ACCURACY = "semantic_accuracy"  # 语义准确性


class QualityLevel(Enum):
    """质量等级"""
    EXCELLENT = "excellent"     # 优秀 (90-100分)
    GOOD = "good"              # 良好 (70-89分)
    ACCEPTABLE = "acceptable"   # 可接受 (50-69分)
    POOR = "poor"              # 较差 (30-49分)
    CRITICAL = "critical"      # 严重问题 (<30分)


@dataclass
class QualityIssue:
    """质量问题"""
    dimension: SQLQualityDimension
    severity: str  # "critical", "major", "minor", "info"
    message: str
    suggestion: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    affected_element: Optional[str] = None
    
    @property
    def severity_score(self) -> int:
        """严重程度分数（扣分）"""
        return {
            "critical": 20,
            "major": 10,
            "minor": 5,
            "info": 1
        }.get(self.severity, 5)


@dataclass
class SQLQualityReport:
    """SQL质量报告"""
    sql_text: str
    overall_score: float
    overall_level: QualityLevel
    dimension_scores: Dict[SQLQualityDimension, float] = field(default_factory=dict)
    issues: List[QualityIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    assessment_time: datetime = field(default_factory=datetime.now)
    
    def get_issues_by_severity(self, severity: str) -> List[QualityIssue]:
        """按严重程度筛选问题"""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_issues_by_dimension(self, dimension: SQLQualityDimension) -> List[QualityIssue]:
        """按维度筛选问题"""
        return [issue for issue in self.issues if issue.dimension == dimension]
    
    def has_critical_issues(self) -> bool:
        """是否存在严重问题"""
        return any(issue.severity == "critical" for issue in self.issues)


class SQLQualityAssessor:
    """SQL质量评估器"""
    
    def __init__(self, 
                 db_session: Optional[Session] = None,
                 enable_performance_check: bool = True,
                 enable_security_check: bool = True):
        
        self.db_session = db_session
        self.enable_performance_check = enable_performance_check
        self.enable_security_check = enable_security_check
        
        # 质量评估器组件
        self._syntax_checker = SQLSyntaxChecker()
        self._performance_analyzer = SQLPerformanceAnalyzer()
        self._security_scanner = SQLSecurityScanner()
        self._business_validator = SQLBusinessValidator()
        self._maintainability_assessor = SQLMaintainabilityAssessor()
        self._semantic_analyzer = SQLSemanticAnalyzer()
        
        logger.info("SQLQualityAssessor initialized")
    
    async def assess_sql_quality(self, 
                                sql_text: str,
                                context: Optional[Dict[str, Any]] = None) -> SQLQualityReport:
        """评估SQL质量"""
        try:
            logger.info(f"开始SQL质量评估，长度: {len(sql_text)}")
            
            # 初始化报告
            report = SQLQualityReport(sql_text=sql_text)
            context = context or {}
            
            # 1. 语法检查
            syntax_result = await self._syntax_checker.check(sql_text, context)
            report.dimension_scores[SQLQualityDimension.SYNTAX] = syntax_result['score']
            report.issues.extend(syntax_result['issues'])
            
            # 如果有严重语法错误，跳过其他检查
            if any(issue.severity == "critical" for issue in syntax_result['issues']):
                report.overall_score = syntax_result['score']
                report.overall_level = self._determine_quality_level(report.overall_score)
                return report
            
            # 2. 性能分析
            if self.enable_performance_check:
                performance_result = await self._performance_analyzer.analyze(sql_text, context)
                report.dimension_scores[SQLQualityDimension.PERFORMANCE] = performance_result['score']
                report.issues.extend(performance_result['issues'])
                report.suggestions.extend(performance_result.get('suggestions', []))
            
            # 3. 安全扫描
            if self.enable_security_check:
                security_result = await self._security_scanner.scan(sql_text, context)
                report.dimension_scores[SQLQualityDimension.SECURITY] = security_result['score']
                report.issues.extend(security_result['issues'])
            
            # 4. 业务逻辑验证
            business_result = await self._business_validator.validate(sql_text, context)
            report.dimension_scores[SQLQualityDimension.BUSINESS_LOGIC] = business_result['score']
            report.issues.extend(business_result['issues'])
            
            # 5. 可维护性评估
            maintainability_result = await self._maintainability_assessor.assess(sql_text, context)
            report.dimension_scores[SQLQualityDimension.MAINTAINABILITY] = maintainability_result['score']
            report.issues.extend(maintainability_result['issues'])
            
            # 6. 语义准确性分析
            semantic_result = await self._semantic_analyzer.analyze(sql_text, context)
            report.dimension_scores[SQLQualityDimension.SEMANTIC_ACCURACY] = semantic_result['score']
            report.issues.extend(semantic_result['issues'])
            
            # 计算综合分数
            report.overall_score = self._calculate_overall_score(report)
            report.overall_level = self._determine_quality_level(report.overall_score)
            
            # 生成改进建议
            report.suggestions.extend(self._generate_improvement_suggestions(report))
            
            # 设置元数据
            report.metadata = {
                'context': context,
                'sql_length': len(sql_text),
                'statement_count': len(sqlparse.split(sql_text)),
                'complexity_score': self._calculate_complexity_score(sql_text)
            }
            
            logger.info(f"SQL质量评估完成，总分: {report.overall_score:.2f}, 等级: {report.overall_level.value}")
            return report
            
        except Exception as e:
            logger.error(f"SQL质量评估失败: {e}")
            return SQLQualityReport(
                sql_text=sql_text,
                overall_score=0.0,
                overall_level=QualityLevel.CRITICAL,
                issues=[QualityIssue(
                    dimension=SQLQualityDimension.SYNTAX,
                    severity="critical",
                    message=f"质量评估失败: {str(e)}",
                    suggestion="请检查SQL语句的基本格式"
                )]
            )
    
    async def compare_sql_quality(self, 
                                sql_versions: List[str],
                                context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """比较多个SQL版本的质量"""
        reports = []
        
        for i, sql_text in enumerate(sql_versions):
            report = await self.assess_sql_quality(sql_text, context)
            report.metadata['version_index'] = i
            reports.append(report)
        
        # 找出最佳版本
        best_report = max(reports, key=lambda r: r.overall_score)
        
        return {
            'reports': reports,
            'best_version_index': best_report.metadata['version_index'],
            'best_score': best_report.overall_score,
            'comparison_summary': self._generate_comparison_summary(reports)
        }
    
    def _calculate_overall_score(self, report: SQLQualityReport) -> float:
        """计算综合分数"""
        if not report.dimension_scores:
            return 0.0
        
        # 权重分配
        weights = {
            SQLQualityDimension.SYNTAX: 0.25,
            SQLQualityDimension.SECURITY: 0.20,
            SQLQualityDimension.BUSINESS_LOGIC: 0.20,
            SQLQualityDimension.PERFORMANCE: 0.15,
            SQLQualityDimension.SEMANTIC_ACCURACY: 0.15,
            SQLQualityDimension.MAINTAINABILITY: 0.05
        }
        
        weighted_score = 0.0
        total_weight = 0.0
        
        for dimension, score in report.dimension_scores.items():
            weight = weights.get(dimension, 0.1)
            weighted_score += score * weight
            total_weight += weight
        
        base_score = weighted_score / total_weight if total_weight > 0 else 0.0
        
        # 根据严重问题进行扣分
        penalty = sum(issue.severity_score for issue in report.issues)
        final_score = max(0.0, min(100.0, base_score - penalty))
        
        return final_score
    
    def _determine_quality_level(self, score: float) -> QualityLevel:
        """确定质量等级"""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 70:
            return QualityLevel.GOOD
        elif score >= 50:
            return QualityLevel.ACCEPTABLE
        elif score >= 30:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
    
    def _calculate_complexity_score(self, sql_text: str) -> float:
        """计算SQL复杂度分数"""
        # 简化的复杂度计算
        complexity_score = 0.0
        
        # 基于长度
        complexity_score += min(len(sql_text) / 1000, 10)
        
        # 基于嵌套查询数量
        subquery_count = sql_text.upper().count('SELECT') - 1
        complexity_score += subquery_count * 5
        
        # 基于JOIN数量
        join_count = len(re.findall(r'\bJOIN\b', sql_text.upper()))
        complexity_score += join_count * 2
        
        # 基于聚合函数数量
        agg_functions = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'GROUP_CONCAT']
        agg_count = sum(sql_text.upper().count(func) for func in agg_functions)
        complexity_score += agg_count * 1.5
        
        return complexity_score
    
    def _generate_improvement_suggestions(self, report: SQLQualityReport) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于问题生成建议
        critical_issues = report.get_issues_by_severity("critical")
        if critical_issues:
            suggestions.append("❗ 请立即修复严重问题，这些问题会导致SQL执行失败")
        
        major_issues = report.get_issues_by_severity("major")
        if major_issues:
            suggestions.append("⚠️ 建议修复主要问题以提高SQL质量和性能")
        
        # 基于分数生成建议
        if report.overall_score < 50:
            suggestions.append("📝 当前SQL质量较低，建议重新设计查询逻辑")
        elif report.overall_score < 70:
            suggestions.append("🔧 SQL基本可用，但建议优化以提高性能和可维护性")
        elif report.overall_score < 90:
            suggestions.append("✨ SQL质量良好，可考虑进一步优化细节")
        
        # 基于维度分数生成建议
        for dimension, score in report.dimension_scores.items():
            if score < 60:
                suggestions.append(f"🎯 {dimension.value}维度得分较低({score:.1f})，需要重点关注")
        
        return suggestions
    
    def _generate_comparison_summary(self, reports: List[SQLQualityReport]) -> Dict[str, Any]:
        """生成比较摘要"""
        summary = {
            'total_versions': len(reports),
            'score_range': {
                'min': min(r.overall_score for r in reports),
                'max': max(r.overall_score for r in reports),
                'avg': sum(r.overall_score for r in reports) / len(reports)
            },
            'dimension_comparison': {},
            'common_issues': []
        }
        
        # 维度比较
        for dimension in SQLQualityDimension:
            scores = [r.dimension_scores.get(dimension, 0) for r in reports]
            if scores:
                summary['dimension_comparison'][dimension.value] = {
                    'best_score': max(scores),
                    'worst_score': min(scores),
                    'avg_score': sum(scores) / len(scores)
                }
        
        # 共同问题
        all_issues = [issue.message for report in reports for issue in report.issues]
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        summary['common_issues'] = [
            {'message': issue, 'frequency': count}
            for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)
            if count > 1
        ]
        
        return summary


class SQLSyntaxChecker:
    """SQL语法检查器"""
    
    async def check(self, sql_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """检查SQL语法"""
        issues = []
        score = 100.0
        
        try:
            # 解析SQL
            parsed = sqlparse.parse(sql_text)
            if not parsed:
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SYNTAX,
                    severity="critical",
                    message="SQL语句无法解析",
                    suggestion="请检查SQL语法的基本结构"
                ))
                score = 0.0
            else:
                # 检查各种语法问题
                for statement in parsed:
                    statement_issues = self._check_statement_syntax(statement)
                    issues.extend(statement_issues)
                
                # 计算语法分数
                if issues:
                    penalty = sum(issue.severity_score for issue in issues)
                    score = max(0.0, score - penalty)
        
        except Exception as e:
            issues.append(QualityIssue(
                dimension=SQLQualityDimension.SYNTAX,
                severity="critical",
                message=f"语法检查失败: {str(e)}",
                suggestion="请检查SQL语句的基本格式"
            ))
            score = 0.0
        
        return {'score': score, 'issues': issues}
    
    def _check_statement_syntax(self, statement) -> List[QualityIssue]:
        """检查单个语句的语法"""
        issues = []
        
        # 检查关键字大小写一致性
        keywords = []
        for token in statement.flatten():
            if token.ttype is tokens.Keyword:
                keywords.append(str(token))
        
        if keywords:
            uppercase_count = sum(1 for kw in keywords if kw.isupper())
            lowercase_count = sum(1 for kw in keywords if kw.islower())
            mixed_case = len(keywords) - uppercase_count - lowercase_count
            
            if mixed_case > 0 or (uppercase_count > 0 and lowercase_count > 0):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SYNTAX,
                    severity="minor",
                    message="SQL关键字大小写不一致",
                    suggestion="建议统一使用大写或小写关键字"
                ))
        
        # 检查是否缺少分号（对于多语句）
        sql_text = str(statement).strip()
        if not sql_text.endswith(';') and ';' in sql_text:
            issues.append(QualityIssue(
                dimension=SQLQualityDimension.SYNTAX,
                severity="minor",
                message="语句可能缺少结束分号",
                suggestion="建议在每个SQL语句末尾添加分号"
            ))
        
        return issues


class SQLPerformanceAnalyzer:
    """SQL性能分析器"""
    
    async def analyze(self, sql_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析SQL性能"""
        issues = []
        suggestions = []
        score = 100.0
        
        try:
            # 检查SELECT *
            if re.search(r'SELECT\s+\*', sql_text.upper()):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.PERFORMANCE,
                    severity="major",
                    message="使用了SELECT *",
                    suggestion="建议明确指定需要的列，避免不必要的数据传输"
                ))
            
            # 检查WHERE子句
            if 'WHERE' not in sql_text.upper():
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.PERFORMANCE,
                    severity="major",
                    message="查询没有WHERE条件",
                    suggestion="建议添加适当的WHERE条件限制结果集"
                ))
            
            # 检查LIMIT子句
            if ('SELECT' in sql_text.upper() and 
                'LIMIT' not in sql_text.upper() and 
                'TOP' not in sql_text.upper()):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.PERFORMANCE,
                    severity="minor",
                    message="查询没有限制返回行数",
                    suggestion="考虑添加LIMIT子句限制返回的行数"
                ))
            
            # 检查函数在WHERE子句中的使用
            where_functions = re.findall(r'WHERE.*?(\w+)\s*\([^)]+\)\s*=', sql_text.upper())
            if where_functions:
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.PERFORMANCE,
                    severity="major",
                    message="WHERE子句中使用了函数",
                    suggestion="尽量避免在WHERE条件中对列使用函数，这会阻止索引使用"
                ))
            
            # 检查子查询
            subquery_count = sql_text.upper().count('SELECT') - 1
            if subquery_count > 3:
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.PERFORMANCE,
                    severity="minor",
                    message=f"查询包含{subquery_count}个子查询",
                    suggestion="过多的子查询可能影响性能，考虑使用JOIN重写"
                ))
            
            # 检查DISTINCT的使用
            if 'DISTINCT' in sql_text.upper():
                suggestions.append("使用了DISTINCT，确认是否真的需要去重，考虑是否可以通过优化查询逻辑避免")
            
            # 检查ORDER BY没有LIMIT
            if ('ORDER BY' in sql_text.upper() and 
                'LIMIT' not in sql_text.upper() and 
                'TOP' not in sql_text.upper()):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.PERFORMANCE,
                    severity="minor",
                    message="ORDER BY没有配合LIMIT使用",
                    suggestion="对大数据集排序时建议配合LIMIT使用"
                ))
            
            # 计算性能分数
            if issues:
                penalty = sum(issue.severity_score for issue in issues)
                score = max(0.0, score - penalty)
        
        except Exception as e:
            logger.warning(f"性能分析失败: {e}")
            score = 80.0  # 默认分数
        
        return {'score': score, 'issues': issues, 'suggestions': suggestions}


class SQLSecurityScanner:
    """SQL安全扫描器"""
    
    async def scan(self, sql_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """扫描SQL安全问题"""
        issues = []
        score = 100.0
        
        # 检查SQL注入风险
        injection_patterns = [
            (r"'\s*OR\s+'\d+'\s*=\s*'\d+'", "可能存在SQL注入攻击模式"),
            (r";\s*DROP\s+", "发现危险的DROP语句"),
            (r";\s*DELETE\s+FROM\s+", "发现危险的DELETE语句"),
            (r"UNION\s+SELECT", "发现UNION SELECT模式，可能存在注入风险"),
            (r"--\s*$", "发现SQL注释，可能被用于注入"),
        ]
        
        for pattern, message in injection_patterns:
            if re.search(pattern, sql_text.upper()):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SECURITY,
                    severity="critical",
                    message=message,
                    suggestion="请使用参数化查询或预处理语句"
                ))
        
        # 检查权限相关操作
        dangerous_operations = ['DROP', 'TRUNCATE', 'DELETE', 'UPDATE', 'INSERT', 'ALTER']
        for op in dangerous_operations:
            if f' {op} ' in sql_text.upper():
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SECURITY,
                    severity="major",
                    message=f"发现数据修改操作: {op}",
                    suggestion="确保操作权限合适，并进行充分测试"
                ))
        
        # 计算安全分数
        if issues:
            penalty = sum(issue.severity_score for issue in issues)
            score = max(0.0, score - penalty)
        
        return {'score': score, 'issues': issues}


class SQLBusinessValidator:
    """SQL业务逻辑验证器"""
    
    async def validate(self, sql_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """验证SQL业务逻辑"""
        issues = []
        score = 100.0
        
        # 检查日期相关逻辑
        if context.get('placeholder_type') in ['date', 'datetime', 'time']:
            if not re.search(r'DATE|TIME|YEAR|MONTH|DAY', sql_text.upper()):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.BUSINESS_LOGIC,
                    severity="minor",
                    message="日期类型占位符但SQL中没有日期函数",
                    suggestion="确认是否需要日期相关的处理逻辑"
                ))
        
        # 检查统计类查询
        if context.get('semantic_type') == 'statistical':
            agg_functions = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']
            if not any(func in sql_text.upper() for func in agg_functions):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.BUSINESS_LOGIC,
                    severity="major",
                    message="统计类占位符但SQL中没有聚合函数",
                    suggestion="统计查询通常需要使用聚合函数"
                ))
        
        # 检查表名合理性
        if context.get('target_table'):
            target_table = context['target_table'].lower()
            if target_table not in sql_text.lower():
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.BUSINESS_LOGIC,
                    severity="major",
                    message="SQL中没有使用推荐的目标表",
                    suggestion=f"建议查询表: {context['target_table']}"
                ))
        
        # 计算业务逻辑分数
        if issues:
            penalty = sum(issue.severity_score for issue in issues)
            score = max(0.0, score - penalty)
        
        return {'score': score, 'issues': issues}


class SQLMaintainabilityAssessor:
    """SQL可维护性评估器"""
    
    async def assess(self, sql_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """评估SQL可维护性"""
        issues = []
        score = 100.0
        
        # 检查SQL长度
        if len(sql_text) > 2000:
            issues.append(QualityIssue(
                dimension=SQLQualityDimension.MAINTAINABILITY,
                severity="minor",
                message="SQL语句过长",
                suggestion="考虑将复杂查询分解为多个步骤"
            ))
        
        # 检查格式化
        lines = sql_text.split('\n')
        if len(lines) == 1 and len(sql_text) > 100:
            issues.append(QualityIssue(
                dimension=SQLQualityDimension.MAINTAINABILITY,
                severity="minor",
                message="SQL缺少适当的格式化",
                suggestion="建议使用适当的缩进和换行提高可读性"
            ))
        
        # 检查别名使用
        if re.search(r'\bAS\s+\w+', sql_text.upper()):
            # 有使用别名，这是好的
            pass
        elif len(re.findall(r'\bJOIN\b', sql_text.upper())) > 1:
            issues.append(QualityIssue(
                dimension=SQLQualityDimension.MAINTAINABILITY,
                severity="minor",
                message="多表JOIN但没有使用表别名",
                suggestion="建议为表使用简短的别名提高可读性"
            ))
        
        # 计算可维护性分数
        if issues:
            penalty = sum(issue.severity_score for issue in issues)
            score = max(0.0, score - penalty)
        
        return {'score': score, 'issues': issues}


class SQLSemanticAnalyzer:
    """SQL语义分析器"""
    
    async def analyze(self, sql_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """分析SQL语义准确性"""
        issues = []
        score = 100.0
        
        # 检查占位符语义匹配
        placeholder_text = context.get('placeholder_text', '').lower()
        semantic_type = context.get('semantic_type', '')
        
        # 数量相关的占位符检查
        quantity_keywords = ['数量', '个数', '总数', '计数', 'count', 'number', 'total']
        if any(kw in placeholder_text for kw in quantity_keywords):
            if 'COUNT' not in sql_text.upper():
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SEMANTIC_ACCURACY,
                    severity="major",
                    message="占位符表示数量但SQL中没有COUNT函数",
                    suggestion="数量类查询建议使用COUNT函数"
                ))
        
        # 比例相关的占位符检查
        ratio_keywords = ['比例', '率', '百分比', 'rate', 'ratio', 'percentage']
        if any(kw in placeholder_text for kw in ratio_keywords):
            if not re.search(r'\*\s*100|/.*?\*\s*100', sql_text):
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SEMANTIC_ACCURACY,
                    severity="minor",
                    message="占位符表示比例但SQL中可能没有计算百分比",
                    suggestion="比例类查询通常需要计算百分比(*100)"
                ))
        
        # 平均值相关检查
        average_keywords = ['平均', '均值', 'average', 'avg', 'mean']
        if any(kw in placeholder_text for kw in average_keywords):
            if 'AVG' not in sql_text.upper():
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SEMANTIC_ACCURACY,
                    severity="major",
                    message="占位符表示平均值但SQL中没有AVG函数",
                    suggestion="平均值查询建议使用AVG函数"
                ))
        
        # 最大/最小值检查
        if '最大' in placeholder_text or 'max' in placeholder_text.lower():
            if 'MAX' not in sql_text.upper():
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SEMANTIC_ACCURACY,
                    severity="major",
                    message="占位符表示最大值但SQL中没有MAX函数",
                    suggestion="最大值查询建议使用MAX函数"
                ))
        
        if '最小' in placeholder_text or 'min' in placeholder_text.lower():
            if 'MIN' not in sql_text.upper():
                issues.append(QualityIssue(
                    dimension=SQLQualityDimension.SEMANTIC_ACCURACY,
                    severity="major",
                    message="占位符表示最小值但SQL中没有MIN函数",
                    suggestion="最小值查询建议使用MIN函数"
                ))
        
        # 计算语义准确性分数
        if issues:
            penalty = sum(issue.severity_score for issue in issues)
            score = max(0.0, score - penalty)
        
        return {'score': score, 'issues': issues}


# 便捷函数
def create_sql_quality_assessor(db_session: Optional[Session] = None,
                               enable_performance_check: bool = True,
                               enable_security_check: bool = True) -> SQLQualityAssessor:
    """创建SQL质量评估器"""
    return SQLQualityAssessor(db_session, enable_performance_check, enable_security_check)


def get_quality_color(level: QualityLevel) -> str:
    """获取质量等级对应的颜色"""
    color_map = {
        QualityLevel.EXCELLENT: "green",
        QualityLevel.GOOD: "lightgreen", 
        QualityLevel.ACCEPTABLE: "yellow",
        QualityLevel.POOR: "orange",
        QualityLevel.CRITICAL: "red"
    }
    return color_map.get(level, "gray")