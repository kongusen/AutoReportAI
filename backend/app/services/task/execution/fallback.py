"""
Fallback Handler

回退处理机制，负责：
- Agent执行失败时的回退处理
- 传统方法作为备用方案
- 错误恢复机制
"""

import logging
from typing import Any, Dict, Optional

from app.services.ai_integration.llm_service import AIService
from app.services.data_processing.etl.intelligent_etl_executor import IntelligentETLExecutor
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class FallbackHandler:
    """回退处理器"""
    
    def __init__(self):
        self.db = SessionLocal()
        self.ai_service = AIService(self.db)
        self.etl_executor = IntelligentETLExecutor(self.db)
    
    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        if hasattr(self, 'db') and self.db:
            try:
                self.db.close()
            except:
                pass
    
    async def fallback_placeholder_analysis(
        self,
        placeholder_data: Dict[str, Any],
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        占位符分析的回退处理
        
        Args:
            placeholder_data: 占位符数据
            data_source_id: 数据源ID
            
        Returns:
            分析结果
        """
        try:
            logger.info(f"使用传统AI服务进行占位符分析: {placeholder_data.get('name', 'unknown')}")
            
            # 使用传统AI服务
            result = await self.ai_service.analyze_placeholder_requirements(
                placeholder_data, data_source_id
            )
            
            logger.info("传统AI服务分析完成")
            return result
            
        except Exception as e:
            logger.error(f"传统AI服务分析失败: {e}")
            
            # 返回默认结果
            return {
                "placeholder": placeholder_data,
                "etl_instruction": {
                    "query_type": "fallback",
                    "description": f"回退处理占位符: {placeholder_data.get('name', 'unknown')}",
                    "error": str(e)
                },
                "data_source_id": data_source_id,
                "fallback_used": True
            }
    
    async def fallback_data_query(
        self,
        etl_instruction: Dict[str, Any],
        data_source_id: str
    ) -> Dict[str, Any]:
        """
        数据查询的回退处理
        
        Args:
            etl_instruction: ETL指令
            data_source_id: 数据源ID
            
        Returns:
            查询结果
        """
        try:
            logger.info("使用传统ETL执行器进行数据查询")
            
            # 使用传统ETL执行器
            result = self.etl_executor.execute_instruction(
                etl_instruction, data_source_id
            )
            
            logger.info("传统ETL执行器查询完成")
            return result
            
        except Exception as e:
            logger.error(f"传统ETL执行器查询失败: {e}")
            
            # 返回默认结果
            return {
                "status": "failed",
                "error": str(e),
                "fallback_used": True,
                "data": None
            }
    
    async def fallback_content_generation(
        self,
        template_content: str,
        query_results: list
    ) -> str:
        """
        内容生成的回退处理
        
        Args:
            template_content: 模板内容
            query_results: 查询结果列表
            
        Returns:
            生成的内容
        """
        try:
            logger.info("使用传统方法进行内容生成")
            
            # 简单的占位符替换
            filled_content = template_content
            
            for result in query_results:
                if result and isinstance(result, dict):
                    placeholder_name = result.get('placeholder_name')
                    data = result.get('data')
                    
                    if placeholder_name and data:
                        placeholder_pattern = f"{{{{{placeholder_name}}}}}"
                        
                        # 简单的数据格式化
                        if isinstance(data, list):
                            replacement = str(data[0]) if data else "无数据"
                        elif isinstance(data, dict):
                            replacement = str(next(iter(data.values()))) if data else "无数据"
                        else:
                            replacement = str(data)
                        
                        filled_content = filled_content.replace(placeholder_pattern, replacement)
            
            logger.info("传统内容生成完成")
            return filled_content
            
        except Exception as e:
            logger.error(f"传统内容生成失败: {e}")
            
            # 返回原始模板内容
            return template_content
    
    def handle_agent_failure(
        self,
        error: str,
        task_id: int,
        fallback_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理Agent执行失败
        
        Args:
            error: 错误信息
            task_id: 任务ID
            fallback_data: 回退数据
            
        Returns:
            处理结果
        """
        logger.warning(f"Agent执行失败，启用回退机制 - 任务ID: {task_id}, 错误: {error}")
        
        # 记录失败信息
        failure_info = {
            "task_id": task_id,
            "error": error,
            "fallback_triggered": True,
            "timestamp": self._get_current_timestamp()
        }
        
        # 如果有回退数据，使用回退数据
        if fallback_data:
            failure_info["fallback_data"] = fallback_data
            logger.info(f"使用提供的回退数据 - 任务ID: {task_id}")
        
        return failure_info
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    async def comprehensive_fallback(
        self,
        task_type: str,
        task_data: Dict[str, Any],
        original_error: str
    ) -> Dict[str, Any]:
        """
        综合回退处理
        
        Args:
            task_type: 任务类型
            task_data: 任务数据
            original_error: 原始错误
            
        Returns:
            回退处理结果
        """
        logger.info(f"开始综合回退处理 - 任务类型: {task_type}")
        
        try:
            if task_type == "placeholder_analysis":
                return await self.fallback_placeholder_analysis(
                    task_data.get("placeholder_data", {}),
                    task_data.get("data_source_id", "")
                )
            
            elif task_type == "data_query":
                return await self.fallback_data_query(
                    task_data.get("etl_instruction", {}),
                    task_data.get("data_source_id", "")
                )
            
            elif task_type == "content_generation":
                return await self.fallback_content_generation(
                    task_data.get("template_content", ""),
                    task_data.get("query_results", [])
                )
            
            else:
                logger.warning(f"未知的任务类型: {task_type}")
                return {
                    "status": "unknown_task_type",
                    "error": f"未知的任务类型: {task_type}",
                    "fallback_used": True
                }
                
        except Exception as e:
            logger.error(f"综合回退处理失败: {e}")
            return {
                "status": "fallback_failed",
                "error": str(e),
                "original_error": original_error,
                "fallback_used": True
            }
