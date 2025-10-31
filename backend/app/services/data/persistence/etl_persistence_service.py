"""
ETL Data Persistence Service

ETL数据持久化服务 - 精简版（针对100占位符场景优化）

核心功能：
1. 将ETL提取的数据批量保存到placeholder_values表
2. 支持批次管理和版本控制
3. 提供缓存键生成（为后续缓存优化预留）
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session

from app import crud
from app.schemas.placeholder_value import PlaceholderValueCreate

logger = logging.getLogger(__name__)


class ETLPersistenceService:
    """ETL数据持久化服务"""

    def __init__(self, db: Session):
        """
        初始化持久化服务

        Args:
            db: 数据库会话（由调用方统一管理事务）
        """
        self.db = db
        self.logger = logger

    @staticmethod
    def generate_batch_id() -> str:
        """
        生成唯一的批次ID

        Returns:
            格式: batch_YYYYMMDDHHMMSS_<uuid8位>
        """
        import uuid
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"batch_{timestamp}_{str(uuid.uuid4())[:8]}"

    async def persist_etl_results(
        self,
        template_id: str,
        etl_results: Dict[str, Any],
        batch_id: str,
        time_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        持久化ETL结果到placeholder_values表（精简版 - 100占位符优化）

        核心逻辑：
        1. 遍历所有成功提取的数据
        2. 批量构建PlaceholderValue对象
        3. 一次性批量插入
        4. 不在此commit（由调用方统一管理事务）

        Args:
            template_id: 模板ID
            etl_results: ETL执行结果（来自_execute_etl_pipeline）
            batch_id: 批次ID
            time_context: 时间上下文

        Returns:
            持久化结果统计
            {
                "success": True/False,
                "batch_id": "batch_xxx",
                "saved_count": 100,
                "failed_count": 0,
                "message": "持久化完成: 成功100, 失败0"
            }
        """
        try:
            saved_count = 0
            failed_count = 0
            values_to_create = []  # 收集所有要插入的数据

            execution_time = time_context.get("execution_time") or datetime.utcnow()
            period_start = time_context.get("period_start")
            period_end = time_context.get("period_end")

            self.logger.info(f"📦 开始持久化ETL结果, batch_id={batch_id}")

            # 遍历每个数据源的结果
            for data_source_id, source_result in etl_results.items():
                extract_data = source_result.get("extract", {}).get("data", {})
                successful_extractions = extract_data.get("successful_extractions", [])

                self.logger.info(f"   数据源 {data_source_id}: {len(successful_extractions)} 个占位符")

                for extraction in successful_extractions:
                    try:
                        placeholder_name = extraction["placeholder"]

                        # 查找占位符配置
                        placeholder = crud.template_placeholder.get_by_template_and_name(
                            db=self.db,
                            template_id=template_id,
                            name=placeholder_name
                        )

                        if not placeholder:
                            self.logger.warning(f"⚠️ 未找到占位符配置: {placeholder_name}")
                            failed_count += 1
                            continue

                        # 构建数据（简化版 - 只保留核心字段）
                        value_data = PlaceholderValueCreate(
                            placeholder_id=placeholder.id,
                            data_source_id=UUID(data_source_id),
                            raw_query_result=extraction["data"],
                            processed_value=extraction["data"],
                            formatted_text=self._format_data(extraction["data"]),
                            execution_sql=placeholder.generated_sql,
                            row_count=extraction.get("row_count", 0),
                            success=True,
                            source="etl",
                            confidence_score=1.0,
                            analysis_metadata={
                                "extraction_mode": extract_data.get("extraction_mode"),
                                "execution_mode": extract_data.get("execution_mode"),
                                "base_date": str(extract_data.get("base_date", ""))
                            },
                            # 时间信息
                            execution_time=execution_time,
                            period_start=period_start,
                            period_end=period_end,
                            sql_parameters_snapshot=time_context.get("additional_params", {}),
                            # 版本控制
                            execution_batch_id=batch_id,
                            is_latest_version=True,
                            # 缓存信息（预留，可选）
                            cache_key=self._generate_cache_key(
                                str(placeholder.id),
                                data_source_id,
                                period_start,
                                period_end
                            ) if period_start else None,
                            expires_at=datetime.utcnow() + timedelta(hours=placeholder.cache_ttl_hours or 24)
                        )

                        values_to_create.append(value_data)
                        saved_count += 1

                    except Exception as e:
                        self.logger.error(f"❌ 处理占位符失败: {extraction.get('placeholder')}, {e}")
                        failed_count += 1

            # 🔑 批量插入（一次性插入100条）
            if values_to_create:
                crud.placeholder_value.create_batch(self.db, values=values_to_create)
                self.logger.info(f"✅ 批量插入 {len(values_to_create)} 条记录到placeholder_values表")

            # 🔑 注意：不在这里commit，由调用方（task_execution_service）统一管理事务

            result = {
                "success": True,
                "batch_id": batch_id,
                "saved_count": saved_count,
                "failed_count": failed_count,
                "message": f"持久化完成: 成功{saved_count}, 失败{failed_count}"
            }

            self.logger.info(f"✅ {result['message']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ ETL数据持久化失败: {e}")
            self.logger.exception(e)
            raise

    async def persist_failed_extractions(
        self,
        template_id: str,
        failed_extractions: List[Dict[str, Any]],
        batch_id: str,
        data_source_id: str
    ) -> int:
        """
        持久化失败的提取记录（可选功能）

        Args:
            template_id: 模板ID
            failed_extractions: 失败的提取列表
            batch_id: 批次ID
            data_source_id: 数据源ID

        Returns:
            保存的失败记录数
        """
        saved_count = 0

        for extraction in failed_extractions:
            try:
                placeholder_name = extraction["placeholder"]

                placeholder = crud.template_placeholder.get_by_template_and_name(
                    db=self.db,
                    template_id=template_id,
                    name=placeholder_name
                )

                if not placeholder:
                    continue

                value_data = PlaceholderValueCreate(
                    placeholder_id=placeholder.id,
                    data_source_id=UUID(data_source_id),
                    success=False,
                    error_message=extraction.get("error", "Unknown error"),
                    execution_batch_id=batch_id,
                    source="etl",
                    execution_time=datetime.utcnow()
                )

                crud.placeholder_value.create(self.db, obj_in=value_data)
                saved_count += 1

            except Exception as e:
                self.logger.error(f"❌ 持久化失败记录异常: {extraction.get('placeholder')}, {e}")

        if saved_count > 0:
            self.logger.info(f"✅ 记录了 {saved_count} 个失败的提取")

        return saved_count

    @staticmethod
    def _format_data(data: Any) -> str:
        """
        简单格式化数据为文本显示

        Args:
            data: 原始数据

        Returns:
            格式化后的字符串
        """
        if isinstance(data, (int, float)):
            return str(data)
        elif isinstance(data, dict):
            if len(data) == 1:
                return str(list(data.values())[0])
            return str(data)
        elif isinstance(data, list):
            if len(data) == 0:
                return "0"
            elif len(data) == 1 and isinstance(data[0], dict):
                if len(data[0]) == 1:
                    return str(list(data[0].values())[0])
            return f"{len(data)} 条记录"
        else:
            return str(data)

    @staticmethod
    def _generate_cache_key(
        placeholder_id: str,
        data_source_id: str,
        period_start: Any,
        period_end: Any
    ) -> str:
        """
        生成缓存键（预留功能，用于后续缓存优化）

        Args:
            placeholder_id: 占位符ID
            data_source_id: 数据源ID
            period_start: 周期开始时间
            period_end: 周期结束时间

        Returns:
            缓存键
        """
        import hashlib

        key_parts = [
            str(placeholder_id),
            str(data_source_id),
            str(period_start) if period_start else "none",
            str(period_end) if period_end else "none"
        ]
        key_string = "_".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
