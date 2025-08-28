"""
LLM服务适配器 - 将独立LLM服务器集成到IAOP平台

为IAOP Agent提供统一的LLM调用接口，连接到独立的LLM服务器
"""

import json
import re
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ...llm import (
    get_llm_client,
    LLMClientConfig,
    call_llm,
    call_llm_with_system_prompt
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class IAOPLLMService:
    """IAOP平台的LLM服务适配器"""
    
    def __init__(self, db: Session = None, llm_server_url: str = None, user_id: str = None):
        self.db = db
        self.llm_server_url = llm_server_url or self._get_default_llm_server_url()
        self.user_id = user_id  # 保留用于日志记录
        
        # 从LLM服务器配置获取API密钥
        api_key = self._get_api_key()
        
        # 配置LLM客户端
        self.client_config = LLMClientConfig(
            base_url=self.llm_server_url,
            api_key=api_key,
            timeout=60,
            max_retries=2
        )
        
        self.client = get_llm_client(self.client_config)
    
    def _get_api_key(self) -> Optional[str]:
        """从LLM服务器配置获取API密钥"""
        if not self.db:
            logger.warning("数据库会话未提供，无法获取API密钥")
            return None
            
        try:
            from app.crud.crud_llm_server import crud_llm_server
            
            # 优先获取健康的服务器
            healthy_servers = crud_llm_server.get_healthy_servers(self.db)
            if healthy_servers:
                server = healthy_servers[0]
                if server.api_key:
                    logger.info(f"使用健康LLM服务器的API密钥: {server.name}")
                    return server.api_key
                else:
                    logger.warning(f"健康服务器 {server.name} 未配置API密钥")
            
            # 如果没有健康服务器，尝试活跃的服务器
            active_servers = crud_llm_server.get_active_servers(self.db)
            if active_servers:
                server = active_servers[0]
                if server.api_key:
                    logger.info(f"使用活跃LLM服务器的API密钥: {server.name}")
                    return server.api_key
                else:
                    logger.warning(f"活跃服务器 {server.name} 未配置API密钥")
            
            logger.error("未找到任何可用的LLM服务器配置")
            return None
            
        except Exception as e:
            logger.error(f"获取LLM服务器API密钥失败: {e}")
            return None
    
    def _get_default_llm_server_url(self) -> str:
        """从数据库获取默认的LLM服务器URL"""
        try:
            if self.db:
                from app.crud.crud_llm_server import crud_llm_server
                # 获取健康的服务器
                healthy_servers = crud_llm_server.get_healthy_servers(self.db)
                if healthy_servers:
                    server = healthy_servers[0]
                    logger.info(f"IAOP使用健康的LLM服务器: {server.name} ({server.base_url})")
                    return server.base_url
                else:
                    # 获取活跃的服务器
                    active_servers = crud_llm_server.get_active_servers(self.db)
                    if active_servers:
                        server = active_servers[0]
                        logger.warning(f"IAOP使用不健康的LLM服务器: {server.name} ({server.base_url})")
                        return server.base_url
        except Exception as e:
            logger.warning(f"IAOP获取数据库LLM配置失败: {e}")
        
        # 如果无法从数据库获取，使用默认配置
        logger.warning("IAOP使用默认LLM配置: localhost:8001")
        return "http://localhost:8001"
    
    def _parse_json_response(self, response_text: str, method_name: str = "") -> Dict[str, Any]:
        """安全地解析LLM返回的JSON响应"""
        if not response_text or not response_text.strip():
            logger.warning(f"{method_name}: 收到空响应")
            return {}
        
        # 记录原始响应（用于调试）
        logger.debug(f"{method_name}: 原始响应长度: {len(response_text)}")
        logger.debug(f"{method_name}: 响应前100字符: {response_text[:100]}")
        
        # 预处理：移除markdown代码块标记
        clean_text = response_text.strip()
        
        # 移除开始的markdown标记
        if clean_text.startswith('```json'):
            clean_text = clean_text[7:].strip()
            logger.debug(f"{method_name}: 移除```json标记")
        elif clean_text.startswith('```'):
            clean_text = clean_text[3:].strip()
            logger.debug(f"{method_name}: 移除```标记")
        
        # 移除结尾的markdown标记
        if clean_text.endswith('```'):
            clean_text = clean_text[:-3].strip()
            logger.debug(f"{method_name}: 移除结尾```标记")
        
        # 记录清理后的文本
        logger.debug(f"{method_name}: 清理后文本长度: {len(clean_text)}")
        logger.debug(f"{method_name}: 清理后前100字符: {clean_text[:100]}")
        
        try:
            # 尝试解析清理后的文本
            result = json.loads(clean_text)
            logger.debug(f"{method_name}: JSON解析成功")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"{method_name}: 清理后的文本JSON解析失败: {e}，尝试提取JSON内容")
            
        # 尝试提取JSON部分（使用清理后的文本）
        # 查找最外层的花括号
        start_idx = clean_text.find('{')
        if start_idx == -1:
            logger.warning(f"{method_name}: 响应中未找到JSON开始标记")
            return {}
        
        # 从开始位置查找匹配的结束花括号
        bracket_count = 0
        end_idx = -1
        for i, char in enumerate(clean_text[start_idx:], start_idx):
            if char == '{':
                bracket_count += 1
            elif char == '}':
                bracket_count -= 1
                if bracket_count == 0:
                    end_idx = i + 1
                    break
        
        if end_idx == -1:
            logger.warning(f"{method_name}: 未找到匹配的JSON结束标记")
            return {}
        
        json_text = clean_text[start_idx:end_idx]
        logger.debug(f"{method_name}: 提取的JSON长度: {len(json_text)}")
        logger.debug(f"{method_name}: 提取的JSON前200字符: {json_text[:200]}")
        
        try:
            result = json.loads(json_text)
            logger.debug(f"{method_name}: 提取JSON解析成功")
            return result
        except json.JSONDecodeError as e:
            logger.error(f"{method_name}: JSON解析失败: {e}")
            logger.error(f"{method_name}: 问题JSON完整内容: {json_text}")
            return {}
        
    async def initialize(self):
        """初始化LLM服务"""
        try:
            await self.client.initialize()
            logger.info(f"✅ IAOP LLM服务已连接到: {self.llm_server_url}")
        except Exception as e:
            logger.error(f"❌ IAOP LLM服务初始化失败: {e}")
            raise
    
    async def understand_placeholder_semantics(
        self,
        placeholder_type: str,
        description: str,
        context: str,
        available_fields: List[str] = None
    ) -> Dict[str, Any]:
        """理解占位符语义"""
        system_prompt = f"""
        你是一个智能占位符理解专家，专门分析中文占位符的语义并提供数据字段匹配建议。

        占位符类型说明：
        - 周期: 时间相关的占位符，如年份、日期、时间段
        - 区域: 地理区域相关，如省份、城市、地区
        - 统计: 统计数据相关，如数量、比例、平均值
        - 图表: 图表可视化相关，如折线图、饼图、柱状图

        请分析占位符并返回JSON格式的理解结果，包含：
        1. semantic_meaning: 语义含义解释
        2. data_type: 数据类型 (string, integer, float, date, percentage)
        3. field_suggestions: 推荐的数据字段匹配
        4. calculation_needed: 是否需要计算
        5. aggregation_type: 聚合类型 (sum, count, avg, max, min)
        6. confidence: 理解置信度 (0-1)
        """
        
        user_message = f"""
        占位符类型: {placeholder_type}
        描述: {description}
        上下文: {context}
        可用字段: {available_fields if available_fields else "未提供"}

        请分析这个占位符的语义含义并提供字段匹配建议。
        """
        
        try:
            response = await call_llm_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.1,
                max_tokens=800
            )
            
            result = self._parse_json_response(response, "understand_placeholder_semantics")
            if not result:
                raise ValueError("Empty JSON response")
            return result
            
        except Exception as e:
            logger.warning(f"占位符语义理解失败: {e}")
            return {
                "semantic_meaning": f"无法理解占位符: {description}",
                "data_type": "string",
                "field_suggestions": [],
                "calculation_needed": False,
                "aggregation_type": None,
                "confidence": 0.0
            }
    
    async def generate_sql_query(
        self,
        requirement: str,
        table_schema: Dict[str, Any],
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """生成SQL查询"""
        system_prompt = """
        你是一个SQL生成专家，根据用户需求和表结构生成准确的SQL查询语句。

        要求：
        1. 生成的SQL必须符合标准SQL语法
        2. 考虑性能优化，适当使用索引
        3. 处理可能的边界情况
        4. 返回JSON格式，包含sql、explanation、estimated_complexity
        """
        
        user_message = f"""
        用户需求: {requirement}
        表结构: {json.dumps(table_schema, ensure_ascii=False, indent=2)}
        上下文: {json.dumps(context or {}, ensure_ascii=False, indent=2)}

        请生成相应的SQL查询语句。
        """
        
        try:
            response = await call_llm_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.1,
                max_tokens=1000
            )
            
            result = self._parse_json_response(response, "generate_sql_query")
            if not result:
                raise ValueError("Empty JSON response")
            return result
            
        except Exception as e:
            logger.error(f"SQL生成失败: {e}")
            return {
                "sql": "SELECT 1 as placeholder",
                "explanation": f"SQL生成失败: {str(e)}",
                "estimated_complexity": "unknown"
            }
    
    async def analyze_data_insights(
        self,
        data_summary: Dict[str, Any],
        context: str = ""
    ) -> Dict[str, Any]:
        """分析数据洞察"""
        system_prompt = """
        你是一个数据分析专家，专门从数据中提取有价值的洞察和趋势。

        请分析数据并返回JSON格式的洞察报告，包含：
        1. key_insights: 关键洞察列表
        2. trends: 趋势分析
        3. anomalies: 异常值识别
        4. recommendations: 行动建议
        5. confidence: 分析置信度
        """
        
        user_message = f"""
        数据摘要: {json.dumps(data_summary, ensure_ascii=False, indent=2)}
        分析上下文: {context}

        请分析这些数据并提供专业的洞察报告。
        """
        
        try:
            response = await call_llm_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                max_tokens=1200
            )
            
            result = self._parse_json_response(response, "analyze_data_insights")
            if not result:
                raise ValueError("Empty JSON response")
            return result
            
        except Exception as e:
            logger.error(f"数据洞察分析失败: {e}")
            return {
                "key_insights": ["数据洞察分析暂时不可用"],
                "trends": [],
                "anomalies": [],
                "recommendations": [],
                "confidence": 0.0
            }
    
    async def generate_chart_config(
        self,
        chart_type: str,
        data_structure: Dict[str, Any],
        requirements: str = ""
    ) -> Dict[str, Any]:
        """生成图表配置"""
        system_prompt = """
        你是一个数据可视化专家，专门生成ECharts图表配置。

        请根据图表类型和数据结构生成ECharts配置，返回JSON格式包含：
        1. echarts_config: 完整的ECharts配置对象
        2. chart_options: 图表选项说明
        3. data_mapping: 数据字段映射
        4. styling_suggestions: 样式建议
        """
        
        user_message = f"""
        图表类型: {chart_type}
        数据结构: {json.dumps(data_structure, ensure_ascii=False, indent=2)}
        特殊要求: {requirements}

        请生成相应的ECharts配置。
        """
        
        try:
            response = await call_llm_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.2,
                max_tokens=1500
            )
            
            result = self._parse_json_response(response, "generate_chart_config")
            if not result:
                raise ValueError("Empty JSON response")
            return result
            
        except Exception as e:
            logger.error(f"图表配置生成失败: {e}")
            return {
                "echarts_config": {
                    "title": {"text": "图表生成失败"},
                    "tooltip": {},
                    "xAxis": {"data": []},
                    "yAxis": {},
                    "series": []
                },
                "chart_options": {"error": str(e)},
                "data_mapping": {},
                "styling_suggestions": []
            }
    
    async def generate_narrative_text(
        self,
        content_type: str,
        data_context: Dict[str, Any],
        style_requirements: str = ""
    ) -> str:
        """生成叙述性文本"""
        system_prompt = f"""
        你是一个专业的商业报告撰写专家，擅长将数据分析结果转化为清晰、专业的中文报告内容。

        内容类型: {content_type}
        写作要求：
        1. 语言专业、简洁明了
        2. 逻辑结构清晰
        3. 突出关键数据和趋势
        4. 提供可操作的洞察
        {f"5. 特殊要求: {style_requirements}" if style_requirements else ""}
        """
        
        user_message = f"""
        数据上下文: {json.dumps(data_context, ensure_ascii=False, indent=2)}

        请基于以上数据生成专业的{content_type}内容。
        """
        
        try:
            response = await call_llm_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.4,
                max_tokens=1000
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"文本生成失败: {e}")
            return f"文本生成暂时不可用，请稍后再试。错误: {str(e)}"
    
    async def optimize_content(
        self,
        content: str,
        optimization_type: str = "general",
        target_audience: str = "business"
    ) -> str:
        """优化内容质量"""
        system_prompt = f"""
        你是一个内容优化专家，专门优化中文商业内容的质量。

        优化类型: {optimization_type}
        目标受众: {target_audience}
        
        优化要求：
        1. 保持内容的准确性和完整性
        2. 改善语言流畅性和专业性
        3. 确保逻辑结构清晰
        4. 使用恰当的商业术语
        5. 提升可读性和说服力
        """
        
        user_message = f"""
        需要优化的内容：
        {content}

        请对以上内容进行专业优化。
        """
        
        try:
            response = await call_llm_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                max_tokens=len(content) + 500  # 给优化后的内容一些余量
            )
            
            return response.strip()
            
        except Exception as e:
            logger.warning(f"内容优化失败: {e}")
            return content  # 返回原始内容
    
    async def validate_data_quality(
        self,
        data: Dict[str, Any],
        expected_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """验证数据质量"""
        system_prompt = """
        你是一个数据质量验证专家，专门检查数据的一致性和合理性。

        请检查数据并返回JSON格式的验证结果，包含：
        1. is_valid: 数据是否有效
        2. issues: 发现的问题列表
        3. suggestions: 修复建议
        4. quality_score: 数据质量评分 (0-100)
        """
        
        user_message = f"""
        待验证数据:
        {json.dumps(data, ensure_ascii=False, indent=2)}

        期望的数据结构:
        {json.dumps(expected_schema, ensure_ascii=False, indent=2)}

        请验证数据的一致性和合理性。
        """
        
        try:
            response = await call_llm_with_system_prompt(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.1,
                max_tokens=800
            )
            
            result = self._parse_json_response(response, "validate_data_quality")
            if not result:
                raise ValueError("Empty JSON response")
            return result
            
        except Exception as e:
            logger.warning(f"数据质量验证失败: {e}")
            return {
                "is_valid": True,
                "issues": [],
                "suggestions": [],
                "quality_score": 50
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            server_health = await self.client.health_check()
            client_stats = self.client.get_client_stats()
            
            return {
                "status": "healthy",
                "server_health": server_health,
                "client_stats": client_stats,
                "connection_url": self.llm_server_url
            }
            
        except Exception as e:
            logger.error(f"LLM服务健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "connection_url": self.llm_server_url
            }
    
    async def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        try:
            providers = await self.client.get_available_providers()
            models = []
            
            for provider in providers:
                models.extend(provider.get("models", []))
            
            return list(set(models))  # 去重
            
        except Exception as e:
            logger.error(f"获取可用模型失败: {e}")
            return []
    
    async def cleanup(self):
        """清理资源"""
        if self.client:
            await self.client.cleanup()


# 全局IAOP LLM服务实例
_global_iaop_llm_service: Optional[IAOPLLMService] = None

def get_iaop_llm_service(db: Session = None, user_id: str = None) -> IAOPLLMService:
    """获取IAOP LLM服务实例"""
    # 尝试从数据库获取活跃的LLM服务器配置
    llm_server_url = "http://localhost:8001"  # 默认值
    api_key = None
    
    if db:
        try:
            from app.models.llm_server import LLMServer
            # 获取第一个活跃的LLM服务器
            active_server = db.query(LLMServer).filter(
                LLMServer.is_active == True
            ).first()
            
            if active_server and active_server.base_url:
                llm_server_url = active_server.base_url
                api_key = active_server.api_key if active_server.auth_enabled else None
                logger.info(f"使用数据库配置的LLM服务器: {llm_server_url}")
                if api_key:
                    logger.info("API密钥已配置")
                else:
                    logger.warning("未配置API密钥")
            else:
                logger.warning("数据库中未找到活跃的LLM服务器，使用默认配置")
                
        except Exception as e:
            logger.warning(f"获取LLM服务器配置失败，使用默认值: {e}")
    
    # 创建新实例并传递API密钥
    service = IAOPLLMService(db, llm_server_url, user_id)
    
    # 如果数据库有API密钥配置，更新服务配置
    if api_key:
        service.client_config.api_key = api_key
        # 重新创建客户端以使用新的API密钥
        service.client = get_llm_client(service.client_config)
    
    return service

def reset_iaop_llm_service():
    """重置全局IAOP LLM服务实例（用于配置更新后重新初始化）"""
    global _global_iaop_llm_service
    if _global_iaop_llm_service:
        logger.info("重置IAOP LLM服务实例")
    _global_iaop_llm_service = None