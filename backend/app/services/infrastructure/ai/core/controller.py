"""
Agent Controller - 核心编排器
借鉴 Claude Code 的 tt 函数思想
"""

import logging
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from datetime import datetime

from .messages import AgentMessage, MessageType
from .tasks import AgentTask, TaskType
from .tools import ToolChain, ToolContext, ToolResult, ToolResultType
from .context import ContextManager
from .time_context import TimeContextManager, create_task_time_context, format_time_context_for_ai

logger = logging.getLogger(__name__)


class AgentController:
    """
    统一的任务编排器，类似 Claude Code 的 tt 函数
    负责任务分解、工具调度、结果聚合
    """
    
    def __init__(self):
        self.tool_chain = ToolChain()
        self.context_manager = ContextManager()
        self.time_context_manager = TimeContextManager()
        self.active_tasks: Dict[str, AgentTask] = {}
        
    def register_tool(self, tool):
        """注册工具到工具链"""
        self.tool_chain.register_tool(tool)
        
    async def execute_task(
        self, 
        task: AgentTask
    ) -> AsyncGenerator[AgentMessage, None]:
        """
        核心执行函数 - 类似 Claude Code 的 tt
        
        执行流程：
        1. 任务分析与分解
        2. 上下文初始化
        3. 工具链编排
        4. 流式执行与进度反馈
        5. 结果聚合与返回
        """
        
        self.active_tasks[task.task_id] = task
        
        try:
            # 1. 任务开始消息
            yield AgentMessage.create_progress(
                current_step="任务开始",
                user_id=task.user_id,
                task_id=task.task_id,
                details=f"开始执行任务: {task.type.value}"
            )
            
            # 2. 初始化上下文
            yield AgentMessage.create_progress(
                current_step="初始化上下文",
                user_id=task.user_id,
                task_id=task.task_id
            )
            
            await self._initialize_context(task)
            
            # 3. 根据任务类型选择执行策略
            if task.type == TaskType.TEMPLATE_ANALYSIS:
                async for message in self._execute_template_analysis(task):
                    yield message
                    
            elif task.type == TaskType.PLACEHOLDER_ANALYSIS:
                async for message in self._execute_placeholder_analysis(task):
                    yield message
                    
            elif task.type == TaskType.SQL_GENERATION:
                async for message in self._execute_sql_generation(task):
                    yield message
                    
            elif task.type == TaskType.FULL_WORKFLOW:
                async for message in self._execute_full_workflow(task):
                    yield message
                    
            else:
                yield AgentMessage.create_error(
                    error_type="unsupported_task_type",
                    error_message=f"不支持的任务类型: {task.type.value}",
                    user_id=task.user_id,
                    task_id=task.task_id
                )
                return
            
            # 4. 任务完成消息
            yield AgentMessage.create_progress(
                current_step="任务完成",
                user_id=task.user_id,
                task_id=task.task_id,
                percentage=100.0
            )
            
        except Exception as e:
            logger.error(f"任务执行失败: {task.task_id} - {e}")
            yield AgentMessage.create_error(
                error_type="task_execution_error",
                error_message=str(e),
                user_id=task.user_id,
                task_id=task.task_id,
                stacktrace=str(e)
            )
        finally:
            # 清理任务
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
    
    async def _initialize_context(self, task: AgentTask):
        """初始化任务上下文"""
        template_id = task.get_template_id()
        data_source_id = task.get_data_source_id()
        
        if template_id and data_source_id:
            await self.context_manager.initialize(
                task_id=task.task_id,
                user_id=task.user_id,
                template_id=template_id,
                data_source_id=data_source_id
            )
    
    async def _execute_template_analysis(
        self, 
        task: AgentTask
    ) -> AsyncGenerator[AgentMessage, None]:
        """执行模板分析任务"""
        
        yield AgentMessage.create_progress(
            current_step="模板分析",
            user_id=task.user_id,
            task_id=task.task_id,
            current_step_number=1,
            total_steps=3
        )
        
        # 准备工具上下文
        tool_context = ToolContext(
            user_id=task.user_id,
            task_id=task.task_id,
            session_id=self.context_manager.execution_context.session_id if self.context_manager.execution_context else "unknown",
            context_data=self.context_manager.get_context_for_agent("template_analyzer"),
            tool_config=task.config
        )
        
        # 执行模板分析工具
        async for tool_result in self.tool_chain.execute_tool(
            "template_analysis_tool",
            task.data,
            tool_context
        ):
            if tool_result.type == ToolResultType.PROGRESS:
                yield AgentMessage.create_progress(
                    current_step=f"模板分析: {tool_result.data}",
                    user_id=task.user_id,
                    task_id=task.task_id,
                    tool_name="template_analysis_tool"
                )
            elif tool_result.type == ToolResultType.RESULT:
                yield AgentMessage.create_result(
                    content=tool_result.data,
                    user_id=task.user_id,
                    task_id=task.task_id,
                    tool_name="template_analysis_tool"
                )
            elif tool_result.type == ToolResultType.ERROR:
                yield AgentMessage.create_error(
                    error_type=tool_result.error_info.get("error_type", "tool_error"),
                    error_message=tool_result.error_info.get("error_message", "工具执行失败"),
                    user_id=task.user_id,
                    task_id=task.task_id,
                    tool_name="template_analysis_tool"
                )
    
    async def _execute_placeholder_analysis(
        self, 
        task: AgentTask
    ) -> AsyncGenerator[AgentMessage, None]:
        """执行单个占位符分析"""
        
        yield AgentMessage.create_progress(
            current_step="占位符分析开始",
            user_id=task.user_id,
            task_id=task.task_id,
            tool_name="placeholder_analysis"
        )
        
        # 构建工具上下文
        tool_context = ToolContext(
            user_id=task.user_id,
            task_id=task.task_id,
            session_id=f"session_{task.task_id}",
            context_data={}
        )
        
        # 准备占位符分析数据
        placeholder_data = {
            "placeholder_name": task.data.get("placeholder_name"),
            "placeholder_text": task.data.get("placeholder_text"),
            "template_id": task.data.get("template_id"),
            "template_context": task.data.get("template_context", ""),
            "data_source_info": task.data.get("data_source_info", {}),
            "task_params": task.data.get("task_params", {})
        }
        
        # 构建任务时间上下文
        cron_expression = task.data.get("cron_expression")
        execution_time = task.data.get("execution_time")
        time_context = create_task_time_context(cron_expression, execution_time, "scheduled")
        time_context_str = format_time_context_for_ai(time_context)
        
        # 获取时间占位符建议
        time_suggestions = self.time_context_manager.suggest_time_placeholders(time_context)
        
        # 使用LLM分析占位符
        from ..llm import ask_agent_for_user
        
        try:
            # 分析占位符用途
            analysis_prompt = f"""
            请分析占位符 '{placeholder_data['placeholder_name']}' 并确定其数据需求。
            
            {time_context_str}
            
            占位符信息：
            - 名称: {placeholder_data['placeholder_name']}
            - 格式: {placeholder_data['placeholder_text']}
            - 模板上下文: {placeholder_data['template_context'][:300] if placeholder_data['template_context'] else '无特定上下文'}
            
            数据源信息: {placeholder_data['data_source_info'].get('type', '未知')} - {placeholder_data['data_source_info'].get('database', '未知')}
            
            时间占位符建议：
            {chr(10).join([f"- {k}: {v}" for k, v in time_suggestions.items() if v])}
            
            请基于任务执行时间和周期性，分析这个占位符需要什么类型的数据，以及合适的时间范围。
            """
            
            yield AgentMessage.create_progress(
                current_step="分析占位符用途",
                user_id=task.user_id,
                task_id=task.task_id,
                tool_name="placeholder_analysis"
            )
            
            analysis_response = await ask_agent_for_user(
                user_id=task.user_id,
                question=analysis_prompt,
                agent_type="placeholder_analysis",
                task_type="placeholder_analysis",
                complexity="medium"
            )
            
            # 生成SQL - 智能推断参数而非硬编码
            task_params = placeholder_data.get("task_params", {})
            
            # 从模板上下文中智能提取相关信息
            template_context = placeholder_data.get('template_context', '')
            placeholder_name = placeholder_data['placeholder_name']
            placeholder_text = placeholder_data['placeholder_text']
            
            # 构建上下文信息字符串，避免硬编码默认值
            context_info = []
            if task_params.get("report_year"):
                context_info.append(f"报告年份: {task_params['report_year']}")
            if task_params.get("region_name"):
                context_info.append(f"地区名称: {task_params['region_name']}")
            
            context_str = "\n".join(context_info) if context_info else "无特定参数约束"
            
            # 生成数据时间范围的SQL条件
            time_sql_condition = self.time_context_manager.get_data_range_sql_conditions(time_context)
            
            sql_prompt = f"""
            请为占位符 '{placeholder_name}' 生成SQL查询语句。
            
            {time_context_str}
            
            占位符信息:
            - 名称: {placeholder_name}
            - 格式: {placeholder_text}
            - 分析结果: {analysis_response}
            
            数据源信息:
            - 类型: {placeholder_data['data_source_info'].get('type', '未知')}
            - 数据库: {placeholder_data['data_source_info'].get('database', '未知')}
            
            模板上下文: {template_context[:500] if template_context else '无特定上下文'}
            
            任务参数: {context_str}
            
            建议的时间范围条件: {time_sql_condition}
            
            时间占位符建议：
            {chr(10).join([f"- {k}: {v}" for k, v in time_suggestions.items() if v])}
            
            请生成一个合适的SQL查询，要求：
            1. 语法正确，适合 {placeholder_data['data_source_info'].get('type', 'MySQL')} 数据库
            2. 基于占位符名称和模板上下文推断实际的业务需求
            3. 使用合理的表名和字段名（基于业务语义）
            4. 包含适当的数据聚合或统计
            5. 根据任务执行时间和周期，使用合适的时间范围条件
            6. 优先使用建议的时间范围条件，适配到实际的日期字段名
            7. 避免使用不相关的硬编码值，时间相关的值应基于任务执行上下文
            8. 如果是周期性任务，考虑同比、环比等时间维度分析
            
            只返回SQL语句，不需要其他解释：
            """
            
            yield AgentMessage.create_progress(
                current_step="生成SQL查询",
                user_id=task.user_id,
                task_id=task.task_id,
                tool_name="placeholder_analysis"
            )
            
            sql_response = await ask_agent_for_user(
                user_id=task.user_id,
                question=sql_prompt,
                agent_type="sql_generation",
                task_type="sql_query_generation",
                complexity="medium"
            )
            
            # 清理SQL语句
            sql = sql_response.strip()
            if sql.startswith("```sql"):
                sql = sql[6:]
            if sql.startswith("```"):
                sql = sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
            sql = sql.strip()
            
            # 构建结果
            result = {
                "placeholder_name": placeholder_data["placeholder_name"],
                "placeholder_text": placeholder_data["placeholder_text"],
                "analysis": analysis_response,
                "description": analysis_response,
                "generated_sql": sql,
                "data_source_info": placeholder_data["data_source_info"],
                "confidence_score": 0.8 if sql else 0.3,
                "sql_validated": bool(sql and len(sql) > 10),
                "analyzed_at": datetime.now().isoformat()
            }
            
            yield AgentMessage.create_result(
                content=result,
                user_id=task.user_id,
                task_id=task.task_id,
                tool_name="placeholder_analysis"
            )
            
        except Exception as e:
            yield AgentMessage.create_error(
                error_type="placeholder_analysis_error",
                error_message=f"占位符分析失败: {str(e)}",
                user_id=task.user_id,
                task_id=task.task_id,
                tool_name="placeholder_analysis"
            )
    
    async def _execute_sql_generation(
        self, 
        task: AgentTask
    ) -> AsyncGenerator[AgentMessage, None]:
        """执行SQL生成任务"""
        
        yield AgentMessage.create_progress(
            current_step="SQL生成",
            user_id=task.user_id,
            task_id=task.task_id
        )
        
        tool_context = ToolContext(
            user_id=task.user_id,
            task_id=task.task_id,
            session_id=self.context_manager.execution_context.session_id if self.context_manager.execution_context else "unknown",
            context_data=self.context_manager.get_context_for_agent("sql_generator"),
            tool_config=task.config
        )
        
        async for tool_result in self.tool_chain.execute_tool(
            "sql_generation_tool",
            task.data,
            tool_context
        ):
            if tool_result.type == ToolResultType.PROGRESS:
                yield AgentMessage.create_progress(
                    current_step=f"SQL生成: {tool_result.data}",
                    user_id=task.user_id,
                    task_id=task.task_id,
                    tool_name="sql_generation_tool"
                )
            elif tool_result.type == ToolResultType.RESULT:
                yield AgentMessage.create_result(
                    content=tool_result.data,
                    user_id=task.user_id,
                    task_id=task.task_id,
                    tool_name="sql_generation_tool"
                )
    
    async def _execute_full_workflow(
        self, 
        task: AgentTask
    ) -> AsyncGenerator[AgentMessage, None]:
        """执行完整工作流"""
        
        total_steps = 4
        current_step = 0
        
        # Step 1: 模板分析
        current_step += 1
        yield AgentMessage.create_progress(
            current_step="完整工作流: 模板分析",
            user_id=task.user_id,
            task_id=task.task_id,
            current_step_number=current_step,
            total_steps=total_steps,
            percentage=(current_step / total_steps) * 100
        )
        
        # 创建子任务用于模板分析
        analysis_task = AgentTask(
            type=TaskType.TEMPLATE_ANALYSIS,
            task_id=f"{task.task_id}_analysis",
            user_id=task.user_id,
            data=task.data
        )
        
        analysis_result = None
        async for message in self._execute_template_analysis(analysis_task):
            if message.type == MessageType.RESULT:
                analysis_result = message.content
            # 转发进度消息
            yield message
        
        if not analysis_result:
            yield AgentMessage.create_error(
                error_type="workflow_error",
                error_message="模板分析失败",
                user_id=task.user_id,
                task_id=task.task_id
            )
            return
        
        # Step 2: SQL生成
        current_step += 1
        yield AgentMessage.create_progress(
            current_step="完整工作流: SQL生成",
            user_id=task.user_id,
            task_id=task.task_id,
            current_step_number=current_step,
            total_steps=total_steps,
            percentage=(current_step / total_steps) * 100
        )
        
        # 基于分析结果生成SQL
        sql_task_data = {**task.data}
        if analysis_result and "placeholder_analysis" in analysis_result:
            sql_task_data["placeholders"] = analysis_result["placeholder_analysis"]["placeholders"]
        
        sql_task = AgentTask(
            type=TaskType.SQL_GENERATION,
            task_id=f"{task.task_id}_sql",
            user_id=task.user_id,
            data=sql_task_data
        )
        
        async for message in self._execute_sql_generation(sql_task):
            # 转发消息
            yield message
        
        # Step 3: 数据执行（这里暂时跳过）
        current_step += 1
        yield AgentMessage.create_progress(
            current_step="完整工作流: 数据执行",
            user_id=task.user_id,
            task_id=task.task_id,
            current_step_number=current_step,
            total_steps=total_steps,
            percentage=(current_step / total_steps) * 100
        )
        
        # Step 4: 报告生成（这里暂时跳过）
        current_step += 1
        yield AgentMessage.create_progress(
            current_step="完整工作流: 报告生成",
            user_id=task.user_id,
            task_id=task.task_id,
            current_step_number=current_step,
            total_steps=total_steps,
            percentage=100.0
        )
        
        # 返回最终结果
        yield AgentMessage.create_result(
            content={
                "workflow_status": "completed",
                "analysis_result": analysis_result,
                "steps_completed": current_step,
                "total_steps": total_steps
            },
            user_id=task.user_id,
            task_id=task.task_id
        )
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.active_tasks:
            return None
            
        task = self.active_tasks[task_id]
        progress = self.context_manager.get_progress_summary() if self.context_manager else {}
        
        return {
            "task_id": task_id,
            "task_type": task.type.value,
            "status": "running",
            "progress": progress,
            "created_at": task.created_at,
            "user_id": task.user_id
        }
    
    def list_active_tasks(self) -> List[str]:
        """列出所有活跃任务"""
        return list(self.active_tasks.keys())
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.active_tasks:
            # 这里应该实现任务取消逻辑
            del self.active_tasks[task_id]
            logger.info(f"任务已取消: {task_id}")
            return True
        return False