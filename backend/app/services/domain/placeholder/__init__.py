"""
智能占位符系统 v3.0 - DAG编排架构
基于DAG编排的智能占位符处理系统
职责：构建上下文工程，调用agents系统DAG处理，协助存储中间结果
"""

import logging

logger = logging.getLogger(__name__)

# 核心模型
from .models import (
    PlaceholderSpec, DocumentContext, BusinessContext, TimeContext,
    ValidationResult, ProcessingResult, StatisticalType, SyntaxType
)

# 解析器
from .parsers import (
    PlaceholderParser, ParameterizedParser, CompositeParser, 
    ConditionalParser, SyntaxValidator, ParserFactory
)

# 语义分析
from .semantic import (
    SemanticPlaceholderParser, IntentClassifier, 
    SemanticAnalyzer, ImplicitParameterInferencer
)

# 上下文分析（上下文工程核心）
from .context import (
    ContextAnalysisEngine, ParagraphAnalyzer, SectionAnalyzer,
    DocumentAnalyzer, BusinessRuleAnalyzer
)

# 权重计算
from .weight import (
    WeightCalculator, DynamicWeightAdjuster, WeightAggregator,
    WeightLearningEngine, WeightComponents
)

# 智能占位符服务（符合DAG架构）
from .intelligent_placeholder_service import (
    IntelligentPlaceholderService,
    get_intelligent_placeholder_service,
    analyze_template_placeholders,
    analyze_single_placeholder
)

# 版本信息
__version__ = "3.0.0-dag"
__author__ = "AutoReportAI Team"

def create_batch_router(db_session=None, user_id=None):
    """
    创建批处理路由器 - React Agent系统适配器
    
    Args:
        db_session: 数据库会话
        user_id: 用户ID
        
    Returns:
        BatchRouter: 批处理路由器实例 (React Agent适配器)
    """
    class BatchRouter:
        def __init__(self, db_session, user_id):
            self.db_session = db_session
            self.user_id = user_id
            
        async def process_placeholders(self, template_id, placeholders, context=None):
            """批量处理占位符 - 基于React Agent实现"""
            if not placeholders:
                return {
                    "success": True,
                    "message": "没有需要处理的占位符",
                    "processed_count": 0,
                    "results": []
                }
            
            try:
                from app.services.infrastructure.ai.agents import create_react_agent
                
                # 创建React Agent实例
                agent = create_react_agent(self.user_id)
                await agent.initialize()
                
                results = []
                processed_count = 0
                
                # 构建批处理提示
                batch_prompt = f"""
                批量处理模板占位符：
                
                模板ID: {template_id}
                占位符数量: {len(placeholders)}
                占位符列表: {[p.get('name', str(p)) for p in placeholders]}
                
                上下文信息: {context or '无'}
                
                请为每个占位符提供：
                1. 语义分析和分类
                2. 数据处理建议
                3. SQL生成建议（如适用）
                4. 数据质量要求
                
                返回每个占位符的详细分析结果。
                """
                
                # 执行批处理分析
                batch_result = await agent.chat(batch_prompt, context={
                    "template_id": template_id,
                    "placeholders": placeholders,
                    "batch_context": context,
                    "task_type": "batch_placeholder_processing"
                })
                
                # 为每个占位符生成结果
                for placeholder in placeholders:
                    placeholder_name = placeholder.get('name', str(placeholder))
                    results.append({
                        "placeholder_name": placeholder_name,
                        "status": "processed",
                        "analysis": batch_result,
                        "processed_by": "react_agent"
                    })
                    processed_count += 1
                
                return {
                    "success": True,
                    "message": f"成功处理 {processed_count} 个占位符",
                    "processed_count": processed_count,
                    "results": results,
                    "batch_analysis": batch_result
                }
                
            except Exception as e:
                logger.error(f"批量处理占位符失败: {str(e)}")
                return {
                    "success": False,
                    "message": f"批量处理失败: {str(e)}",
                    "processed_count": 0,
                    "results": [],
                    "error": str(e)
                }
    
    return BatchRouter(db_session, user_id)


# 主要导出
__all__ = [
    # 核心类
    'IntelligentPlaceholderService',
    
    # 便捷函数
    'get_intelligent_placeholder_service',
    'analyze_template_placeholders',
    'analyze_single_placeholder',
    'create_batch_router',
    
    # 模型
    'PlaceholderSpec',
    'DocumentContext', 
    'BusinessContext',
    'TimeContext',
    'ValidationResult',
    'ProcessingResult',
    'StatisticalType',
    'SyntaxType',
    
    # 解析器
    'PlaceholderParser',
    'ParameterizedParser', 
    'CompositeParser',
    'ConditionalParser',
    'SyntaxValidator',
    'ParserFactory',
    
    # 语义分析
    'SemanticPlaceholderParser',
    'IntentClassifier',
    'SemanticAnalyzer', 
    'ImplicitParameterInferencer',
    
    # 上下文分析
    'ContextAnalysisEngine',
    'ParagraphAnalyzer',
    'SectionAnalyzer',
    'DocumentAnalyzer', 
    'BusinessRuleAnalyzer',
    
    # 权重计算
    'WeightCalculator',
    'DynamicWeightAdjuster',
    'WeightAggregator',
    'WeightLearningEngine',
    'WeightComponents'
]

async def create_context_engine_for_placeholder(
    template_content: str,
    template_metadata: dict = None,
    context_data: dict = None
) -> dict:
    """
    创建占位符专用上下文工程（符合DAG架构）
    
    Args:
        template_content: 模板内容
        template_metadata: 模板元数据
        context_data: 额外的上下文数据
    
    Returns:
        dict: 构建好的上下文工程数据
    """
    service = await get_intelligent_placeholder_service()
    
    time_context = context_data.get("time_context") if context_data else None
    business_context = context_data.get("business_context") if context_data else None
    document_context = context_data.get("document_context") if context_data else None
    
    return await service._build_context_engine_data(
        template_content,
        time_context or service._create_default_time_context(),
        business_context or service._create_default_business_context(),
        document_context or service._create_default_document_context()
    )

def get_system_info() -> dict:
    """
    获取系统信息（DAG架构版本）
    
    Returns:
        dict: 系统版本和功能信息
    """
    return {
        'version': __version__,
        'author': __author__,
        'architecture': 'DAG编排架构',
        'responsibilities': [
            '构建上下文工程',
            '调用agents系统DAG处理', 
            '协助存储中间结果',
            '占位符预处理'
        ],
        'features': {
            'context_engine_building': True,
            'dag_agents_integration': True,
            'intermediate_result_storage': True,
            'advanced_parsing': True,
            'semantic_analysis': True,
            'context_awareness': True,
            'dynamic_weighting': True,
            'performance_tracking': True
        },
        'agents_integration': {
            'dag_orchestration': True,
            'background_controller': True,
            'think_default_models': True,
            'quality_control': True
        },
        'supported_types': [
            '统计', '趋势', '极值', '列表', 
            '统计图', '对比', '预测'
        ],
        'syntax_types': [
            'basic', 'parameterized', 'composite', 'conditional'
        ]
    }