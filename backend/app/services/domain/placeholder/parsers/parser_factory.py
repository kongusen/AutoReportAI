"""
占位符解析器工厂

提供统一的解析器创建和管理接口
"""

import logging
from typing import Dict, Optional, List
from ..models import SyntaxType, PlaceholderSpec, PlaceholderParserInterface, PlaceholderSyntaxError
from .placeholder_parser import PlaceholderParser
from .parameterized_parser import ParameterizedParser
from .composite_parser import CompositeParser, AdvancedCompositeParser
from .conditional_parser import ConditionalParser, AdvancedConditionalParser
from .syntax_validator import SyntaxValidator

logger = logging.getLogger(__name__)


class ParserRegistry:
    """解析器注册表"""
    
    def __init__(self):
        self._parsers: Dict[SyntaxType, PlaceholderParserInterface] = {}
        self._fallback_parser: Optional[PlaceholderParserInterface] = None
        self._validator = SyntaxValidator()
    
    def register_parser(self, syntax_type: SyntaxType, parser: PlaceholderParserInterface):
        """注册解析器"""
        self._parsers[syntax_type] = parser
        logger.info(f"已注册解析器: {syntax_type.value}")
    
    def get_parser(self, syntax_type: SyntaxType) -> Optional[PlaceholderParserInterface]:
        """获取解析器"""
        return self._parsers.get(syntax_type)
    
    def set_fallback_parser(self, parser: PlaceholderParserInterface):
        """设置回退解析器"""
        self._fallback_parser = parser
    
    def get_all_parsers(self) -> Dict[SyntaxType, PlaceholderParserInterface]:
        """获取所有解析器"""
        return self._parsers.copy()
    
    def get_validator(self) -> SyntaxValidator:
        """获取验证器"""
        return self._validator


class ParserFactory:
    """占位符解析器工厂"""
    
    def __init__(self, use_advanced_parsers: bool = False):
        self.use_advanced_parsers = use_advanced_parsers
        self.registry = ParserRegistry()
        self._initialize_parsers()
    
    def _initialize_parsers(self):
        """初始化解析器"""
        # 注册基础解析器
        self.registry.register_parser(SyntaxType.BASIC, PlaceholderParser())
        self.registry.register_parser(SyntaxType.PARAMETERIZED, ParameterizedParser())
        
        # 注册高级解析器
        if self.use_advanced_parsers:
            self.registry.register_parser(SyntaxType.COMPOSITE, AdvancedCompositeParser())
            self.registry.register_parser(SyntaxType.CONDITIONAL, AdvancedConditionalParser())
        else:
            self.registry.register_parser(SyntaxType.COMPOSITE, CompositeParser())
            self.registry.register_parser(SyntaxType.CONDITIONAL, ConditionalParser())
        
        # 设置回退解析器
        self.registry.set_fallback_parser(PlaceholderParser())
        
        logger.info(f"解析器工厂初始化完成，使用高级解析器: {self.use_advanced_parsers}")
    
    async def parse(self, placeholder_text: str, validate: bool = True) -> PlaceholderSpec:
        """解析占位符"""
        try:
            # 预处理
            placeholder_text = self._preprocess_text(placeholder_text)
            
            # 语法验证
            if validate:
                validation_result = self.registry.get_validator().validate(placeholder_text)
                if not validation_result.is_valid:
                    raise PlaceholderSyntaxError(
                        f"语法验证失败: {'; '.join(validation_result.errors)}"
                    )
            
            # 识别语法类型
            syntax_type = self._identify_syntax_type(placeholder_text)
            
            # 获取对应的解析器
            parser = self.registry.get_parser(syntax_type)
            
            if parser and parser.supports_syntax(syntax_type):
                result = await parser.parse(placeholder_text)
                logger.debug(f"成功解析占位符 [{syntax_type.value}]: {placeholder_text}")
                return result
            else:
                # 使用回退解析器
                fallback_parser = self.registry._fallback_parser
                if fallback_parser:
                    logger.warning(f"使用回退解析器解析: {placeholder_text}")
                    return await fallback_parser.parse(placeholder_text)
                else:
                    raise PlaceholderSyntaxError(f"没有可用的解析器处理: {placeholder_text}")
        
        except Exception as e:
            logger.error(f"占位符解析失败: {placeholder_text}, 错误: {e}")
            raise
    
    async def parse_batch(self, placeholder_texts: List[str], validate: bool = True) -> List[PlaceholderSpec]:
        """批量解析占位符"""
        results = []
        
        for text in placeholder_texts:
            try:
                result = await self.parse(text, validate)
                results.append(result)
            except Exception as e:
                logger.error(f"批量解析中的占位符失败: {text}, 错误: {e}")
                # 可以选择跳过错误的占位符或抛出异常
                raise
        
        return results
    
    def _preprocess_text(self, text: str) -> str:
        """预处理占位符文本"""
        # 清理空白字符
        text = text.strip()
        
        # 标准化分隔符
        text = text.replace(':', '：')  # 统一使用中文冒号
        
        # 清理多余的空格
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text
    
    def _identify_syntax_type(self, text: str) -> SyntaxType:
        """识别语法类型"""
        import re
        
        # 按复杂度从高到低检查
        patterns = [
            (SyntaxType.CONDITIONAL, r'\{\{(\w+)：([^|}]+)\|(条件|如果|当|筛选)='),
            (SyntaxType.COMPOSITE, r'\{\{(组合|计算|聚合|转换)：'),
            (SyntaxType.PARAMETERIZED, r'\{\{(\w+)：([^|}]+)\|'),
            (SyntaxType.BASIC, r'\{\{(\w+)：([^}|]+)\}\}')
        ]
        
        for syntax_type, pattern in patterns:
            if re.search(pattern, text):
                return syntax_type
        
        # 默认返回基础类型
        return SyntaxType.BASIC
    
    def get_supported_syntax_types(self) -> List[SyntaxType]:
        """获取支持的语法类型"""
        return list(self.registry.get_all_parsers().keys())
    
    def get_parser_info(self) -> Dict[str, any]:
        """获取解析器信息"""
        return {
            "use_advanced_parsers": self.use_advanced_parsers,
            "supported_syntax_types": [st.value for st in self.get_supported_syntax_types()],
            "registered_parsers": len(self.registry.get_all_parsers()),
            "has_fallback_parser": self.registry._fallback_parser is not None,
            "has_validator": self.registry.get_validator() is not None
        }
    
    def validate_syntax(self, placeholder_text: str):
        """验证语法（公开接口）"""
        return self.registry.get_validator().validate(placeholder_text)
    
    def get_syntax_help(self, syntax_type: SyntaxType = None) -> str:
        """获取语法帮助"""
        return self.registry.get_validator().get_syntax_help(syntax_type)


class AdvancedParserFactory(ParserFactory):
    """高级解析器工厂 - 提供更强大的解析能力"""
    
    def __init__(self):
        super().__init__(use_advanced_parsers=True)
        self._setup_advanced_features()
    
    def _setup_advanced_features(self):
        """设置高级特性"""
        # 添加自定义解析器
        self._add_custom_parsers()
        
        # 配置解析器链
        self._setup_parser_chain()
    
    def _add_custom_parsers(self):
        """添加自定义解析器"""
        # 这里可以添加更多特定的解析器
        pass
    
    def _setup_parser_chain(self):
        """设置解析器链 - 支持多阶段解析"""
        # 实现解析器链模式，支持复杂的嵌套解析
        pass


class ParserFactoryBuilder:
    """解析器工厂构建器"""
    
    def __init__(self):
        self._use_advanced = False
        self._custom_parsers: Dict[SyntaxType, PlaceholderParserInterface] = {}
        self._enable_validation = True
        self._enable_logging = True
    
    def with_advanced_parsers(self) -> 'ParserFactoryBuilder':
        """启用高级解析器"""
        self._use_advanced = True
        return self
    
    def with_custom_parser(self, syntax_type: SyntaxType, parser: PlaceholderParserInterface) -> 'ParserFactoryBuilder':
        """添加自定义解析器"""
        self._custom_parsers[syntax_type] = parser
        return self
    
    def disable_validation(self) -> 'ParserFactoryBuilder':
        """禁用语法验证"""
        self._enable_validation = False
        return self
    
    def disable_logging(self) -> 'ParserFactoryBuilder':
        """禁用日志"""
        self._enable_logging = False
        return self
    
    def build(self) -> ParserFactory:
        """构建解析器工厂"""
        if self._use_advanced:
            factory = AdvancedParserFactory()
        else:
            factory = ParserFactory(use_advanced_parsers=self._use_advanced)
        
        # 注册自定义解析器
        for syntax_type, parser in self._custom_parsers.items():
            factory.registry.register_parser(syntax_type, parser)
        
        # 配置日志级别
        if not self._enable_logging:
            logging.getLogger(__name__).setLevel(logging.ERROR)
        
        return factory


# 便捷函数
def create_parser_factory(advanced: bool = False) -> ParserFactory:
    """创建解析器工厂的便捷函数"""
    return ParserFactory(use_advanced_parsers=advanced)


def create_advanced_parser_factory() -> AdvancedParserFactory:
    """创建高级解析器工厂的便捷函数"""
    return AdvancedParserFactory()


async def quick_parse(placeholder_text: str, advanced: bool = False) -> PlaceholderSpec:
    """快速解析单个占位符的便捷函数"""
    factory = create_parser_factory(advanced=advanced)
    return await factory.parse(placeholder_text)