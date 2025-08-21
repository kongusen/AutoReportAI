"""
Context-Aware Multi-Database Agent

基于上下文工程的多数据库智能代理，展示如何使用新的上下文工程架构：
1. 上下文感知的决策
2. 智能提示生成
3. 对话历史管理
4. 能力注册和发现
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from sqlalchemy.orm import Session

from ..core import (
    ContextAwareAgent, AgentContext, ContextScope,
    PromptEngine, create_default_prompt_engine,
    get_context_manager, get_agent_registry
)

logger = logging.getLogger(__name__)


class ContextAwareMultiDatabaseAgent(ContextAwareAgent):
    """上下文感知的多数据库代理"""
    
    def __init__(self, db_session: Session = None, user_id: str = None):
        # 初始化上下文管理器
        context_manager = get_context_manager()
        
        super().__init__("multi_database_agent", context_manager)
        
        self.db_session = db_session
        self.user_id = user_id
        
        # 初始化提示引擎
        self.prompt_engine = create_default_prompt_engine()
        
        # 注册Agent能力
        self._register_capabilities()
        
        # 声明所需的上下文
        self.require_context(
            'data_source_info',
            'schema_metadata',
            'user_preferences'
        )
        
        # 初始化AI服务
        self._init_ai_service()
        
        logger.info(f"ContextAwareMultiDatabaseAgent initialized for user: {user_id}")
    
    def _register_capabilities(self):
        """注册Agent能力"""
        self.register_capability(
            "analyze_placeholder",
            "分析占位符并生成相应的SQL查询",
            metadata={
                "input_schema": {
                    "placeholder_text": {"type": "string", "required": True},
                    "template_context": {"type": "object", "required": False},
                    "data_source_id": {"type": "string", "required": True}
                },
                "output_schema": {
                    "analysis": {"type": "object"},
                    "sql_query": {"type": "string"},
                    "confidence": {"type": "number"}
                },
                "tags": ["sql", "analysis", "placeholder"],
                "requirements": ["database_access", "ai_service"]
            }
        )
        
        self.register_capability(
            "generate_sql_query", 
            "根据自然语言描述生成SQL查询",
            metadata={
                "input_schema": {
                    "description": {"type": "string", "required": True},
                    "data_source_id": {"type": "string", "required": True},
                    "constraints": {"type": "array", "required": False}
                },
                "output_schema": {
                    "sql_query": {"type": "string"},
                    "explanation": {"type": "string"},
                    "estimated_complexity": {"type": "string"}
                },
                "tags": ["sql", "generation", "nlp"],
                "requirements": ["database_access", "ai_service"]
            }
        )
        
        self.register_capability(
            "optimize_query",
            "优化SQL查询性能",
            metadata={
                "input_schema": {
                    "original_query": {"type": "string", "required": True},
                    "data_source_id": {"type": "string", "required": True}
                },
                "output_schema": {
                    "optimized_query": {"type": "string"},
                    "optimizations": {"type": "array"},
                    "performance_gain": {"type": "string"}
                },
                "tags": ["sql", "optimization", "performance"],
                "requirements": ["database_access", "query_analyzer"]
            }
        )
    
    def _init_ai_service(self):
        """初始化AI服务"""
        try:
            from app.services.agents.core.ai_service import UnifiedAIService
            if self.user_id and self.db_session:
                from app.core.ai_service_factory import UserAIServiceFactory
                factory = UserAIServiceFactory()
                self.ai_service = factory.get_user_ai_service(self.user_id)
            else:
                self.ai_service = UnifiedAIService(db_session=self.db_session)
        except Exception as e:
            logger.warning(f"AI service initialization failed: {e}")
            self.ai_service = None
    
    async def _execute_action(self, context: AgentContext, action: str, 
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体的Agent操作"""
        if action == "analyze_placeholder":
            return await self._analyze_placeholder(context, parameters)
        elif action == "generate_sql_query":
            return await self._generate_sql_query(context, parameters)
        elif action == "optimize_query":
            return await self._optimize_query(context, parameters)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def _analyze_placeholder(self, context: AgentContext, 
                                 parameters: Dict[str, Any]) -> Dict[str, Any]:
        """分析占位符"""
        placeholder_text = parameters.get('placeholder_text')
        template_context = parameters.get('template_context', {})
        data_source_id = parameters.get('data_source_id')
        
        if not placeholder_text:
            raise ValueError("placeholder_text is required")
        
        # 更新上下文
        self.update_context(context, 'current_placeholder', placeholder_text, ContextScope.REQUEST)
        self.update_context(context, 'current_data_source', data_source_id, ContextScope.REQUEST)
        
        # 构建上下文感知的提示
        additional_context = {
            'placeholder_text': placeholder_text,
            'template_context': template_context,
            'data_source_id': data_source_id,
            'data_source_type': self._get_data_source_type(context, data_source_id),
            'available_tables': self._get_available_tables(context, data_source_id),
            'schema_info': self._get_schema_info(context, data_source_id)
        }
        
        # 生成分析提示
        analysis_prompt = self.prompt_engine.generate_prompt(
            'placeholder_analysis',
            context,
            additional_context
        )
        
        # 调用AI服务分析
        if self.ai_service:
            try:
                ai_response = await self.ai_service.complete(analysis_prompt)
                analysis_result = self._parse_ai_response(ai_response)
                
                # 记录分析结果到上下文
                self.update_context(
                    context, 
                    'last_analysis_result', 
                    analysis_result, 
                    ContextScope.TASK
                )
                
                return {
                    'success': True,
                    'analysis': analysis_result,
                    'sql_query': analysis_result.get('sql_logic', ''),
                    'confidence': analysis_result.get('confidence', 0.8),
                    'context_used': additional_context
                }
                
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'fallback_analysis': self._fallback_placeholder_analysis(placeholder_text)
                }
        else:
            # 回退到基于规则的分析
            return {
                'success': True,
                'analysis': self._fallback_placeholder_analysis(placeholder_text),
                'sql_query': '',
                'confidence': 0.5,
                'note': 'Used fallback analysis due to AI service unavailability'
            }
    
    async def _generate_sql_query(self, context: AgentContext,
                                parameters: Dict[str, Any]) -> Dict[str, Any]:
        """生成SQL查询"""
        description = parameters.get('description')
        data_source_id = parameters.get('data_source_id') 
        constraints = parameters.get('constraints', [])
        
        if not description:
            raise ValueError("description is required")
        
        # 构建上下文
        additional_context = {
            'query_description': description,
            'data_source_id': data_source_id,
            'data_source_type': self._get_data_source_type(context, data_source_id),
            'available_tables': self._get_available_tables(context, data_source_id),
            'constraints': constraints,
            'user_preferences': context.get_context('user_preferences', {})
        }
        
        # 生成SQL提示
        system_prompt = self.prompt_engine.generate_prompt(
            'sql_analysis_system',
            context,
            additional_context
        )
        
        user_prompt = f"请根据以下描述生成SQL查询：{description}"
        if constraints:
            user_prompt += f"\n约束条件：{', '.join(constraints)}"
        
        # 多轮对话
        conversation = self.prompt_engine.generate_multi_turn_prompt(
            context.session_id,
            [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        
        if self.ai_service:
            try:
                ai_response = await self.ai_service.chat_complete(conversation)
                
                return {
                    'success': True,
                    'sql_query': ai_response.get('content', ''),
                    'explanation': 'Generated by AI service',
                    'estimated_complexity': 'medium',
                    'conversation_id': context.session_id
                }
                
            except Exception as e:
                logger.error(f"SQL generation failed: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
        else:
            return {
                'success': False,
                'error': 'AI service not available'
            }
    
    async def _optimize_query(self, context: AgentContext,
                            parameters: Dict[str, Any]) -> Dict[str, Any]:
        """优化SQL查询"""
        original_query = parameters.get('original_query')
        data_source_id = parameters.get('data_source_id')
        
        if not original_query:
            raise ValueError("original_query is required")
        
        # 简单的优化规则示例
        optimizations = []
        optimized_query = original_query
        
        # 基于规则的优化
        if 'SELECT *' in original_query:
            optimizations.append("建议指定具体字段而不是使用SELECT *")
        
        if 'ORDER BY' in original_query and 'LIMIT' not in original_query:
            optimizations.append("考虑添加LIMIT以提高性能")
        
        return {
            'success': True,
            'optimized_query': optimized_query,
            'optimizations': optimizations,
            'performance_gain': 'low' if not optimizations else 'medium'
        }
    
    def _get_data_source_type(self, context: AgentContext, data_source_id: str) -> str:
        """获取数据源类型"""
        # 从上下文获取或查询数据库
        data_source_info = context.get_context('data_source_info', {})
        return data_source_info.get(data_source_id, {}).get('type', 'unknown')
    
    def _get_available_tables(self, context: AgentContext, data_source_id: str) -> List[str]:
        """获取可用表列表"""
        # 从上下文获取或查询schema
        schema_metadata = context.get_context('schema_metadata', {})
        return schema_metadata.get(data_source_id, {}).get('tables', [])
    
    def _get_schema_info(self, context: AgentContext, data_source_id: str) -> Dict[str, Any]:
        """获取schema信息"""
        schema_metadata = context.get_context('schema_metadata', {})
        return schema_metadata.get(data_source_id, {})
    
    def _parse_ai_response(self, response: str) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 尝试解析JSON响应
            if response.strip().startswith('{'):
                return json.loads(response)
            else:
                # 文本响应的简单解析
                return {
                    'analysis': response,
                    'confidence': 0.7
                }
        except json.JSONDecodeError:
            return {
                'analysis': response,
                'confidence': 0.6,
                'parse_error': True
            }
    
    def _fallback_placeholder_analysis(self, placeholder_text: str) -> Dict[str, Any]:
        """回退的占位符分析"""
        # 基于规则的简单分析
        analysis = {
            'business_meaning': f"占位符 '{placeholder_text}' 的含义需要进一步分析",
            'data_type': 'string',  # 默认类型
            'suggested_source': 'unknown'
        }
        
        # 基于关键词的简单推断
        text_lower = placeholder_text.lower()
        if any(keyword in text_lower for keyword in ['count', 'sum', 'total', '数量', '总计']):
            analysis['data_type'] = 'number'
            analysis['suggested_source'] = 'aggregation'
        elif any(keyword in text_lower for keyword in ['date', 'time', '日期', '时间']):
            analysis['data_type'] = 'date'
            analysis['suggested_source'] = 'temporal'
        
        return analysis


# 创建并注册Agent的工厂函数
def create_and_register_context_aware_multi_db_agent(
    db_session: Session = None, 
    user_id: str = None
) -> str:
    """创建并注册上下文感知的多数据库代理"""
    
    # 创建Agent实例
    agent = ContextAwareMultiDatabaseAgent(db_session=db_session, user_id=user_id)
    
    # 获取注册表并注册
    registry = get_agent_registry()
    agent_id = registry.register_agent(agent, priority=1, max_concurrent=5)
    
    logger.info(f"Context-aware multi-database agent registered with ID: {agent_id}")
    return agent_id


# 使用示例
async def usage_example():
    """使用示例"""
    from sqlalchemy.orm import Session
    
    # 假设的session和user_id
    db_session = None  # 实际使用时需要提供Session
    user_id = "user123"
    
    # 创建并注册Agent
    agent_id = create_and_register_context_aware_multi_db_agent(db_session, user_id)
    
    # 获取上下文管理器并创建会话上下文
    context_manager = get_context_manager()
    session_id = "session_" + str(datetime.now().timestamp())
    context = context_manager.create_context(session_id, user_id=user_id)
    
    # 设置一些上下文信息
    context.set_context('data_source_info', {
        'ds1': {'type': 'mysql', 'name': '业务数据库'}
    }, ContextScope.SESSION)
    
    context.set_context('schema_metadata', {
        'ds1': {
            'tables': ['users', 'orders', 'products'],
            'schema': {'users': ['id', 'name', 'email']}
        }
    }, ContextScope.SESSION)
    
    # 获取注册表并执行能力
    registry = get_agent_registry()
    
    try:
        result = await registry.execute_capability(
            'analyze_placeholder',
            session_id,
            {
                'placeholder_text': '{{用户总数}}',
                'data_source_id': 'ds1',
                'template_context': {'report_type': 'summary'}
            }
        )
        
        print("Analysis result:", result)
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(usage_example())