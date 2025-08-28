"""
增强的占位符分析Agent
集成时间周期和业务上下文，提供更准确的占位符分析
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.services.iaop.context.enhanced_context_builder import EnhancedContextBuilder
from app.services.iaop.integration.llm_service_adapter import IAOPLLMService
from app.services.iaop.agents.specialized.sql_generation_agent import SQLGenerationAgent
from app.services.iaop.core.intelligent_model_selector import IntelligentModelSelector, IAOPTaskType


class EnhancedPlaceholderAnalysisAgent:
    """增强的占位符分析Agent，集成时间周期和业务上下文"""
    
    def __init__(self, db_session: Session, user_id: Optional[str] = None):
        self.db_session = db_session
        self.user_id = user_id
        self.context_builder = EnhancedContextBuilder(db_session)
        self.ai_service = None  # 将在需要时初始化
        self.sql_agent = SQLGenerationAgent(db_session)
        self.model_selector = IntelligentModelSelector(db_session)
    
    async def analyze_task_placeholders(self, task_id: int) -> Dict[str, Any]:
        """
        分析任务的所有占位符
        集成任务的时间周期上下文
        """
        from app.models.task import Task
        from app.models.template_placeholder import TemplatePlaceholder
        
        # 1. 获取任务信息
        task = self.db_session.query(Task).filter(Task.id == task_id).first()
        if not task:
            return {'success': False, 'error': 'Task not found'}
        
        # 2. 构建任务时间上下文
        temporal_context = self.context_builder.build_task_temporal_context(task_id)
        
        # 3. 获取模板的所有占位符
        placeholders = self.db_session.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == task.template_id
        ).all()
        
        if not placeholders:
            return {
                'success': True,
                'task_id': task_id,
                'temporal_context': temporal_context,
                'placeholder_count': 0,
                'results': [],
                'message': 'No placeholders found for this task'
            }
        
        # 4. 分析每个占位符
        analysis_results = []
        for placeholder in placeholders:
            try:
                placeholder_result = await self._analyze_single_placeholder(
                    placeholder, temporal_context, task
                )
                analysis_results.append(placeholder_result)
            except Exception as e:
                analysis_results.append({
                    'placeholder_id': str(placeholder.id),
                    'placeholder_name': placeholder.placeholder_name,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'task_id': task_id,
            'temporal_context': temporal_context,
            'placeholder_count': len(placeholders),
            'results': analysis_results
        }
    
    async def _analyze_single_placeholder(self, placeholder, temporal_context: Dict[str, Any], task) -> Dict[str, Any]:
        """分析单个占位符"""
        
        # 1. 构建业务上下文
        business_context = self.context_builder.build_placeholder_business_context(
            placeholder.placeholder_name, temporal_context
        )
        
        # 2. 加载数据源上下文
        data_source_context = await self.sql_agent._load_data_source_context(str(task.data_source_id))
        
        # 3. 生成增强的SQL
        sql_result = await self._generate_contextual_sql(
            placeholder.placeholder_name,
            business_context,
            data_source_context
        )
        
        # 4. 存储分析结果
        await self._store_analysis_result(placeholder, sql_result, temporal_context)
        
        return {
            'placeholder_id': str(placeholder.id),
            'placeholder_name': placeholder.placeholder_name,
            'success': sql_result.get('success', False),
            'generated_sql': sql_result.get('sql_query'),
            'target_table': sql_result.get('target_table'),
            'target_columns': sql_result.get('target_columns', []),
            'confidence': sql_result.get('confidence', 0.0),
            'temporal_context_applied': True,
            'business_context': business_context['business_intent'],
            'error': sql_result.get('error') if not sql_result.get('success') else None
        }
    
    async def _generate_contextual_sql(self, placeholder_text: str, business_context: Dict[str, Any], data_source_context: Dict[str, Any]) -> Dict[str, Any]:
        """生成包含时间上下文的SQL"""
        
        # 1. 智能选择最优模型
        selected_model = None
        model_selection_info = {}
        
        if self.user_id:
            # 创建任务上下文 - 重点关注对模型类型的需求
            task_context = {
                "accuracy_requirement": "high",        # SQL生成需要高精度
                "requires_structured_output": True,    # 需要结构化的JSON输出
                "reasoning_intensive": True,           # SQL生成需要推理能力
                "conversational": False                # 非对话性任务
            }
            
            selected_model, model_selection_info = self.model_selector.select_optimal_model(
                user_id=self.user_id,
                task_type=IAOPTaskType.SQL_GENERATION,
                context=task_context
            )
        
        # 2. 构建增强的提示词
        enhanced_prompt = self._build_contextual_prompt(placeholder_text, business_context, data_source_context)
        
        try:
            # 3. 使用选定的模型调用LLM
            response = None
            
            if selected_model:
                # 使用智能选择的模型
                response = await self._call_llm_with_selected_model(
                    selected_model,
                    system_prompt="你是一个专业的SQL分析师，专门为报告占位符生成准确的SQL查询语句。",
                    user_message=enhanced_prompt
                )
            else:
                # 回退到默认LLM服务
                from app.services.llm import call_llm_with_system_prompt
                response = await call_llm_with_system_prompt(
                    system_prompt="你是一个专业的SQL分析师，专门为报告占位符生成准确的SQL查询语句。",
                    user_message=enhanced_prompt
                )
            
            # 4. 解析响应
            if not self.ai_service:
                self.ai_service = IAOPLLMService(self.db_session)
                
            sql_result = self.ai_service._parse_json_response(response, "generate_contextual_sql")
            
            if sql_result:
                result = {
                    'success': True,
                    'sql_query': sql_result.get('sql_query'),
                    'target_table': sql_result.get('target_table'),
                    'target_columns': sql_result.get('target_columns', []),
                    'confidence': sql_result.get('confidence', 0.8),
                    'model_used': selected_model.name if selected_model else 'default',
                    'model_selection_info': model_selection_info
                }
                return result
            else:
                return {
                    'success': False,
                    'error': 'Failed to parse LLM response',
                    'sql_query': None,
                    'model_used': selected_model.name if selected_model else 'default',
                    'model_selection_info': model_selection_info
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'sql_query': None,
                'model_used': selected_model.name if selected_model else 'default',
                'model_selection_info': model_selection_info
            }
    
    def _build_contextual_prompt(self, placeholder_text: str, business_context: Dict[str, Any], data_source_context: Dict[str, Any]) -> str:
        """构建包含时间上下文的提示词"""
        
        temporal_info = business_context['temporal_scope']
        time_hints = business_context['sql_time_hints']
        business_intent = business_context['business_intent']
        
        prompt = f"""请为占位符"{placeholder_text}"生成SQL查询语句。

时间上下文：
- 报告周期：{temporal_info['period_description']}
- 数据范围：{temporal_info['data_start_date']} 至 {temporal_info['data_end_date']}
- 时间过滤模板：{time_hints['time_filter_template']}

业务意图：
- 主要意图：{business_intent['primary_intent']}
- 检测到的意图：{', '.join(business_intent['detected_intents'])}
- 复杂度：{business_intent['complexity']}

可用表结构："""
        
        # 添加表结构信息
        for table in data_source_context.get('tables', []):
            prompt += f"""
表名：{table['table_name']}
业务分类：{table.get('business_category', '未分类')}
主要字段："""
            for col in table['columns'][:8]:  # 显示前8个字段
                prompt += f"""
  - {col['name']} ({col['type']}): {col['business_description'] or '无描述'}"""
            if len(table['columns']) > 8:
                prompt += f"""
  ... 还有 {len(table['columns']) - 8} 个字段"""
            prompt += "\n"
        
        prompt += f"""
特别要求：
1. 必须使用实际存在的表名和字段名（从上面的表结构中选择）
2. 必须包含时间范围过滤条件，使用合适的日期字段
3. 根据业务意图选择合适的聚合函数和分组方式：
   - statistics: 使用 COUNT(), SUM(), AVG() 等
   - trend: 包含时间分组，如 GROUP BY DATE(date_column)
   - comparison: 使用分类字段分组
   - ranking: 使用 ORDER BY 和 LIMIT
   - distribution: 使用分类统计
4. 确保SQL语法正确且高效
5. 优先选择业务相关性最高的表和字段

返回JSON格式：
{{
    "sql_query": "完整的SQL查询语句",
    "target_table": "主要查询的表名",
    "target_columns": ["主要返回的列名1", "主要返回的列名2"],
    "confidence": 0.85
}}"""
        
        return prompt
    
    def _assess_data_complexity(self, data_source_context: Dict[str, Any]) -> str:
        """评估数据复杂度"""
        
        tables = data_source_context.get('tables', [])
        
        if not tables:
            return "low"
        
        total_columns = sum(len(table.get('columns', [])) for table in tables)
        table_count = len(tables)
        
        # 根据表数量和字段总数判断复杂度
        if table_count >= 3 or total_columns >= 50:
            return "high"
        elif table_count >= 2 or total_columns >= 20:
            return "medium"
        else:
            return "low"
    
    async def _call_llm_with_selected_model(self, model, system_prompt: str, user_message: str) -> str:
        """使用选定的模型调用LLM"""
        
        # 为了简化实现，这里仍使用全局LLM服务
        # 在实际生产环境中，可以根据具体模型创建专门的客户端
        from app.services.llm import call_llm_with_system_prompt
        
        # TODO: 在未来版本中，可以根据选定的模型创建特定的LLM客户端配置
        # 现在先记录使用的模型信息
        logger.info(f"使用选定模型 {model.name} 进行SQL生成")
        
        return await call_llm_with_system_prompt(
            system_prompt=system_prompt,
            user_message=user_message
        )
    
    async def _store_analysis_result(self, placeholder, sql_result: Dict[str, Any], temporal_context: Dict[str, Any]):
        """存储分析结果"""
        try:
            if sql_result.get('success'):
                placeholder.generated_sql = sql_result.get('sql_query')
                placeholder.confidence = sql_result.get('confidence', 0.0)
                placeholder.last_analysis_at = datetime.now()
                
                # 存储时间上下文元数据
                if not placeholder.metadata:
                    placeholder.metadata = {}
                placeholder.metadata['temporal_context'] = temporal_context
                placeholder.metadata['analysis_timestamp'] = datetime.now().isoformat()
                placeholder.metadata['target_table'] = sql_result.get('target_table')
                placeholder.metadata['target_columns'] = sql_result.get('target_columns', [])
                
                self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            raise e
    
    async def analyze_single_placeholder_by_id(self, placeholder_id: str, task_id: Optional[int] = None) -> Dict[str, Any]:
        """分析单个占位符（通过ID）"""
        from app.models.template_placeholder import TemplatePlaceholder
        from app.models.task import Task
        
        # 获取占位符
        placeholder = self.db_session.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.id == placeholder_id
        ).first()
        
        if not placeholder:
            return {'success': False, 'error': 'Placeholder not found'}
        
        # 获取关联的任务或使用默认任务
        if task_id:
            task = self.db_session.query(Task).filter(Task.id == task_id).first()
        else:
            # 查找使用此模板的第一个任务
            task = self.db_session.query(Task).filter(
                Task.template_id == placeholder.template_id
            ).first()
        
        if not task:
            return {'success': False, 'error': 'No associated task found'}
        
        # 构建时间上下文
        temporal_context = self.context_builder.build_task_temporal_context(task.id)
        
        # 分析占位符
        result = await self._analyze_single_placeholder(placeholder, temporal_context, task)
        
        return {
            'success': True,
            'temporal_context': temporal_context,
            'result': result
        }