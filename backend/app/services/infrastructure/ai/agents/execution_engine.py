"""
Infrastructure层AI执行引擎

原始来源: app/services/agents/core/execution_engine.py
重构为符合DDD Infrastructure层的AI执行引擎服务

核心职责：
- 提供AI任务执行的技术基础设施
- 协调DAG控制器和模型调用
- 管理执行状态和性能监控
- 为上层Agent提供执行引擎支撑

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层的Agent调用
- 提供稳定的AI任务执行服务
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union
from enum import Enum
from datetime import datetime

from .task_context import (
    AITaskContext,
    ExecutionStep,
    ExecutionStepType,
    ModelRequirement
)
from .dag_controller import (
    DAGController,
    ControlContext,
    ControlDecision,
    ExecutionStatus,
    StepResult,
    create_control_context
)

logger = logging.getLogger(__name__)


class AIExecutionEngine:
    """
    Infrastructure层AI执行引擎
    
    核心职责：
    1. 执行DAG中的每个步骤
    2. 协调DAG Controller的决策
    3. 管理Think/Default模型的调用
    4. 处理工具调用和结果处理
    5. 监控执行进度和性能
    
    技术定位：
    - Infrastructure层技术基础设施
    - 为上层Agent提供AI执行能力
    - 不包含具体业务逻辑
    """
    
    def __init__(self):
        self.dag_controller = DAGController()
        
        # 模型和工具注册表 (将在后续实现中注入)
        self.think_model = None
        self.default_model = None
        self.tools_registry = {}
        
        # 执行统计
        self.execution_stats = {
            "total_tasks_executed": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "avg_execution_time": 0.0,
            "step_stats": {},
            "model_stats": {"think": 0, "default": 0}
        }
        
        logger.info("AI执行引擎Infrastructure服务初始化完成")
    
    def register_models(self, think_model: Any, default_model: Any):
        """注册Think和Default模型"""
        self.think_model = think_model
        self.default_model = default_model
        logger.info("模型已注册到AI执行引擎")
    
    def register_tools(self, tools_registry: Dict[str, Any]):
        """注册工具注册表"""
        self.tools_registry = tools_registry
        logger.info(f"工具已注册到AI执行引擎: {list(tools_registry.keys())}")
    
    async def execute_placeholder_task(
        self,
        placeholder_text: str,
        statistical_type: str,
        description: str,
        context_engine: Dict[str, Any],
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        执行占位符处理任务 - Infrastructure层主入口
        
        这是原execute_placeholder_with_context函数的Infrastructure层实现，
        保持API兼容性但使用新的DDD架构。
        
        Args:
            placeholder_text: 占位符文本
            statistical_type: 统计类型
            description: 需求描述
            context_engine: 上下文工程数据
            user_id: 用户ID
            
        Returns:
            执行结果字典
        """
        try:
            # 创建AI任务上下文
            from .task_context import create_ai_task_context_from_placeholder_analysis
            
            # 从context_engine提取上下文分析
            context_analysis = context_engine.get('context_analysis', {})
            
            task_context = create_ai_task_context_from_placeholder_analysis(
                placeholder_text=placeholder_text,
                statistical_type=statistical_type,
                description=description,
                context_analysis=context_analysis,
                user_id=user_id,
                context_engine=context_engine
            )
            
            # 执行任务
            return await self.execute_ai_task(task_context)
            
        except Exception as e:
            logger.error(f"占位符任务执行失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': 'infrastructure_ai_execution_engine'
            }
    
    async def execute_ai_task(
        self, 
        task_context: AITaskContext
    ) -> Dict[str, Any]:
        """
        执行完整的AI任务
        
        Args:
            task_context: AI任务上下文
            
        Returns:
            执行结果字典
        """
        execution_start_time = time.time()
        task_context.execution_started_at = datetime.fromtimestamp(execution_start_time)
        
        # 创建控制上下文
        control_context = create_control_context(task_context)
        
        logger.info(f"开始执行AI任务: {task_context.get_task_summary()}")
        
        try:
            # 执行完整的DAG流程（保持现有逻辑）
            result = await self._execute_full_mode(task_context, control_context)
            
            # 检查上下文工程中的输出控制参数
            context_engine = task_context.context_engine if hasattr(task_context, 'context_engine') else {}
            output_control = context_engine.get("output_control", {})
            data_context = context_engine.get("data_context", {})
            
            execution_mode = output_control.get("mode", "full")
            
            if execution_mode != "full":
                logger.info(f"应用输出控制模式: {execution_mode}")
                # 根据控制模式调整最终输出
                return await self._apply_output_control(result, output_control, data_context, task_context)
            
            return result
            
        except Exception as e:
            logger.error(f"任务执行异常: {task_context.task_id}, 错误: {e}")
            return await self._generate_error_result(control_context, str(e))
    
    async def _execute_full_mode(
        self, 
        task_context: AITaskContext,
        control_context: ControlContext
    ) -> Dict[str, Any]:
        """执行完整模式（原有逻辑）"""
        try:
            # 主执行循环
            while True:
                # 1. DAG Controller 控制决策
                decision, next_step = await self.dag_controller.control_execution(control_context)
                
                # 2. 根据决策执行相应操作
                if decision == ControlDecision.COMPLETE:
                    logger.info(f"任务执行完成: {task_context.task_id}")
                    break
                    
                elif decision == ControlDecision.ABORT:
                    logger.error(f"任务执行中止: {task_context.task_id}")
                    break
                    
                elif decision == ControlDecision.CONTINUE:
                    if next_step:
                        result = await self._execute_step(next_step, control_context)
                        control_context.step_results[next_step.step_id] = result
                        
                elif decision == ControlDecision.RETRY:
                    if next_step:
                        logger.info(f"重试步骤: {next_step.step_id}")
                        result = await self._execute_step(next_step, control_context)
                        control_context.step_results[next_step.step_id] = result
                        control_context.retry_count += 1
                
                # 3. 检查是否有致命错误
                if control_context.error_count > control_context.max_errors:
                    logger.error(f"错误数量超限，中止执行: {task_context.task_id}")
                    break
            
            # 执行完成，生成最终结果
            execution_result = await self._generate_final_result(control_context)
            
            # 更新统计
            self._update_execution_stats(control_context, execution_result)
            
            task_context.execution_completed_at = time.time()
            
            logger.info(f"任务执行结束: {task_context.task_id}, 用时: {execution_result['execution_time']:.2f}s")
            
            return execution_result
            
        except Exception as e:
            logger.error(f"任务执行异常: {task_context.task_id}, 错误: {e}")
            return await self._generate_error_result(control_context, str(e))
    
    async def _execute_step(
        self,
        step: ExecutionStep,
        control_context: ControlContext
    ) -> StepResult:
        """
        执行单个步骤
        
        Args:
            step: 执行步骤
            control_context: 控制上下文
            
        Returns:
            步骤执行结果
        """
        step_start_time = time.time()
        
        logger.info(f"执行步骤: {step.step_id} ({step.step_type.value}), 模型: {step.model_requirement.value}")
        
        try:
            # 1. 检查依赖
            if not await self._check_dependencies(step, control_context):
                return StepResult(
                    step_id=step.step_id,
                    status=ExecutionStatus.FAILED,
                    error_message="依赖步骤未完成或失败"
                )
            
            # 2. 准备输入数据
            input_data = await self._prepare_step_input(step, control_context)
            
            # 3. 选择并调用模型
            model_result = await self._execute_with_model(step, input_data, control_context)
            
            # 4. 调用工具 (如果需要)
            if step.tools_needed:
                tool_result = await self._execute_with_tools(step, model_result, control_context)
                final_result = tool_result
            else:
                final_result = model_result
            
            # 5. 验证结果
            validation_result = await self._validate_step_result(step, final_result, control_context)
            
            execution_time = time.time() - step_start_time
            
            # 创建成功结果
            step_result = StepResult(
                step_id=step.step_id,
                status=ExecutionStatus.SUCCESS,
                result_data=final_result,
                execution_time=execution_time,
                model_used=step.model_requirement.value,
                confidence_score=validation_result.get('confidence', 0.8),
                quality_score=validation_result.get('quality', 0.8)
            )
            
            logger.info(f"步骤执行成功: {step.step_id}, 用时: {execution_time:.2f}s")
            
            return step_result
            
        except Exception as e:
            execution_time = time.time() - step_start_time
            control_context.error_count += 1
            
            logger.error(f"步骤执行失败: {step.step_id}, 错误: {e}")
            
            return StepResult(
                step_id=step.step_id,
                status=ExecutionStatus.FAILED,
                error_message=str(e),
                execution_time=execution_time,
                model_used=step.model_requirement.value
            )
    
    async def _check_dependencies(
        self,
        step: ExecutionStep,
        control_context: ControlContext
    ) -> bool:
        """检查步骤依赖是否满足"""
        if not step.dependencies:
            return True
        
        for dep_step_id in step.dependencies:
            dep_result = control_context.step_results.get(dep_step_id)
            if not dep_result or dep_result.status != ExecutionStatus.SUCCESS:
                logger.warning(f"步骤 {step.step_id} 的依赖 {dep_step_id} 未满足")
                return False
        
        return True
    
    async def _prepare_step_input(
        self,
        step: ExecutionStep,
        control_context: ControlContext
    ) -> Dict[str, Any]:
        """准备步骤输入数据"""
        input_data = {
            "step_info": {
                "step_id": step.step_id,
                "step_type": step.step_type.value,
                "expected_output": step.expected_output
            },
            "task_context": control_context.task_context.to_dict(),
            "dependency_results": {}
        }
        
        # 添加依赖步骤的结果
        for dep_step_id in step.dependencies:
            dep_result = control_context.step_results.get(dep_step_id)
            if dep_result and dep_result.status == ExecutionStatus.SUCCESS:
                input_data["dependency_results"][dep_step_id] = dep_result.result_data
        
        # 根据步骤类型添加特定数据
        if step.step_type == ExecutionStepType.PARSE:
            input_data["placeholder_text"] = control_context.task_context.placeholder_text
            
        elif step.step_type == ExecutionStepType.CONTEXT_ANALYSIS:
            input_data["context_analysis"] = control_context.task_context.context_analysis
            
        elif step.step_type == ExecutionStepType.SQL_GENERATION:
            input_data["business_domain"] = control_context.task_context.business_domain
            input_data["requires_multiple_tables"] = control_context.task_context.has_multiple_tables
            
        return input_data
    
    async def _execute_with_model(
        self,
        step: ExecutionStep,
        input_data: Dict[str, Any],
        control_context: ControlContext
    ) -> Any:
        """使用模型执行步骤"""
        
        # 选择模型
        if step.model_requirement == ModelRequirement.THINK:
            model = self.think_model
            model_name = "think"
        else:
            model = self.default_model  
            model_name = "default"
        
        if not model:
            # 如果模型未注册，抛出错误
            error_msg = f"模型 {model_name} 未注册，无法执行步骤"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # 构造模型输入
        model_input = await self._build_model_input(step, input_data, control_context)
        
        # 调用模型
        model_result = await self._call_model(model, model_input, step)
        
        # 更新统计
        self.execution_stats["model_stats"][model_name] += 1
        
        return model_result
    
    
    async def _build_model_input(
        self,
        step: ExecutionStep,
        input_data: Dict[str, Any],
        control_context: ControlContext
    ) -> str:
        """构建模型输入提示"""
        
        task_context = control_context.task_context
        
        base_prompt = f"""
你是一个专业的数据分析助手，正在处理AI任务。

任务信息:
- 任务ID: {task_context.task_id}
- 占位符: {task_context.placeholder_text}
- 统计类型: {task_context.statistical_type}
- 需求描述: {task_context.description}
- 复杂度: {task_context.complexity.value}
- 业务领域: {task_context.business_domain}

当前步骤:
- 步骤ID: {step.step_id}
- 步骤类型: {step.step_type.value}
- 期望输出: {step.expected_output}
- 使用模型: {step.model_requirement.value}
"""
        
        # 根据步骤类型添加特定提示
        if step.step_type == ExecutionStepType.PARSE:
            base_prompt += f"""
任务: 解析占位符文本，提取统计需求和参数
占位符文本: {input_data.get('placeholder_text')}
请提取: 统计类型、参数、条件、时间范围等信息
"""
        
        elif step.step_type == ExecutionStepType.SQL_GENERATION:
            base_prompt += f"""
任务: 根据需求生成SQL查询语句
业务领域: {input_data.get('business_domain')}
多表关联: {input_data.get('requires_multiple_tables')}
请生成高质量的SQL查询语句
"""
        
        elif step.step_type == ExecutionStepType.BUSINESS_LOGIC:
            base_prompt += f"""
任务: 处理业务逻辑和规则
请根据业务上下文处理数据，应用相关的业务规则
"""
        
        elif step.step_type == ExecutionStepType.VALIDATION:
            base_prompt += f"""
任务: 验证结果的正确性和完整性
请检查数据质量、格式正确性、业务逻辑合理性
"""
        
        elif step.step_type == ExecutionStepType.FORMATTING:
            base_prompt += f"""
任务: 格式化输出结果
请将结果格式化为适合占位符替换的格式
"""
        
        # 添加依赖结果
        if input_data.get("dependency_results"):
            base_prompt += f"""
上一步骤的结果:
{input_data["dependency_results"]}
"""
        
        return base_prompt
    
    async def _call_model(self, model: Any, model_input: str, step: ExecutionStep) -> Any:
        """调用模型"""
        try:
            # 这里需要根据实际模型接口进行调用
            if hasattr(model, 'achat'):
                # LLM模型调用
                from llama_index.core.base.llms.types import ChatMessage
                messages = [ChatMessage(role="user", content=model_input)]
                response = await model.achat(messages)
                return response.message.content
            elif hasattr(model, 'generate'):
                # 其他模型调用
                return await model.generate(model_input)
            else:
                # 默认调用方式
                return str(model(model_input))
        except Exception as e:
            logger.error(f"模型调用失败: {e}")
            raise
    
    async def _execute_with_tools(
        self,
        step: ExecutionStep,
        model_result: Any,
        control_context: ControlContext
    ) -> Any:
        """使用工具执行步骤"""
        
        tool_results = {}
        
        for tool_name in step.tools_needed:
            tool = self.tools_registry.get(tool_name)
            if not tool:
                logger.warning(f"工具 {tool_name} 未找到")
                continue
            
            try:
                # 调用工具
                tool_input = {
                    "model_result": model_result,
                    "step_info": step,
                    "task_context": control_context.task_context
                }
                
                if hasattr(tool, 'execute'):
                    tool_result = await tool.execute(tool_input)
                else:
                    tool_result = tool(tool_input)
                    
                tool_results[tool_name] = tool_result
                
            except Exception as e:
                logger.error(f"工具 {tool_name} 执行失败: {e}")
                tool_results[tool_name] = {"error": str(e)}
        
        # 合并工具结果
        if len(tool_results) == 1:
            return list(tool_results.values())[0]
        else:
            return {
                "model_result": model_result,
                "tool_results": tool_results
            }
    
    async def _validate_step_result(
        self,
        step: ExecutionStep,
        result: Any,
        control_context: ControlContext
    ) -> Dict[str, float]:
        """验证步骤结果"""
        
        validation = {
            "confidence": 0.8,  # 默认置信度
            "quality": 0.8      # 默认质量分数
        }
        
        # 根据步骤类型进行特定验证
        if step.step_type == ExecutionStepType.SQL_GENERATION:
            if result and "SELECT" in str(result).upper():
                validation["confidence"] = 0.9
                validation["quality"] = 0.9
            else:
                validation["confidence"] = 0.3
                validation["quality"] = 0.3
        
        elif step.step_type == ExecutionStepType.DATA_QUERY:
            if result and result != "":
                validation["confidence"] = 0.8
                validation["quality"] = 0.8
            else:
                validation["confidence"] = 0.2
                validation["quality"] = 0.2
        
        return validation
    
    async def _generate_final_result(self, control_context: ControlContext) -> Dict[str, Any]:
        """生成最终执行结果"""
        task_context = control_context.task_context
        
        # 获取最后一个成功步骤的结果
        final_result = None
        for step in reversed(task_context.execution_steps):
            step_result = control_context.step_results.get(step.step_id)
            if step_result and step_result.status == ExecutionStatus.SUCCESS:
                final_result = step_result.result_data
                break
        
        if isinstance(task_context.execution_started_at, datetime):
            total_time = time.time() - task_context.execution_started_at.timestamp()
        elif isinstance(task_context.execution_started_at, (int, float)):
            total_time = time.time() - task_context.execution_started_at
        else:
            total_time = 0
        
        return {
            "task_id": task_context.task_id,
            "status": "success",
            "result": final_result,
            "execution_time": total_time,
            "steps_executed": len(control_context.step_results),
            "step_results": {k: v.status.value for k, v in control_context.step_results.items()},
            "performance_metrics": control_context.performance_metrics,
            "execution_history": control_context.execution_history
        }
    
    async def _generate_error_result(self, control_context: ControlContext, error_message: str) -> Dict[str, Any]:
        """生成错误结果"""
        task_context = control_context.task_context
        
        if isinstance(task_context.execution_started_at, datetime):
            total_time = time.time() - task_context.execution_started_at.timestamp()
        elif isinstance(task_context.execution_started_at, (int, float)):
            total_time = time.time() - task_context.execution_started_at
        else:
            total_time = 0
        
        return {
            "task_id": task_context.task_id,
            "status": "failed",
            "error": error_message,
            "execution_time": total_time,
            "steps_executed": len(control_context.step_results),
            "step_results": {k: v.status.value for k, v in control_context.step_results.items()},
            "error_count": control_context.error_count,
            "retry_count": control_context.retry_count
        }
    
    def _update_execution_stats(self, control_context: ControlContext, result: Dict[str, Any]):
        """更新执行统计"""
        self.execution_stats["total_tasks_executed"] += 1
        
        if result["status"] == "success":
            self.execution_stats["successful_tasks"] += 1
        else:
            self.execution_stats["failed_tasks"] += 1
        
        # 更新平均执行时间
        total_tasks = self.execution_stats["total_tasks_executed"]
        if total_tasks > 1:
            current_avg = self.execution_stats["avg_execution_time"]
            new_avg = (current_avg * (total_tasks - 1) + result["execution_time"]) / total_tasks
            self.execution_stats["avg_execution_time"] = new_avg
        else:
            self.execution_stats["avg_execution_time"] = result["execution_time"]
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息"""
        return {
            "ai_execution_engine_stats": self.execution_stats,
            "dag_controller_stats": self.dag_controller.get_execution_statistics()
        }
    
    async def _apply_output_control(
        self, 
        dag_result: Dict[str, Any], 
        output_control: Dict[str, Any], 
        data_context: Dict[str, Any],
        task_context: AITaskContext
    ) -> Dict[str, Any]:
        """根据输出控制参数调整最终输出"""
        
        mode = output_control.get("mode", "full")
        
        if mode == "sql_only":
            return await self._generate_sql_only_output(dag_result, output_control, data_context, task_context)
        elif mode == "chart_test":
            return await self._generate_chart_test_output(dag_result, output_control, data_context, task_context)
        elif mode == "sql_validation":
            return await self._generate_sql_validation_output(dag_result, output_control, data_context, task_context)
        elif mode == "chart_etl":
            return await self._generate_chart_etl_output(dag_result, output_control, data_context, task_context)
        
        return dag_result
    
    async def _generate_sql_only_output(
        self, 
        dag_result: Dict[str, Any], 
        output_control: Dict[str, Any], 
        data_context: Dict[str, Any],
        task_context: AITaskContext
    ) -> Dict[str, Any]:
        """生成仅SQL的输出（模板SQL生成模式）"""
        
        # 从DAG结果中提取SQL
        sql_query = ""
        quality_score = 0.0
        
        # 查找SQL生成结果
        if dag_result.get("result"):
            result_data = dag_result["result"]
            if isinstance(result_data, dict):
                sql_query = result_data.get("sql", result_data.get("generated_sql", ""))
                quality_score = result_data.get("quality_score", 0.8)
            elif isinstance(result_data, str) and ("SELECT" in result_data.upper() or "WITH" in result_data.upper()):
                sql_query = result_data
                quality_score = 0.8
        
        # 调用实际存储服务
        try:
            from app.services.infrastructure.storage.sql_storage_service import sql_storage_service
            storage_result = await sql_storage_service.store_sql(
                task_id=task_context.task_id,
                sql_query=sql_query,
                quality_score=quality_score,
                user_id=task_context.user_id
            )
            storage_success = storage_result.get('success', False)
            storage_id = storage_result.get('storage_id')
        except Exception as e:
            logger.error(f"SQL存储失败: {e}")
            storage_success = False
            storage_id = None
        
        logger.info(f"SQL生成模式输出: SQL长度={len(sql_query)}, 质量分数={quality_score}")
        
        return {
            "task_id": task_context.task_id,
            "mode": "sql_only",
            "status": "success" if storage_success else "failed",
            "sql_generated": bool(sql_query),
            "sql_query": sql_query,
            "quality_score": quality_score,
            "storage_success": storage_success,
            "storage_id": storage_id,
            "execution_time": dag_result.get("execution_time", 0),
            "next_step": "manual_testing_required",
            "target_system": output_control.get("target_system", "storage")
        }
    
    async def _generate_chart_test_output(
        self, 
        dag_result: Dict[str, Any], 
        output_control: Dict[str, Any], 
        data_context: Dict[str, Any],
        task_context: AITaskContext
    ) -> Dict[str, Any]:
        """生成图表测试输出（前端预览模式）"""
        
        # 从数据上下文获取存储的SQL和测试数据
        stored_sql_id = data_context.get("stored_sql_id")
        test_data = data_context.get("test_data", {})
        
        # 从DAG结果中提取图表配置
        chart_config = {}
        chart_data = []
        
        if dag_result.get("result"):
            result_data = dag_result["result"]
            if isinstance(result_data, dict):
                chart_config = result_data.get("chart_config", result_data.get("echarts_config", {}))
                chart_data = result_data.get("chart_data", result_data.get("data", []))
        
        # 确保有图表配置
        if not chart_config:
            chart_config = {
                "title": {"text": "测试图表"},
                "xAxis": {"type": "category", "data": ["A", "B", "C"]},
                "yAxis": {"type": "value"},
                "series": [{"data": [120, 200, 150], "type": "bar"}]
            }
        
        logger.info(f"图表测试模式输出: 使用SQL={stored_sql_id}, 图表类型={chart_config.get('series', [{}])[0].get('type', 'unknown')}")
        
        return {
            "task_id": task_context.task_id,
            "mode": "chart_test",
            "status": "success",
            "sql_used": stored_sql_id,
            "chart_config": chart_config,
            "chart_data": chart_data,
            "test_data_applied": bool(test_data),
            "frontend_ready": True,
            "execution_time": dag_result.get("execution_time", 0),
            "target_system": output_control.get("target_system", "frontend")
        }
    
    async def _generate_sql_validation_output(
        self, 
        dag_result: Dict[str, Any], 
        output_control: Dict[str, Any], 
        data_context: Dict[str, Any],
        task_context: AITaskContext
    ) -> Dict[str, Any]:
        """生成SQL验证输出（时效性检查模式）"""
        
        # 调用实际验证服务
        try:
            from app.services.infrastructure.validation.sql_validation_service import sql_validation_service
            validation_result = await sql_validation_service.validate_sql(
                task_id=task_context.task_id,
                user_id=task_context.user_id
            )
        except Exception as e:
            logger.error(f"SQL验证失败: {e}")
            raise ValueError(f"SQL验证服务不可用: {str(e)}")
        
        logger.info(f"SQL验证模式输出: 任务={task_context.task_id}, 验证通过={validation_result['is_current']}")
        
        return {
            "task_id": task_context.task_id,
            "mode": "sql_validation",
            "status": "success",
            "validation_result": validation_result,
            "execution_time": dag_result.get("execution_time", 0),
            "target_system": output_control.get("target_system", "task_scheduler")
        }
    
    async def _generate_chart_etl_output(
        self, 
        dag_result: Dict[str, Any], 
        output_control: Dict[str, Any], 
        data_context: Dict[str, Any],
        task_context: AITaskContext
    ) -> Dict[str, Any]:
        """生成ETL图表输出（报告系统模式）"""
        
        # 调用实际ETL图表服务
        try:
            from app.services.domain.reporting.chart_integration_service import chart_integration_service
            chart_result = await chart_integration_service.generate_etl_chart(
                task_id=task_context.task_id,
                user_id=task_context.user_id,
                dag_result=dag_result
            )
            chart_config = chart_result.get('chart_config')
            if not chart_config:
                raise ValueError("ETL图表生成失败")
        except Exception as e:
            logger.error(f"ETL图表生成失败: {e}")
            raise ValueError(f"ETL图表服务不可用: {str(e)}")
        
        logger.info(f"ETL图表模式输出: 任务={task_context.task_id}, 图表配置已生成")
        
        return {
            "task_id": task_context.task_id,
            "mode": "chart_etl",
            "status": "success",
            "chart_config": chart_config,
            "chart_data": [],
            "etl_data_applied": True,
            "reporting_ready": True,
            "execution_time": dag_result.get("execution_time", 0),
            "target_system": output_control.get("target_system", "reporting")
        }