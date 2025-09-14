"""
智能上下文处理器
==================

业务场景感知的智能上下文构建和处理引擎。
实现自动场景识别、复杂度评估、Agent推荐等智能化功能。
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
from enum import Enum

from .intelligent_prompt_orchestrator import SmartContext, TaskComplexity, WorkflowType

logger = logging.getLogger(__name__)


class ScenarioConfidence(Enum):
    """场景识别置信度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class ScenarioAnalysis:
    """场景分析结果"""
    scenario: str
    confidence: ScenarioConfidence
    reasoning: str
    alternative_scenarios: List[str] = field(default_factory=list)
    key_indicators: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComplexityAssessment:
    """复杂度评估结果"""
    level: TaskComplexity
    score: float  # 0-1
    factors: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    recommendations: List[str] = field(default_factory=list)


@dataclass
class AgentRecommendation:
    """Agent推荐结果"""
    agent_type: str
    confidence: float
    reasoning: str
    alternative_agents: List[str] = field(default_factory=list)
    required_capabilities: List[str] = field(default_factory=list)


class BusinessScenarioDetector:
    """业务场景检测器"""
    
    def __init__(self):
        # 场景识别规则
        self.scenario_patterns = {
            "placeholder_analysis": {
                "keywords": ["占位符", "placeholder", "填充", "替换", "参数", "变量", "模板"],
                "patterns": [
                    r"\{\{.*?\}\}",  # {{变量}}
                    r"\{.*?\}",      # {变量}
                    r"%.*?%",        # %变量%
                    r"\$\{.*?\}"     # ${变量}
                ],
                "context_indicators": ["template_info", "placeholder_text", "template_data"],
                "priority": 0.9
            },
            "sql_generation": {
                "keywords": ["sql", "查询", "数据库", "表", "select", "query", "database", "table"],
                "patterns": [
                    r"select\s+.*?\s+from",
                    r"生成.*?sql",
                    r"查询.*?数据"
                ],
                "context_indicators": ["data_source_info", "table_schema", "database_config"],
                "priority": 0.85
            },
            "data_analysis": {
                "keywords": ["分析", "统计", "趋势", "analysis", "statistics", "trend", "pattern"],
                "patterns": [
                    r"分析.*?数据",
                    r"统计.*?信息",
                    r"趋势.*?分析"
                ],
                "context_indicators": ["data_source", "metrics", "kpi_definition"],
                "priority": 0.8
            },
            "report_generation": {
                "keywords": ["报告", "报表", "生成", "report", "generate", "dashboard", "可视化"],
                "patterns": [
                    r"生成.*?报告",
                    r"创建.*?报表",
                    r"dashboard"
                ],
                "context_indicators": ["template_config", "chart_config", "report_template"],
                "priority": 0.75
            },
            "system_maintenance": {
                "keywords": ["系统", "维护", "监控", "system", "maintenance", "monitor", "管理"],
                "patterns": [
                    r"系统.*?维护",
                    r"文件.*?操作",
                    r"监控.*?系统"
                ],
                "context_indicators": ["system_config", "file_path", "command"],
                "priority": 0.7
            }
        }
        
        # LLM工具用于复杂场景分析
        self.llm_tool = None
        self._initialize_llm_tool()
    
    def _initialize_llm_tool(self):
        """初始化LLM工具"""
        try:
            from ..tools.llm import get_llm_reasoning_tool
            self.llm_tool = get_llm_reasoning_tool()
        except Exception as e:
            logger.warning(f"Failed to initialize LLM tool for scenario detection: {e}")
    
    async def detect_scenario(
        self,
        task_description: str,
        context_data: Dict[str, Any] = None
    ) -> ScenarioAnalysis:
        """检测业务场景"""
        
        try:
            # 1. 基于规则的初步检测
            rule_based_results = self._rule_based_detection(task_description, context_data)
            
            # 2. 如果规则检测置信度不高，使用LLM增强检测
            if rule_based_results.confidence in [ScenarioConfidence.LOW, ScenarioConfidence.MEDIUM] and self.llm_tool:
                llm_enhanced_result = await self._llm_enhanced_detection(
                    task_description, context_data, rule_based_results
                )
                if llm_enhanced_result:
                    return llm_enhanced_result
            
            return rule_based_results
            
        except Exception as e:
            logger.error(f"Scenario detection failed: {e}")
            return ScenarioAnalysis(
                scenario="general",
                confidence=ScenarioConfidence.LOW,
                reasoning=f"Detection failed: {str(e)}"
            )
    
    def _rule_based_detection(
        self,
        task_description: str,
        context_data: Dict[str, Any] = None
    ) -> ScenarioAnalysis:
        """基于规则的场景检测"""
        
        description_lower = task_description.lower()
        context_data = context_data or {}
        
        scenario_scores = {}
        detailed_analysis = {}
        
        # 计算每个场景的匹配分数
        for scenario, config in self.scenario_patterns.items():
            score = 0.0
            matched_indicators = []
            
            # 1. 关键词匹配
            keyword_matches = sum(1 for keyword in config["keywords"] if keyword in description_lower)
            keyword_score = (keyword_matches / len(config["keywords"])) * 0.4
            score += keyword_score
            
            if keyword_matches > 0:
                matched_indicators.extend([k for k in config["keywords"] if k in description_lower])
            
            # 2. 模式匹配
            pattern_matches = sum(1 for pattern in config["patterns"] 
                                if re.search(pattern, description_lower, re.IGNORECASE))
            pattern_score = (pattern_matches / len(config["patterns"])) * 0.3
            score += pattern_score
            
            # 3. 上下文指示符匹配
            context_matches = sum(1 for indicator in config["context_indicators"] 
                                if indicator in context_data)
            if config["context_indicators"]:
                context_score = (context_matches / len(config["context_indicators"])) * 0.3
                score += context_score
            
            # 应用场景优先级权重
            score *= config["priority"]
            
            scenario_scores[scenario] = score
            detailed_analysis[scenario] = {
                "keyword_score": keyword_score,
                "pattern_score": pattern_score,
                "context_score": context_score if config["context_indicators"] else 0,
                "matched_indicators": matched_indicators,
                "total_score": score
            }
        
        # 选择得分最高的场景
        best_scenario = max(scenario_scores.items(), key=lambda x: x[1])
        scenario_name = best_scenario[0]
        max_score = best_scenario[1]
        
        # 确定置信度
        if max_score >= 0.8:
            confidence = ScenarioConfidence.VERY_HIGH
        elif max_score >= 0.6:
            confidence = ScenarioConfidence.HIGH
        elif max_score >= 0.4:
            confidence = ScenarioConfidence.MEDIUM
        else:
            confidence = ScenarioConfidence.LOW
        
        # 获取备选场景
        sorted_scenarios = sorted(scenario_scores.items(), key=lambda x: x[1], reverse=True)
        alternative_scenarios = [s[0] for s in sorted_scenarios[1:3] if s[1] > 0.2]
        
        # 生成推理说明
        analysis = detailed_analysis[scenario_name]
        reasoning_parts = []
        if analysis["keyword_score"] > 0:
            reasoning_parts.append(f"关键词匹配: {analysis['keyword_score']:.2f}")
        if analysis["pattern_score"] > 0:
            reasoning_parts.append(f"模式匹配: {analysis['pattern_score']:.2f}")
        if analysis["context_score"] > 0:
            reasoning_parts.append(f"上下文匹配: {analysis['context_score']:.2f}")
        
        reasoning = f"基于规则检测: {', '.join(reasoning_parts)}, 总分: {max_score:.2f}"
        
        return ScenarioAnalysis(
            scenario=scenario_name,
            confidence=confidence,
            reasoning=reasoning,
            alternative_scenarios=alternative_scenarios,
            key_indicators=analysis["matched_indicators"],
            metadata={"scores": scenario_scores, "detailed_analysis": detailed_analysis}
        )
    
    async def _llm_enhanced_detection(
        self,
        task_description: str,
        context_data: Dict[str, Any],
        rule_result: ScenarioAnalysis
    ) -> Optional[ScenarioAnalysis]:
        """LLM增强场景检测"""
        
        try:
            detection_prompt = f"""
分析以下任务的业务场景类型：

任务描述: {task_description}

上下文信息: {json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else '无'}

规则检测结果: 
- 初步场景: {rule_result.scenario}
- 置信度: {rule_result.confidence.value}
- 备选场景: {', '.join(rule_result.alternative_scenarios)}

请分析这个任务最可能属于以下哪个业务场景：
1. placeholder_analysis - 占位符分析和填充
2. sql_generation - SQL查询生成
3. data_analysis - 数据分析统计
4. report_generation - 报告生成
5. system_maintenance - 系统维护管理
6. general - 通用任务

请返回JSON格式的分析结果：
{{
    "scenario": "最可能的场景名称",
    "confidence": "high|medium|low",
    "reasoning": "详细的判断理由",
    "alternative_scenarios": ["备选场景1", "备选场景2"],
    "key_indicators": ["关键指示词1", "关键指示词2"]
}}
"""
            
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id="system")
            
            async for result in self.llm_tool.execute(
                {"problem": detection_prompt, "reasoning_depth": "detailed"}, 
                tool_context
            ):
                if result.success and not result.is_partial:
                    return self._parse_llm_detection_result(result.result)
            
        except Exception as e:
            logger.error(f"LLM enhanced detection failed: {e}")
        
        return None
    
    def _parse_llm_detection_result(self, llm_result: str) -> Optional[ScenarioAnalysis]:
        """解析LLM检测结果"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_result, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group(1))
            else:
                result_data = json.loads(llm_result)
            
            confidence_map = {
                "high": ScenarioConfidence.HIGH,
                "medium": ScenarioConfidence.MEDIUM,
                "low": ScenarioConfidence.LOW,
                "very_high": ScenarioConfidence.VERY_HIGH
            }
            
            return ScenarioAnalysis(
                scenario=result_data.get("scenario", "general"),
                confidence=confidence_map.get(result_data.get("confidence", "medium"), ScenarioConfidence.MEDIUM),
                reasoning=f"LLM分析: {result_data.get('reasoning', '')}",
                alternative_scenarios=result_data.get("alternative_scenarios", []),
                key_indicators=result_data.get("key_indicators", []),
                metadata={"source": "llm_enhanced", "raw_result": llm_result}
            )
            
        except Exception as e:
            logger.error(f"Failed to parse LLM detection result: {e}")
            return None


class TaskComplexityEvaluator:
    """任务复杂度评估器"""
    
    def __init__(self):
        # 复杂度评估因子
        self.complexity_factors = {
            "text_length": {"weight": 0.15, "thresholds": [50, 200, 500]},
            "data_volume": {"weight": 0.2, "thresholds": [100, 1000, 10000]},
            "integration_points": {"weight": 0.2, "thresholds": [1, 3, 5]},
            "analysis_depth": {"weight": 0.15, "thresholds": [1, 3, 5]},
            "user_requirements": {"weight": 0.1, "thresholds": [1, 3, 5]},
            "domain_expertise": {"weight": 0.1, "thresholds": [1, 2, 3]},
            "time_constraints": {"weight": 0.1, "thresholds": [0.3, 0.6, 0.9]}
        }
        
        self.llm_tool = None
        self._initialize_llm_tool()
    
    def _initialize_llm_tool(self):
        """初始化LLM工具"""
        try:
            from ..tools.llm import get_llm_reasoning_tool
            self.llm_tool = get_llm_reasoning_tool()
        except Exception as e:
            logger.warning(f"Failed to initialize LLM tool for complexity evaluation: {e}")
    
    async def assess_complexity(
        self,
        task_description: str,
        scenario: str,
        context_data: Dict[str, Any] = None
    ) -> ComplexityAssessment:
        """评估任务复杂度"""
        
        try:
            # 1. 基于规则的初步评估
            rule_assessment = self._rule_based_assessment(task_description, scenario, context_data)
            
            # 2. 如果需要更精确的评估，使用LLM
            if rule_assessment.level == TaskComplexity.MEDIUM and self.llm_tool:
                llm_assessment = await self._llm_enhanced_assessment(
                    task_description, scenario, context_data, rule_assessment
                )
                if llm_assessment:
                    return llm_assessment
            
            return rule_assessment
            
        except Exception as e:
            logger.error(f"Complexity assessment failed: {e}")
            return ComplexityAssessment(
                level=TaskComplexity.MEDIUM,
                score=0.5,
                reasoning=f"Assessment failed: {str(e)}"
            )
    
    def _rule_based_assessment(
        self,
        task_description: str,
        scenario: str,
        context_data: Dict[str, Any] = None
    ) -> ComplexityAssessment:
        """基于规则的复杂度评估"""
        
        context_data = context_data or {}
        factor_scores = {}
        
        # 1. 文本长度因子
        text_len = len(task_description)
        factor_scores["text_length"] = self._calculate_factor_score("text_length", text_len)
        
        # 2. 数据量因子
        data_indicators = ["data_source_info", "table_schema", "dataset", "database_config"]
        data_count = sum(1 for key in data_indicators if key in context_data)
        if "data_source_info" in context_data:
            tables = context_data["data_source_info"].get("table_details", [])
            data_count += len(tables)
        factor_scores["data_volume"] = self._calculate_factor_score("data_volume", data_count)
        
        # 3. 集成点因子  
        integration_count = 0
        if context_data.get("data_source_info"):
            integration_count += 1
        if context_data.get("template_info"):
            integration_count += 1
        if context_data.get("api_config"):
            integration_count += 1
        factor_scores["integration_points"] = self._calculate_factor_score("integration_points", integration_count)
        
        # 4. 分析深度因子
        analysis_keywords = ["分析", "统计", "预测", "优化", "模式", "趋势"]
        analysis_depth = sum(1 for keyword in analysis_keywords if keyword in task_description.lower())
        factor_scores["analysis_depth"] = self._calculate_factor_score("analysis_depth", analysis_depth)
        
        # 5. 用户需求因子
        requirement_keywords = ["要求", "必须", "需要", "应该", "建议"]
        req_count = sum(1 for keyword in requirement_keywords if keyword in task_description)
        factor_scores["user_requirements"] = self._calculate_factor_score("user_requirements", req_count)
        
        # 6. 领域专业性因子
        domain_complexity = {
            "placeholder_analysis": 1,
            "data_analysis": 3,
            "sql_generation": 2,
            "report_generation": 2,
            "system_maintenance": 3,
            "business_intelligence": 3
        }
        domain_score = domain_complexity.get(scenario, 2)
        factor_scores["domain_expertise"] = self._calculate_factor_score("domain_expertise", domain_score)
        
        # 7. 时间约束因子
        time_pressure = 0.5  # 默认中等时间压力
        if context_data.get("resource_constraints", {}).get("time_limited"):
            time_pressure = 0.9
        factor_scores["time_constraints"] = self._calculate_factor_score("time_constraints", time_pressure)
        
        # 计算加权总分
        total_score = sum(
            factor_scores[factor] * config["weight"]
            for factor, config in self.complexity_factors.items()
        )
        
        # 确定复杂度等级
        if total_score >= 0.8:
            level = TaskComplexity.EXPERT
        elif total_score >= 0.6:
            level = TaskComplexity.HIGH
        elif total_score >= 0.4:
            level = TaskComplexity.MEDIUM
        else:
            level = TaskComplexity.LOW
        
        # 生成建议
        recommendations = self._generate_complexity_recommendations(level, factor_scores, scenario)
        
        # 生成推理说明
        high_factors = [f for f, score in factor_scores.items() if score > 0.7]
        reasoning = f"总体复杂度: {total_score:.2f}, 主要影响因子: {', '.join(high_factors)}"
        
        return ComplexityAssessment(
            level=level,
            score=total_score,
            factors=factor_scores,
            reasoning=reasoning,
            recommendations=recommendations
        )
    
    def _calculate_factor_score(self, factor: str, value: Union[int, float]) -> float:
        """计算单个因子分数"""
        if factor not in self.complexity_factors:
            return 0.5
        
        thresholds = self.complexity_factors[factor]["thresholds"]
        
        if value <= thresholds[0]:
            return 0.25
        elif value <= thresholds[1]:
            return 0.5
        elif value <= thresholds[2]:
            return 0.75
        else:
            return 1.0
    
    def _generate_complexity_recommendations(
        self,
        level: TaskComplexity,
        factors: Dict[str, float],
        scenario: str
    ) -> List[str]:
        """生成复杂度处理建议"""
        
        recommendations = []
        
        if level == TaskComplexity.LOW:
            recommendations.append("使用简化的处理流程")
            recommendations.append("可以采用基础工具和模板")
        elif level == TaskComplexity.MEDIUM:
            recommendations.append("采用标准的六阶段处理流程")
            recommendations.append("建议使用LLM增强分析")
        elif level == TaskComplexity.HIGH:
            recommendations.append("启用专家级分析模式")
            recommendations.append("增加质量检查和优化环节")
            recommendations.append("考虑分步骤处理和中间结果验证")
        else:  # EXPERT
            recommendations.append("使用最高级别的处理策略")
            recommendations.append("启用多轮迭代优化")
            recommendations.append("建议人工审核关键环节")
        
        # 基于具体因子的建议
        if factors.get("data_volume", 0) > 0.7:
            recommendations.append("注意数据处理性能优化")
            recommendations.append("考虑分批处理大数据集")
        
        if factors.get("time_constraints", 0) > 0.7:
            recommendations.append("优先使用高性能工具")
            recommendations.append("启用并行处理模式")
        
        if factors.get("domain_expertise", 0) > 0.7:
            recommendations.append("增加领域专家验证环节")
            recommendations.append("使用专业化工具和模板")
        
        return recommendations
    
    async def _llm_enhanced_assessment(
        self,
        task_description: str,
        scenario: str,
        context_data: Dict[str, Any],
        rule_assessment: ComplexityAssessment
    ) -> Optional[ComplexityAssessment]:
        """LLM增强复杂度评估"""
        
        try:
            assessment_prompt = f"""
评估以下任务的复杂度等级：

任务描述: {task_description}
业务场景: {scenario}
上下文信息: {json.dumps(context_data, ensure_ascii=False, indent=2) if context_data else '无'}

规则评估结果:
- 复杂度等级: {rule_assessment.level.value}
- 分数: {rule_assessment.score:.2f}
- 主要因子: {', '.join([f for f, s in rule_assessment.factors.items() if s > 0.6])}

请从以下维度评估任务复杂度：
1. 技术难度 - 实现的技术复杂性
2. 业务复杂性 - 业务逻辑的复杂程度
3. 数据复杂性 - 数据处理的复杂度
4. 集成复杂性 - 系统集成的难度
5. 时间约束 - 时间压力的影响

复杂度等级：
- low: 简单直接的任务
- medium: 中等复杂度，需要一定处理
- high: 高复杂度，需要专业处理
- expert: 专家级复杂度，需要深度分析

请返回JSON格式的评估结果：
{{
    "complexity_level": "low|medium|high|expert",
    "confidence_score": 0.8,
    "key_complexity_factors": ["因子1", "因子2"],
    "reasoning": "详细的评估理由",
    "processing_recommendations": ["建议1", "建议2"]
}}
"""
            
            from ..tools.core.base import ToolExecutionContext
            tool_context = ToolExecutionContext(user_id="system")
            
            async for result in self.llm_tool.execute(
                {"problem": assessment_prompt, "reasoning_depth": "detailed"},
                tool_context
            ):
                if result.success and not result.is_partial:
                    return self._parse_llm_assessment_result(result.result, rule_assessment)
            
        except Exception as e:
            logger.error(f"LLM enhanced assessment failed: {e}")
        
        return None
    
    def _parse_llm_assessment_result(
        self,
        llm_result: str,
        rule_assessment: ComplexityAssessment
    ) -> Optional[ComplexityAssessment]:
        """解析LLM评估结果"""
        try:
            # 尝试提取JSON
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_result, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group(1))
            else:
                result_data = json.loads(llm_result)
            
            level_map = {
                "low": TaskComplexity.LOW,
                "medium": TaskComplexity.MEDIUM,
                "high": TaskComplexity.HIGH,
                "expert": TaskComplexity.EXPERT
            }
            
            llm_level = level_map.get(result_data.get("complexity_level", "medium"), TaskComplexity.MEDIUM)
            llm_score = result_data.get("confidence_score", 0.8)
            
            # 综合规则评估和LLM评估
            final_score = (rule_assessment.score + llm_score) / 2
            
            # 如果LLM和规则评估差异很大，倾向于更保守的评估
            if abs(rule_assessment.score - llm_score) > 0.3:
                final_level = min(rule_assessment.level, llm_level, key=lambda x: x.value)
            else:
                final_level = llm_level
            
            return ComplexityAssessment(
                level=final_level,
                score=final_score,
                factors=rule_assessment.factors,
                reasoning=f"LLM增强评估: {result_data.get('reasoning', '')}, 规则评估: {rule_assessment.reasoning}",
                recommendations=result_data.get("processing_recommendations", []) + rule_assessment.recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to parse LLM assessment result: {e}")
            return None


class AgentTypeRecommender:
    """Agent类型推荐器"""
    
    def __init__(self):
        # Agent类型映射
        self.agent_mappings = {
            "placeholder_analysis": {
                "primary": "data_analysis",
                "alternatives": ["business_intelligence", "development"],
                "confidence": 0.9,
                "reasoning": "占位符分析需要数据处理和模式识别能力"
            },
            "sql_generation": {
                "primary": "data_analysis", 
                "alternatives": ["business_intelligence", "development"],
                "confidence": 0.85,
                "reasoning": "SQL生成需要数据分析和查询优化专业知识"
            },
            "data_analysis": {
                "primary": "data_analysis",
                "alternatives": ["business_intelligence"],
                "confidence": 0.95,
                "reasoning": "数据分析任务的最佳选择"
            },
            "report_generation": {
                "primary": "business_intelligence",
                "alternatives": ["data_analysis"],
                "confidence": 0.9,
                "reasoning": "报告生成需要商业智能和数据可视化能力"
            },
            "system_maintenance": {
                "primary": "system_administration",
                "alternatives": ["development"],
                "confidence": 0.95,
                "reasoning": "系统管理任务的专业选择"
            }
        }
        
        # 复杂度调整
        self.complexity_adjustments = {
            TaskComplexity.LOW: {"confidence_boost": 0.0, "prefer_simple": True},
            TaskComplexity.MEDIUM: {"confidence_boost": 0.05, "prefer_simple": False}, 
            TaskComplexity.HIGH: {"confidence_boost": 0.1, "prefer_specialized": True},
            TaskComplexity.EXPERT: {"confidence_boost": 0.15, "require_expert": True}
        }
    
    async def recommend_agent_type(
        self,
        scenario: str,
        complexity: TaskComplexity,
        context_data: Dict[str, Any] = None
    ) -> AgentRecommendation:
        """推荐最佳Agent类型"""
        
        try:
            # 1. 基于场景的基础推荐
            base_recommendation = self._get_base_recommendation(scenario)
            
            # 2. 基于复杂度的调整
            adjusted_recommendation = self._adjust_for_complexity(base_recommendation, complexity)
            
            # 3. 基于上下文的优化
            final_recommendation = self._optimize_for_context(adjusted_recommendation, context_data)
            
            return final_recommendation
            
        except Exception as e:
            logger.error(f"Agent recommendation failed: {e}")
            return AgentRecommendation(
                agent_type="data_analysis",
                confidence=0.6,
                reasoning=f"推荐失败，使用默认: {str(e)}"
            )
    
    def _get_base_recommendation(self, scenario: str) -> AgentRecommendation:
        """获取基础推荐"""
        
        if scenario in self.agent_mappings:
            mapping = self.agent_mappings[scenario]
            return AgentRecommendation(
                agent_type=mapping["primary"],
                confidence=mapping["confidence"],
                reasoning=mapping["reasoning"],
                alternative_agents=mapping["alternatives"]
            )
        else:
            return AgentRecommendation(
                agent_type="data_analysis",
                confidence=0.7,
                reasoning="未知场景，使用通用数据分析Agent",
                alternative_agents=["business_intelligence", "development"]
            )
    
    def _adjust_for_complexity(
        self,
        base_rec: AgentRecommendation,
        complexity: TaskComplexity
    ) -> AgentRecommendation:
        """基于复杂度调整推荐"""
        
        if complexity not in self.complexity_adjustments:
            return base_rec
        
        adjustment = self.complexity_adjustments[complexity]
        
        # 调整置信度
        adjusted_confidence = min(1.0, base_rec.confidence + adjustment["confidence_boost"])
        
        # 高复杂度任务可能需要专业化Agent
        if complexity in [TaskComplexity.HIGH, TaskComplexity.EXPERT]:
            if base_rec.agent_type == "data_analysis":
                # 对于高复杂度的数据任务，可能需要商业智能Agent
                if "business_intelligence" in base_rec.alternative_agents:
                    return AgentRecommendation(
                        agent_type="business_intelligence",
                        confidence=adjusted_confidence,
                        reasoning=f"{base_rec.reasoning} (因复杂度{complexity.value}升级为商业智能Agent)",
                        alternative_agents=[base_rec.agent_type] + [a for a in base_rec.alternative_agents if a != "business_intelligence"],
                        required_capabilities=["advanced_reasoning", "optimization", "statistical_analysis"]
                    )
        
        return AgentRecommendation(
            agent_type=base_rec.agent_type,
            confidence=adjusted_confidence,
            reasoning=f"{base_rec.reasoning} (复杂度调整: {complexity.value})",
            alternative_agents=base_rec.alternative_agents,
            required_capabilities=base_rec.required_capabilities
        )
    
    def _optimize_for_context(
        self,
        base_rec: AgentRecommendation,
        context_data: Dict[str, Any] = None
    ) -> AgentRecommendation:
        """基于上下文优化推荐"""
        
        if not context_data:
            return base_rec
        
        # 检查特定上下文指示符
        if "template_info" in context_data and base_rec.agent_type == "data_analysis":
            # 有模板信息时，可能更适合商业智能Agent
            return AgentRecommendation(
                agent_type="business_intelligence",
                confidence=min(1.0, base_rec.confidence + 0.1),
                reasoning=f"{base_rec.reasoning} (检测到模板信息，优化为商业智能Agent)",
                alternative_agents=[base_rec.agent_type] + base_rec.alternative_agents,
                required_capabilities=base_rec.required_capabilities + ["template_processing", "document_generation"]
            )
        
        if "system_config" in context_data:
            # 有系统配置时，可能需要系统管理能力
            base_rec.required_capabilities.append("system_management")
        
        if context_data.get("data_sensitivity") == "high":
            # 高敏感数据需要额外安全能力
            base_rec.required_capabilities.append("data_security")
        
        return base_rec


class SmartContextProcessor:
    """
    智能上下文处理器
    
    核心功能：
    1. 业务场景智能识别
    2. 任务复杂度评估
    3. 最佳Agent类型推荐
    4. 智能上下文构建
    """
    
    def __init__(self):
        self.scenario_detector = BusinessScenarioDetector()
        self.complexity_evaluator = TaskComplexityEvaluator()
        self.agent_recommender = AgentTypeRecommender()
        
        logger.info("SmartContextProcessor initialized")
    
    async def build_intelligent_context(
        self,
        task_description: str,
        context_data: Dict[str, Any] = None,
        user_id: str = None
    ) -> SmartContext:
        """构建智能上下文"""
        
        try:
            logger.info(f"Building intelligent context for task: {task_description[:50]}...")
            
            # 1. 业务场景识别
            scenario_analysis = await self.scenario_detector.detect_scenario(
                task_description, context_data
            )
            logger.info(f"Detected scenario: {scenario_analysis.scenario} (confidence: {scenario_analysis.confidence.value})")
            
            # 2. 复杂度评估
            complexity_assessment = await self.complexity_evaluator.assess_complexity(
                task_description, scenario_analysis.scenario, context_data
            )
            logger.info(f"Assessed complexity: {complexity_assessment.level.value} (score: {complexity_assessment.score:.2f})")
            
            # 3. Agent类型推荐
            agent_recommendation = await self.agent_recommender.recommend_agent_type(
                scenario_analysis.scenario, complexity_assessment.level, context_data
            )
            logger.info(f"Recommended agent: {agent_recommendation.agent_type} (confidence: {agent_recommendation.confidence:.2f})")
            
            # 4. 工具生态预分析
            available_tools = await self._analyze_available_tools(
                scenario_analysis.scenario, agent_recommendation.agent_type, context_data
            )
            
            # 5. 工作流类型确定
            workflow_type = self._determine_workflow_type(
                scenario_analysis.scenario, complexity_assessment.level
            )
            
            # 6. 用户角色和环境分析
            user_role = self._infer_user_role(user_id, context_data)
            data_sensitivity = self._assess_data_sensitivity(context_data)
            resource_constraints = self._analyze_resource_constraints(context_data)
            
            # 7. 构建智能上下文
            smart_context = SmartContext(
                task_description=task_description,
                context_data=context_data or {},
                user_id=user_id,
                scenario=scenario_analysis.scenario,
                complexity_level=complexity_assessment.level,
                optimal_agent_type=agent_recommendation.agent_type,
                available_tools=available_tools,
                workflow_type=workflow_type,
                user_role=user_role,
                data_sensitivity=data_sensitivity,
                resource_constraints=resource_constraints,
                data_sources=self._extract_data_sources(context_data),
                constraints=complexity_assessment.recommendations,
                success_criteria=self._define_success_criteria(scenario_analysis.scenario, complexity_assessment.level)
            )
            
            logger.info("Intelligent context built successfully")
            return smart_context
            
        except Exception as e:
            logger.error(f"Failed to build intelligent context: {e}")
            # 返回基础上下文
            return SmartContext(
                task_description=task_description,
                context_data=context_data or {},
                user_id=user_id,
                scenario="general",
                complexity_level=TaskComplexity.MEDIUM,
                optimal_agent_type="data_analysis"
            )
    
    async def _analyze_available_tools(
        self,
        scenario: str,
        agent_type: str,
        context_data: Dict[str, Any] = None
    ) -> List[str]:
        """分析可用工具"""
        
        # 基于场景的工具映射
        scenario_tools = {
            "placeholder_analysis": ["placeholder_analyzer", "context_extractor", "reasoning_tool"],
            "sql_generation": ["sql_generator", "query_optimizer", "data_validator"],
            "data_analysis": ["data_analyzer", "statistical_tool", "reasoning_tool"],
            "report_generation": ["report_generator", "visualization_tool", "data_analyzer"],
            "system_maintenance": ["file_tool", "bash_tool", "system_monitor"]
        }
        
        # 基于Agent类型的工具映射
        agent_tools = {
            "data_analysis": ["reasoning_tool", "data_analyzer", "sql_generator"],
            "business_intelligence": ["reasoning_tool", "report_generator", "visualization_tool"],
            "system_administration": ["bash_tool", "file_tool", "system_monitor"],
            "development": ["reasoning_tool", "code_analyzer", "file_tool"]
        }
        
        # 合并工具列表
        tools = set()
        tools.update(scenario_tools.get(scenario, []))
        tools.update(agent_tools.get(agent_type, []))
        
        # 添加基础工具
        tools.add("reasoning_tool")
        
        return list(tools)
    
    def _determine_workflow_type(self, scenario: str, complexity: TaskComplexity) -> WorkflowType:
        """确定工作流类型"""
        
        workflow_mapping = {
            "placeholder_analysis": WorkflowType.DATA_PIPELINE,
            "sql_generation": WorkflowType.DATA_PIPELINE,
            "data_analysis": WorkflowType.DATA_PIPELINE,
            "report_generation": WorkflowType.BUSINESS_INTELLIGENCE,
            "system_maintenance": WorkflowType.SYSTEM_MAINTENANCE
        }
        
        base_workflow = workflow_mapping.get(scenario, WorkflowType.DATA_PIPELINE)
        
        # 高复杂度任务可能需要特殊工作流
        if complexity in [TaskComplexity.HIGH, TaskComplexity.EXPERT] and scenario in ["data_analysis", "sql_generation"]:
            return WorkflowType.BUSINESS_INTELLIGENCE
        
        return base_workflow
    
    def _infer_user_role(self, user_id: str, context_data: Dict[str, Any] = None) -> str:
        """推断用户角色"""
        
        # 从上下文推断
        if context_data:
            if "dashboard" in str(context_data).lower() or "report" in str(context_data).lower():
                return "executive"
            elif "sql" in str(context_data).lower() or "database" in str(context_data).lower():
                return "analyst"
            elif "system" in str(context_data).lower() or "file" in str(context_data).lower():
                return "developer"
        
        # 默认角色
        return "analyst"
    
    def _assess_data_sensitivity(self, context_data: Dict[str, Any] = None) -> str:
        """评估数据敏感性"""
        
        if not context_data:
            return "medium"
        
        # 检查敏感数据指示符
        sensitive_indicators = ["password", "token", "secret", "key", "credential", "personal", "private"]
        
        context_str = str(context_data).lower()
        sensitive_count = sum(1 for indicator in sensitive_indicators if indicator in context_str)
        
        if sensitive_count >= 3:
            return "high"
        elif sensitive_count >= 1:
            return "medium"
        else:
            return "low"
    
    def _analyze_resource_constraints(self, context_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """分析资源约束"""
        
        constraints = {
            "memory_limited": False,
            "time_limited": False,
            "compute_limited": False
        }
        
        if context_data:
            # 检查时间约束指示符
            if any(indicator in str(context_data).lower() 
                  for indicator in ["urgent", "asap", "quickly", "fast", "紧急", "快速"]):
                constraints["time_limited"] = True
            
            # 检查数据量指示符
            if "large" in str(context_data).lower() or "big" in str(context_data).lower():
                constraints["memory_limited"] = True
                constraints["compute_limited"] = True
        
        return constraints
    
    def _extract_data_sources(self, context_data: Dict[str, Any] = None) -> List[str]:
        """提取数据源"""
        
        if not context_data:
            return []
        
        data_sources = []
        
        if "data_source_info" in context_data:
            data_sources.append("configured_database")
        
        if "file_path" in context_data:
            data_sources.append("file_system")
        
        if "api_config" in context_data:
            data_sources.append("external_api")
        
        return data_sources
    
    def _define_success_criteria(self, scenario: str, complexity: TaskComplexity) -> List[str]:
        """定义成功标准"""
        
        base_criteria = ["任务完成", "结果准确"]
        
        scenario_criteria = {
            "placeholder_analysis": ["占位符正确解析", "上下文信息提取完整"],
            "sql_generation": ["SQL语法正确", "查询结果准确", "性能可接受"],
            "data_analysis": ["数据分析完整", "统计结果可靠", "洞察有价值"],
            "report_generation": ["报告格式正确", "数据可视化清晰", "内容完整"],
            "system_maintenance": ["操作安全执行", "系统状态正常", "无数据丢失"]
        }
        
        criteria = base_criteria + scenario_criteria.get(scenario, [])
        
        # 高复杂度任务有额外要求
        if complexity in [TaskComplexity.HIGH, TaskComplexity.EXPERT]:
            criteria.extend(["质量检查通过", "性能优化达标", "错误处理完善"])
        
        return criteria


# 便利函数
def create_scenario_analysis(
    scenario: str,
    confidence: ScenarioConfidence = ScenarioConfidence.MEDIUM,
    **kwargs
) -> ScenarioAnalysis:
    """快速创建场景分析结果"""
    return ScenarioAnalysis(
        scenario=scenario,
        confidence=confidence,
        reasoning="快速创建",
        **kwargs
    )


__all__ = [
    "SmartContextProcessor",
    "BusinessScenarioDetector",
    "TaskComplexityEvaluator", 
    "AgentTypeRecommender",
    "ScenarioAnalysis",
    "ComplexityAssessment",
    "AgentRecommendation",
    "ScenarioConfidence",
    "create_scenario_analysis"
]