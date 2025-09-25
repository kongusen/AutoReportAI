"""
占位符分析领域服务 - DDD架构v2.0

纯业务逻辑的占位符分析，通过基础设施层的agents实现技术功能
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Domain services should not import from application layer to avoid circular dependencies

logger = logging.getLogger(__name__)


class PlaceholderAnalysisDomainService:
    """
    占位符分析领域服务
    
    职责：
    1. 占位符业务规则定义
    2. 占位符语义分析业务逻辑
    3. 业务上下文构建
    4. 通过基础设施层agents执行技术实现
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    async def analyze_placeholder_business_requirements(
        self,
        placeholder_text: str,
        business_context: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        分析占位符的业务需求
        
        结合基础设施层的技术分析和领域层的业务逻辑
        
        Args:
            placeholder_text: 占位符文本
            business_context: 业务上下文
            
        Returns:
            业务需求分析结果
        """
        self.logger.info(f"[领域服务] 分析占位符业务需求: {placeholder_text}")
        
        # 1. 调用基础设施层进行技术分析
        technical_analysis = await self._get_technical_analysis(placeholder_text, user_id, business_context)
        
        # 2. 基于技术分析结果进行业务分析
        business_type = self._identify_business_type(placeholder_text, technical_analysis)
        
        # 3. 业务优先级评估
        priority = self._evaluate_business_priority(placeholder_text, business_context)
        
        # 4. 业务约束识别
        constraints = self._identify_business_constraints(placeholder_text, business_context)
        
        # 5. 构建业务需求
        requirements = {
            "business_type": business_type,
            "priority": priority,
            "constraints": constraints,
            "semantic_intent": self._extract_semantic_intent(placeholder_text),
            "data_requirements": self._analyze_data_requirements(placeholder_text, technical_analysis),
            "time_sensitivity": self._assess_time_sensitivity(placeholder_text),
            "technical_analysis": technical_analysis.get("technical_analysis", {})
        }
        
        return requirements
    
    async def _get_technical_analysis(self, placeholder_text: str, user_id: Optional[str] = None, business_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        通过基础设施层获取技术分析
        
        这是正确的DDD架构：领域服务调用基础设施层
        """
        try:
            # 导入基础设施层agent
            from app.services.infrastructure.agents import analyze_placeholder_technical
            
            self.logger.info(f"[领域服务] 调用基础设施层agent进行技术分析")
            # 传递业务上下文给基础设施层
            technical_context = {
                "business_context": business_context or {},
                "placeholder_text": placeholder_text
            }
            technical_result = await analyze_placeholder_technical(placeholder_text, technical_context=technical_context, user_id=user_id)
            
            if technical_result.get("success"):
                return technical_result
            else:
                self.logger.warning(f"技术分析失败，使用默认分析: {technical_result.get('error')}")
                return {"technical_analysis": {"detected_patterns": [], "complexity_level": "unknown"}}
                
        except Exception as e:
            self.logger.error(f"调用基础设施层agent失败: {str(e)}")
            return {"technical_analysis": {"detected_patterns": [], "complexity_level": "unknown"}}
    
    def validate_placeholder_business_rules(
        self,
        placeholder_text: str,
        template_context: Dict[str, Any],
        data_source_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证占位符业务规则
        
        Args:
            placeholder_text: 占位符文本
            template_context: 模板上下文
            data_source_context: 数据源上下文
            
        Returns:
            业务规则验证结果
        """
        self.logger.info(f"验证占位符业务规则: {placeholder_text}")
        
        validation_result = {
            "is_valid": True,
            "business_rule_violations": [],
            "warnings": [],
            "recommendations": []
        }
        
        # 1. 检查业务逻辑一致性
        consistency_check = self._check_business_consistency(
            placeholder_text, template_context, data_source_context
        )
        if not consistency_check["is_consistent"]:
            validation_result["business_rule_violations"].extend(consistency_check["violations"])
            validation_result["is_valid"] = False
        
        # 2. 检查数据源兼容性
        compatibility_check = self._check_data_source_compatibility(
            placeholder_text, data_source_context
        )
        if not compatibility_check["is_compatible"]:
            validation_result["warnings"].extend(compatibility_check["warnings"])
        
        # 3. 生成业务建议
        recommendations = self._generate_business_recommendations(
            placeholder_text, template_context, data_source_context
        )
        validation_result["recommendations"].extend(recommendations)
        
        return validation_result
    
    def create_placeholder_execution_strategy(
        self,
        placeholder_text: str,
        business_requirements: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建占位符执行策略
        
        Args:
            placeholder_text: 占位符文本
            business_requirements: 业务需求
            execution_context: 执行上下文
            
        Returns:
            执行策略
        """
        self.logger.info(f"创建占位符执行策略: {placeholder_text}")
        
        strategy = {
            "execution_mode": self._determine_execution_mode(business_requirements),
            "data_access_strategy": self._create_data_access_strategy(business_requirements),
            "performance_requirements": self._define_performance_requirements(business_requirements),
            "fallback_strategy": self._create_fallback_strategy(business_requirements),
            "monitoring_requirements": self._define_monitoring_requirements(business_requirements)
        }
        
        # 基于业务优先级调整策略
        if business_requirements.get("priority") == "high":
            strategy["execution_mode"] = "priority"
            strategy["performance_requirements"]["timeout"] = min(
                strategy["performance_requirements"]["timeout"], 30
            )
        
        return strategy
    
    def _identify_business_type(self, placeholder_text: str, technical_analysis: Dict[str, Any] = None) -> str:
        """
        识别业务类型
        
        结合技术分析和业务逻辑进行判断
        """
        text_lower = placeholder_text.lower()
        
        # 首先基于技术分析结果
        if technical_analysis and technical_analysis.get("technical_analysis"):
            tech_patterns = technical_analysis["technical_analysis"].get("detected_patterns", [])
            
            if any(p in tech_patterns for p in ["count", "sum"]):
                return "statistical"
            elif "date" in tech_patterns:
                return "temporal"
        
        # 回退到传统的文本分析
        if any(keyword in text_lower for keyword in ["统计", "总数", "数量", "count"]):
            return "statistical"
        elif any(keyword in text_lower for keyword in ["时间", "日期", "周期", "period"]):
            return "temporal"
        elif any(keyword in text_lower for keyword in ["金额", "收入", "成本", "amount"]):
            return "financial"
        elif any(keyword in text_lower for keyword in ["用户", "客户", "人员", "user"]):
            return "user_related"
        else:
            return "general"
    
    def _evaluate_business_priority(self, placeholder_text: str, context: Dict[str, Any]) -> str:
        """评估业务优先级"""
        # 基于业务关键词和上下文评估优先级
        high_priority_keywords = ["关键", "重要", "核心", "主要", "critical", "important"]
        text_lower = placeholder_text.lower()
        
        if any(keyword in text_lower for keyword in high_priority_keywords):
            return "high"
        elif context.get("template_type") == "executive_summary":
            return "high"
        elif context.get("execution_urgency") == "urgent":
            return "high"
        else:
            return "normal"
    
    def _identify_business_constraints(self, placeholder_text: str, context: Dict[str, Any]) -> List[str]:
        """识别业务约束"""
        constraints = []
        
        # 时间约束
        if "实时" in placeholder_text or "real-time" in placeholder_text.lower():
            constraints.append("real_time_requirement")
        
        # 精度约束
        if "精确" in placeholder_text or "准确" in placeholder_text:
            constraints.append("high_accuracy_requirement")
        
        # 数据范围约束
        if context.get("data_scope") == "limited":
            constraints.append("limited_data_scope")
        
        return constraints
    
    def _extract_semantic_intent(self, placeholder_text: str) -> str:
        """提取语义意图"""
        text_lower = placeholder_text.lower()
        
        if "获取" in text_lower or "查询" in text_lower:
            return "data_retrieval"
        elif "计算" in text_lower or "统计" in text_lower:
            return "data_calculation"
        elif "分析" in text_lower or "评估" in text_lower:
            return "data_analysis"
        elif "展示" in text_lower or "显示" in text_lower:
            return "data_presentation"
        else:
            return "data_processing"
    
    def _analyze_data_requirements(self, placeholder_text: str, technical_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析数据需求
        
        结合技术分析结果和业务逻辑
        """
        requirements = {
            "data_types": [],
            "aggregation_needed": False,
            "time_range_needed": False,
            "filtering_needed": False,
            "grouping_needed": False
        }
        
        # 首先基于技术分析结果
        if technical_analysis and technical_analysis.get("technical_analysis"):
            tech_analysis = technical_analysis["technical_analysis"]
            requirements["aggregation_needed"] = tech_analysis.get("requires_aggregation", False)
            requirements["grouping_needed"] = tech_analysis.get("requires_grouping", False)
            requirements["time_range_needed"] = tech_analysis.get("requires_date_handling", False)
        
        # 补充业务层面的分析
        text_lower = placeholder_text.lower()
        
        # 检查是否需要聚合（如果技术分析没有检测到）
        if not requirements["aggregation_needed"]:
            if any(keyword in text_lower for keyword in ["总计", "平均", "最大", "最小", "sum", "avg", "max", "min"]):
                requirements["aggregation_needed"] = True
        
        # 检查是否需要时间范围
        if not requirements["time_range_needed"]:
            if any(keyword in text_lower for keyword in ["今天", "昨天", "本月", "上月", "today", "yesterday"]):
                requirements["time_range_needed"] = True
        
        # 检查是否需要过滤
        if any(keyword in text_lower for keyword in ["条件", "筛选", "过滤", "where", "filter"]):
            requirements["filtering_needed"] = True
        
        return requirements
    
    def _assess_time_sensitivity(self, placeholder_text: str) -> str:
        """评估时间敏感性"""
        text_lower = placeholder_text.lower()
        
        if any(keyword in text_lower for keyword in ["实时", "即时", "real-time", "instant"]):
            return "real_time"
        elif any(keyword in text_lower for keyword in ["当前", "最新", "current", "latest"]):
            return "near_real_time"
        else:
            return "batch"
    
    def _check_business_consistency(
        self, 
        placeholder_text: str, 
        template_context: Dict[str, Any], 
        data_source_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查业务逻辑一致性"""
        result = {"is_consistent": True, "violations": []}
        
        # 检查数据类型一致性
        placeholder_business_type = self._identify_business_type(placeholder_text)
        template_business_type = template_context.get("business_type", "general")
        
        if placeholder_business_type != "general" and template_business_type != "general":
            if placeholder_business_type != template_business_type:
                result["violations"].append(
                    f"占位符业务类型({placeholder_business_type})与模板业务类型({template_business_type})不一致"
                )
                result["is_consistent"] = False
        
        return result
    
    def _check_data_source_compatibility(
        self, 
        placeholder_text: str, 
        data_source_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检查数据源兼容性"""
        result = {"is_compatible": True, "warnings": []}
        
        # 检查数据源类型是否支持所需操作
        data_requirements = self._analyze_data_requirements(placeholder_text)
        data_source_capabilities = data_source_context.get("capabilities", {})
        
        if data_requirements["aggregation_needed"] and not data_source_capabilities.get("supports_aggregation", True):
            result["warnings"].append("数据源可能不支持聚合操作，性能可能受影响")
        
        if data_requirements["time_range_needed"] and not data_source_capabilities.get("supports_time_queries", True):
            result["warnings"].append("数据源可能不支持时间范围查询")
        
        return result
    
    def _generate_business_recommendations(
        self, 
        placeholder_text: str, 
        template_context: Dict[str, Any], 
        data_source_context: Dict[str, Any]
    ) -> List[str]:
        """生成业务建议"""
        recommendations = []
        
        business_type = self._identify_business_type(placeholder_text)
        
        if business_type == "statistical":
            recommendations.append("建议添加数据验证步骤确保统计结果准确性")
        
        if business_type == "financial":
            recommendations.append("建议添加金额格式化和精度控制")
        
        if self._assess_time_sensitivity(placeholder_text) == "real_time":
            recommendations.append("建议考虑缓存策略以提高实时查询性能")
        
        return recommendations
    
    def _determine_execution_mode(self, requirements: Dict[str, Any]) -> str:
        """确定执行模式"""
        if requirements.get("priority") == "high":
            return "priority"
        elif requirements.get("time_sensitivity") == "real_time":
            return "real_time"
        else:
            return "standard"
    
    def _create_data_access_strategy(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """创建数据访问策略"""
        strategy = {
            "cache_strategy": "default",
            "batch_size": 1000,
            "retry_policy": "exponential_backoff"
        }
        
        if requirements.get("time_sensitivity") == "real_time":
            strategy["cache_strategy"] = "minimal"
            strategy["batch_size"] = 100
        
        return strategy
    
    def _define_performance_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """定义性能需求"""
        perf_requirements = {
            "timeout": 60,  # 秒
            "max_memory": "512MB",
            "max_cpu": "50%"
        }
        
        if requirements.get("priority") == "high":
            perf_requirements["timeout"] = 30
        
        return perf_requirements
    
    def _create_fallback_strategy(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """创建回退策略"""
        return {
            "fallback_mode": "cached_result",
            "fallback_timeout": 10,
            "error_handling": "graceful_degradation"
        }
    
    def _define_monitoring_requirements(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """定义监控需求"""
        return {
            "track_execution_time": True,
            "track_data_quality": True,
            "alert_on_errors": requirements.get("priority") == "high",
            "log_level": "INFO" if requirements.get("priority") == "high" else "WARNING"
        }


logger.info("✅ Placeholder Analysis Domain Service DDD架构v2.0加载完成")