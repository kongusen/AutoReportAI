"""
基础分析Agent
提供通用的分析功能，包括AI分析、数据验证和错误处理
"""

import logging
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session
import time

from ..core_types import BaseAgent, AgentConfig, AgentType
from ..core import get_ai_service, get_analysis_parser, get_error_handler


class BaseAnalysisAgent(BaseAgent):
    """基础分析Agent - 提供通用的分析功能"""
    
    def __init__(self, db_session: Session = None, config: AgentConfig = None):
        # 如果没有提供配置，创建默认配置
        if config is None:
            config = AgentConfig(
                agent_id=f"analysis_agent_{id(self)}",
                agent_type=AgentType.ANALYSIS,
                name="BaseAnalysisAgent",
                description="基础分析Agent"
            )
        
        super().__init__(config)
        self.db_session = db_session
        self.ai_service = get_ai_service(db_session)
        self.response_parser = get_analysis_parser()
        self.error_handler = get_error_handler()
        self.logger = logging.getLogger(__name__)
    
    async def analyze_with_ai(
        self,
        context: str,
        prompt: str,
        task_type: str,
        analysis_type: str = "general",
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用AI服务进行分析
        
        Args:
            context: 分析上下文
            prompt: 分析提示
            task_type: 任务类型
            analysis_type: 分析类型 (general, relationship, semantic, quality)
            **kwargs: 其他参数
            
        Returns:
            分析结果
        """
        try:
            # 调用AI服务进行分析
            response = await self.ai_service.analyze_with_context(
                context=context,
                prompt=prompt,
                task_type=task_type,
                **kwargs
            )
            
            # 解析响应
            if analysis_type in ["relationship", "semantic", "quality"]:
                result = self.response_parser.parse_analysis_response(response, analysis_type)
            else:
                result = self.response_parser.parse(response)
            
            return result
            
        except Exception as e:
            # 错误处理
            error_info = self.error_handler.handle_error(
                e, 
                context=f"AI分析失败: {task_type}",
                prompt=prompt,
                analysis_type=analysis_type
            )
            
            # 尝试恢复
            recovery_result = self.error_handler.try_recovery(error_info)
            if recovery_result:
                return recovery_result
            
            # 返回错误结果
            return self._get_error_result(str(e), analysis_type)
    
    def validate_analysis_data(
        self, 
        data: Dict[str, Any], 
        required_fields: List[str]
    ) -> bool:
        """
        验证分析数据
        
        Args:
            data: 要验证的数据
            required_fields: 必需字段列表
            
        Returns:
            验证结果
        """
        if not data:
            self.logger.warning("数据为空")
            return False
        
        for field in required_fields:
            if field not in data:
                self.logger.warning(f"缺少必需字段: {field}")
                return False
        
        return True
    
    def build_context_template(self, template: str, **kwargs) -> str:
        """
        构建上下文模板
        
        Args:
            template: 模板字符串
            **kwargs: 模板参数
            
        Returns:
            构建后的上下文
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            self.logger.error(f"模板参数缺失: {e}")
            return template
    
    async def get_analysis_summary(
        self, 
        data: Dict[str, Any], 
        summary_prompt: str
    ) -> Dict[str, Any]:
        """
        获取分析摘要
        
        Args:
            data: 分析数据
            summary_prompt: 摘要提示
            
        Returns:
            分析摘要
        """
        try:
            context = "分析摘要生成"
            response = await self.ai_service.analyze_with_context(
                context=context,
                prompt=summary_prompt,
                task_type="analysis_summary"
            )
            
            return {
                "summary": response,
                "data_info": self._extract_data_info(data)
            }
            
        except Exception as e:
            error_info = self.error_handler.handle_error(
                e, 
                context="获取分析摘要失败"
            )
            
            return {
                "summary": f"摘要生成失败: {str(e)}",
                "data_info": self._extract_data_info(data)
            }
    
    def _extract_data_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """提取数据信息"""
        info = {}
        
        if isinstance(data, dict):
            if "tables" in data:
                info["table_count"] = len(data.get("tables", []))
                info["total_columns"] = sum(
                    len(table.get("columns", [])) 
                    for table in data.get("tables", [])
                )
            elif "data" in data:
                info["record_count"] = len(data.get("data", []))
        
        return info
    
    def _get_error_result(self, error_message: str, analysis_type: str = "general") -> Dict[str, Any]:
        """获取错误结果"""
        base_error = {
            "error": error_message,
            "success": False,
            "insights": [f"分析失败: {error_message}"]
        }
        
        # 根据分析类型添加特定字段
        if analysis_type == "relationship":
            base_error.update({
                "relationships": [],
                "confidence_scores": {},
                "recommendations": []
            })
        elif analysis_type == "semantic":
            base_error.update({
                "business_categories": {},
                "semantic_patterns": {},
                "data_entities": [],
                "domain_insights": [f"分析失败: {error_message}"]
            })
        elif analysis_type == "quality":
            base_error.update({
                "overall_score": 0.0,
                "table_quality": [],
                "recommendations": [f"分析失败: {error_message}"],
                "quality_insights": [],
                "best_practices": []
            })
        
        return base_error
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        health = await super().health_check()
        
        # 检查AI服务
        try:
            ai_health = await self.ai_service.health_check()
            health["ai_service"] = ai_health
        except Exception as e:
            health["ai_service"] = {"status": "error", "error": str(e)}
            health["healthy"] = False
        
        # 检查解析器
        try:
            test_response = '{"test": "data"}'
            parsed = self.response_parser.parse(test_response)
            health["response_parser"] = "healthy" if "test" in parsed else "error"
        except Exception as e:
            health["response_parser"] = f"error: {str(e)}"
            health["healthy"] = False
        
        # 检查错误处理器
        health["error_handler"] = "healthy"
        
        return health
    
    async def execute(
        self, 
        input_data: Any, 
        context: Dict[str, Any] = None
    ) -> "AgentResult":
        """
        执行Agent的主要功能
        
        Args:
            input_data: 输入数据
            context: 上下文信息
            
        Returns:
            AgentResult 包含执行结果
        """
        from ..core_types import AgentResult
        
        context = context or {}
        start_time = time.time()
        
        try:
            # 根据输入数据类型选择分析方法
            if isinstance(input_data, dict) and "tables" in input_data:
                # 表结构分析
                result = await self.analyze_with_ai(
                    context=str(input_data),
                    prompt="请分析这个表结构",
                    task_type="schema_analysis"
                )
            else:
                # 通用分析
                result = await self.analyze_with_ai(
                    context=str(input_data),
                    prompt="请分析这些数据",
                    task_type="general_analysis"
                )
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                success=True,
                agent_id=self.config.agent_id,
                agent_type=self.config.agent_type,
                data=result,
                execution_time=execution_time,
                metadata={
                    "analysis_type": "general",
                    "input_size": len(str(input_data))
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return AgentResult(
                success=False,
                agent_id=self.config.agent_id,
                agent_type=self.config.agent_type,
                error_message=str(e),
                execution_time=execution_time,
                metadata={
                    "analysis_type": "general",
                    "input_size": len(str(input_data))
                }
            )
