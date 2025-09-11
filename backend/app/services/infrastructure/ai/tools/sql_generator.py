"""
优化的SQL生成器 v3.0 - 适配新的BaseTool架构
===============================================

基于增强的工具架构和提示词系统：
- 完全集成新的BaseTool和ToolContext
- 使用企业级提示词管理系统
- 支持迭代执行和智能重试
- 集成提示词监控和性能分析
"""

import json
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from ..core.tools import IterativeTool, ToolContext, ToolResult, ToolResultType, ToolPriority
from ..core.prompts import (
    get_sql_reasoning_prompt,
    get_sql_generation_prompt, 
    get_sql_reflection_prompt,
    PromptComplexity
)
from ..core.prompt_monitor import get_prompt_monitor

logger = logging.getLogger(__name__)


class AdvancedSQLGenerator(IterativeTool):
    """高级SQL生成器 - 适配新架构v3.0"""
    
    def __init__(self):
        super().__init__(
            tool_name="advanced_sql_generator",
            tool_category="sql_generation",
            priority=ToolPriority.HIGH,
            max_retries=3,
            timeout=300
        )
        self.max_iterations = 5
        self.monitor = get_prompt_monitor()
        
    async def execute_single_iteration(
        self,
        input_data: Dict[str, Any],
        context: ToolContext,
        iteration: int
    ) -> AsyncGenerator[ToolResult, None]:
        """执行单次SQL生成迭代 - 新架构版本"""
        
        # 提取参数
        placeholders = input_data.get("placeholders", [])
        if not placeholders:
            yield self.create_error_result("未提供占位符信息")
            return
            
        first_placeholder = placeholders[0]
        placeholder_name = first_placeholder.get("name", "")
        placeholder_text = first_placeholder.get("text", "")
        
        # 获取数据源信息
        data_source_info = input_data.get("data_source_info") or context.data_source_info or {}
        available_tables = data_source_info.get("tables", [])
        table_details = data_source_info.get("table_details", [])
        
        if not available_tables:
            yield self.create_error_result("缺少可用表信息")
            return
        
        yield self.create_progress_result(
            f"🧠 第{iteration + 1}轮: 推理阶段",
            step="reasoning",
            percentage=25 * iteration / self.max_iterations
        )
        
        execution_start = datetime.utcnow()
        
        try:
            # 阶段1: 推理 - 使用提示词系统
            reasoning_result = await self._reasoning_phase_enhanced(
                context, iteration, placeholder_name, placeholder_text,
                available_tables, table_details
            )
            
            if not reasoning_result:
                yield self.create_error_result("推理阶段失败")
                return
            
            yield self.create_progress_result(
                f"✅ 推理完成: 选择表 '{reasoning_result.get('selected_table')}'",
                step="reasoning_complete",
                percentage=25 * (iteration + 0.33) / self.max_iterations,
                insights=[f"选择表: {reasoning_result.get('selected_table')}"]
            )
            
            # 阶段2: SQL生成
            yield self.create_progress_result(
                f"💽 第{iteration + 1}轮: SQL生成阶段",
                step="generation",
                percentage=25 * (iteration + 0.66) / self.max_iterations
            )
            
            sql_result = await self._generation_phase_enhanced(
                context, reasoning_result, placeholder_name, placeholder_text
            )
            
            if not sql_result:
                yield self.create_error_result("SQL生成阶段失败")
                return
            
            # 阶段3: 验证
            yield self.create_progress_result(
                f"🔍 第{iteration + 1}轮: 验证阶段",
                step="validation",
                percentage=25 * (iteration + 1) / self.max_iterations
            )
            
            validation_result = await self._validation_phase_enhanced(
                sql_result, reasoning_result, available_tables, table_details
            )
            
            # 记录成功的提示词使用
            execution_time = (datetime.utcnow() - execution_start).total_seconds() * 1000
            self.monitor.record_usage(
                category="sql_generation",
                prompt_type="complete_iteration", 
                complexity=self._get_prompt_complexity(context).value,
                success=validation_result.get('validation_passed', False),
                execution_time_ms=execution_time,
                prompt_length=len(placeholder_text),
                user_id=context.user_id,
                iterations=iteration + 1
            )
            
            if validation_result.get('validation_passed', False):
                # 成功生成SQL
                confidence = min(
                    reasoning_result.get('confidence', 0.7),
                    validation_result.get('confidence', 0.7)
                )
                
                insights = [
                    f"第{iteration + 1}轮成功生成SQL",
                    f"使用表: {reasoning_result.get('selected_table')}",
                    f"置信度: {confidence:.2f}"
                ]
                
                # 添加学习洞察
                context.add_insight(f"成功策略: {reasoning_result.get('query_strategy')}")
                
                yield self.create_success_result(
                    data={
                        "generated_sql": sql_result,
                        "reasoning_result": reasoning_result,
                        "validation_result": validation_result,
                        "iteration": iteration + 1,
                        "placeholder_name": placeholder_name,
                        "table_used": reasoning_result.get('selected_table')
                    },
                    confidence=confidence,
                    insights=insights,
                    optimization_suggestions=[
                        "SQL生成成功，建议缓存此类模式"
                    ]
                )
                return
            else:
                # 验证失败，记录错误并准备下一轮
                errors = validation_result.get('errors', [])
                for error in errors:
                    context.add_error("validation_error", error)
                
                yield self.create_error_result(
                    f"第{iteration + 1}轮验证失败: {'; '.join(errors[:2])}",
                    recoverable=True,
                    recovery_suggestions=[
                        "将在下一轮尝试不同的表或字段组合",
                        "基于验证错误调整生成策略"
                    ]
                )
                
        except Exception as e:
            execution_time = (datetime.utcnow() - execution_start).total_seconds() * 1000
            self.monitor.record_usage(
                category="sql_generation",
                prompt_type="complete_iteration",
                complexity=self._get_prompt_complexity(context).value,
                success=False,
                execution_time_ms=execution_time,
                prompt_length=len(placeholder_text),
                error_message=str(e),
                user_id=context.user_id,
                iterations=iteration + 1
            )
            
            yield self.create_error_result(
                f"第{iteration + 1}轮执行异常: {str(e)}",
                recoverable=True
            )
    
    async def _reasoning_phase_enhanced(
        self,
        context: ToolContext,
        iteration: int,
        placeholder_name: str,
        placeholder_text: str,
        available_tables: List[str],
        table_details: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """增强的推理阶段"""
        
        try:
            # 获取优化的提示词
            complexity = self._get_prompt_complexity(context)
            
            reasoning_prompt = get_sql_reasoning_prompt(
                placeholder_name=placeholder_name,
                placeholder_analysis=placeholder_text,
                available_tables=available_tables,
                table_details=table_details,
                learned_insights=context.learned_insights[-5:],
                iteration_history=context.iteration_history[-3:],
                iteration=iteration,
                complexity=complexity
            )
            
            # 调用LLM
            from ..llm import ask_agent_for_user
            
            reasoning_response = await ask_agent_for_user(
                user_id=context.user_id,
                question=reasoning_prompt,
                agent_type="sql_analyst",
                task_type="sql_reasoning"
            )
            
            # 解析结果
            return self._parse_json_response(reasoning_response, [
                'reasoning_process', 'selected_table', 'relevant_fields',
                'query_strategy', 'confidence'
            ])
            
        except Exception as e:
            self.logger.error(f"推理阶段异常: {e}")
            return None
    
    async def _generation_phase_enhanced(
        self,
        context: ToolContext,
        reasoning_result: Dict[str, Any],
        placeholder_name: str,
        placeholder_text: str
    ) -> Optional[str]:
        """增强的SQL生成阶段"""
        
        try:
            generation_prompt = get_sql_generation_prompt(
                selected_table=reasoning_result.get('selected_table', ''),
                relevant_fields=reasoning_result.get('relevant_fields', []),
                query_strategy=reasoning_result.get('query_strategy', ''),
                field_mappings=reasoning_result.get('field_mappings', {}),
                placeholder_name=placeholder_name,
                placeholder_analysis=placeholder_text,
                learned_insights=context.learned_insights[-3:],
                complexity=self._get_prompt_complexity(context)
            )
            
            from ..llm import ask_agent_for_user
            
            sql_response = await ask_agent_for_user(
                user_id=context.user_id,
                question=generation_prompt,
                agent_type="sql_generator",
                task_type="sql_generation"
            )
            
            # 清理SQL响应
            sql = self._clean_sql_response(sql_response)
            return sql
            
        except Exception as e:
            self.logger.error(f"SQL生成阶段异常: {e}")
            return None
    
    async def _validation_phase_enhanced(
        self,
        sql: str,
        reasoning_result: Dict[str, Any],
        available_tables: List[str],
        table_details: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """增强的验证阶段"""
        
        errors = []
        warnings = []
        confidence = 1.0
        
        try:
            # 基础SQL验证
            if not sql or not sql.strip():
                return {
                    'validation_passed': False,
                    'errors': ['SQL为空'],
                    'confidence': 0.0
                }
            
            sql_upper = sql.upper()
            
            # 检查SELECT语句
            if 'SELECT' not in sql_upper:
                errors.append("SQL不包含SELECT语句")
                confidence *= 0.1
            
            # 检查表名
            selected_table = reasoning_result.get('selected_table', '')
            if selected_table and selected_table not in available_tables:
                errors.append(f"表 '{selected_table}' 不在可用表列表中")
                confidence *= 0.2
            
            if selected_table and selected_table not in sql:
                errors.append(f"SQL中未使用推理选择的表 '{selected_table}'")
                confidence *= 0.5
            
            # 检查危险操作
            dangerous_ops = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'UPDATE']
            for op in dangerous_ops:
                if op in sql_upper:
                    errors.append(f"SQL包含危险操作: {op}")
                    confidence *= 0.1
            
            # 检查字段使用
            relevant_fields = reasoning_result.get('relevant_fields', [])
            if relevant_fields:
                used_fields = sum(1 for field in relevant_fields if field in sql)
                if used_fields == 0:
                    warnings.append("SQL中未使用推理阶段选择的字段")
                    confidence *= 0.8
            
            return {
                'validation_passed': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'confidence': max(0.0, confidence)
            }
            
        except Exception as e:
            return {
                'validation_passed': False,
                'errors': [f"验证过程异常: {str(e)}"],
                'confidence': 0.0
            }
    
    def _get_prompt_complexity(self, context: ToolContext) -> PromptComplexity:
        """获取提示词复杂度"""
        # 基于错误历史和上下文复杂度评估
        error_count = len(context.error_history)
        if error_count >= 3:
            return PromptComplexity.CRITICAL
        elif error_count >= 1:
            return PromptComplexity.HIGH
        elif context.data_source_info and len(context.data_source_info.get("tables", [])) > 20:
            return PromptComplexity.HIGH
        else:
            return PromptComplexity.MEDIUM
    
    def _parse_json_response(self, response: str, required_fields: List[str]) -> Optional[Dict[str, Any]]:
        """解析JSON响应"""
        try:
            # 清理响应
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                response = '\n'.join(lines)
            
            # 提取JSON
            start = response.find('{')
            end = response.rfind('}')
            
            if start >= 0 and end >= 0 and start <= end:
                json_str = response[start:end+1]
                result = json.loads(json_str)
                
                # 验证必需字段
                for field in required_fields:
                    if field not in result:
                        self.logger.warning(f"响应缺少字段: {field}")
                
                return result
            
            return None
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            self.logger.error(f"响应解析异常: {e}")
            return None
    
    def _clean_sql_response(self, response: str) -> Optional[str]:
        """清理SQL响应"""
        try:
            response = response.strip()
            
            # 移除markdown标记
            if response.startswith('```'):
                lines = response.split('\n')
                if lines[0].startswith('```'):
                    lines = lines[1:]
                if lines and lines[-1].strip() == '```':
                    lines = lines[:-1]
                response = '\n'.join(lines)
            
            response = response.strip()
            
            # 查找SELECT语句
            if '\n' in response:
                for line in response.split('\n'):
                    line = line.strip()
                    if line.upper().startswith('SELECT'):
                        return line
            
            if response.upper().startswith('SELECT'):
                return response
            
            return None
            
        except Exception as e:
            self.logger.error(f"SQL清理异常: {e}")
            return None
    
    async def _validate_specific_input(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """验证输入数据"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "suggestions": []
        }
        
        # 检查占位符
        placeholders = input_data.get("placeholders", [])
        if not placeholders:
            validation_result["valid"] = False
            validation_result["errors"].append("缺少占位符信息")
            return validation_result
        
        first_placeholder = placeholders[0]
        if not first_placeholder.get("name"):
            validation_result["valid"] = False
            validation_result["errors"].append("占位符缺少名称")
        
        if not first_placeholder.get("text"):
            validation_result["valid"] = False
            validation_result["errors"].append("占位符缺少文本描述")
        
        # 检查数据源信息
        data_source_info = input_data.get("data_source_info")
        if not data_source_info:
            validation_result["warnings"].append("未提供数据源信息")
        elif not data_source_info.get("tables"):
            validation_result["warnings"].append("数据源信息中缺少表列表")
        
        return validation_result


# 保持向后兼容的别名
SQLGenerationTool = AdvancedSQLGenerator