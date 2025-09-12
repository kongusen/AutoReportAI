"""
占位符验证和修复服务

负责处理过期的或空置的占位符，包括：
1. SQL验证和测试
2. SQL修复和优化
3. 时间上下文相关的动态修复
4. 与统一AI门面的集成
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from app.utils.time_context import TimeContextManager

logger = logging.getLogger(__name__)


@dataclass
class PlaceholderValidationResult:
    """占位符验证结果"""
    placeholder_name: str
    is_valid: bool
    sql_content: str
    validation_error: Optional[str] = None
    repair_suggestions: List[str] = None
    confidence_score: float = 0.0
    test_result: Optional[Dict[str, Any]] = None
    repaired_sql: Optional[str] = None
    repair_applied: bool = False


@dataclass
class SQLRepairContext:
    """SQL修复上下文"""
    original_sql: str
    error_message: str
    placeholder_name: str
    data_source_info: Dict[str, Any]
    time_context: Optional[Dict[str, Any]] = None
    repair_attempts: int = 0
    max_attempts: int = 3


class PlaceholderValidationService:
    """
    占位符验证和修复服务
    
    基于DDD Domain层的业务服务，专注于占位符相关的业务逻辑：
    1. 占位符SQL的验证和测试
    2. 基于错误信息的自动修复
    3. 时间上下文感知的动态调整
    4. 与统一AI门面的集成
    """
    
    def __init__(self, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for PlaceholderValidationService")
        self.user_id = user_id
        self.max_retry_attempts = 3
        self.validation_timeout = 30  # 秒
        self.time_context_manager = TimeContextManager()
        
    async def validate_and_repair_placeholders(
        self,
        template_id: str,
        placeholders: List[Dict[str, Any]],
        data_source_info: Dict[str, Any],
        time_context: Optional[Dict[str, Any]] = None
    ) -> List[PlaceholderValidationResult]:
        """
        验证并修复占位符列表
        
        Args:
            template_id: 模板ID
            placeholders: 占位符列表
            data_source_info: 数据源信息
            time_context: 时间上下文（包含cron表达式、执行时间等）
            
        Returns:
            验证结果列表
        """
        logger.info(f"开始验证和修复占位符: template_id={template_id}, count={len(placeholders)}")
        
        validation_results = []
        
        # 并发验证所有占位符
        validation_tasks = []
        for placeholder in placeholders:
            task = self._validate_single_placeholder(
                placeholder=placeholder,
                data_source_info=data_source_info,
                time_context=time_context
            )
            validation_tasks.append(task)
        
        # 等待所有验证任务完成
        results = await asyncio.gather(*validation_tasks, return_exceptions=True)
        
        # 处理验证结果
        for placeholder, result in zip(placeholders, results):
            if isinstance(result, Exception):
                validation_results.append(PlaceholderValidationResult(
                    placeholder_name=placeholder.get('name', '未知占位符'),
                    is_valid=False,
                    sql_content=placeholder.get('generated_sql', ''),
                    validation_error=f"验证异常: {str(result)}",
                    confidence_score=0.0
                ))
            else:
                validation_results.append(result)
        
        logger.info(f"占位符验证完成: 总计={len(validation_results)}, "
                   f"有效={len([r for r in validation_results if r.is_valid])}, "
                   f"修复={len([r for r in validation_results if r.repair_applied])}")
        
        return validation_results
    
    async def _validate_single_placeholder(
        self,
        placeholder: Dict[str, Any],
        data_source_info: Dict[str, Any],
        time_context: Optional[Dict[str, Any]] = None
    ) -> PlaceholderValidationResult:
        """验证单个占位符"""
        placeholder_name = placeholder.get('name') or placeholder.get('placeholder_name', '未知占位符')
        sql_content = placeholder.get('generated_sql', '')
        
        logger.debug(f"验证占位符: {placeholder_name}")
        
        # 初始验证结果
        result = PlaceholderValidationResult(
            placeholder_name=placeholder_name,
            is_valid=False,
            sql_content=sql_content
        )
        
        # 1. 基本SQL检查
        if not sql_content or sql_content.strip() == '':
            result.validation_error = "SQL内容为空"
            result.repair_suggestions = ["重新生成SQL"]
            return await self._attempt_sql_repair(result, placeholder, data_source_info, time_context)
        
        # 2. 检查是否包含未替换的占位符
        if '{{' in sql_content and '}}' in sql_content:
            result.validation_error = "SQL包含未替换的占位符"
            result.repair_suggestions = ["替换占位符为具体值"]
            return await self._attempt_sql_repair(result, placeholder, data_source_info, time_context)
        
        # 3. 数据库连接测试
        try:
            test_result = await self._test_sql_execution(sql_content, data_source_info)
            result.test_result = test_result
            
            if test_result.get('success', False):
                result.is_valid = True
                result.confidence_score = 0.9
                logger.debug(f"占位符 {placeholder_name} 验证成功")
                return result
            else:
                result.validation_error = test_result.get('error', '未知SQL执行错误')
                result.repair_suggestions = self._analyze_sql_error(test_result.get('error', ''))
                return await self._attempt_sql_repair(result, placeholder, data_source_info, time_context)
                
        except Exception as e:
            result.validation_error = f"SQL测试异常: {str(e)}"
            result.repair_suggestions = ["检查数据源连接", "重新生成SQL"]
            return await self._attempt_sql_repair(result, placeholder, data_source_info, time_context)
    
    async def _test_sql_execution(
        self,
        sql_content: str,
        data_source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """测试SQL执行"""
        try:
            # 根据数据源类型选择连接器
            source_type = data_source_info.get('type', 'unknown')
            
            if source_type == 'doris':
                return await self._test_doris_sql(sql_content, data_source_info)
            else:
                return {
                    "success": False,
                    "error": f"不支持的数据源类型: {source_type}",
                    "data": [],
                    "row_count": 0
                }
                
        except Exception as e:
            logger.error(f"SQL测试异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "row_count": 0
            }
    
    async def _test_doris_sql(
        self,
        sql_content: str,
        data_source_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """测试Doris SQL执行"""
        try:
            from app.services.data.connectors.doris_connector import DorisConnector, DorisConfig
            from app.core.data_source_utils import DataSourcePasswordManager
            
            # 从data_source_info构建DorisConfig
            config = DorisConfig(
                source_type='doris',
                name=data_source_info.get('name', 'test_source'),
                description='SQL验证测试',
                fe_hosts=data_source_info.get('fe_hosts', ['localhost']),
                mysql_host=data_source_info.get('mysql_host', 'localhost'),
                mysql_port=data_source_info.get('mysql_port', 9030),
                query_port=data_source_info.get('query_port', 9030),
                username=data_source_info.get('username', 'root'),
                password=DataSourcePasswordManager.get_password(
                    data_source_info.get('password', '')
                ),
                database=data_source_info.get('database', 'default'),
                mysql_username=data_source_info.get('username', 'root'),
                mysql_password=DataSourcePasswordManager.get_password(
                    data_source_info.get('password', '')
                ),
                mysql_database=data_source_info.get('database', 'default'),
                use_mysql_protocol=False
            )
            
            connector = DorisConnector(config=config)
            
            try:
                # 为了验证，我们添加LIMIT限制
                test_sql = sql_content.strip()
                if test_sql.upper().startswith('SELECT') and 'LIMIT' not in test_sql.upper():
                    test_sql = f"SELECT * FROM ({test_sql}) AS validation_query LIMIT 1"
                
                result = await connector.execute_query(test_sql)
                
                if hasattr(result, 'to_dict'):
                    return result.to_dict()
                else:
                    return {
                        "success": True,
                        "data": getattr(result, 'data', []),
                        "columns": getattr(result, 'columns', []),
                        "row_count": getattr(result, 'row_count', 0)
                    }
                    
            finally:
                if hasattr(connector, 'close'):
                    await connector.close()
                    
        except Exception as e:
            logger.error(f"Doris SQL测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "data": [],
                "row_count": 0
            }
    
    def _analyze_sql_error(self, error_message: str) -> List[str]:
        """分析SQL错误并提供修复建议"""
        suggestions = []
        error_lower = error_message.lower()
        
        if 'table' in error_lower and 'not found' in error_lower:
            suggestions.extend([
                "检查表名是否正确",
                "确认表存在于指定数据库中",
                "检查数据库连接权限"
            ])
        elif 'column' in error_lower and ('not found' in error_lower or 'unknown' in error_lower):
            suggestions.extend([
                "检查列名是否正确",
                "确认列存在于表中",
                "检查列名拼写和大小写"
            ])
        elif 'syntax error' in error_lower or 'sql syntax' in error_lower:
            suggestions.extend([
                "检查SQL语法",
                "验证关键字使用",
                "检查括号匹配"
            ])
        elif 'permission' in error_lower or 'access' in error_lower:
            suggestions.extend([
                "检查数据库访问权限",
                "确认用户有查询权限",
                "验证数据源配置"
            ])
        elif 'timeout' in error_lower:
            suggestions.extend([
                "优化查询性能",
                "添加合适的WHERE条件",
                "考虑添加索引"
            ])
        else:
            suggestions.extend([
                "检查SQL语句完整性",
                "验证数据源连接",
                "重新生成SQL"
            ])
        
        return suggestions
    
    async def _attempt_sql_repair(
        self,
        validation_result: PlaceholderValidationResult,
        placeholder: Dict[str, Any],
        data_source_info: Dict[str, Any],
        time_context: Optional[Dict[str, Any]] = None
    ) -> PlaceholderValidationResult:
        """尝试修复SQL"""
        logger.info(f"尝试修复占位符SQL: {validation_result.placeholder_name}")
        
        # 构建修复上下文
        repair_context = SQLRepairContext(
            original_sql=validation_result.sql_content,
            error_message=validation_result.validation_error or '',
            placeholder_name=validation_result.placeholder_name,
            data_source_info=data_source_info,
            time_context=time_context
        )
        
        # 通过统一AI门面进行SQL修复
        repaired_sql = await self._repair_sql_with_ai(repair_context, placeholder)
        
        if repaired_sql and repaired_sql != validation_result.sql_content:
            # 测试修复后的SQL
            test_result = await self._test_sql_execution(repaired_sql, data_source_info)
            
            validation_result.repaired_sql = repaired_sql
            validation_result.test_result = test_result
            
            if test_result.get('success', False):
                validation_result.is_valid = True
                validation_result.repair_applied = True
                validation_result.confidence_score = 0.8  # 修复后的置信度稍低
                validation_result.sql_content = repaired_sql  # 更新为修复后的SQL
                logger.info(f"SQL修复成功: {validation_result.placeholder_name}")
            else:
                validation_result.validation_error = f"修复后仍失败: {test_result.get('error', '')}"
                logger.warning(f"SQL修复失败: {validation_result.placeholder_name}")
        
        return validation_result
    
    async def _repair_sql_with_ai(
        self,
        repair_context: SQLRepairContext,
        placeholder: Dict[str, Any]
    ) -> Optional[str]:
        """使用AI修复SQL"""
        try:
            # Service orchestrator migrated to agents
from app.services.infrastructure.agents import execute_agent_task
            
            orchestrator = execute_agent_task
            
            # 构建增强的时间上下文提示
            time_context_prompt = self._build_time_context_prompt(repair_context.time_context)
            
            # 构建修复请求
            repair_request = {
                "placeholder_name": repair_context.placeholder_name,
                "placeholder_text": placeholder.get('text', placeholder.get('placeholder_text', '')),
                "template_id": placeholder.get('template_id', 'unknown'),
                "template_context": f"""SQL修复任务 - 原SQL执行失败: {repair_context.error_message}

{time_context_prompt}

重要：生成的SQL必须使用动态时间范围，不能写死固定日期。使用相对时间表达式如：
- CURDATE() - INTERVAL 1 DAY （前一天）
- DATE_SUB(CURDATE(), INTERVAL 1 DAY) （前一天）
- DATE_FORMAT(CURDATE() - INTERVAL 1 DAY, '%Y-%m-%d') （前一天格式化）

示例：
- 错误：WHERE date = '2024-11-30'
- 正确：WHERE date = CURDATE() - INTERVAL 1 DAY""",
                "data_source_info": repair_context.data_source_info,
                "task_params": {
                    "original_sql": repair_context.original_sql,
                    "error_message": repair_context.error_message,
                    "repair_mode": True,
                    "validation_mode": True,
                    "dynamic_time_required": True,
                    "time_context": repair_context.time_context
                }
            }
            
            # 添加时间上下文
            if repair_context.time_context:
                repair_request.update({
                    "cron_expression": repair_context.time_context.get('cron_expression'),
                    "execution_time": repair_context.time_context.get('execution_time'),
                    "task_type": "repair"
                })
            
            # 调用统一AI门面进行SQL修复
            result = await orchestrator.analyze_single_placeholder_simple(
                user_id=self.user_id,
                placeholder_name=repair_request["placeholder_name"],
                placeholder_text=repair_request["placeholder_text"],
                template_id=repair_request["template_id"],
                template_context=repair_request["template_context"],
                data_source_info=repair_request["data_source_info"],
                task_params=repair_request["task_params"],
                cron_expression=repair_request.get("cron_expression"),
                execution_time=repair_request.get("execution_time"),
                task_type=repair_request.get("task_type", "repair")
            )
            
            if result.get('status') == 'completed':
                generated_sql = result.get('generated_sql', {})
                raw_sql = None
                
                if isinstance(generated_sql, dict):
                    raw_sql = generated_sql.get(repair_context.placeholder_name) or generated_sql.get('sql', '')
                elif isinstance(generated_sql, str):
                    raw_sql = generated_sql
                
                if raw_sql:
                    # 后处理：确保SQL使用动态时间
                    processed_sql = self._ensure_dynamic_time_in_sql(raw_sql, repair_context.time_context)
                    return processed_sql
            
            logger.warning(f"AI修复未成功: {result.get('status', 'unknown')}")
            return None
            
        except Exception as e:
            logger.error(f"AI修复异常: {e}")
            return None
    
    def _build_time_context_prompt(self, time_context: Optional[Dict[str, Any]]) -> str:
        """构建时间上下文提示"""
        if not time_context:
            return "注意：这是一个需要时间范围的查询，请使用动态时间表达式。"
        
        cron_expr = time_context.get('cron_expression', '')
        execution_time = time_context.get('execution_time', '')
        task_type = time_context.get('task_type', 'manual')
        
        prompt = f"时间上下文信息：\n"
        
        if cron_expr:
            # 解析cron表达式
            # AI core components migrated to agents
from app.services.infrastructure.agents.core import *
            try:
                time_manager = TimeContextManager()
                context = time_manager.build_task_time_context(cron_expr, execution_time)
                
                prompt += f"- 任务调度：{cron_expr} ({context.period_description})\n"
                prompt += f"- 数据时间范围：{context.data_start_time} 到 {context.data_end_time}\n"
                prompt += f"- 执行时间：{execution_time}\n"
                
                # 根据周期给出具体的SQL时间范围建议
                if "每日" in context.period_description:
                    prompt += "- SQL时间范围建议：使用 CURDATE() - INTERVAL 1 DAY 查询前一天数据\n"
                elif "每周" in context.period_description:
                    prompt += "- SQL时间范围建议：使用 DATE_SUB(CURDATE(), INTERVAL 1 WEEK) 查询上一周数据\n"
                elif "每月" in context.period_description:
                    prompt += "- SQL时间范围建议：使用 DATE_SUB(CURDATE(), INTERVAL 1 MONTH) 查询上个月数据\n"
                    
            except Exception as e:
                logger.warning(f"解析时间上下文失败: {e}")
                prompt += f"- 调度表达式：{cron_expr}\n"
        
        prompt += f"- 任务类型：{task_type}\n"
        prompt += "\n重要：SQL中的时间条件必须使用动态表达式，每次执行时自动计算正确的时间范围。"
        
        return prompt
    
    def _ensure_dynamic_time_in_sql(self, sql: str, time_context: Optional[Dict[str, Any]]) -> str:
        """确保SQL使用动态时间表达式 - 使用TimeContextManager"""
        try:
            if not time_context:
                logger.warning("No time context provided, unable to ensure dynamic time in SQL")
                return sql
            
            # 使用TimeContextManager替换时间占位符
            processed_sql = self.time_context_manager.replace_sql_time_placeholders(sql, time_context)
            
            # 记录替换结果
            if processed_sql != sql:
                logger.info(f"Applied dynamic time replacements to SQL")
                logger.debug(f"Original SQL: {sql}")
                logger.debug(f"Processed SQL: {processed_sql}")
            
            return processed_sql
            
        except Exception as e:
            logger.error(f"处理SQL动态时间失败: {e}")
            return sql
    
    
    async def get_placeholder_repair_status(
        self,
        template_id: str
    ) -> Dict[str, Any]:
        """获取模板占位符修复状态"""
        try:
            from app.crud import template_placeholder as crud_placeholder
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            try:
                placeholders = crud_placeholder.get_by_template(db, template_id=template_id)
                
                total_count = len(placeholders)
                valid_count = 0
                empty_count = 0
                error_count = 0
                
                for placeholder in placeholders:
                    if placeholder.generated_sql and placeholder.sql_validated:
                        valid_count += 1
                    elif not placeholder.generated_sql:
                        empty_count += 1
                    else:
                        error_count += 1
                
                return {
                    "template_id": template_id,
                    "total_placeholders": total_count,
                    "valid_placeholders": valid_count,
                    "empty_placeholders": empty_count,
                    "error_placeholders": error_count,
                    "repair_needed": empty_count + error_count > 0,
                    "completion_rate": valid_count / total_count if total_count > 0 else 0.0,
                    "status": "healthy" if error_count == 0 and empty_count == 0 else "needs_repair"
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"获取占位符修复状态失败: {e}")
            return {
                "template_id": template_id,
                "error": str(e),
                "status": "error"
            }
    
    async def batch_repair_template_placeholders(
        self,
        template_id: str,
        data_source_info: Dict[str, Any],
        time_context: Optional[Dict[str, Any]] = None,
        force_repair: bool = False
    ) -> Dict[str, Any]:
        """批量修复模板占位符"""
        logger.info(f"开始批量修复模板占位符: template_id={template_id}")
        
        try:
            from app.crud import template_placeholder as crud_placeholder
            from app.db.session import SessionLocal
            
            db = SessionLocal()
            try:
                # 获取模板所有占位符
                placeholders = crud_placeholder.get_by_template(db, template_id=template_id)
                
                # 转换为字典格式
                placeholder_dicts = []
                for p in placeholders:
                    placeholder_dict = {
                        'id': p.id,
                        'name': p.placeholder_name,
                        'placeholder_name': p.placeholder_name,
                        'text': p.placeholder_text,
                        'placeholder_text': p.placeholder_text,
                        'generated_sql': p.generated_sql or '',
                        'template_id': p.template_id,
                        'sql_validated': p.sql_validated
                    }
                    
                    # 只修复需要修复的占位符
                    if force_repair or not p.generated_sql or not p.sql_validated:
                        placeholder_dicts.append(placeholder_dict)
                
                if not placeholder_dicts:
                    return {
                        "template_id": template_id,
                        "status": "no_repair_needed",
                        "message": "所有占位符都已有效",
                        "repaired_count": 0,
                        "total_count": len(placeholders)
                    }
                
                # 执行验证和修复
                validation_results = await self.validate_and_repair_placeholders(
                    template_id=template_id,
                    placeholders=placeholder_dicts,
                    data_source_info=data_source_info,
                    time_context=time_context
                )
                
                # 更新数据库中的占位符
                repaired_count = 0
                for result in validation_results:
                    if result.repair_applied and result.is_valid:
                        # 找到对应的占位符并更新
                        for p in placeholders:
                            if p.placeholder_name == result.placeholder_name:
                                p.generated_sql = result.repaired_sql
                                p.sql_validated = True
                                p.confidence_score = result.confidence_score
                                db.commit()
                                repaired_count += 1
                                break
                
                return {
                    "template_id": template_id,
                    "status": "completed",
                    "message": f"成功修复 {repaired_count} 个占位符",
                    "repaired_count": repaired_count,
                    "total_count": len(placeholder_dicts),
                    "validation_results": [
                        {
                            "placeholder_name": r.placeholder_name,
                            "is_valid": r.is_valid,
                            "repair_applied": r.repair_applied,
                            "confidence_score": r.confidence_score
                        }
                        for r in validation_results
                    ]
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"批量修复占位符失败: {e}")
            return {
                "template_id": template_id,
                "status": "error",
                "error": str(e),
                "repaired_count": 0
            }


# 工厂函数
def create_placeholder_validation_service(user_id: str) -> PlaceholderValidationService:
    """创建占位符验证服务实例"""
    return PlaceholderValidationService(user_id=user_id)