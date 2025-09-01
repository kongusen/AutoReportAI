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


class MockTool:
    """模拟工具类（当实际工具不可用时使用）"""
    def __init__(self, name: str, description: str, func: Callable = None):
        self.name = name
        self.description = description
        self.func = func or self._default_mock_func
        
        # 模拟LlamaIndex FunctionTool的接口
        class MockMetadata:
            def __init__(self, name: str, description: str):
                self.name = name
                self.description = description
        
        self.metadata = MockMetadata(name, description)
    
    def _default_mock_func(self, *args, **kwargs):
        """默认模拟函数"""
        return f"模拟工具 {self.name} 执行结果: 参数 {args} {kwargs}"
    
    async def acall(self, *args, **kwargs):
        """异步调用"""
        if self.func:
            try:
                import asyncio
                if asyncio.iscoroutinefunction(self.func):
                    return await self.func(*args, **kwargs)
                else:
                    return self.func(*args, **kwargs)
            except ImportError:
                return self.func(*args, **kwargs)
        return self._default_mock_func(*args, **kwargs)
    
    def call(self, *args, **kwargs):
        """同步调用"""
        if self.func:
            return self.func(*args, **kwargs)
        return self._default_mock_func(*args, **kwargs)
    
    def __call__(self, *args, **kwargs):
        return self.call(*args, **kwargs)


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
            logger.warning("LlamaIndex不可用，将使用模拟工具")
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
            "enhanced_reasoning": self._create_enhanced_reasoning_tool
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
                tool = MockTool(name=name, description=description, func=func)
            
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
            # 模拟解析逻辑
            return {
                "original_text": placeholder_text,
                "parsed_type": "count",
                "parameters": {"entity": "users", "filters": []},
                "confidence": 0.8,
                "context_used": bool(context)
            }
        
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
            return {
                "enhanced_context": context_data,
                "insights": ["insight1", "insight2"],
                "confidence_improvement": 0.2,
                "analysis_complete": True
            }
        
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
        def generate_sql(requirements: Dict[str, Any], schema_info: Dict = None) -> str:
            """生成SQL"""
            # 模拟SQL生成
            entity = requirements.get("entity", "table")
            operation = requirements.get("operation", "COUNT")
            
            sql = f"SELECT {operation}(*) as result FROM {entity}"
            
            if requirements.get("filters"):
                sql += " WHERE " + " AND ".join(requirements["filters"])
            
            return sql
        
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
            # 模拟数据执行
            return {
                "result": 1000,
                "rows": 1,
                "execution_time": 0.05,
                "query_executed": sql_query,
                "status": "success"
            }
        
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
            # 模拟业务逻辑处理
            processed_data = data
            
            if rules:
                for rule in rules:
                    # 应用业务规则
                    pass
            
            return {
                "processed_data": processed_data,
                "rules_applied": len(rules) if rules else 0,
                "status": "processed"
            }
        
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
            validation_result = {
                "is_valid": True,
                "confidence": 0.9,
                "quality_score": 0.8,
                "issues": [],
                "validated_result": result
            }
            
            # 模拟验证逻辑
            if criteria:
                for criterion, expected in criteria.items():
                    # 执行具体验证
                    pass
            
            return validation_result
        
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
        def enhanced_reasoning(problem: str, context: Dict = None) -> Dict[str, Any]:
            """增强推理"""
            return {
                "analysis": f"对问题 '{problem}' 的深度分析",
                "reasoning_steps": [
                    "1. 问题理解和分解",
                    "2. 上下文信息整合",
                    "3. 多角度分析",
                    "4. 结论推导"
                ],
                "confidence": 0.9,
                "recommendations": ["建议1", "建议2"],
                "enhanced_result": True
            }
        
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