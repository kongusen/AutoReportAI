"""
Infrastructure层AI工具工厂

负责创建和管理各种AI工具的实例化

核心职责：
- 提供工具创建和实例化服务
- 管理工具依赖和配置
- 支持工具组合和定制
- 为上层Agent提供工具工厂服务

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层的Agent使用
- 提供稳定的工具创建服务
"""

import logging
from typing import Any, Dict, List, Optional, Callable, Type
from datetime import datetime
from functools import wraps

from .registry import AIToolsRegistry, ToolMetadata, ToolCategory, ToolComplexity

logger = logging.getLogger(__name__)


class ToolCreationError(Exception):
    """工具创建错误"""
    pass




def create_standard_tool(
    func: Callable,
    name: str,
    description: str,
    category: ToolCategory = ToolCategory.GENERAL,
    complexity: ToolComplexity = ToolComplexity.MEDIUM,
    cache_enabled: bool = True,
    timeout: int = 60,
    requires_auth: bool = False,
    tags: List[str] = None,
    version: str = "1.0.0"
):
    """
    创建标准工具装饰器
    
    Args:
        func: 工具函数
        name: 工具名称
        description: 工具描述
        category: 工具类别
        complexity: 复杂度
        cache_enabled: 是否启用缓存
        timeout: 超时时间
        requires_auth: 是否需要认证
        tags: 标签列表
        version: 版本号
        
    Returns:
        装饰器函数
    """
    def decorator(original_func):
        @wraps(original_func)
        def wrapper(*args, **kwargs):
            start_time = datetime.utcnow()
            
            try:
                # 执行原函数
                result = original_func(*args, **kwargs)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                logger.debug(f"工具 {name} 执行成功，用时: {execution_time:.2f}s")
                
                return result
                
            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                logger.error(f"工具 {name} 执行失败，用时: {execution_time:.2f}s, 错误: {e}")
                raise
        
        # 添加工具元数据
        wrapper._tool_metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            complexity=complexity,
            cache_enabled=cache_enabled,
            timeout=timeout,
            requires_auth=requires_auth,
            tags=tags or [],
            version=version
        )
        
        return wrapper
    
    return decorator


class AIToolsFactory:
    """
    Infrastructure层AI工具工厂
    
    核心职责：
    1. 创建和实例化各种AI工具
    2. 管理工具依赖和配置
    3. 提供工具组合和定制服务
    4. 集成工具注册表进行管理
    
    技术定位：
    - Infrastructure层技术基础设施
    - 为上层Agent提供工具创建能力
    - 不包含具体业务逻辑
    """
    
    def __init__(self, registry: Optional[AIToolsRegistry] = None):
        self.registry = registry or AIToolsRegistry()
        self.tool_builders: Dict[str, Callable] = {}
        self.created_tools_cache: Dict[str, Any] = {}
        
        # 检查LlamaIndex可用性
        self.llamaindex_available = self._check_llamaindex_availability()
        
        # 注册内置工具构建器
        self._register_builtin_builders()
        
        logger.info("AI工具工厂初始化完成")
    
    def _check_llamaindex_availability(self) -> bool:
        """检查LlamaIndex是否可用"""
        try:
            from llama_index.core.tools import FunctionTool
            return True
        except ImportError:
            logger.error("LlamaIndex不可用，无法创建工具")
            raise ImportError("LlamaIndex依赖不可用，无法创建工具")
            return False
    
    def _register_builtin_builders(self):
        """注册内置工具构建器"""
        self.tool_builders.update({
            "placeholder_parser": self._create_placeholder_parser_tool,
            "context_analyzer": self._create_context_analyzer_tool,
            "sql_generator": self._create_sql_generator_tool,
            "data_executor": self._create_data_executor_tool,
            "business_processor": self._create_business_processor_tool,
            "calculator": self._create_calculator_tool,
            "result_validator": self._create_result_validator_tool,
            "formatter": self._create_formatter_tool,
            "chart_generator": self._create_chart_generator_tool,
            "enhanced_reasoning": self._create_enhanced_reasoning_tool,
            
            # Additional specialized tools for domain services
            "data_source_analyzer": self._create_data_source_analyzer_tool,
            "template_processor": self._create_template_processor_tool,
            "report_quality_checker": self._create_report_quality_checker_tool,
            "schema_inspector": self._create_schema_inspector_tool,
            "performance_optimizer": self._create_performance_optimizer_tool
        })
    
    def create_tool_from_function(
        self,
        func: Callable,
        name: str,
        description: str,
        **kwargs
    ) -> Any:
        """
        从函数创建工具
        
        Args:
            func: 函数
            name: 工具名称
            description: 工具描述
            **kwargs: 其他参数
            
        Returns:
            创建的工具
        """
        try:
            if self.llamaindex_available:
                from llama_index.core.tools import FunctionTool
                
                tool = FunctionTool.from_defaults(
                    fn=func,
                    name=name,
                    description=description,
                    **kwargs
                )
            else:
                raise ToolCreationError(f"无法创建工具 {name}: LlamaIndex不可用")
            
            # 创建元数据
            metadata = ToolMetadata(
                name=name,
                description=description,
                category=kwargs.get('category', ToolCategory.GENERAL),
                complexity=kwargs.get('complexity', ToolComplexity.MEDIUM),
                tags=kwargs.get('tags', []),
                version=kwargs.get('version', '1.0.0')
            )
            
            # 注册到注册表
            self.registry.register_tool(tool, metadata, overwrite=True)
            
            logger.debug(f"从函数创建工具: {name}")
            return tool
            
        except Exception as e:
            logger.error(f"从函数创建工具失败: {name}, 错误: {e}")
            raise ToolCreationError(f"创建工具 {name} 失败: {e}")
    
    def create_tool_by_name(self, tool_name: str, **kwargs) -> Any:
        """
        根据名称创建工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 创建参数
            
        Returns:
            创建的工具
        """
        if tool_name in self.created_tools_cache:
            logger.debug(f"从缓存获取工具: {tool_name}")
            return self.created_tools_cache[tool_name]
        
        if tool_name in self.tool_builders:
            try:
                tool = self.tool_builders[tool_name](**kwargs)
                self.created_tools_cache[tool_name] = tool
                logger.debug(f"创建工具: {tool_name}")
                return tool
            except Exception as e:
                logger.error(f"创建工具失败: {tool_name}, 错误: {e}")
                raise ToolCreationError(f"创建工具 {tool_name} 失败: {e}")
        else:
            logger.error(f"未知的工具名称: {tool_name}")
            raise ToolCreationError(f"未知的工具名称: {tool_name}")
    
    def create_all_tools(self) -> List[Any]:
        """
        创建所有注册的工具
        
        Returns:
            工具列表
        """
        tools = []
        
        for tool_name in self.tool_builders.keys():
            try:
                tool = self.create_tool_by_name(tool_name)
                tools.append(tool)
            except Exception as e:
                logger.error(f"创建工具 {tool_name} 失败: {e}")
                continue
        
        logger.info(f"成功创建 {len(tools)} 个工具")
        return tools
    
    def create_tools_by_category(self, category: ToolCategory) -> List[Any]:
        """
        根据类别创建工具
        
        Args:
            category: 工具类别
            
        Returns:
            工具列表
        """
        return self.registry.get_tools_by_category(category)
    
    def register_tool_builder(self, name: str, builder: Callable):
        """
        注册工具构建器
        
        Args:
            name: 工具名称
            builder: 构建器函数
        """
        self.tool_builders[name] = builder
        logger.info(f"注册工具构建器: {name}")
    
    # 内置工具创建方法
    
    def _create_placeholder_parser_tool(self, **kwargs):
        """创建占位符解析工具"""
        @create_standard_tool(
            func=None,
            name="placeholder_parser",
            description="解析占位符文本，提取统计需求和参数",
            category=ToolCategory.PLACEHOLDER,
            complexity=ToolComplexity.MEDIUM,
            tags=["placeholder", "parsing", "analysis"]
        )
        def parse_placeholder(placeholder_text: str, context: Dict = None) -> Dict[str, Any]:
            """解析占位符"""
            from app.services.domain.placeholder.placeholder_parser import parse_placeholder_text
            return parse_placeholder_text(placeholder_text, context)
        
        return self.create_tool_from_function(
            func=parse_placeholder,
            name="placeholder_parser",
            description="解析占位符文本，提取统计需求和参数"
        )
    
    def _create_context_analyzer_tool(self, **kwargs):
        """创建上下文分析工具"""
        @create_standard_tool(
            func=None,
            name="context_analyzer",
            description="分析和增强上下文信息",
            category=ToolCategory.DATA_PROCESSING,
            complexity=ToolComplexity.HIGH,
            tags=["context", "analysis", "enhancement"]
        )
        def analyze_context(context_data: Dict[str, Any], requirements: Dict = None) -> Dict[str, Any]:
            """分析上下文"""
            from app.services.infrastructure.ai.context.context_analyzer_service import context_analyzer_service
            return context_analyzer_service.analyze_context(context_data, requirements)
        
        return self.create_tool_from_function(
            func=analyze_context,
            name="context_analyzer",
            description="分析和增强上下文信息"
        )
    
    def _create_sql_generator_tool(self, **kwargs):
        """创建SQL生成工具"""
        @create_standard_tool(
            func=None,
            name="sql_generator",
            description="根据需求生成SQL查询语句",
            category=ToolCategory.SQL_GENERATION,
            complexity=ToolComplexity.HIGH,
            tags=["sql", "generation", "database"]
        )
        async def generate_sql(requirements: Dict[str, Any], schema_info: Dict = None) -> Dict[str, Any]:
            """生成SQL"""
            from app.services.infrastructure.ai.sql.sql_generator_service import sql_generator_service
            return await sql_generator_service.generate_query(requirements, schema_info)
        
        return self.create_tool_from_function(
            func=generate_sql,
            name="sql_generator",
            description="根据需求生成SQL查询语句"
        )
    
    def _create_data_executor_tool(self, **kwargs):
        """创建数据执行工具"""
        @create_standard_tool(
            func=None,
            name="data_executor",
            description="执行数据查询和处理操作",
            category=ToolCategory.DATA_PROCESSING,
            complexity=ToolComplexity.MEDIUM,
            tags=["data", "execution", "query"]
        )
        def execute_data_query(sql_query: str, connection_params: Dict = None) -> Dict[str, Any]:
            """执行数据查询"""
            from app.services.data.query.query_executor_service import query_executor_service
            return query_executor_service.execute_query(sql_query, connection_params)
        
        return self.create_tool_from_function(
            func=execute_data_query,
            name="data_executor",
            description="执行数据查询和处理操作"
        )
    
    def _create_business_processor_tool(self, **kwargs):
        """创建业务逻辑处理工具"""
        @create_standard_tool(
            func=None,
            name="business_processor",
            description="处理业务逻辑和规则",
            category=ToolCategory.BUSINESS_LOGIC,
            complexity=ToolComplexity.HIGH,
            tags=["business", "logic", "rules"]
        )
        def process_business_logic(data: Any, rules: List[str] = None) -> Any:
            """处理业务逻辑"""
            from app.services.domain.business.business_logic_processor import business_logic_processor
            return business_logic_processor.process(data, rules)
        
        return self.create_tool_from_function(
            func=process_business_logic,
            name="business_processor",
            description="处理业务逻辑和规则"
        )
    
    def _create_calculator_tool(self, **kwargs):
        """创建计算工具"""
        @create_standard_tool(
            func=None,
            name="calculator",
            description="执行数学计算和聚合操作",
            category=ToolCategory.DATA_PROCESSING,
            complexity=ToolComplexity.LOW,
            tags=["calculation", "math", "aggregation"]
        )
        def calculate(expression: str, data: List[float] = None) -> float:
            """执行计算"""
            try:
                if data:
                    # 如果有数据，执行聚合计算
                    if expression.lower() == "sum":
                        return sum(data)
                    elif expression.lower() == "avg":
                        return sum(data) / len(data)
                    elif expression.lower() == "max":
                        return max(data)
                    elif expression.lower() == "min":
                        return min(data)
                
                # 简单数学表达式计算
                return eval(expression)  # 注意：在生产中需要安全的表达式求值
                
            except Exception as e:
                logger.error(f"计算失败: {e}")
                return 0.0
        
        return self.create_tool_from_function(
            func=calculate,
            name="calculator",
            description="执行数学计算和聚合操作"
        )
    
    def _create_result_validator_tool(self, **kwargs):
        """创建结果验证工具"""
        @create_standard_tool(
            func=None,
            name="result_validator",
            description="验证结果的正确性和完整性",
            category=ToolCategory.VALIDATION,
            complexity=ToolComplexity.MEDIUM,
            tags=["validation", "quality", "verification"]
        )
        def validate_result(result: Any, criteria: Dict[str, Any] = None) -> Dict[str, Any]:
            """验证结果"""
            from app.services.domain.validation.result_validator_service import result_validator_service
            return result_validator_service.validate(result, criteria)
        
        return self.create_tool_from_function(
            func=validate_result,
            name="result_validator",
            description="验证结果的正确性和完整性"
        )
    
    def _create_formatter_tool(self, **kwargs):
        """创建格式化工具"""
        @create_standard_tool(
            func=None,
            name="formatter",
            description="格式化输出结果",
            category=ToolCategory.FORMATTING,
            complexity=ToolComplexity.LOW,
            tags=["formatting", "output", "display"]
        )
        def format_result(result: Any, format_type: str = "string") -> str:
            """格式化结果"""
            if format_type == "string":
                return str(result)
            elif format_type == "json":
                import json
                return json.dumps(result, ensure_ascii=False, indent=2)
            elif format_type == "number":
                if isinstance(result, (int, float)):
                    return f"{result:,.2f}" if result % 1 else f"{result:,}"
                return str(result)
            else:
                return str(result)
        
        return self.create_tool_from_function(
            func=format_result,
            name="formatter",
            description="格式化输出结果"
        )
    
    def _create_chart_generator_tool(self, **kwargs):
        """创建图表生成工具"""
        @create_standard_tool(
            func=None,
            name="chart_generator",
            description="生成图表配置和数据",
            category=ToolCategory.CHART_GENERATION,
            complexity=ToolComplexity.HIGH,
            tags=["chart", "visualization", "graphics"]
        )
        def generate_chart(data: List[Dict], chart_type: str = "bar") -> Dict[str, Any]:
            """生成图表"""
            chart_config = {
                "title": {"text": "数据图表"},
                "xAxis": {"type": "category", "data": []},
                "yAxis": {"type": "value"},
                "series": [{"data": [], "type": chart_type}]
            }
            
            if data:
                # 从数据中提取x轴和y轴数据
                x_data = [item.get('name', f'项目{i}') for i, item in enumerate(data)]
                y_data = [item.get('value', 0) for item in data]
                
                chart_config["xAxis"]["data"] = x_data
                chart_config["series"][0]["data"] = y_data
            
            return chart_config
        
        return self.create_tool_from_function(
            func=generate_chart,
            name="chart_generator",
            description="生成图表配置和数据"
        )
    
    def _create_enhanced_reasoning_tool(self, **kwargs):
        """创建增强推理工具"""
        @create_standard_tool(
            func=None,
            name="enhanced_reasoning",
            description="提供增强的推理和分析能力",
            category=ToolCategory.CORE,
            complexity=ToolComplexity.VERY_HIGH,
            tags=["reasoning", "analysis", "enhancement"]
        )
        async def enhanced_reasoning(problem: str, context: Dict = None) -> Dict[str, Any]:
            """增强推理"""
            from app.services.infrastructure.ai.reasoning.enhanced_reasoning_service import enhanced_reasoning_service
            return await enhanced_reasoning_service.perform_reasoning(problem, context)
        
        return self.create_tool_from_function(
            func=enhanced_reasoning,
            name="enhanced_reasoning",
            description="提供增强的推理和分析能力"
        )
    
    def get_factory_info(self) -> Dict[str, Any]:
        """获取工厂信息"""
        return {
            "factory_name": "Infrastructure AI Tools Factory",
            "version": "2.0.0-ddd",
            "architecture": "DDD Infrastructure Layer",
            "llamaindex_available": self.llamaindex_available,
            "total_builders": len(self.tool_builders),
            "available_builders": list(self.tool_builders.keys()),
            "cached_tools": len(self.created_tools_cache),
            "registry_stats": self.registry.get_statistics()
        }
    
    def clear_cache(self):
        """清空工具缓存"""
        self.created_tools_cache.clear()
        logger.info("工具缓存已清空")
    
    # Additional specialized tools for domain services
    
    def _create_data_source_analyzer_tool(self, **kwargs):
        """创建数据源分析工具"""
        @create_standard_tool(
            func=None,
            name="data_source_analyzer",
            description="分析数据源连接性、性能和结构",
            category=ToolCategory.DATA_PROCESSING,
            complexity=ToolComplexity.HIGH,
            tags=["data_source", "analysis", "performance"]
        )
        async def analyze_data_source(data_source_config: Dict[str, Any]) -> Dict[str, Any]:
            """分析数据源"""
            from app.services.infrastructure.ai.analyzer.data_source_analyzer_service import data_source_analyzer_service
            return await data_source_analyzer_service.analyze_data_source(data_source_config)
        
        return self.create_tool_from_function(
            func=analyze_data_source,
            name="data_source_analyzer",
            description="分析数据源连接性、性能和结构"
        )
    
    def _create_template_processor_tool(self, **kwargs):
        """创建模板处理工具"""
        @create_standard_tool(
            func=None,
            name="template_processor",
            description="智能处理和优化模板内容",
            category=ToolCategory.DATA_PROCESSING,
            complexity=ToolComplexity.MEDIUM,
            tags=["template", "processing", "optimization"]
        )
        def process_template(template_content: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
            """处理模板"""
            from app.services.domain.template.template_processor_service import template_processor_service
            return template_processor_service.process_template(template_content, context)
        
        return self.create_tool_from_function(
            func=process_template,
            name="template_processor",
            description="智能处理和优化模板内容"
        )
    
    def _create_report_quality_checker_tool(self, **kwargs):
        """创建报告质量检查工具"""
        @create_standard_tool(
            func=None,
            name="report_quality_checker",
            description="检查和评估报告质量",
            category=ToolCategory.VALIDATION,
            complexity=ToolComplexity.HIGH,
            tags=["report", "quality", "validation"]
        )
        async def check_report_quality(report_content: str, quality_criteria: Dict[str, Any] = None) -> Dict[str, Any]:
            """检查报告质量"""
            from app.services.infrastructure.ai.quality.report_quality_checker_service import report_quality_checker_service
            return await report_quality_checker_service.check_report_quality(report_content, quality_criteria)
        
        return self.create_tool_from_function(
            func=check_report_quality,
            name="report_quality_checker",
            description="检查和评估报告质量"
        )
    
    def _create_schema_inspector_tool(self, **kwargs):
        """创建Schema检查工具"""
        @create_standard_tool(
            func=None,
            name="schema_inspector",
            description="深度检查和分析数据库Schema",
            category=ToolCategory.DATA_PROCESSING,
            complexity=ToolComplexity.HIGH,
            tags=["schema", "database", "inspection"]
        )
        async def inspect_schema(schema_info: Dict[str, Any]) -> Dict[str, Any]:
            """检查Schema"""
            from app.services.infrastructure.ai.schema.schema_inspector_service import schema_inspector_service
            return await schema_inspector_service.inspect_schema(schema_info)
        
        return self.create_tool_from_function(
            func=inspect_schema,
            name="schema_inspector",
            description="深度检查和分析数据库Schema"
        )
    
    def _create_performance_optimizer_tool(self, **kwargs):
        """创建性能优化工具"""
        @create_standard_tool(
            func=None,
            name="performance_optimizer",
            description="分析和优化系统性能",
            category=ToolCategory.DATA_PROCESSING,
            complexity=ToolComplexity.VERY_HIGH,
            tags=["performance", "optimization", "tuning"]
        )
        async def optimize_performance(performance_data: Dict[str, Any]) -> Dict[str, Any]:
            """优化性能"""
            from app.services.infrastructure.ai.performance.performance_optimizer_service import performance_optimizer_service
            return await performance_optimizer_service.optimize_performance(performance_data)
        
        return self.create_tool_from_function(
            func=optimize_performance,
            name="performance_optimizer",
            description="分析和优化系统性能"
        )