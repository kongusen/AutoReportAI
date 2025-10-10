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
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from .ports.sql_execution_port import SqlExecutionPort
from app.utils.time_context import TimeContextManager

logger = logging.getLogger(__name__)

# 单用户并发限流：全局信号量注册表（进程内生效）
_USER_SEMAPHORES: Dict[str, asyncio.Semaphore] = {}


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


from .ports.ai_sql_repair_port import AiSqlRepairPort


class PlaceholderValidationService:
    """
    占位符验证和修复服务
    
    基于DDD Domain层的业务服务，专注于占位符相关的业务逻辑：
    1. 占位符SQL的验证和测试
    2. 基于错误信息的自动修复
    3. 时间上下文感知的动态调整
    4. 与统一AI门面的集成
    """
    
    def __init__(self, user_id: str, ai_sql_repair_port: Optional[AiSqlRepairPort] = None, sql_execution_port: Optional[SqlExecutionPort] = None):
        if not user_id:
            raise ValueError("user_id is required for PlaceholderValidationService")
        self.user_id = user_id
        self.max_retry_attempts = 3
        self.validation_timeout = 30  # 秒
        self.time_context_manager = TimeContextManager()
        self._ai_sql_repair_port = ai_sql_repair_port
        self._sql_execution_port = sql_execution_port
        # 单用户限流（默认2，可通过环境变量 PLACEHOLDER_USER_CONCURRENCY 覆盖）
        try:
            limit = int(os.getenv("PLACEHOLDER_USER_CONCURRENCY", "2"))
            if limit < 1:
                limit = 1
        except Exception:
            limit = 2
        # 进程内对同一 user_id 复用同一个信号量，确保跨实例限流
        if self.user_id not in _USER_SEMAPHORES:
            _USER_SEMAPHORES[self.user_id] = asyncio.BoundedSemaphore(limit)
        self._user_semaphore = _USER_SEMAPHORES[self.user_id]
        
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

        # 受限并发验证（单用户限流），默认并发度=2
        async def _guarded_validate(ph: Dict[str, Any]):
            async with self._user_semaphore:
                try:
                    return await self._validate_single_placeholder(
                        placeholder=ph,
                        data_source_info=data_source_info,
                        time_context=time_context
                    )
                except Exception as e:
                    return e

        validation_tasks = [_guarded_validate(p) for p in placeholders]
        # 使用 gather 收集结果，但由于信号量限制，实际并发度受控
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
        """通过执行端口测试SQL执行（Domain不直接依赖具体连接器）。"""
        if not self._sql_execution_port:
            return {"success": False, "error": "未配置SQL执行端口", "data": [], "row_count": 0}
        try:
            ds_id = data_source_info.get('id') or data_source_info.get('data_source_id') or data_source_info.get('name') or 'default'
            qr = await self._sql_execution_port.execute(sql_content, ds_id)
            return {"success": True, "data": qr.rows, "row_count": qr.row_count}
        except Exception as e:
            logger.error(f"SQL测试异常: {e}")
            return {"success": False, "error": str(e), "data": [], "row_count": 0}
    
    # 旧的 _test_doris_sql 逻辑已移除，统一通过 SqlExecutionPort 执行
    
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
        """使用AI修复SQL（通过Domain Port）"""
        if not self._ai_sql_repair_port:
            logger.warning("AI SQL repair port not configured; skipping repair.")
            return None

        repaired = await self._ai_sql_repair_port.repair_sql(
            user_id=self.user_id,
            placeholder_name=repair_context.placeholder_name,
            placeholder_text=placeholder.get('text', placeholder.get('placeholder_text', '')),
            template_id=placeholder.get('template_id', 'unknown'),
            original_sql=repair_context.original_sql,
            error_message=repair_context.error_message,
            data_source_info=repair_context.data_source_info,
            time_context=repair_context.time_context,
        )
        if repaired:
            # 确保使用动态时间表达式
            return self._ensure_dynamic_time_in_sql(repaired, repair_context.time_context)
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
