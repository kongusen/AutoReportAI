"""
SQL验证服务 - 独立功能

专门用于验证存储的占位符SQL，替换真实日期并执行查询返回实际数据
与Agent生成SQL的验证逻辑完全分离
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.services.data.template.time_inference_service import time_inference_service
from app.services.data.query.query_executor_service import query_executor_service

logger = logging.getLogger(__name__)


class SQLValidationService:
    """SQL验证服务 - 执行占位符SQL并返回真实数据"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def validate_and_execute_placeholder_sql(
        self,
        sql_template: str,
        data_source_id: str,
        placeholder_name: str = "SQL验证",
        execution_mode: str = "test",
        fixed_date: Optional[str] = None,
        days_offset: int = -1
    ) -> Dict[str, Any]:
        """
        验证并执行带占位符的SQL，返回真实数据

        Args:
            sql_template: 带占位符的SQL模板 (如: SELECT COUNT(*) FROM table WHERE dt >= {{start_date}})
            data_source_id: 数据源ID
            placeholder_name: 占位符名称，用于日志
            execution_mode: 执行模式 ("test" 使用固定日期, "production" 使用cron推断)
            fixed_date: 固定日期 (test模式)
            days_offset: 日期偏移 (test模式)

        Returns:
            验证和执行结果
        """
        try:
            self.logger.info(f"🔍 开始验证占位符SQL: {placeholder_name}")

            # 1. 时间推断 - 获取真实日期
            if execution_mode == "test":
                time_result = time_inference_service.get_test_validation_date(
                    fixed_date=fixed_date,
                    days_offset=days_offset
                )
            else:
                # 生产模式，可以后续扩展cron支持
                time_result = time_inference_service.get_test_validation_date(
                    fixed_date=None,
                    days_offset=days_offset
                )

            base_date = time_result["base_date"]
            self.logger.info(f"📅 使用基准日期: {base_date}")

            # 2. 替换占位符为真实日期
            executable_sql = self._replace_placeholders(sql_template, base_date)
            self.logger.info(f"🔄 替换占位符后的SQL: {executable_sql}")

            # 3. 执行SQL查询
            self.logger.info(f"⚡ 执行SQL查询: {executable_sql}")
            query_result = await query_executor_service.execute_query(
                executable_sql,
                {"data_source_id": data_source_id}
            )

            # 4. 处理查询结果
            if query_result.get("success"):
                rows = query_result.get("data", [])
                metadata = query_result.get("metadata", {})

                # 提取第一行第一列作为主要结果（适用于COUNT等聚合查询）
                primary_value = None
                if rows and len(rows) > 0 and len(rows[0]) > 0:
                    primary_value = rows[0][0]

                validation_result = {
                    "success": True,
                    "placeholder_name": placeholder_name,
                    "original_sql_template": sql_template,
                    "executable_sql": executable_sql,
                    "base_date": base_date,
                    "time_info": time_result,
                    "execution_result": {
                        "rows": rows,
                        "row_count": len(rows),
                        "primary_value": primary_value,
                        "metadata": metadata
                    },
                    "validation_passed": True,
                    "executed_at": datetime.now().isoformat()
                }

                self.logger.info(f"✅ SQL验证成功: {placeholder_name}, 返回 {len(rows)} 行数据")
                if primary_value is not None:
                    self.logger.info(f"📊 主要结果值: {primary_value}")

                return validation_result

            else:
                # 查询失败
                error_message = query_result.get("error", "未知查询错误")
                self.logger.error(f"❌ SQL查询失败: {error_message}")

                return {
                    "success": False,
                    "placeholder_name": placeholder_name,
                    "original_sql_template": sql_template,
                    "executable_sql": executable_sql,
                    "base_date": base_date,
                    "time_info": time_result,
                    "error": error_message,
                    "error_type": "query_execution_failed",
                    "validation_passed": False,
                    "executed_at": datetime.now().isoformat()
                }

        except Exception as e:
            self.logger.error(f"❌ SQL验证异常: {e}")
            return {
                "success": False,
                "placeholder_name": placeholder_name,
                "original_sql_template": sql_template,
                "error": str(e),
                "error_type": "validation_exception",
                "validation_passed": False,
                "executed_at": datetime.now().isoformat()
            }

    def _replace_placeholders(self, sql_template: str, base_date: str) -> str:
        """
        替换SQL模板中的占位符为真实日期

        Args:
            sql_template: 带占位符的SQL模板
            base_date: 基准日期 YYYY-MM-DD

        Returns:
            替换后的可执行SQL
        """
        executable_sql = sql_template

        # 替换基本日期占位符
        executable_sql = executable_sql.replace("{{start_date}}", f"'{base_date}'")
        executable_sql = executable_sql.replace("{{end_date}}", f"'{base_date}'")

        # 如果需要支持日期范围，可以扩展
        # 例如：周报、月报等

        return executable_sql

    async def batch_validate_placeholder_sqls(
        self,
        sql_templates: Dict[str, str],
        data_source_id: str,
        execution_mode: str = "test",
        fixed_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量验证多个占位符SQL

        Args:
            sql_templates: 占位符名称到SQL模板的映射
            data_source_id: 数据源ID
            execution_mode: 执行模式
            fixed_date: 固定日期

        Returns:
            批量验证结果
        """
        batch_results = {}
        successful_count = 0
        failed_count = 0

        self.logger.info(f"🔍 开始批量验证 {len(sql_templates)} 个占位符SQL")

        for placeholder_name, sql_template in sql_templates.items():
            try:
                result = await self.validate_and_execute_placeholder_sql(
                    sql_template=sql_template,
                    data_source_id=data_source_id,
                    placeholder_name=placeholder_name,
                    execution_mode=execution_mode,
                    fixed_date=fixed_date
                )

                batch_results[placeholder_name] = result

                if result.get("success"):
                    successful_count += 1
                else:
                    failed_count += 1

            except Exception as e:
                self.logger.error(f"❌ 批量验证异常 {placeholder_name}: {e}")
                batch_results[placeholder_name] = {
                    "success": False,
                    "placeholder_name": placeholder_name,
                    "error": str(e),
                    "error_type": "batch_validation_exception"
                }
                failed_count += 1

        summary = {
            "total_count": len(sql_templates),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "success_rate": successful_count / len(sql_templates) if sql_templates else 0.0
        }

        self.logger.info(f"📊 批量验证完成: {summary}")

        return {
            "success": successful_count > 0,
            "summary": summary,
            "results": batch_results,
            "executed_at": datetime.now().isoformat()
        }


# 全局服务实例
sql_validation_service = SQLValidationService()