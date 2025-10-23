"""
占位符流水线健康检查服务
确保所有组件和依赖正常工作
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from app.core.container import container
from app.services.infrastructure.agents import AgentService
from app.services.application.facades.unified_service_facade import create_unified_service_facade
from app.db.session import get_db_session

logger = logging.getLogger(__name__)


class PipelineHealthService:
    """流水线健康检查服务"""

    def __init__(self):
        self.health_results = {}

    async def comprehensive_health_check(self) -> Dict[str, Any]:
        """全面健康检查"""
        logger.info("🔍 开始占位符流水线健康检查")

        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "unknown",
            "components": {},
            "recommendations": []
        }

        # 1. Agent系统检查
        agent_health = await self._check_agent_system()
        health_report["components"]["agent_system"] = agent_health

        # 2. 数据源连接检查
        datasource_health = await self._check_datasource_connections()
        health_report["components"]["datasource"] = datasource_health

        # 3. Schema发现检查
        schema_health = await self._check_schema_discovery()
        health_report["components"]["schema_discovery"] = schema_health

        # 4. 时间上下文管理检查
        time_context_health = await self._check_time_context()
        health_report["components"]["time_context"] = time_context_health

        # 5. 统一门面服务检查
        facade_health = await self._check_facade_services()
        health_report["components"]["facade_services"] = facade_health

        # 6. Celery任务系统检查
        celery_health = await self._check_celery_system()
        health_report["components"]["celery_system"] = celery_health

        # 计算整体状态
        health_report["overall_status"] = self._calculate_overall_status(health_report["components"])
        health_report["recommendations"] = self._generate_recommendations(health_report["components"])

        logger.info(f"✅ 健康检查完成，整体状态: {health_report['overall_status']}")
        return health_report

    async def _check_agent_system(self) -> Dict[str, Any]:
        """检查Agent系统"""
        try:
            agent_service = AgentService(container=container)

            # 简单的Agent执行测试
            from app.services.infrastructure.agents.types import (
                AgentInput, PlaceholderSpec, SchemaInfo, TaskContext, AgentConstraints
            )

            test_input = AgentInput(
                user_prompt="健康检查：生成简单查询",
                placeholder=PlaceholderSpec(id="test", description="测试占位符", type="stat"),
                schema=SchemaInfo(tables=["test_table"], columns={"test_table": ["id", "name"]}),
                context=TaskContext(),
                constraints=AgentConstraints(sql_only=True, output_kind="sql")
            )

            # 测试执行（允许失败，记录状态）
            try:
                result = await agent_service.execute(test_input)
                agent_status = "healthy" if result.success else "degraded"
                error_msg = None if result.success else result.metadata.get("error", "执行失败")
            except Exception as e:
                agent_status = "unhealthy"
                error_msg = f"Agent执行异常: {str(e)}"

            return {
                "status": agent_status,
                "message": error_msg or "Agent系统正常",
                "tested_at": datetime.now().isoformat(),
                "details": {
                    "facade_available": True,
                    "container_available": True,
                    "execution_successful": agent_status == "healthy"
                }
            }

        except Exception as e:
            logger.error(f"Agent系统检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"Agent系统不可用: {str(e)}",
                "tested_at": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }

    async def _check_datasource_connections(self) -> Dict[str, Any]:
        """检查数据源连接"""
        try:
            with get_db_session() as db:
                from app import crud

                # 获取所有数据源
                data_sources = crud.data_source.get_multi(db, limit=5)

                connection_results = []
                healthy_count = 0

                for ds in data_sources:
                    try:
                        # 测试基础连接
                        from app.services.data.connectors.connector_factory import create_connector
                        connector = create_connector(ds)

                        await connector.connect()
                        test_result = await connector.test_connection()
                        await connector.disconnect()

                        if test_result:
                            healthy_count += 1
                            status = "healthy"
                        else:
                            status = "degraded"

                        connection_results.append({
                            "data_source_id": str(ds.id),
                            "name": ds.name,
                            "type": str(ds.source_type),
                            "status": status,
                            "message": "连接正常" if status == "healthy" else "连接异常"
                        })

                    except Exception as e:
                        connection_results.append({
                            "data_source_id": str(ds.id),
                            "name": ds.name,
                            "type": str(ds.source_type),
                            "status": "unhealthy",
                            "message": f"连接失败: {str(e)}"
                        })

                overall_status = (
                    "healthy" if healthy_count == len(data_sources) else
                    "degraded" if healthy_count > 0 else
                    "unhealthy"
                )

                return {
                    "status": overall_status,
                    "message": f"数据源连接检查完成: {healthy_count}/{len(data_sources)} 健康",
                    "tested_at": datetime.now().isoformat(),
                    "details": {
                        "total_datasources": len(data_sources),
                        "healthy_count": healthy_count,
                        "connections": connection_results
                    }
                }

        except Exception as e:
            logger.error(f"数据源连接检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"数据源检查异常: {str(e)}",
                "tested_at": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }

    async def _check_schema_discovery(self) -> Dict[str, Any]:
        """检查Schema发现功能"""
        try:
            from app.services.infrastructure.agents.adapters.schema_discovery_adapter import SchemaDiscoveryAdapter

            schema_adapter = SchemaDiscoveryAdapter()

            # 测试Schema发现（选择一个数据源）
            with get_db_session() as db:
                from app import crud
                data_sources = crud.data_source.get_multi(db, limit=1)

                if not data_sources:
                    return {
                        "status": "degraded",
                        "message": "无可用数据源进行Schema测试",
                        "tested_at": datetime.now().isoformat(),
                        "details": {"no_datasources": True}
                    }

                ds = data_sources[0]

                try:
                    schema_result = await schema_adapter.introspect(str(ds.id))

                    if schema_result.tables:
                        status = "healthy"
                        message = f"Schema发现正常，发现 {len(schema_result.tables)} 个表"
                    else:
                        status = "degraded"
                        message = "Schema发现功能正常但未发现表结构"

                    return {
                        "status": status,
                        "message": message,
                        "tested_at": datetime.now().isoformat(),
                        "details": {
                            "data_source_tested": str(ds.id),
                            "tables_found": len(schema_result.tables),
                            "tables": schema_result.tables[:5]  # 只显示前5个
                        }
                    }

                except Exception as e:
                    return {
                        "status": "unhealthy",
                        "message": f"Schema发现失败: {str(e)}",
                        "tested_at": datetime.now().isoformat(),
                        "details": {"error": str(e)}
                    }

        except Exception as e:
            logger.error(f"Schema发现检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"Schema发现检查异常: {str(e)}",
                "tested_at": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }

    async def _check_time_context(self) -> Dict[str, Any]:
        """检查时间上下文管理"""
        try:
            from app.utils.time_context import TimeContextManager

            tm = TimeContextManager()

            # 测试不同的cron表达式
            test_cases = [
                ("0 9 * * *", "每日9点"),      # 日报
                ("0 9 * * 1", "每周一9点"),     # 周报
                ("0 9 1 * *", "每月1号9点"),    # 月报
            ]

            test_results = []
            all_success = True

            for cron, description in test_cases:
                try:
                    test_time = datetime(2024, 9, 26, 9, 0, 0)  # 2024年9月26日周四
                    context = tm.build_task_time_context(cron, test_time)

                    test_results.append({
                        "cron": cron,
                        "description": description,
                        "status": "success",
                        "period": context.get("period"),
                        "period_description": context.get("period_description"),
                        "data_range": f"{context.get('data_start_time')} ~ {context.get('data_end_time')}"
                    })

                except Exception as e:
                    all_success = False
                    test_results.append({
                        "cron": cron,
                        "description": description,
                        "status": "error",
                        "error": str(e)
                    })

            return {
                "status": "healthy" if all_success else "degraded",
                "message": f"时间上下文测试完成: {len([r for r in test_results if r['status'] == 'success'])}/{len(test_cases)} 成功",
                "tested_at": datetime.now().isoformat(),
                "details": {
                    "test_cases": test_results
                }
            }

        except Exception as e:
            logger.error(f"时间上下文检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"时间上下文检查异常: {str(e)}",
                "tested_at": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }

    async def _check_facade_services(self) -> Dict[str, Any]:
        """检查统一门面服务"""
        try:
            with get_db_session() as db:
                facade = create_unified_service_facade(db, "health_check_user")

                # 测试占位符流水线是否可以初始化
                pipeline = await facade._get_placeholder_pipeline()

                return {
                    "status": "healthy",
                    "message": "统一门面服务正常",
                    "tested_at": datetime.now().isoformat(),
                    "details": {
                        "facade_created": True,
                        "pipeline_available": pipeline is not None
                    }
                }

        except Exception as e:
            logger.error(f"统一门面服务检查失败: {e}")
            return {
                "status": "unhealthy",
                "message": f"统一门面服务异常: {str(e)}",
                "tested_at": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }

    async def _check_celery_system(self) -> Dict[str, Any]:
        """检查Celery任务系统"""
        try:
            from app.core.celery_app import celery_app

            # 检查Celery应用状态
            app_status = "healthy" if celery_app else "unhealthy"

            # 检查是否有worker（可选，因为可能还没启动worker）
            inspect = celery_app.control.inspect()
            active_workers = {}
            try:
                stats = inspect.stats()
                active_workers = stats or {}
            except Exception:
                # Worker未启动是正常的
                pass

            return {
                "status": app_status,
                "message": f"Celery应用状态正常，发现 {len(active_workers)} 个worker",
                "tested_at": datetime.now().isoformat(),
                "details": {
                    "app_available": app_status == "healthy",
                    "active_workers": len(active_workers),
                    "worker_nodes": list(active_workers.keys()) if active_workers else []
                }
            }

        except Exception as e:
            logger.error(f"Celery系统检查失败: {e}")
            return {
                "status": "degraded",  # Celery问题不应该完全阻断系统
                "message": f"Celery系统检查异常: {str(e)}",
                "tested_at": datetime.now().isoformat(),
                "details": {"error": str(e)}
            }

    def _calculate_overall_status(self, components: Dict[str, Any]) -> str:
        """计算整体状态"""
        statuses = [comp.get("status", "unknown") for comp in components.values()]

        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status == "unhealthy" for status in statuses if status != "unknown"):
            # 关键组件不健康
            critical_unhealthy = any(
                comp.get("status") == "unhealthy"
                for key, comp in components.items()
                if key in ["agent_system", "datasource", "facade_services"]
            )
            return "unhealthy" if critical_unhealthy else "degraded"
        else:
            return "degraded"

    def _generate_recommendations(self, components: Dict[str, Any]) -> list:
        """生成改进建议"""
        recommendations = []

        for component_name, component_info in components.items():
            status = component_info.get("status", "unknown")

            if status == "unhealthy":
                if component_name == "agent_system":
                    recommendations.append("检查LLM配置和网络连接，确保Agent系统可用")
                elif component_name == "datasource":
                    recommendations.append("检查数据源连接配置，确保数据库可访问")
                elif component_name == "schema_discovery":
                    recommendations.append("检查数据源权限，确保可以读取表结构")
                elif component_name == "facade_services":
                    recommendations.append("检查服务依赖注入和初始化配置")

            elif status == "degraded":
                if component_name == "agent_system":
                    recommendations.append("Agent系统部分功能异常，可使用回退逻辑")
                elif component_name == "datasource":
                    recommendations.append("部分数据源连接异常，检查网络和配置")
                elif component_name == "celery_system":
                    recommendations.append("Celery系统异常，定时任务可能受影响")

        if not recommendations:
            recommendations.append("所有系统组件运行正常")

        return recommendations

    async def quick_health_check(self) -> Dict[str, Any]:
        """快速健康检查（关键组件）"""
        try:
            # 只检查关键组件
            agent_health = await self._check_agent_system()
            facade_health = await self._check_facade_services()

            overall_healthy = (
                agent_health.get("status") in ["healthy", "degraded"] and
                facade_health.get("status") == "healthy"
            )

            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "critical_components": {
                    "agent_system": agent_health.get("status"),
                    "facade_services": facade_health.get("status")
                },
                "ready_for_pipeline": overall_healthy
            }

        except Exception as e:
            logger.error(f"快速健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "ready_for_pipeline": False
            }


# 单例实例
_health_service = PipelineHealthService()


async def get_pipeline_health() -> Dict[str, Any]:
    """获取流水线健康状态"""
    return await _health_service.comprehensive_health_check()


async def get_quick_health() -> Dict[str, Any]:
    """获取快速健康检查结果"""
    return await _health_service.quick_health_check()


if __name__ == "__main__":
    # 测试用例
    async def test_health_check():
        health_service = PipelineHealthService()
        result = await health_service.comprehensive_health_check()
        print("健康检查结果:")
        print(f"整体状态: {result['overall_status']}")
        print(f"建议: {result['recommendations']}")

        for component, info in result['components'].items():
            print(f"{component}: {info['status']} - {info['message']}")

    asyncio.run(test_health_check())
