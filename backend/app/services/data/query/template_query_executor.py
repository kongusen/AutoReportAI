"""
模板化查询执行器

基于用户提供的Python脚本思想，实现稳定的模板化SQL执行
比Agent直接生成带时间的SQL更稳定可靠
"""

import logging
import time
import asyncio
import decimal
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
import json

from .query_executor_service import QueryExecutorService, QueryResult
from ..template.sql_template_service import sql_template_service
from ..template.time_inference_service import time_inference_service

logger = logging.getLogger(__name__)


class TemplateQueryExecutor:
    """模板化查询执行器"""

    def __init__(self, base_executor: Optional[QueryExecutorService] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.base_executor = base_executor or QueryExecutorService()
        self.template_service = sql_template_service
        self.time_inference_service = time_inference_service

    async def execute_template_query(
        self,
        sql_template: str,
        base_date: str,
        connection_params: Optional[Dict] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行模板化SQL查询

        Args:
            sql_template: SQL模板（包含占位符）
            base_date: 基准日期 YYYY-MM-DD
            connection_params: 数据库连接参数
            additional_params: 额外的模板参数

        Returns:
            查询结果
        """
        start_time = time.time()

        try:
            self.logger.info(f"🚀 开始执行模板化查询")
            self.logger.debug(f"SQL模板: {sql_template[:200]}...")

            # 1. 验证SQL模板
            validation_result = self.template_service.validate_template_sql(sql_template)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": f"SQL模板验证失败: {validation_result['issues']}",
                    "validation_issues": validation_result["issues"],
                    "execution_time": time.time() - start_time
                }

            # 2. 构建模板参数
            template_params = self.template_service.build_template_parameters(
                base_date=base_date,
                additional_params=additional_params
            )

            # 3. 填充SQL模板
            executable_sql = self.template_service.fill_template(sql_template, template_params)
            self.logger.info(f"✅ SQL模板填充完成")
            self.logger.debug(f"可执行SQL: {executable_sql}")

            # 4. 执行SQL
            execution_result = await self.base_executor.execute_query(
                sql_query=executable_sql,
                connection_params=connection_params
            )

            # 5. 增强返回结果
            execution_result.update({
                "template_info": {
                    "sql_template": sql_template,
                    "base_date": base_date,
                    "template_params": template_params,
                    "executable_sql": executable_sql,
                    "placeholders_found": validation_result["placeholders"]
                },
                "template_execution": True
            })

            execution_time = time.time() - start_time
            execution_result["total_execution_time"] = execution_time

            self.logger.info(f"🎉 模板化查询执行成功，耗时: {execution_time:.3f}s")
            return execution_result

        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"❌ 模板化查询执行失败: {e}")

            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time,
                "template_execution": True,
                "template_info": {
                    "sql_template": sql_template,
                    "base_date": base_date,
                    "error_stage": "execution"
                }
            }

    async def batch_execute_templates(
        self,
        placeholder_sql_map: Dict[str, str],
        base_date: str,
        connection_params: Optional[Dict] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        批量执行模板化查询，类似用户Python脚本的逻辑

        Args:
            placeholder_sql_map: 占位符名称到SQL模板的映射
            base_date: 基准日期
            connection_params: 数据库连接参数
            additional_params: 额外参数
            max_concurrent: 最大并发数

        Returns:
            执行结果汇总
        """
        start_time = time.time()

        try:
            self.logger.info(f"🚀 开始批量执行模板化查询: {len(placeholder_sql_map)} 个占位符")

            # 1. 处理周期性占位符（直接计算值）
            placeholder_data_map = {}
            sql_tasks = []

            for placeholder_name, sql_template in placeholder_sql_map.items():
                if placeholder_name.startswith("{{周期：") or "周期" in placeholder_name:
                    # 直接计算周期值
                    period_value = self.template_service.calculate_period_value(placeholder_name, base_date)
                    placeholder_data_map[placeholder_name] = period_value
                    self.logger.info(f"📅 计算周期值: {placeholder_name} -> {period_value}")
                elif not sql_template or not sql_template.strip():
                    # 空SQL模板
                    placeholder_data_map[placeholder_name] = None
                    self.logger.warning(f"⚠️ 跳过空SQL模板: {placeholder_name}")
                else:
                    # 需要执行SQL查询的占位符
                    sql_tasks.append((placeholder_name, sql_template))

            # 2. 批量执行SQL查询（控制并发）
            semaphore = asyncio.Semaphore(max_concurrent)

            async def execute_single_template(placeholder_name: str, sql_template: str):
                async with semaphore:
                    try:
                        result = await self.execute_template_query(
                            sql_template=sql_template,
                            base_date=base_date,
                            connection_params=connection_params,
                            additional_params=additional_params
                        )

                        if result["success"]:
                            # 智能解包结果，类似Python脚本的unpack_result函数
                            data = result.get("data", [])
                            unpacked_value = self._unpack_query_result(data)

                            # 处理百分比占位符
                            if self._is_percentage_placeholder(placeholder_name) and unpacked_value is not None:
                                unpacked_value = f"{unpacked_value}%"

                            return placeholder_name, unpacked_value
                        else:
                            self.logger.error(f"❌ 查询失败: {placeholder_name} - {result.get('error')}")
                            return placeholder_name, f"ERROR: {result.get('error')}"

                    except Exception as e:
                        self.logger.error(f"❌ 执行异常: {placeholder_name} - {e}")
                        return placeholder_name, f"ERROR: {e}"

            # 并发执行所有SQL任务
            if sql_tasks:
                self.logger.info(f"🔄 并发执行 {len(sql_tasks)} 个SQL查询（最大并发: {max_concurrent}）")
                sql_results = await asyncio.gather(*[
                    execute_single_template(name, template) for name, template in sql_tasks
                ])

                # 合并SQL执行结果
                for placeholder_name, result_value in sql_results:
                    placeholder_data_map[placeholder_name] = result_value

            # 3. 构建执行汇总
            execution_summary = {
                "success": True,
                "placeholder_data_map": placeholder_data_map,
                "execution_stats": {
                    "total_placeholders": len(placeholder_sql_map),
                    "period_placeholders": len(placeholder_sql_map) - len(sql_tasks),
                    "sql_placeholders": len(sql_tasks),
                    "successful_executions": sum(1 for v in placeholder_data_map.values()
                                               if v is not None and not str(v).startswith("ERROR:")),
                    "failed_executions": sum(1 for v in placeholder_data_map.values()
                                           if str(v).startswith("ERROR:")),
                    "execution_time": time.time() - start_time
                },
                "base_date": base_date,
                "template_execution": True
            }

            self.logger.info(f"🎉 批量执行完成: {execution_summary['execution_stats']}")
            return execution_summary

        except Exception as e:
            self.logger.error(f"❌ 批量执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time,
                "template_execution": True
            }

    def _unpack_query_result(self, result: List[Dict[str, Any]]) -> Any:
        """
        智能解包查询结果，类似Python脚本的unpack_result函数

        Args:
            result: 查询结果列表

        Returns:
            解包后的值
        """
        if not result:
            return None

        if len(result) > 1:
            return result

        first_row = result[0]
        if len(first_row.keys()) > 1:
            return result

        # 返回单行单列的值
        return list(first_row.values())[0]

    def _is_percentage_placeholder(self, placeholder_name: str) -> bool:
        """
        判断是否为百分比占位符

        Args:
            placeholder_name: 占位符名称

        Returns:
            是否为百分比占位符
        """
        return ("占比" in placeholder_name or "百分比" in placeholder_name) and "图表" not in placeholder_name

    def _json_serializable(self, obj: Any) -> Any:
        """
        处理JSON序列化，类似Python脚本的json_default_encoder

        Args:
            obj: 要序列化的对象

        Returns:
            可序列化的对象
        """
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    async def save_results_to_file(
        self,
        placeholder_data_map: Dict[str, Any],
        output_file: str
    ) -> bool:
        """
        保存结果到JSON文件，类似Python脚本功能

        Args:
            placeholder_data_map: 占位符数据映射
            output_file: 输出文件路径

        Returns:
            是否保存成功
        """
        try:
            # 处理特殊类型的序列化
            serializable_data = {}
            for key, value in placeholder_data_map.items():
                serializable_data[key] = self._json_serializable(value)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"💾 结果已保存到文件: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"❌ 保存文件失败: {e}")
            return False

    async def execute_template_query_with_task_context(
        self,
        sql_template: str,
        task_info: Dict[str, Any],
        connection_params: Optional[Dict] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        is_test_mode: bool = False
    ) -> Dict[str, Any]:
        """
        基于任务上下文执行模板化查询，自动推断时间参数

        Args:
            sql_template: SQL模板
            task_info: 任务信息（包含cron表达式、执行时间等）
            connection_params: 数据库连接参数
            additional_params: 额外参数
            is_test_mode: 是否为测试模式

        Returns:
            查询结果
        """
        try:
            self.logger.info(f"🚀 基于任务上下文执行模板化查询")

            # 1. 推断基准时间
            if is_test_mode:
                # 测试模式：使用固定时间，便于核查
                time_info = self.time_inference_service.get_test_validation_date(
                    fixed_date=task_info.get("test_base_date"),
                    days_offset=task_info.get("test_days_offset", -1)
                )
                base_date = time_info["base_date"]
                self.logger.info(f"📅 测试模式: 使用固定基准日期 {base_date}")
            else:
                # 生产模式：基于cron表达式和执行时间推断
                cron_expression = task_info.get("cron_expression")
                execution_time = task_info.get("execution_time")

                if not cron_expression:
                    raise ValueError("生产模式需要提供cron_expression")

                time_info = self.time_inference_service.infer_base_date_from_cron(
                    cron_expression=cron_expression,
                    task_execution_time=execution_time
                )
                base_date = time_info["base_date"]
                self.logger.info(f"🕐 生产模式: 推断基准日期 {base_date} (置信度: {time_info.get('inference_confidence', 0)})")

            # 2. 执行模板化查询
            result = await self.execute_template_query(
                sql_template=sql_template,
                base_date=base_date,
                connection_params=connection_params,
                additional_params=additional_params
            )

            # 3. 增强返回结果
            result["task_context"] = {
                "task_info": task_info,
                "time_inference": time_info,
                "is_test_mode": is_test_mode
            }

            return result

        except Exception as e:
            self.logger.error(f"❌ 基于任务上下文执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_context": {
                    "task_info": task_info,
                    "is_test_mode": is_test_mode,
                    "error_stage": "task_context_execution"
                }
            }

    async def batch_execute_templates_with_task_context(
        self,
        placeholder_sql_map: Dict[str, str],
        task_info: Dict[str, Any],
        connection_params: Optional[Dict] = None,
        additional_params: Optional[Dict[str, Any]] = None,
        is_test_mode: bool = False,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        基于任务上下文批量执行模板化查询

        Args:
            placeholder_sql_map: 占位符-SQL模板映射
            task_info: 任务信息
            connection_params: 连接参数
            additional_params: 额外参数
            is_test_mode: 是否为测试模式
            max_concurrent: 最大并发数

        Returns:
            批量执行结果
        """
        try:
            self.logger.info(f"🚀 基于任务上下文批量执行: {len(placeholder_sql_map)} 个占位符")

            # 1. 推断基准时间
            if is_test_mode:
                time_info = self.time_inference_service.get_test_validation_date(
                    fixed_date=task_info.get("test_base_date"),
                    days_offset=task_info.get("test_days_offset", -1)
                )
                base_date = time_info["base_date"]
                self.logger.info(f"📅 测试模式批量执行: 使用基准日期 {base_date}")
            else:
                cron_expression = task_info.get("cron_expression")
                execution_time = task_info.get("execution_time")

                if not cron_expression:
                    raise ValueError("生产模式需要提供cron_expression")

                time_info = self.time_inference_service.infer_base_date_from_cron(
                    cron_expression=cron_expression,
                    task_execution_time=execution_time
                )
                base_date = time_info["base_date"]
                self.logger.info(f"🕐 生产模式批量执行: 推断基准日期 {base_date}")

            # 2. 执行批量处理
            result = await self.batch_execute_templates(
                placeholder_sql_map=placeholder_sql_map,
                base_date=base_date,
                connection_params=connection_params,
                additional_params=additional_params,
                max_concurrent=max_concurrent
            )

            # 3. 增强返回结果
            result["task_context"] = {
                "task_info": task_info,
                "time_inference": time_info,
                "is_test_mode": is_test_mode
            }

            return result

        except Exception as e:
            self.logger.error(f"❌ 基于任务上下文批量执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_context": {
                    "task_info": task_info,
                    "is_test_mode": is_test_mode,
                    "error_stage": "batch_task_context_execution"
                }
            }

    async def validate_templates_for_task(
        self,
        placeholder_sql_map: Dict[str, str],
        task_info: Dict[str, Any],
        sample_connection_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        验证模板是否适合指定任务，包括时间推断和SQL验证

        Args:
            placeholder_sql_map: 占位符-SQL模板映射
            task_info: 任务信息
            sample_connection_params: 样本连接参数

        Returns:
            验证结果
        """
        try:
            self.logger.info(f"🔍 验证任务模板兼容性: {len(placeholder_sql_map)} 个占位符")

            validation_results = {
                "overall_valid": True,
                "placeholder_validations": {},
                "time_inference": {},
                "task_compatibility": {},
                "recommendations": []
            }

            # 1. 时间推断验证
            try:
                cron_expression = task_info.get("cron_expression")
                if cron_expression:
                    time_info = self.time_inference_service.infer_base_date_from_cron(cron_expression)
                    validation_results["time_inference"] = time_info

                    if time_info["inference_confidence"] < 0.7:
                        validation_results["recommendations"].append(
                            f"cron表达式置信度较低 ({time_info['inference_confidence']:.2f})，建议检查任务频率设置"
                        )
                else:
                    validation_results["recommendations"].append("未提供cron表达式，无法进行时间推断验证")

            except Exception as e:
                validation_results["time_inference"]["error"] = str(e)
                validation_results["recommendations"].append(f"时间推断失败: {e}")

            # 2. 模板验证
            for placeholder_name, sql_template in placeholder_sql_map.items():
                placeholder_validation = self.template_service.validate_template_sql(sql_template)
                validation_results["placeholder_validations"][placeholder_name] = placeholder_validation

                if not placeholder_validation["valid"]:
                    validation_results["overall_valid"] = False

            # 3. 任务兼容性检查
            validation_results["task_compatibility"] = {
                "has_time_placeholders": any(
                    any(keyword in " ".join(validation["placeholders"]) for keyword in ["date", "time", "start", "end"])
                    for validation in validation_results["placeholder_validations"].values()
                ),
                "cron_expression_provided": bool(task_info.get("cron_expression")),
                "time_inference_available": "time_inference" in validation_results and "error" not in validation_results["time_inference"]
            }

            self.logger.info(f"✅ 任务模板验证完成: {'通过' if validation_results['overall_valid'] else '失败'}")
            return validation_results

        except Exception as e:
            self.logger.error(f"❌ 任务模板验证失败: {e}")
            return {
                "overall_valid": False,
                "error": str(e),
                "recommendations": ["验证过程异常，请检查输入参数"]
            }


# 全局服务实例
template_query_executor = TemplateQueryExecutor()