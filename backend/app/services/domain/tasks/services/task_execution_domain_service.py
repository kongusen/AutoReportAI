"""
任务执行领域服务 - DDD架构v2.0

纯业务逻辑的任务执行，通过基础设施层的agents实现技术功能
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from enum import Enum

# Domain services should not import from application layer to avoid circular dependencies

logger = logging.getLogger(__name__)


class TaskExecutionStrategy(Enum):
    """任务执行策略"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel" 
    PRIORITY_BASED = "priority_based"
    RESOURCE_OPTIMIZED = "resource_optimized"


class TaskComplexity(Enum):
    """任务复杂度"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    HIGHLY_COMPLEX = "highly_complex"


class TaskExecutionDomainService:
    """
    任务执行领域服务
    
    职责：
    1. 任务执行业务规则定义
    2. 任务优先级和调度逻辑
    3. 任务依赖关系管理
    4. 通过基础设施层agents执行技术实现
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze_task_execution_requirements(
        self,
        task_definition: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        分析任务执行需求
        
        Args:
            task_definition: 任务定义
            execution_context: 执行上下文
            
        Returns:
            任务执行需求分析结果
        """
        self.logger.info(f"分析任务执行需求: {task_definition.get('name', 'Unknown')}")
        
        # 1. 评估任务复杂度
        complexity = self._assess_task_complexity(task_definition)
        
        # 2. 确定执行策略
        execution_strategy = self._determine_execution_strategy(task_definition, complexity)
        
        # 3. 计算资源需求
        resource_requirements = self._calculate_resource_requirements(task_definition, complexity)
        
        # 4. 分析依赖关系
        dependencies = self._analyze_task_dependencies(task_definition, execution_context)
        
        # 5. 估算执行时间
        estimated_duration = self._estimate_execution_duration(task_definition, complexity)
        
        requirements = {
            "complexity": complexity.value,
            "execution_strategy": execution_strategy.value,
            "resource_requirements": resource_requirements,
            "dependencies": dependencies,
            "estimated_duration": estimated_duration,
            "business_priority": self._evaluate_business_priority(task_definition),
            "risk_assessment": self._assess_execution_risks(task_definition, complexity)
        }
        
        return requirements
    
    def validate_task_execution_feasibility(
        self,
        task_definition: Dict[str, Any],
        available_resources: Dict[str, Any],
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        验证任务执行可行性
        
        Args:
            task_definition: 任务定义
            available_resources: 可用资源
            execution_context: 执行上下文
            
        Returns:
            可行性验证结果
        """
        self.logger.info(f"验证任务执行可行性: {task_definition.get('name', 'Unknown')}")
        
        validation_result = {
            "is_feasible": True,
            "blocking_issues": [],
            "warnings": [],
            "recommendations": []
        }
        
        # 1. 检查资源可用性
        resource_check = self._check_resource_availability(task_definition, available_resources)
        if not resource_check["sufficient"]:
            validation_result["blocking_issues"].extend(resource_check["issues"])
            validation_result["is_feasible"] = False
        
        # 2. 检查依赖满足情况
        dependency_check = self._check_dependency_satisfaction(task_definition, execution_context)
        if not dependency_check["satisfied"]:
            validation_result["blocking_issues"].extend(dependency_check["missing_dependencies"])
            validation_result["is_feasible"] = False
        
        # 3. 检查业务约束
        business_check = self._check_business_constraints(task_definition, execution_context)
        if not business_check["compliant"]:
            validation_result["warnings"].extend(business_check["violations"])
        
        # 4. 生成执行建议
        recommendations = self._generate_execution_recommendations(
            task_definition, available_resources, execution_context
        )
        validation_result["recommendations"].extend(recommendations)
        
        return validation_result
    
    def create_task_execution_plan(
        self,
        task_definition: Dict[str, Any],
        execution_requirements: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        创建任务执行计划
        
        Args:
            task_definition: 任务定义
            execution_requirements: 执行需求
            constraints: 约束条件
            
        Returns:
            任务执行计划
        """
        self.logger.info(f"创建任务执行计划: {task_definition.get('name', 'Unknown')}")
        
        # 1. 分解任务为子步骤
        execution_steps = self._decompose_task_into_steps(task_definition, execution_requirements)
        
        # 2. 确定执行顺序
        execution_order = self._determine_execution_order(execution_steps, execution_requirements)
        
        # 3. 分配资源
        resource_allocation = self._allocate_resources(execution_steps, execution_requirements, constraints)
        
        # 4. 设置监控点
        monitoring_points = self._define_monitoring_points(execution_steps)
        
        # 5. 制定回滚策略
        rollback_strategy = self._create_rollback_strategy(execution_steps, task_definition)
        
        execution_plan = {
            "plan_id": f"plan_{datetime.now().timestamp()}",
            "task_id": task_definition.get("task_id"),
            "execution_steps": execution_order,
            "resource_allocation": resource_allocation,
            "monitoring_points": monitoring_points,
            "rollback_strategy": rollback_strategy,
            "estimated_completion": self._calculate_estimated_completion(execution_order),
            "quality_gates": self._define_quality_gates(execution_steps),
            "fallback_options": self._create_fallback_options(task_definition, execution_requirements)
        }
        
        return execution_plan
    
    def _assess_task_complexity(self, task_definition: Dict[str, Any]) -> TaskComplexity:
        """评估任务复杂度"""
        complexity_score = 0
        
        # 基于数据源数量
        data_sources = task_definition.get("data_source_ids", [])
        complexity_score += len(data_sources) * 2
        
        # 基于模板复杂度
        template_info = task_definition.get("template_info", {})
        template_size = len(template_info.get("content", ""))
        if template_size > 5000:
            complexity_score += 3
        elif template_size > 1000:
            complexity_score += 2
        else:
            complexity_score += 1
        
        # 基于处理模式
        processing_mode = task_definition.get("processing_mode", "simple")
        if processing_mode == "intelligent":
            complexity_score += 3
        elif processing_mode == "advanced":
            complexity_score += 2
        
        # 基于工作流类型
        workflow_type = task_definition.get("workflow_type", "simple_report")
        if workflow_type == "complex_analysis":
            complexity_score += 4
        elif workflow_type == "multi_step_report":
            complexity_score += 3
        elif workflow_type == "simple_report":
            complexity_score += 1
        
        # 确定复杂度级别
        if complexity_score >= 12:
            return TaskComplexity.HIGHLY_COMPLEX
        elif complexity_score >= 8:
            return TaskComplexity.COMPLEX
        elif complexity_score >= 4:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.SIMPLE
    
    def _determine_execution_strategy(
        self, 
        task_definition: Dict[str, Any], 
        complexity: TaskComplexity
    ) -> TaskExecutionStrategy:
        """确定执行策略"""
        # 基于复杂度和业务优先级
        priority = self._evaluate_business_priority(task_definition)
        
        if priority == "critical" or complexity == TaskComplexity.HIGHLY_COMPLEX:
            return TaskExecutionStrategy.RESOURCE_OPTIMIZED
        elif priority == "high":
            return TaskExecutionStrategy.PRIORITY_BASED
        elif complexity in [TaskComplexity.MEDIUM, TaskComplexity.COMPLEX]:
            return TaskExecutionStrategy.PARALLEL
        else:
            return TaskExecutionStrategy.SEQUENTIAL
    
    def _calculate_resource_requirements(
        self, 
        task_definition: Dict[str, Any], 
        complexity: TaskComplexity
    ) -> Dict[str, Any]:
        """计算资源需求"""
        base_requirements = {
            "cpu_cores": 1,
            "memory_mb": 512,
            "storage_mb": 100,
            "network_bandwidth": "low",
            "execution_time_minutes": 5
        }
        
        # 基于复杂度调整资源需求
        complexity_multiplier = {
            TaskComplexity.SIMPLE: 1.0,
            TaskComplexity.MEDIUM: 2.0,
            TaskComplexity.COMPLEX: 4.0,
            TaskComplexity.HIGHLY_COMPLEX: 8.0
        }
        
        multiplier = complexity_multiplier[complexity]
        
        requirements = {
            "cpu_cores": max(1, int(base_requirements["cpu_cores"] * multiplier)),
            "memory_mb": int(base_requirements["memory_mb"] * multiplier),
            "storage_mb": int(base_requirements["storage_mb"] * multiplier),
            "network_bandwidth": "high" if multiplier >= 4.0 else "medium" if multiplier >= 2.0 else "low",
            "execution_time_minutes": int(base_requirements["execution_time_minutes"] * multiplier)
        }
        
        return requirements
    
    def _analyze_task_dependencies(
        self, 
        task_definition: Dict[str, Any], 
        execution_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析任务依赖关系"""
        dependencies = {
            "data_dependencies": [],
            "service_dependencies": [],
            "resource_dependencies": [],
            "temporal_dependencies": []
        }
        
        # 数据依赖
        data_sources = task_definition.get("data_source_ids", [])
        for ds_id in data_sources:
            dependencies["data_dependencies"].append({
                "type": "data_source",
                "resource_id": ds_id,
                "requirement": "available"
            })
        
        # 服务依赖
        if task_definition.get("processing_mode") == "intelligent":
            dependencies["service_dependencies"].append({
                "type": "agent_service",
                "service_name": "placeholder_analysis_agent",
                "requirement": "active"
            })
        
        # 模板依赖
        template_id = task_definition.get("template_id")
        if template_id:
            dependencies["resource_dependencies"].append({
                "type": "template",
                "resource_id": template_id,
                "requirement": "accessible"
            })
        
        return dependencies
    
    def _estimate_execution_duration(
        self, 
        task_definition: Dict[str, Any], 
        complexity: TaskComplexity
    ) -> Dict[str, Any]:
        """估算执行时间"""
        base_duration_minutes = {
            TaskComplexity.SIMPLE: 2,
            TaskComplexity.MEDIUM: 5,
            TaskComplexity.COMPLEX: 15,
            TaskComplexity.HIGHLY_COMPLEX: 30
        }
        
        base_time = base_duration_minutes[complexity]
        
        # 基于数据源数量调整
        data_source_count = len(task_definition.get("data_source_ids", []))
        if data_source_count > 1:
            base_time *= (1 + (data_source_count - 1) * 0.3)
        
        return {
            "estimated_minutes": int(base_time),
            "confidence": "medium",
            "factors": {
                "complexity": complexity.value,
                "data_sources": data_source_count,
                "processing_mode": task_definition.get("processing_mode", "simple")
            }
        }
    
    def _evaluate_business_priority(self, task_definition: Dict[str, Any]) -> str:
        """评估业务优先级"""
        # 基于任务名称和属性评估优先级
        task_name = task_definition.get("name", "").lower()
        
        if any(keyword in task_name for keyword in ["urgent", "critical", "紧急", "关键"]):
            return "critical"
        elif any(keyword in task_name for keyword in ["important", "high", "重要", "高"]):
            return "high"
        elif task_definition.get("workflow_type") == "executive_summary":
            return "high"
        else:
            return "normal"
    
    def _assess_execution_risks(
        self, 
        task_definition: Dict[str, Any], 
        complexity: TaskComplexity
    ) -> Dict[str, Any]:
        """评估执行风险"""
        risks = {
            "overall_risk": "low",
            "risk_factors": [],
            "mitigation_strategies": []
        }
        
        # 复杂度风险
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.HIGHLY_COMPLEX]:
            risks["risk_factors"].append("high_complexity")
            risks["mitigation_strategies"].append("增加监控点和检查点")
        
        # 数据源风险
        data_source_count = len(task_definition.get("data_source_ids", []))
        if data_source_count > 3:
            risks["risk_factors"].append("multiple_data_sources")
            risks["mitigation_strategies"].append("实施数据源连接池和重试机制")
        
        # 确定总体风险级别
        if len(risks["risk_factors"]) >= 3:
            risks["overall_risk"] = "high"
        elif len(risks["risk_factors"]) >= 1:
            risks["overall_risk"] = "medium"
        
        return risks
    
    def _decompose_task_into_steps(
        self, 
        task_definition: Dict[str, Any], 
        execution_requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """分解任务为执行步骤"""
        steps = []
        
        # 1. 准备阶段
        steps.append({
            "step_id": "preparation",
            "name": "任务准备",
            "type": "preparation",
            "estimated_duration": 30,  # 秒
            "dependencies": [],
            "agents_required": ["task_coordination_agent"]
        })
        
        # 2. 数据获取阶段
        steps.append({
            "step_id": "data_acquisition",
            "name": "数据获取",
            "type": "data_processing", 
            "estimated_duration": 120,
            "dependencies": ["preparation"],
            "agents_required": ["data_acquisition_agent"]
        })
        
        # 3. 占位符处理阶段
        if task_definition.get("processing_mode") == "intelligent":
            steps.append({
                "step_id": "placeholder_processing",
                "name": "占位符处理",
                "type": "business_logic",
                "estimated_duration": 180,
                "dependencies": ["data_acquisition"],
                "agents_required": ["placeholder_analysis_agent"]
            })
        
        # 4. 报告生成阶段
        steps.append({
            "step_id": "report_generation",
            "name": "报告生成",
            "type": "output_generation",
            "estimated_duration": 90,
            "dependencies": ["placeholder_processing"] if task_definition.get("processing_mode") == "intelligent" else ["data_acquisition"],
            "agents_required": ["report_generation_agent"]
        })
        
        # 5. 完成阶段
        steps.append({
            "step_id": "completion",
            "name": "任务完成",
            "type": "finalization",
            "estimated_duration": 30,
            "dependencies": ["report_generation"],
            "agents_required": []
        })
        
        return steps
    
    def _determine_execution_order(
        self, 
        execution_steps: List[Dict[str, Any]], 
        execution_requirements: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """确定执行顺序"""
        # 基于依赖关系排序执行步骤
        ordered_steps = []
        remaining_steps = execution_steps.copy()
        
        while remaining_steps:
            # 找到没有未满足依赖的步骤
            executable_steps = []
            for step in remaining_steps:
                dependencies = step.get("dependencies", [])
                completed_step_ids = [s["step_id"] for s in ordered_steps]
                
                if all(dep in completed_step_ids or dep == [] for dep in dependencies):
                    executable_steps.append(step)
            
            if not executable_steps:
                # 如果没有可执行的步骤，可能存在循环依赖
                self.logger.warning("检测到可能的循环依赖，强制执行剩余步骤")
                executable_steps = remaining_steps[:1]
            
            # 添加可执行步骤到有序列表
            for step in executable_steps:
                ordered_steps.append(step)
                remaining_steps.remove(step)
        
        return ordered_steps


logger.info("✅ Task Execution Domain Service DDD架构v2.0加载完成")