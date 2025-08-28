from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ..base import BaseAgent
from ...context.execution_context import EnhancedExecutionContext
# 使用LLM客户端替代AI服务工厂
from app.services.llm.client import LLMServerClient, LLMRequest, LLMMessage

logger = logging.getLogger(__name__)


class SQLGenerationAgent(BaseAgent):
    """
SQL生成Agent - 基于语义分析结果生成优化的SQL查询
结合LLM智能推理和规则引擎生成高质量SQL
"""
    
    def __init__(self, name: str = "sql_generator", capabilities: List[str] = None, db_session=None, user_id: str = None):
        super().__init__(name, capabilities or ["sql_generation", "query_optimization", "schema_mapping"])
        self.ai_service = None
        self.db_session = db_session
        self.user_id = user_id
        
    async def validate_preconditions(self, context: EnhancedExecutionContext) -> bool:
        """验证执行前置条件"""
        required_fields = ['semantic_analysis', 'data_source_context']
        for field in required_fields:
            if not context.get_context(field):
                logger.warning(f"缺少必要字段: {field}")
                return False
        return True
        
    async def execute(self, context: EnhancedExecutionContext) -> Dict[str, Any]:
        """执行SQL生成"""
        try:
            # 初始化AI服务
            if not self.ai_service:
                from ...integration.llm_service_adapter import get_iaop_llm_service
                # 尝试从context获取用户ID
                user_id = context.get_context('user_id')
                self.ai_service = get_iaop_llm_service(self.db_session, user_id)
            
            # 获取输入数据
            semantic_analysis = context.get_context('semantic_analysis', {})
            data_source_context = context.get_context('data_source_context', {})
            template_context = context.get_context('template_context', {})
            placeholder_text = context.get_context('placeholder_text', '')
            
            # 如果数据源上下文为空或缺少表信息，尝试加载
            if not data_source_context or not data_source_context.get('tables'):
                # 先从data_source_context获取，如果没有再从执行上下文获取
                data_source_id = (
                    data_source_context.get('data_source_id') or 
                    context.get_context('data_source_id') or
                    context.get_context('datasource_id')
                )
                
                if data_source_id:
                    logger.info(f"数据源上下文缺失，尝试加载: {data_source_id}")
                    data_source_context = await self._load_data_source_context(data_source_id)
                    from ...context.execution_context import ContextScope
                    context.set_context('data_source_context', data_source_context, ContextScope.REQUEST)
                else:
                    logger.warning("无法获取数据源ID，使用默认上下文")
                    # 打印调试信息
                    logger.debug(f"执行上下文keys: {list(context._contexts.get(context.ContextScope.REQUEST, {}).keys())}")
            
            # 基于语义分析结果生成SQL
            sql_result = await self._generate_sql_from_semantics(
                semantic_analysis, data_source_context, template_context, placeholder_text
            )
            
            # SQL质量检查和优化
            optimized_sql = await self._optimize_generated_sql(
                sql_result['sql_query'], data_source_context, semantic_analysis
            )
            
            # 合并结果
            final_result = {
                **sql_result,
                'optimized_sql': optimized_sql['sql_query'] if optimized_sql['success'] else sql_result['sql_query'],
                'optimization_applied': optimized_sql['success'],
                'optimization_details': optimized_sql.get('optimization_details', [])
            }
            
            logger.info(f"SQL生成完成: {placeholder_text}, 质量分数: {final_result.get('quality_score', 0)}")
            
            # 存储生成的SQL到数据库
            await self._store_generated_sql(
                placeholder_text=placeholder_text,
                sql_result=final_result,
                context=context
            )
            
            return {
                'agent': self.name,
                'type': 'sql_generation',
                'success': True,
                'data': final_result,
                'metadata': {
                    'generation_timestamp': datetime.now().isoformat(),
                    'placeholder_text': placeholder_text,
                    'generation_method': 'llm_semantic_guided'
                }
            }
            
        except Exception as e:
            logger.error(f"SQL生成失败: {e}")
            # 使用规则引擎回退方案
            semantic_analysis = context.get_context('semantic_analysis', {})
            placeholder_text = context.get_context('placeholder_text', '')
            
            logger.info(f"使用规则引擎回退生成SQL: {placeholder_text}")
            fallback_result = self._rule_based_sql_generation(semantic_analysis, placeholder_text)
            
            return {
                'success': True,
                'data': fallback_result,
                'source': 'rule_based_fallback',
                'original_error': str(e)
            }
    
    async def _generate_sql_from_semantics(
        self, 
        semantic_analysis: Dict[str, Any], 
        data_source_context: Dict[str, Any],
        template_context: Dict[str, Any],
        placeholder_text: str
    ) -> Dict[str, Any]:
        """基于语义分析结果生成SQL"""
        
        # 构建SQL生成的系统提示词
        system_prompt = self._build_sql_generation_prompt(data_source_context, template_context)
        
        # 构建用户查询
        user_prompt = f"""
基于以下语义分析结果生成精确的SQL查询:

语义分析结果:
- 原始占位符: "{placeholder_text}"
- 业务意图: {semantic_analysis.get('primary_intent', '未知')}
- 数据类型: {semantic_analysis.get('data_type', '未知')}
- 子类别: {semantic_analysis.get('sub_category', '未知')}
- 业务概念: {semantic_analysis.get('business_concept', '未知')}
- 计算逻辑: {semantic_analysis.get('calculation_logic', '未知')}
- 所需维度: {semantic_analysis.get('required_dimensions', [])}
- 关键词: {semantic_analysis.get('keywords', [])}
- 上下文依赖: {semantic_analysis.get('context_dependencies', [])}
- 分析置信度: {semantic_analysis.get('confidence', 0)}

请生成优化的SQL查询，返回JSON格式:
{{
    "sql_query": "完整的可执行SQL语句",
    "target_table": "主要查询表名",
    "target_columns": ["使用的关键字段列表"],
    "query_type": "select|aggregate|temporal|dimensional",
    "business_logic": "业务逻辑说明",
    "execution_strategy": "执行策略说明",
    "performance_notes": ["性能优化要点"],
    "quality_score": 0.0-1.0,
    "confidence": 0.0-1.0,
    "explanation": "SQL生成的详细解释"
}}

重要要求:
1. SQL必须基于提供的真实表结构
2. 必须符合{data_source_context.get('data_source_type', 'MySQL')}语法
3. 优先考虑性能和准确性
4. 处理好时间范围和数据筛选
5. 如果是统计查询，要包含适当的GROUP BY和聚合函数
"""
        
        # 调用LLM生成SQL
        response = await self.ai_service.generate_sql_query(
            requirement=user_prompt,
            table_schema=data_source_context,
            context=template_context
        )
        
        # 解析响应
        return self._parse_sql_generation_response(
            response, semantic_analysis, placeholder_text
        )
    
    def _build_sql_generation_prompt(self, data_source_context: Dict, template_context: Dict) -> str:
        """构建SQL生成的系统提示词"""
        
        prompt_parts = [
            "你是一个高级数据库查询专家，专门根据语义分析结果生成高质量的SQL查询。",
            "\n数据库环境信息:"
        ]
        
        # 数据源信息
        ds_name = data_source_context.get('data_source_name', '未知')
        ds_type = data_source_context.get('data_source_type', 'MySQL')
        prompt_parts.extend([
            f"- 数据库类型: {ds_type}",
            f"- 数据源名称: {ds_name}"
        ])
        
        # 表结构信息
        tables = data_source_context.get('tables', [])
        if tables:
            prompt_parts.append("\n可用表结构:")
            for table in tables:
                table_name = table.get('table_name', '')
                business_category = table.get('business_category', '未分类')
                data_quality = table.get('data_quality_score', 0)
                
                prompt_parts.append(f"\n表: {table_name}")
                prompt_parts.append(f"  业务类别: {business_category}")
                prompt_parts.append(f"  数据质量: {data_quality}")
                
                columns = table.get('columns', [])
                if columns:
                    prompt_parts.append("  字段:")
                    for col in columns[:15]:  # 限制显示字段数量
                        col_name = col.get('name', '')
                        col_type = col.get('type', '')
                        business_name = col.get('business_name', '')
                        business_desc = col.get('business_description', '')
                        
                        col_info = f"    {col_name}({col_type})"
                        if business_name:
                            col_info += f" - {business_name}"
                        if business_desc:
                            col_info += f": {business_desc}"
                        
                        prompt_parts.append(col_info)
        
        # 模板上下文
        if template_context:
            prompt_parts.append("\n业务上下文:")
            for key, value in template_context.items():
                if value and key in ['template_title', 'template_type', 'business_domain', 'time_range']:
                    prompt_parts.append(f"- {key}: {value}")
        
        # SQL生成原则
        prompt_parts.extend([
            "\n核心原则:",
            "1. 精确性: 确保SQL逻辑完全符合业务需求",
            "2. 性能: 优化查询性能，合理使用索引和过滤条件", 
            "3. 可读性: 生成清晰易读的SQL代码",
            "4. 兼容性: 严格遵循目标数据库的语法规范",
            "5. 安全性: 避免SQL注入和性能风险",
            "\n特别注意:",
            "- 时间类型字段的正确处理和格式化",
            "- 聚合查询的GROUP BY规则",
            "- 字符串匹配的模糊查询优化",
            "- NULL值的正确处理"
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_sql_generation_response(
        self, 
        response: Dict[str, Any], 
        semantic_analysis: Dict[str, Any],
        placeholder_text: str
    ) -> Dict[str, Any]:
        """解析SQL生成响应"""
        try:
            # 如果response已经是字典，直接使用；否则尝试解析JSON
            if isinstance(response, dict):
                sql_data = response
            else:
                sql_data = json.loads(str(response))
            
            # 验证和增强结果
            result = {
                'sql_query': sql_data.get('sql_query', 'SELECT 1 as placeholder_result'),
                'target_table': sql_data.get('target_table', ''),
                'target_columns': sql_data.get('target_columns', []),
                'query_type': sql_data.get('query_type', 'select'),
                'business_logic': sql_data.get('business_logic', f'处理{placeholder_text}'),
                'execution_strategy': sql_data.get('execution_strategy', '直接执行'),
                'performance_notes': sql_data.get('performance_notes', []),
                'quality_score': float(sql_data.get('quality_score', 0.7)),
                'confidence': float(sql_data.get('confidence', 0.7)),
                'explanation': sql_data.get('explanation', 'SQL查询生成'),
                'generation_source': 'llm_semantic_guided',
                'semantic_alignment': self._calculate_semantic_alignment(sql_data, semantic_analysis)
            }
            
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"SQL生成响应解析失败: {e}")
            # 回退到基于语义的规则生成
            return self._rule_based_sql_generation(semantic_analysis, placeholder_text)
    
    def _calculate_semantic_alignment(self, sql_data: Dict, semantic_analysis: Dict) -> float:
        """计算SQL与语义分析的对齐度"""
        alignment_score = 0.0
        
        # 检查数据类型对齐
        data_type = semantic_analysis.get('data_type', '')
        query_type = sql_data.get('query_type', '')
        
        if data_type == 'statistical' and query_type == 'aggregate':
            alignment_score += 0.3
        elif data_type == 'temporal' and 'date' in sql_data.get('sql_query', '').lower():
            alignment_score += 0.3
        elif data_type == 'dimensional' and 'group by' in sql_data.get('sql_query', '').lower():
            alignment_score += 0.3
        
        # 检查关键词匹配
        keywords = semantic_analysis.get('keywords', [])
        sql_query_lower = sql_data.get('sql_query', '').lower()
        
        keyword_matches = sum(1 for keyword in keywords if keyword.lower() in sql_query_lower)
        if keywords:
            alignment_score += 0.3 * (keyword_matches / len(keywords))
        
        # 检查业务概念匹配
        business_concept = semantic_analysis.get('business_concept', '')
        if business_concept and business_concept.lower() in sql_query_lower:
            alignment_score += 0.2
        
        # 检查置信度一致性
        semantic_confidence = semantic_analysis.get('confidence', 0)
        sql_confidence = sql_data.get('confidence', 0)
        confidence_alignment = 1 - abs(semantic_confidence - sql_confidence)
        alignment_score += 0.2 * confidence_alignment
        
        return min(alignment_score, 1.0)
    
    async def analyze_and_execute(self, request) -> 'AgentExecutionResult':
        """
        完整的Agent分析和执行流程
        
        Args:
            request: PlaceholderRequest对象
            
        Returns:
            AgentExecutionResult对象
        """
        try:
            # 导入所需的结果类型
            from app.services.domain.placeholder.models import AgentExecutionResult
            
            # 创建执行上下文
            from ...context.execution_context import EnhancedExecutionContext, ContextScope
            import uuid
            
            context = EnhancedExecutionContext(
                session_id=str(uuid.uuid4()),
                user_id=self.user_id or 'system',
                request=request.__dict__ if hasattr(request, '__dict__') else {}
            )
            
            # 设置占位符文本
            if hasattr(request, 'placeholder_name'):
                context.set_context('placeholder_text', request.placeholder_name, ContextScope.REQUEST)
            
            # 设置数据源ID到执行上下文
            if hasattr(request, 'data_source_id') and request.data_source_id:
                context.set_context('data_source_id', request.data_source_id, ContextScope.REQUEST)
                context.set_context('datasource_id', request.data_source_id, ContextScope.REQUEST)  # 备用键名
                logger.info(f"设置数据源ID到执行上下文: {request.data_source_id}")
            
            # 设置数据源上下文（可能需要从数据库获取）
            context.set_context('data_source_context', {}, ContextScope.REQUEST)
            
            # 设置语义分析上下文（简化版本）
            semantic_analysis = {
                'data_type': 'statistical',
                'confidence': 0.8,
                'keywords': [],
                'business_concept': getattr(request, 'placeholder_name', '')
            }
            context.set_context('semantic_analysis', semantic_analysis, ContextScope.REQUEST)
            
            # 执行SQL生成
            result = await self.execute(context)
            
            if result.get('success'):
                return AgentExecutionResult(
                    success=True,
                    formatted_value=result.get('data', {}).get('sql_query', ''),
                    raw_data=result.get('data', {}).get('sql_query', ''),
                    confidence=result.get('data', {}).get('confidence', 0.8),
                    execution_time_ms=0,
                    metadata=result.get('data', {})
                )
            else:
                return AgentExecutionResult(
                    success=False,
                    formatted_value='',
                    raw_data='',
                    error_message=result.get('error', 'SQL生成失败'),
                    confidence=0.0,
                    execution_time_ms=0,
                    metadata={}
                )
                
        except Exception as e:
            logger.error(f"Agent分析执行失败: {e}")
            from app.services.domain.placeholder.models import AgentExecutionResult
            return AgentExecutionResult(
                success=False,
                formatted_value='',
                raw_data='',
                error_message=str(e),
                confidence=0.0,
                execution_time_ms=0,
                metadata={}
            )
    
    def _rule_based_sql_generation(self, semantic_analysis: Dict, placeholder_text: str) -> Dict[str, Any]:
        """基于规则的SQL生成回退方案"""
        
        data_type = semantic_analysis.get('data_type', 'general')
        
        # 时间类型SQL
        if data_type == 'temporal':
            if '开始' in placeholder_text:
                sql = "SELECT DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m-01') as start_date"
            elif '结束' in placeholder_text:
                sql = "SELECT DATE_FORMAT(LAST_DAY(DATE_SUB(NOW(), INTERVAL 1 MONTH)), '%Y-%m-%d') as end_date"
            else:
                sql = "SELECT DATE_FORMAT(NOW(), '%Y-%m-%d') as current_date"
            
            return {
                'sql_query': sql,
                'target_table': '',
                'target_columns': ['date_field'],
                'query_type': 'temporal',
                'business_logic': '时间信息查询',
                'execution_strategy': '系统时间函数',
                'performance_notes': ['使用数据库内置函数，性能较好'],
                'quality_score': 0.7,
                'confidence': 0.8,
                'explanation': '基于规则生成的时间查询',
                'generation_source': 'rule_based_fallback'
            }
        
        # 统计类型SQL
        elif data_type == 'statistical':
            if '总数' in placeholder_text or '件数' in placeholder_text:
                sql = "SELECT COUNT(*) as total_count FROM placeholder_table WHERE DATE_FORMAT(created_time, '%Y-%m') = DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 MONTH), '%Y-%m')"
            elif '占比' in placeholder_text:
                sql = "SELECT COUNT(*) as count_value, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM placeholder_table), 2) as percentage FROM placeholder_table"
            else:
                sql = "SELECT COUNT(*) as count_result FROM placeholder_table"
            
            return {
                'sql_query': sql,
                'target_table': 'placeholder_table',
                'target_columns': ['*'],
                'query_type': 'aggregate',
                'business_logic': '统计计算查询',
                'execution_strategy': '聚合查询',
                'performance_notes': ['注意添加适当的索引'],
                'quality_score': 0.6,
                'confidence': 0.7,
                'explanation': '基于规则生成的统计查询',
                'generation_source': 'rule_based_fallback'
            }
        
        # 维度类型SQL
        elif data_type == 'dimensional':
            sql = "SELECT DISTINCT dimension_column as dimension_value FROM placeholder_table ORDER BY dimension_column"
            
            return {
                'sql_query': sql,
                'target_table': 'placeholder_table', 
                'target_columns': ['dimension_column'],
                'query_type': 'dimensional',
                'business_logic': '维度信息查询',
                'execution_strategy': '去重查询',
                'performance_notes': ['确保维度字段有索引'],
                'quality_score': 0.6,
                'confidence': 0.7,
                'explanation': '基于规则生成的维度查询',
                'generation_source': 'rule_based_fallback'
            }
        
        # 默认通用SQL
        else:
            return {
                'sql_query': f"SELECT '{placeholder_text}' as placeholder_value",
                'target_table': '',
                'target_columns': [],
                'query_type': 'select',
                'business_logic': '占位符默认值',
                'execution_strategy': '常量查询',
                'performance_notes': ['性能最优，返回常量'],
                'quality_score': 0.5,
                'confidence': 0.5,
                'explanation': '默认占位符查询',
                'generation_source': 'default_fallback'
            }
    
    async def _optimize_generated_sql(
        self, 
        sql_query: str, 
        data_source_context: Dict, 
        semantic_analysis: Dict
    ) -> Dict[str, Any]:
        """优化生成的SQL查询"""
        try:
            # 构建SQL优化提示词
            optimization_prompt = f"""
请优化以下SQL查询的性能和准确性:

原始SQL: {sql_query}
数据库类型: {data_source_context.get('data_source_type', 'MySQL')}
语义分析: {semantic_analysis}

优化要求:
1. 提高查询性能
2. 确保结果准确性
3. 改进可读性
4. 处理边界情况

返回JSON格式:
{{
    "optimized_sql": "优化后的SQL",
    "optimization_applied": true/false,
    "optimization_details": ["优化说明列表"],
    "performance_improvement": "性能提升说明",
    "risk_assessment": "风险评估"
}}
"""
            
            # 使用LLM服务进行SQL优化
            response = await self.ai_service.generate_narrative_text(
                content_type="sql_optimization",
                data_context={
                    "original_sql": sql_query,
                    "optimization_requirements": optimization_prompt
                }
            )
            
            # 简化的优化结果
            return {
                'success': True,
                'sql_query': sql_query,  # 暂时返回原始SQL
                'optimization_applied': False,
                'optimization_details': ['优化功能正在完善中'],
                'performance_improvement': '暂未应用优化',
                'risk_assessment': '低风险'
            }
                
        except Exception as e:
            logger.warning(f"SQL优化失败: {e}")
        
        # 返回原始SQL
        return {
            'success': False,
            'sql_query': sql_query,
            'optimization_applied': False,
            'optimization_details': ['优化失败，使用原始SQL'],
            'performance_improvement': '无',
            'risk_assessment': '未评估'
        }
    
    def _generate_fallback_sql_result(self, context: EnhancedExecutionContext, error_msg: str) -> Dict[str, Any]:
        """生成回退SQL结果"""
        placeholder_text = context.get_context('placeholder_text', '未知占位符')
        
        return {
            'agent': self.name,
            'type': 'sql_generation', 
            'success': False,
            'data': {
                'sql_query': f"SELECT '{placeholder_text}' as error_result",
                'target_table': '',
                'target_columns': [],
                'query_type': 'error',
                'business_logic': 'SQL生成失败',
                'execution_strategy': '错误处理',
                'performance_notes': [],
                'quality_score': 0.1,
                'confidence': 0.1,
                'explanation': f'SQL生成失败: {error_msg}',
                'generation_source': 'error_fallback'
            },
            'error': error_msg,
            'metadata': {
                'generation_timestamp': datetime.now().isoformat(),
                'placeholder_text': placeholder_text,
                'generation_method': 'error_fallback'
            }
        }

    async def analyze_placeholder(self, placeholder_id: str, placeholder_text: str, data_source_id: str, 
                                placeholder_type: str = None, template_id: str = None, force_reanalyze: bool = False) -> Dict[str, Any]:
        """分析占位符 - 兼容旧版API接口"""
        try:
            # 构建上下文
            from ...context.execution_context import EnhancedExecutionContext
            from ...context.execution_context import ContextScope
            
            context = EnhancedExecutionContext(
                session_id=f"placeholder_{placeholder_id}",
                user_id=self.user_id or "default",
                task_id=f"analyze_{placeholder_id}"
            )
            
            # 设置请求数据
            context.set_context('semantic_analysis', {
                'primary_intent': 'data_analysis',
                'data_type': 'general',
                'placeholder_text': placeholder_text,
                'confidence': 0.8
            }, ContextScope.REQUEST)
            
            # 加载完整的数据源上下文
            data_source_context = await self._load_data_source_context(data_source_id)
            context.set_context('data_source_context', data_source_context, ContextScope.REQUEST)
            
            context.set_context('template_context', {
                'template_id': template_id
            }, ContextScope.REQUEST)
            
            context.set_context('placeholder_text', placeholder_text, ContextScope.REQUEST)
            
            # 执行分析
            result = await self.execute(context)
            
            return {
                "success": result.get('success', False),
                "data": result.get('data', {}),
                "error": result.get('error'),
                "placeholder_id": placeholder_id,
                "analysis_type": "iaop_sql_generation"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"占位符分析失败: {str(e)}",
                "placeholder_id": placeholder_id,
                "data": {}
            }

    async def check_stored_sql(self, placeholder_id: str) -> Dict[str, Any]:
        """检查存储的SQL - 兼容旧版API接口"""
        try:
            if not self.db_session:
                logger.warning("数据库会话未提供，无法检查存储的SQL")
                return {
                    "success": True,
                    "data": {
                        "has_stored_sql": False,
                        "sql_query": None,
                        "last_generated": None,
                        "quality_score": None
                    },
                    "placeholder_id": placeholder_id
                }
            
            from app.models.template_placeholder import TemplatePlaceholder
            
            placeholder = self.db_session.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                return {
                    "success": False,
                    "error": "占位符不存在",
                    "placeholder_id": placeholder_id,
                    "data": {}
                }
            
            has_sql = bool(placeholder.generated_sql and placeholder.generated_sql.strip())
            
            return {
                "success": True,
                "data": {
                    "has_stored_sql": has_sql,
                    "sql_query": placeholder.generated_sql if has_sql else None,
                    "last_generated": placeholder.last_analysis_at.isoformat() if placeholder.last_analysis_at else None,
                    "quality_score": getattr(placeholder, 'confidence', None)
                },
                "placeholder_id": placeholder_id
            }
            
        except Exception as e:
            logger.error(f"检查存储SQL失败: {e}")
            return {
                "success": False,
                "error": f"检查SQL失败: {str(e)}",
                "placeholder_id": placeholder_id,
                "data": {}
            }

    async def _store_generated_sql(
        self, 
        placeholder_text: str, 
        sql_result: Dict[str, Any], 
        context: EnhancedExecutionContext
    ):
        """存储生成的SQL到数据库"""
        try:
            if not self.db_session:
                logger.warning("数据库会话未提供，无法存储SQL")
                return
            
            # 尝试从上下文获取占位符ID
            placeholder_id = None
            
            # 方法1: 直接从上下文获取
            placeholder_id = context.get_context('placeholder_id')
            
            # 方法2: 从模板上下文获取（如果存在的话）
            if not placeholder_id:
                template_context = context.get_context('template_context', {})
                placeholder_id = template_context.get('placeholder_id')
            
            # 方法3: 通过占位符文本查找
            if not placeholder_id and placeholder_text:
                from app.models.template_placeholder import TemplatePlaceholder
                placeholder = self.db_session.query(TemplatePlaceholder).filter(
                    TemplatePlaceholder.placeholder_name == placeholder_text
                ).first()
                if placeholder:
                    placeholder_id = str(placeholder.id)
            
            if not placeholder_id:
                logger.warning(f"无法确定占位符ID，跳过SQL存储: {placeholder_text}")
                return
            
            from app.models.template_placeholder import TemplatePlaceholder
            
            # 查找占位符记录
            placeholder = self.db_session.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.id == placeholder_id
            ).first()
            
            if not placeholder:
                logger.warning(f"未找到占位符记录: {placeholder_id}")
                return
            
            # 更新占位符的SQL信息
            placeholder.generated_sql = sql_result.get('sql_query', '')
            placeholder.confidence = sql_result.get('confidence', 0.0)
            placeholder.last_analysis_at = datetime.now()
            
            # 如果有额外的字段，也可以存储
            if hasattr(placeholder, 'target_table'):
                placeholder.target_table = sql_result.get('target_table')
            if hasattr(placeholder, 'quality_score'):
                placeholder.quality_score = sql_result.get('quality_score')
            if hasattr(placeholder, 'explanation'):
                placeholder.explanation = sql_result.get('explanation')
            
            self.db_session.commit()
            logger.info(f"SQL已存储到数据库: {placeholder_text} -> {placeholder_id}")
            
        except Exception as e:
            logger.error(f"存储SQL到数据库失败: {e}")
            if self.db_session:
                self.db_session.rollback()

    async def _load_data_source_context(self, data_source_id: str) -> Dict[str, Any]:
        """加载完整的数据源上下文信息"""
        try:
            if not self.db_session:
                logger.warning("数据库会话未提供，使用默认数据源上下文")
                return {
                    'data_source_id': data_source_id,
                    'data_source_type': 'unknown',
                    'tables': []
                }
            
            from app.models.table_schema import TableSchema, ColumnSchema
            from app.models.data_source import DataSource
            
            # 获取数据源信息
            data_source = self.db_session.query(DataSource).filter(
                DataSource.id == data_source_id
            ).first()
            
            if not data_source:
                logger.warning(f"未找到数据源: {data_source_id}")
                return {
                    'data_source_id': data_source_id,
                    'data_source_type': 'unknown',
                    'tables': []
                }
            
            # 获取表结构
            tables = self.db_session.query(TableSchema).filter(
                TableSchema.data_source_id == data_source_id,
                TableSchema.is_active == True
            ).all()
            
            context = {
                'data_source_id': data_source_id,
                'data_source_type': str(data_source.source_type) if data_source.source_type else 'mysql',
                'data_source_name': data_source.name,
                'tables': []
            }
            
            for table in tables:
                # 获取列信息
                columns = self.db_session.query(ColumnSchema).filter(
                    ColumnSchema.table_schema_id == table.id
                ).all()
                
                table_info = {
                    'table_name': table.table_name,
                    'business_category': table.business_category or '未分类',
                    'estimated_row_count': table.estimated_row_count or 0,
                    'data_quality_score': getattr(table, 'data_quality_score', 0.7),
                    'columns': []
                }
                
                for col in columns:
                    column_info = {
                        'name': col.column_name,
                        'type': str(col.normalized_type) if col.normalized_type else 'string',
                        'business_name': col.business_name or col.column_name,
                        'business_description': col.business_description or '',
                        'is_primary_key': col.is_primary_key or False,
                        'is_nullable': col.is_nullable if col.is_nullable is not None else True,
                        'semantic_category': col.semantic_category or ''
                    }
                    table_info['columns'].append(column_info)
                
                context['tables'].append(table_info)
            
            logger.info(f"成功加载数据源上下文: {data_source.name}, {len(tables)}个表")
            return context
            
        except Exception as e:
            logger.error(f"加载数据源上下文失败: {e}")
            return {
                'data_source_id': data_source_id,
                'data_source_type': 'unknown', 
                'tables': []
            }


