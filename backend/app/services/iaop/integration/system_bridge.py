"""
IAOP系统桥接器 - 将IAOP平台与现有系统集成

提供统一接口，连接IAOP平台与现有的模板、任务、数据源系统
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session

from ..core.integration import get_iaop_integrator
from ..api.schemas import (
    ReportGenerationRequest, 
    PlaceholderRequest,
    TaskType,
    ExecutionMode,
    AgentExecutionRequest
)
from app.models.template import Template
from app.models.task import Task
from app.models.data_source import DataSource

logger = logging.getLogger(__name__)


class IAOPSystemBridge:
    """IAOP系统桥接器 - 连接IAOP与现有系统"""
    
    def __init__(self, db: Session):
        self.db = db
        self.integrator = get_iaop_integrator()
        self._initialized = False
    
    async def initialize(self) -> None:
        """初始化桥接器"""
        if not self._initialized:
            if not self.integrator._initialized:
                await self.integrator.initialize()
            self._initialized = True
            logger.info("IAOP系统桥接器初始化完成")
    
    async def process_template_with_iaop(
        self, 
        template_id: str, 
        data_source_id: str, 
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """使用IAOP处理模板"""
        await self.initialize()
        
        try:
            # 获取模板信息
            template = self.db.query(Template).filter(Template.id == template_id).first()
            if not template:
                return {"success": False, "error": "模板不存在"}
            
            # 获取数据源信息
            data_source = self.db.query(DataSource).filter(DataSource.id == data_source_id).first()
            if not data_source:
                return {"success": False, "error": "数据源不存在"}
            
            # 从模板内容中提取占位符
            placeholders = await self._extract_placeholders_from_template(template)
            
            if not placeholders:
                return {"success": False, "error": "模板中未找到占位符"}
            
            # 处理每个占位符
            results = {}
            service_factory = self.integrator.get_service_factory()
            iaop_service = await service_factory.get_iaop_service()
            
            for placeholder in placeholders:
                try:
                    # 创建IAOP请求
                    iaop_request = ReportGenerationRequest(
                        placeholder_text=placeholder['text'],
                        task_type=self._classify_placeholder_type(placeholder),
                        data_source_context={
                            "data_source_id": data_source_id,
                            "data_source_name": data_source.name,
                            "source_type": data_source.source_type.value,
                            "connection_params": self._get_safe_connection_params(data_source)
                        },
                        template_context={
                            "template_id": template_id,
                            "template_name": template.name,
                            "template_type": template.template_type,
                            "placeholder_context": placeholder.get('context', {})
                        },
                        execution_mode=ExecutionMode.SEQUENTIAL,
                        user_context={
                            "user_id": user_id,
                            "execution_time": datetime.utcnow().isoformat(),
                            **(execution_context or {})
                        }
                    )
                    
                    # 使用IAOP服务处理
                    result = await iaop_service.generate_report(iaop_request)
                    results[placeholder['name']] = {
                        "success": result.success,
                        "content": result.content if result.success else None,
                        "chart_config": result.chart_config if result.success else None,
                        "narrative": result.narrative if result.success else None,
                        "error": result.error_message if not result.success else None,
                        "execution_time": result.execution_time_ms,
                        "confidence_score": result.confidence_score,
                        "source": "iaop_agent"
                    }
                    
                except Exception as e:
                    logger.error(f"IAOP处理占位符失败: {placeholder['name']}, 错误: {e}")
                    results[placeholder['name']] = {
                        "success": False,
                        "error": str(e),
                        "source": "error"
                    }
            
            # 生成处理摘要
            summary = self._generate_processing_summary(results)
            
            return {
                "success": True,
                "results": results,
                "summary": summary,
                "processed_by": "iaop_platform",
                "processing_time": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"IAOP模板处理失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def process_task_with_iaop(
        self, 
        task_id: str, 
        user_id: str,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """使用IAOP处理任务"""
        await self.initialize()
        
        try:
            # 获取任务信息
            task = self.db.query(Task).filter(Task.id == task_id).first()
            if not task:
                return {"success": False, "error": "任务不存在"}
            
            if not task.template_id or not task.data_source_id:
                return {"success": False, "error": "任务配置不完整，缺少模板或数据源"}
            
            # 使用模板处理功能
            result = await self.process_template_with_iaop(
                str(task.template_id),
                str(task.data_source_id), 
                user_id,
                {
                    "task_id": task_id,
                    "task_name": task.name,
                    "report_period": task.report_period.value if task.report_period else "monthly",
                    **(execution_context or {})
                }
            )
            
            # 添加任务特定信息
            if result["success"]:
                result["task_info"] = {
                    "task_id": task_id,
                    "task_name": task.name,
                    "schedule": task.schedule,
                    "report_period": task.report_period.value if task.report_period else None,
                    "recipients": task.recipients or []
                }
            
            return result
            
        except Exception as e:
            logger.error(f"IAOP任务处理失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_process_placeholders(
        self,
        template_content: str,
        data_source_id: str,
        user_id: str,
        variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """批量处理占位符"""
        await self.initialize()
        
        try:
            service_factory = self.integrator.get_service_factory()
            iaop_service = await service_factory.get_iaop_service()
            
            # 创建批量处理请求
            placeholder_request = PlaceholderRequest(
                template_content=template_content,
                variables=variables or {},
                data_source_context={"data_source_id": data_source_id},
                user_context={"user_id": user_id},
                execution_mode=ExecutionMode.PIPELINE
            )
            
            # 使用IAOP服务处理
            result = await iaop_service.process_placeholders(placeholder_request)
            
            return {
                "success": result.success,
                "results": [r.__dict__ for r in result.results],
                "summary": {
                    "total_placeholders": result.total_placeholders,
                    "successful_replacements": result.successful_replacements,
                    "failed_replacements": result.failed_replacements,
                    "processing_time_ms": result.processing_time_ms
                },
                "processed_by": "iaop_batch_processor"
            }
            
        except Exception as e:
            logger.error(f"IAOP批量处理失败: {e}")
            return {"success": False, "error": str(e)}
    
    async def execute_agent_directly(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """直接执行指定的Agent"""
        await self.initialize()
        
        try:
            service_factory = self.integrator.get_service_factory()
            iaop_service = await service_factory.get_iaop_service()
            
            # 创建Agent执行请求
            agent_request = AgentExecutionRequest(
                agent_name=agent_name,
                input_data=input_data,
                context=context or {},
                execution_mode=ExecutionMode.SEQUENTIAL
            )
            
            # 执行Agent
            result = await iaop_service.execute_agent(agent_request)
            
            return {
                "success": True,
                "result": result,
                "executed_by": f"iaop_agent_{agent_name}"
            }
            
        except Exception as e:
            logger.error(f"IAOP Agent执行失败: {agent_name}, 错误: {e}")
            return {"success": False, "error": str(e)}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取IAOP系统状态"""
        await self.initialize()
        
        try:
            status = self.integrator.get_system_status()
            
            # 添加集成桥接器状态
            status["bridge_status"] = {
                "initialized": self._initialized,
                "database_connected": self.db is not None,
                "last_check": datetime.utcnow().isoformat()
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取IAOP系统状态失败: {e}")
            return {"status": "error", "error": str(e)}
    
    # 私有辅助方法
    
    async def _extract_placeholders_from_template(self, template: Template) -> List[Dict[str, Any]]:
        """从模板中提取占位符"""
        try:
            # 使用现有的模板解析器
            from app.services.domain.reporting.document_pipeline import TemplateParser
            parser = TemplateParser()
            
            content = template.content or ""
            extracted = parser.extract_placeholders(content)
            
            placeholders = []
            for placeholder in extracted:
                placeholders.append({
                    "name": placeholder.get("name", ""),
                    "text": f"{{{{{placeholder.get('name', '')}}}}}", 
                    "type": placeholder.get("type", "text"),
                    "description": placeholder.get("description", ""),
                    "context": {
                        "content_type": placeholder.get("content_type", "text"),
                        "required": placeholder.get("required", True),
                        "original_type": placeholder.get("type", "text")
                    }
                })
            
            return placeholders
            
        except Exception as e:
            logger.error(f"占位符提取失败: {e}")
            return []
    
    def _classify_placeholder_type(self, placeholder: Dict[str, Any]) -> TaskType:
        """分类占位符类型"""
        placeholder_type = placeholder.get("type", "").lower()
        
        type_mapping = {
            "统计": TaskType.DATA_QUERY,
            "图表": TaskType.CHART_GENERATION, 
            "表格": TaskType.DATA_QUERY,
            "分析": TaskType.DATA_ANALYSIS,
            "日期时间": TaskType.DATA_QUERY,
            "标题": TaskType.CONTENT_GENERATION,
            "摘要": TaskType.CONTENT_GENERATION,
            "作者": TaskType.CONTENT_GENERATION,
            "变量": TaskType.DATA_EXTRACTION,
            "中文": TaskType.CONTENT_GENERATION,
            "文本": TaskType.CONTENT_GENERATION
        }
        
        return type_mapping.get(placeholder_type, TaskType.DATA_QUERY)
    
    def _get_safe_connection_params(self, data_source: DataSource) -> Dict[str, Any]:
        """获取安全的连接参数（不包含敏感信息）"""
        return {
            "source_type": data_source.source_type.value,
            "host": getattr(data_source, 'doris_fe_hosts', []) if hasattr(data_source, 'doris_fe_hosts') else [],
            "database": getattr(data_source, 'doris_database', '') if hasattr(data_source, 'doris_database') else '',
            "query_port": getattr(data_source, 'doris_query_port', 9030) if hasattr(data_source, 'doris_query_port') else 9030
            # 注意：不包含用户名和密码等敏感信息
        }
    
    def _generate_processing_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """生成处理摘要"""
        total = len(results)
        successful = len([r for r in results.values() if r.get("success", False)])
        failed = total - successful
        
        sources = {}
        execution_times = []
        confidence_scores = []
        
        for result in results.values():
            source = result.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
            
            if result.get("execution_time"):
                execution_times.append(result["execution_time"])
            
            if result.get("confidence_score"):
                confidence_scores.append(result["confidence_score"])
        
        return {
            "total_placeholders": total,
            "successful_placeholders": successful,
            "failed_placeholders": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "source_distribution": sources,
            "average_execution_time_ms": sum(execution_times) / len(execution_times) if execution_times else 0,
            "average_confidence_score": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
            "processing_grade": self._calculate_processing_grade(successful, total, confidence_scores)
        }
    
    def _calculate_processing_grade(self, successful: int, total: int, confidence_scores: List[float]) -> str:
        """计算处理等级"""
        success_rate = (successful / total * 100) if total > 0 else 0
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
        
        if success_rate >= 95 and avg_confidence >= 0.9:
            return "A+"
        elif success_rate >= 90 and avg_confidence >= 0.8:
            return "A"
        elif success_rate >= 80 and avg_confidence >= 0.7:
            return "B"
        elif success_rate >= 70 and avg_confidence >= 0.6:
            return "C"
        elif success_rate >= 60:
            return "D"
        else:
            return "F"


# 全局桥接器实例
_global_bridge = None

def get_iaop_bridge(db: Session) -> IAOPSystemBridge:
    """获取IAOP系统桥接器实例"""
    global _global_bridge
    if _global_bridge is None:
        _global_bridge = IAOPSystemBridge(db)
    return _global_bridge


# 便捷的集成函数

async def process_template_with_iaop(
    db: Session,
    template_id: str, 
    data_source_id: str, 
    user_id: str,
    execution_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """便捷的模板处理函数"""
    bridge = get_iaop_bridge(db)
    return await bridge.process_template_with_iaop(
        template_id, data_source_id, user_id, execution_context
    )


async def process_task_with_iaop(
    db: Session,
    task_id: str, 
    user_id: str,
    execution_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """便捷的任务处理函数"""
    bridge = get_iaop_bridge(db)
    return await bridge.process_task_with_iaop(task_id, user_id, execution_context)