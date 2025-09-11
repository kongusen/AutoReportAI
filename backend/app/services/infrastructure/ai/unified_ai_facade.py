"""
统一AI门面服务 - 集中管理所有AI调用
Unified AI Facade - Centralized AI call management

提供统一的AI调用接口，隐藏底层ServiceOrchestrator的复杂性
各业务层通过这个门面进行AI调用，实现标准化和集中管理
"""

import logging
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
from enum import Enum

from .service_orchestrator import get_service_orchestrator
from .core import TaskType
from .core.prompts import prompt_manager, PromptComplexity
from .tools.sql_generator import AdvancedSQLGenerator

logger = logging.getLogger(__name__)


class AITaskCategory(Enum):
    """AI任务分类 - 用于统一管理不同业务场景"""
    
    # 模板相关
    TEMPLATE_ANALYSIS = "template_analysis"
    PLACEHOLDER_ANALYSIS = "placeholder_analysis"
    TEMPLATE_PARSING = "template_parsing"
    
    # 数据相关  
    SCHEMA_ANALYSIS = "schema_analysis"
    DATA_ANALYSIS = "data_analysis"
    QUERY_OPTIMIZATION = "query_optimization"
    
    # SQL相关
    SQL_GENERATION = "sql_generation"
    SQL_REPAIR = "sql_repair"
    SQL_OPTIMIZATION = "sql_optimization"
    
    # ETL相关
    ETL_PLANNING = "etl_planning"
    ETL_EXECUTION = "etl_execution"
    DATA_TRANSFORMATION = "data_transformation"
    
    # 报告相关
    CONTENT_GENERATION = "content_generation"
    BUSINESS_EXPLANATION = "business_explanation"
    DATA_INTERPRETATION = "data_interpretation"
    
    # 工作流相关
    WORKFLOW_ORCHESTRATION = "workflow_orchestration"
    STEP_EXECUTION = "step_execution"
    TASK_COORDINATION = "task_coordination"


class UnifiedAIFacade:
    """
    统一AI门面服务
    
    职责：
    1. 提供统一的AI调用接口
    2. 隐藏ServiceOrchestrator的复杂性  
    3. 标准化输入输出格式
    4. 集中管理AI任务类型
    5. 提供业务友好的API
    """
    
    def __init__(self):
        self.orchestrator = get_service_orchestrator()
        self.prompt_manager = prompt_manager
        self.enhanced_sql_tool = AdvancedSQLGenerator()
        logger.info("统一AI门面服务初始化完成 - 已集成企业级提示词系统")
    
    # === 模板相关AI服务 ===
    
    async def analyze_template(
        self,
        user_id: str,
        template_id: str,
        template_content: str,
        data_source_info: Optional[Dict[str, Any]] = None,
        streaming: bool = False
    ) -> Dict[str, Any]:
        """模板智能分析"""
        
        if streaming:
            # 流式处理 - 返回AsyncGenerator
            return self.orchestrator.analyze_template_streaming(
                user_id=user_id,
                template_id=template_id,
                template_content=template_content,
                data_source_info=data_source_info
            )
        else:
            # 简单调用
            return await self.orchestrator.analyze_template_simple(
                user_id=user_id,
                template_id=template_id,
                template_content=template_content,
                data_source_info=data_source_info
            )
    
    async def analyze_placeholder(
        self,
        user_id: str,
        placeholder_name: str,
        placeholder_text: str,
        template_id: str,
        template_context: Optional[str] = None,
        data_source_info: Optional[Dict[str, Any]] = None,
        task_params: Optional[Dict[str, Any]] = None,
        streaming: bool = False
    ) -> Dict[str, Any]:
        """单个占位符智能分析"""
        
        if streaming:
            return self.orchestrator.analyze_single_placeholder_streaming(
                user_id=user_id,
                placeholder_name=placeholder_name,
                placeholder_text=placeholder_text,
                template_id=template_id,
                template_context=template_context,
                data_source_info=data_source_info,
                task_params=task_params
            )
        else:
            return await self.orchestrator.analyze_single_placeholder_simple(
                user_id=user_id,
                placeholder_name=placeholder_name,
                placeholder_text=placeholder_text,
                template_id=template_id,
                template_context=template_context,
                data_source_info=data_source_info,
                task_params=task_params
            )
    
    async def batch_analyze_placeholders(
        self,
        user_id: str,
        placeholders: List[Dict[str, Any]],
        template_id: str,
        template_context: str,
        data_source_info: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """批量占位符分析"""
        
        results = []
        for placeholder in placeholders:
            result = await self.analyze_placeholder(
                user_id=user_id,
                placeholder_name=placeholder.get("name"),
                placeholder_text=placeholder.get("text"),
                template_id=template_id,
                template_context=template_context,
                data_source_info=data_source_info,
                task_params=placeholder.get("params", {})
            )
            results.append(result)
        
        return results
    
    # === SQL相关AI服务 ===
    
    async def generate_sql(
        self,
        user_id: str,
        placeholders: List[Dict[str, Any]],
        data_source_info: Optional[Dict[str, Any]] = None,
        template_context: Optional[str] = None,
        streaming: bool = False
    ) -> Dict[str, Any]:
        """SQL智能生成"""
        
        if streaming:
            return self.orchestrator.generate_sql_streaming(
                user_id=user_id,
                placeholders=placeholders,
                data_source_info=data_source_info,
                template_context=template_context
            )
        else:
            # 创建简单的SQL生成方法
            result = None
            async for message_data in self.orchestrator.generate_sql_streaming(
                user_id=user_id,
                placeholders=placeholders,
                data_source_info=data_source_info,
                template_context=template_context
            ):
                if message_data["type"] == "result":
                    result = message_data["result"]
                elif message_data["type"] == "error":
                    return {
                        "status": "error",
                        "error": message_data["error"]
                    }
            
            return result or {
                "status": "completed",
                "generated_sql": {},
                "placeholders": placeholders
            }
    
    async def generate_sql_enhanced(
        self,
        user_id: str,
        placeholders: List[Dict[str, Any]],
        data_source_info: Optional[Dict[str, Any]] = None,
        template_context: Optional[str] = None,
        use_enterprise_prompts: bool = True
    ) -> Dict[str, Any]:
        """增强的SQL生成 - 使用企业级提示词系统"""
        
        try:
            if use_enterprise_prompts and self.enhanced_sql_tool:
                self.logger.info(f"🚀 使用企业级提示词系统生成SQL: {len(placeholders)} 个占位符")
                
                # 构建工具上下文
                from ..core.context import ToolContext
                
                tool_context = ToolContext(
                    user_id=user_id,
                    task_id=str(uuid.uuid4()),
                    session_id=str(uuid.uuid4()),
                    timestamp=datetime.now()
                )
                
                # 准备输入数据
                input_data = {
                    "placeholders": placeholders,
                    "data_source_info": data_source_info or {},
                    "template_context": template_context or ""
                }
                
                # 执行增强的SQL生成
                results = []
                async for result in self.enhanced_sql_tool.execute(input_data, tool_context):
                    if result.result_type == "success":
                        return {
                            "status": "success",
                            "data": result.data,
                            "message": "使用企业级提示词系统成功生成SQL",
                            "enhanced": True,
                            "tool_version": "enhanced_v2.0"
                        }
                    elif result.result_type == "error":
                        self.logger.error(f"增强SQL生成失败: {result.error_message}")
                        # 回退到标准方法
                        break
                    else:
                        # 进度结果
                        results.append({
                            "type": "progress", 
                            "message": result.message,
                            "progress": result.progress
                        })
                
                # 如果增强方法失败，回退到标准方法
                self.logger.warning("增强SQL生成失败，回退到标准方法")
            
            # 使用标准方法作为回退
            return await self.generate_sql(
                user_id=user_id,
                placeholders=placeholders,
                data_source_info=data_source_info,
                template_context=template_context,
                streaming=False
            )
            
        except Exception as e:
            self.logger.error(f"SQL生成失败: {e}")
            return {
                "status": "error",
                "error": str(e),
                "fallback_attempted": True
            }
    
    async def optimize_query(
        self,
        user_id: str,
        sql_query: str,
        schema_info: Dict[str, Any],
        performance_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """查询优化建议"""
        
        # 使用通用AI调用
        return await self._execute_ai_task(
            category=AITaskCategory.QUERY_OPTIMIZATION,
            user_id=user_id,
            task_data={
                "sql_query": sql_query,
                "schema_info": schema_info,
                "performance_requirements": performance_requirements or {}
            }
        )
    
    # === 数据分析AI服务 ===
    
    async def analyze_schema(
        self,
        user_id: str,
        schema_data: Dict[str, Any],
        analysis_depth: str = "standard"
    ) -> Dict[str, Any]:
        """Schema结构智能分析"""
        
        return await self._execute_ai_task(
            category=AITaskCategory.SCHEMA_ANALYSIS,
            user_id=user_id,
            task_data={
                "schema_data": schema_data,
                "analysis_depth": analysis_depth
            }
        )
    
    async def analyze_data_quality(
        self,
        user_id: str,
        data_sample: Dict[str, Any],
        quality_metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """数据质量智能分析"""
        
        return await self._execute_ai_task(
            category=AITaskCategory.DATA_ANALYSIS,
            user_id=user_id,
            task_data={
                "data_sample": data_sample,
                "quality_metrics": quality_metrics or ["completeness", "accuracy", "consistency"]
            }
        )
    
    # === ETL相关AI服务 ===
    
    async def plan_etl_workflow(
        self,
        user_id: str,
        source_schema: Dict[str, Any],
        target_schema: Dict[str, Any],
        business_requirements: Optional[str] = None
    ) -> Dict[str, Any]:
        """ETL工作流智能规划"""
        
        return await self._execute_ai_task(
            category=AITaskCategory.ETL_PLANNING,
            user_id=user_id,
            task_data={
                "source_schema": source_schema,
                "target_schema": target_schema,
                "business_requirements": business_requirements or ""
            }
        )
    
    async def execute_data_transformation(
        self,
        user_id: str,
        transformation_rules: List[Dict[str, Any]],
        source_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """数据转换智能执行"""
        
        return await self._execute_ai_task(
            category=AITaskCategory.DATA_TRANSFORMATION,
            user_id=user_id,
            task_data={
                "transformation_rules": transformation_rules,
                "source_data": source_data
            }
        )
    
    # === 报告生成AI服务 ===
    
    async def generate_content(
        self,
        user_id: str,
        template_parts: List[Dict[str, Any]],
        data_context: Dict[str, Any],
        style_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """报告内容智能生成"""
        
        return await self._execute_ai_task(
            category=AITaskCategory.CONTENT_GENERATION,
            user_id=user_id,
            task_data={
                "template_parts": template_parts,
                "data_context": data_context,
                "style_requirements": style_requirements or {}
            }
        )
    
    async def explain_business_insights(
        self,
        user_id: str,
        data_analysis_results: Dict[str, Any],
        business_context: str,
        target_audience: str = "business"
    ) -> Dict[str, Any]:
        """业务洞察智能解释"""
        
        return await self._execute_ai_task(
            category=AITaskCategory.BUSINESS_EXPLANATION,
            user_id=user_id,
            task_data={
                "analysis_results": data_analysis_results,
                "business_context": business_context,
                "target_audience": target_audience
            }
        )
    
    # === 工作流相关AI服务 ===
    
    async def orchestrate_workflow_step(
        self,
        user_id: str,
        step_definition: Dict[str, Any],
        workflow_context: Dict[str, Any],
        previous_results: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """工作流步骤智能编排"""
        
        return await self._execute_ai_task(
            category=AITaskCategory.WORKFLOW_ORCHESTRATION,
            user_id=user_id,
            task_data={
                "step_definition": step_definition,
                "workflow_context": workflow_context,
                "previous_results": previous_results or []
            }
        )
    
    # === 核心执行方法 ===
    
    async def _execute_ai_task(
        self,
        category: AITaskCategory,
        user_id: str,
        task_data: Dict[str, Any],
        task_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        通用AI任务执行方法
        所有业务层都通过这个方法进行AI调用，确保统一性
        """
        
        # 根据分类映射到具体的任务类型
        task_type_mapping = {
            AITaskCategory.TEMPLATE_ANALYSIS: TaskType.TEMPLATE_ANALYSIS,
            AITaskCategory.PLACEHOLDER_ANALYSIS: TaskType.PLACEHOLDER_ANALYSIS,
            AITaskCategory.SQL_GENERATION: TaskType.SQL_GENERATION,
            AITaskCategory.SQL_REPAIR: TaskType.SQL_REPAIR,
            AITaskCategory.DATA_TRANSFORMATION: TaskType.DATA_TRANSFORMATION,
            # 其他任务类型可以扩展
        }
        
        task_type = task_type_mapping.get(category)
        if not task_type:
            # 对于不直接支持的任务类型，使用通用处理
            return await self._execute_generic_ai_task(category, user_id, task_data)
        
        # 使用现有的ServiceOrchestrator架构
        from .core import AgentTask
        
        task = AgentTask(
            type=task_type,
            task_id=f"{category.value}_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            data=task_data,
            config=task_config,
            created_at=datetime.utcnow().isoformat()
        )
        
        # 执行并收集结果
        result = None
        error = None
        
        async for message in self.orchestrator.controller.execute_task(task):
            if message.type.value == "result":
                result = message.content
            elif message.type.value == "error":
                error = message.error
        
        if error:
            return {
                "status": "error",
                "category": category.value,
                "error": {
                    "type": error.error_type,
                    "message": error.error_message,
                    "recoverable": error.recoverable
                }
            }
        
        return result or {
            "status": "completed",
            "category": category.value,
            "message": "AI任务执行完成，但未返回具体结果"
        }
    
    async def _execute_generic_ai_task(
        self,
        category: AITaskCategory,
        user_id: str,
        task_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        通用AI任务处理 - 用于处理尚未映射到具体TaskType的任务
        """
        
        # 使用底层的LLM服务
        from .llm import ask_agent_for_user
        
        # 根据任务分类构建提示词
        prompt = self._build_prompt_for_category(category, task_data)
        
        try:
            # 处理UUID格式问题 - 如果user_id不是有效UUID，创建一个系统默认UUID
            import uuid
            try:
                if user_id in ["test-user", "system", "test-user-001", "test-user-002", "test-user-003", "test-user-004", "test-user-005", "test-user-006", "test-user-007"]:
                    # 为测试用户创建固定UUID
                    test_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))
                else:
                    # 验证是否为有效UUID
                    uuid.UUID(user_id)
                    test_uuid = user_id
            except ValueError:
                # 如果不是有效UUID，创建一个基于字符串的UUID
                test_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, user_id))
                
            response = await ask_agent_for_user(
                user_id=test_uuid,
                question=prompt,
                agent_type=category.value,
                task_type=category.value,
                complexity="medium"
            )
            
            # 确保响应不为None
            if response is None:
                response = f"AI服务返回空结果，任务类别: {category.value}"
                
            return {
                "status": "completed",
                "category": category.value,
                "result": response,
                "processed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "category": category.value,
                "error": {
                    "type": "generic_ai_error",
                    "message": str(e),
                    "recoverable": True
                }
            }
    
    def _build_prompt_for_category(
        self,
        category: AITaskCategory,
        task_data: Dict[str, Any]
    ) -> str:
        """根据任务分类构建提示词"""
        
        base_prompts = {
            AITaskCategory.SCHEMA_ANALYSIS: f"""
            请分析以下数据库Schema结构：
            {task_data.get('schema_data', {})}
            
            分析要求：
            1. 表结构特征分析
            2. 字段类型分布
            3. 关系分析
            4. 优化建议
            """,
            
            AITaskCategory.QUERY_OPTIMIZATION: f"""
            请分析并优化以下SQL查询：
            SQL: {task_data.get('sql_query', '')}
            Schema: {task_data.get('schema_info', {})}
            
            优化要求：
            1. 索引优化建议
            2. 查询重写建议
            3. 性能提升预估
            """,
            
            AITaskCategory.DATA_ANALYSIS: f"""
            请分析以下数据质量：
            数据样本: {task_data.get('data_sample', {})}
            质量指标: {task_data.get('quality_metrics', [])}
            
            分析要求：
            1. 数据完整性评估
            2. 数据准确性检查
            3. 异常值检测
            4. 质量改进建议
            """,
            
            AITaskCategory.ETL_PLANNING: f"""
            请规划ETL工作流：
            源Schema: {task_data.get('source_schema', {})}
            目标Schema: {task_data.get('target_schema', {})}
            业务需求: {task_data.get('business_requirements', '')}
            
            规划要求：
            1. 数据映射规则
            2. 转换步骤设计
            3. 数据验证规则
            4. 性能优化建议
            """,
            
            AITaskCategory.CONTENT_GENERATION: f"""
            请生成报告内容：
            模板部分: {task_data.get('template_parts', [])}
            数据上下文: {task_data.get('data_context', {})}
            风格要求: {task_data.get('style_requirements', {})}
            
            生成要求：
            1. 内容逻辑清晰
            2. 数据引用准确
            3. 语言表达专业
            4. 符合风格要求
            """,
            
            AITaskCategory.BUSINESS_EXPLANATION: f"""
            请解释业务洞察：
            分析结果: {task_data.get('analysis_results', {})}
            业务背景: {task_data.get('business_context', '')}
            目标受众: {task_data.get('target_audience', 'business')}
            
            解释要求：
            1. 通俗易懂的语言
            2. 突出关键洞察
            3. 提供行动建议
            4. 符合受众特点
            """
        }
        
        return base_prompts.get(category, f"请处理{category.value}任务：{task_data}")
    
    # === 健康检查和状态管理 ===
    
    async def health_check(self) -> Dict[str, Any]:
        """AI服务健康检查"""
        try:
            orchestrator_health = {
                "orchestrator_status": "healthy",
                "active_tasks": len(self.orchestrator.list_active_tasks())
            }
            
            # 检查LLM服务健康状态
            from .llm import health_check
            llm_health = await health_check()
            
            return {
                "status": "healthy",
                "unified_facade": "operational",
                "orchestrator": orchestrator_health,
                "llm_services": llm_health,
                "supported_categories": [cat.value for cat in AITaskCategory],
                "checked_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.now().isoformat()
            }
    
    def get_supported_categories(self) -> List[str]:
        """获取支持的AI任务分类"""
        return [category.value for category in AITaskCategory]


    # === 企业级提示词管理 ===
    
    def get_optimized_prompt(
        self,
        category: str,
        prompt_type: str,
        context: Dict[str, Any],
        complexity: Optional[PromptComplexity] = None
    ) -> str:
        """获取优化的提示词"""
        try:
            return self.prompt_manager.get_prompt(
                category=category,
                prompt_type=prompt_type,
                context=context,
                complexity=complexity
            )
        except Exception as e:
            self.logger.error(f"获取提示词失败: {category}.{prompt_type} - {e}")
            raise
    
    def assess_prompt_complexity(self, context: Dict[str, Any]) -> PromptComplexity:
        """评估提示词复杂度需求"""
        return self.prompt_manager._assess_complexity(context)
    
    async def analyze_prompt_performance(
        self,
        category: str,
        prompt_type: str,
        usage_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """分析提示词性能表现"""
        
        try:
            # 基于使用统计分析提示词效果
            performance_metrics = {
                "success_rate": usage_stats.get("success_count", 0) / max(usage_stats.get("total_count", 1), 1),
                "average_complexity": usage_stats.get("avg_complexity", "medium"),
                "error_patterns": usage_stats.get("common_errors", []),
                "optimization_suggestions": []
            }
            
            # 生成优化建议
            if performance_metrics["success_rate"] < 0.8:
                performance_metrics["optimization_suggestions"].append(
                    "建议增加提示词复杂度或添加更多约束"
                )
            
            if len(performance_metrics["error_patterns"]) > 3:
                performance_metrics["optimization_suggestions"].append(
                    "建议分析错误模式，优化错误恢复机制"
                )
            
            return {
                "status": "success",
                "performance_metrics": performance_metrics,
                "category": category,
                "prompt_type": prompt_type
            }
            
        except Exception as e:
            self.logger.error(f"提示词性能分析失败: {e}")
            return {
                "status": "error",
                "error": str(e)
            }


# === 全局实例管理 ===

_unified_facade: Optional[UnifiedAIFacade] = None


def get_unified_ai_facade() -> UnifiedAIFacade:
    """获取统一AI门面服务单例"""
    global _unified_facade
    if _unified_facade is None:
        _unified_facade = UnifiedAIFacade()
    return _unified_facade


# === 便捷导入 ===

__all__ = [
    "UnifiedAIFacade",
    "AITaskCategory", 
    "get_unified_ai_facade"
]