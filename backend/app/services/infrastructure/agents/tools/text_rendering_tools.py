"""
智能文本生成与条件渲染工具

根据数据特征智能决定文本内容的展示逻辑，避免无意义或冗余信息
支持空数据集的友好提示、零值指标的简化表达、条件性明细展示等场景
"""

import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from .base import Tool

logger = logging.getLogger(__name__)


class ConditionalTextRenderingTool(Tool):
    """条件文本渲染工具"""

    def __init__(self, container=None):
        super().__init__()
        self.name = "conditional_text_rendering"
        self.description = "根据数据特征智能生成条件文本内容"
        self.container = container

        # 预定义文本模板
        self.templates = {
            "empty_data": {
                "sales": "本期暂无销售数据记录",
                "products": "暂未发现相关产品信息",
                "customers": "当前客户列表为空",
                "orders": "本期订单数据为空",
                "default": "暂无相关数据"
            },
            "zero_value": {
                "sales": "本期销售额为零",
                "revenue": "本期收入为零",
                "profit": "本期利润为零",
                "count": "数量为零",
                "default": "数值为零"
            },
            "low_value": {
                "sales": "本期销售额较低",
                "performance": "表现较为一般",
                "default": "数值偏低"
            },
            "high_value": {
                "sales": "本期销售额表现优异",
                "performance": "表现突出",
                "default": "数值较高"
            }
        }

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行条件文本渲染

        Args:
            input_data: {
                "data": Any,                    # 要分析的数据
                "context": str,                 # 数据上下文 (如 "sales", "products")
                "render_type": str,             # 渲染类型 ("conditional", "summary", "detail")
                "threshold_config": Dict,       # 阈值配置
                "template_override": Dict       # 自定义模板
            }
        """
        try:
            data = input_data.get("data")
            context = input_data.get("context", "default")
            render_type = input_data.get("render_type", "conditional")
            threshold_config = input_data.get("threshold_config", {})
            template_override = input_data.get("template_override", {})

            logger.info(f"开始条件文本渲染: 上下文={context}, 类型={render_type}")

            # 数据特征分析
            data_characteristics = self._analyze_data_characteristics(data)

            # 根据渲染类型生成文本
            if render_type == "conditional":
                rendered_text = await self._render_conditional_text(
                    data, data_characteristics, context, threshold_config, template_override
                )
            elif render_type == "summary":
                rendered_text = await self._render_summary_text(
                    data, data_characteristics, context
                )
            elif render_type == "detail":
                rendered_text = await self._render_detail_text(
                    data, data_characteristics, context
                )
            else:
                rendered_text = await self._render_conditional_text(
                    data, data_characteristics, context, threshold_config, template_override
                )

            return {
                "success": True,
                "result": rendered_text,
                "data_characteristics": data_characteristics,
                "context": context,
                "render_type": render_type,
                "metadata": {
                    "processed_at": datetime.now().isoformat(),
                    "data_size": data_characteristics.get("size", 0),
                    "rendering_decision": data_characteristics.get("category", "unknown")
                }
            }

        except Exception as e:
            logger.error(f"条件文本渲染失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": ""
            }

    def _analyze_data_characteristics(self, data: Any) -> Dict[str, Any]:
        """分析数据特征"""
        characteristics = {
            "is_empty": False,
            "is_zero": False,
            "is_low": False,
            "is_high": False,
            "size": 0,
            "data_type": type(data).__name__,
            "category": "normal"
        }

        # 处理不同数据类型
        if data is None:
            characteristics.update({
                "is_empty": True,
                "category": "empty",
                "size": 0
            })
        elif isinstance(data, (list, tuple)):
            size = len(data)
            characteristics.update({
                "size": size,
                "is_empty": size == 0,
                "category": "empty" if size == 0 else "list"
            })
        elif isinstance(data, dict):
            size = len(data)
            characteristics.update({
                "size": size,
                "is_empty": size == 0,
                "category": "empty" if size == 0 else "dict"
            })
        elif isinstance(data, (int, float)):
            characteristics.update({
                "size": 1,
                "is_zero": data == 0,
                "is_low": 0 < data < 100,  # 可配置阈值
                "is_high": data > 10000,   # 可配置阈值
                "category": "zero" if data == 0 else ("low" if 0 < data < 100 else ("high" if data > 10000 else "normal"))
            })
        elif isinstance(data, str):
            size = len(data.strip())
            characteristics.update({
                "size": size,
                "is_empty": size == 0,
                "category": "empty" if size == 0 else "string"
            })

        return characteristics

    async def _render_conditional_text(
        self,
        data: Any,
        characteristics: Dict[str, Any],
        context: str,
        threshold_config: Dict[str, Any],
        template_override: Dict[str, Any]
    ) -> str:
        """条件文本渲染"""

        # 处理空数据
        if characteristics["is_empty"]:
            template = template_override.get("empty_data", {}).get(context) or \
                      self.templates["empty_data"].get(context, self.templates["empty_data"]["default"])
            return template

        # 处理零值
        if characteristics["is_zero"]:
            template = template_override.get("zero_value", {}).get(context) or \
                      self.templates["zero_value"].get(context, self.templates["zero_value"]["default"])
            return template

        # 处理低值
        if characteristics["is_low"]:
            template = template_override.get("low_value", {}).get(context) or \
                      self.templates["low_value"].get(context, self.templates["low_value"]["default"])
            return f"{template}（数值：{data}）"

        # 处理高值
        if characteristics["is_high"]:
            template = template_override.get("high_value", {}).get(context) or \
                      self.templates["high_value"].get(context, self.templates["high_value"]["default"])
            return f"{template}（数值：{data}）"

        # 正常数据的详细渲染
        return await self._render_normal_data(data, characteristics, context)

    async def _render_normal_data(self, data: Any, characteristics: Dict[str, Any], context: str) -> str:
        """渲染正常数据"""
        if isinstance(data, (list, tuple)):
            size = len(data)
            if size == 1:
                return f"共有 1 条{context}记录"
            elif size <= 5:
                return f"共有 {size} 条{context}记录，明细如下"
            else:
                return f"共有 {size} 条{context}记录，显示前 5 条主要项目"

        elif isinstance(data, dict):
            keys = list(data.keys())
            if len(keys) <= 3:
                return f"{context}包含以下项目：{', '.join(keys)}"
            else:
                return f"{context}包含 {len(keys)} 个项目，主要包括：{', '.join(keys[:3])} 等"

        elif isinstance(data, (int, float)):
            return f"{context}为 {data:,.2f}" if isinstance(data, float) else f"{context}为 {data:,}"

        elif isinstance(data, str):
            if len(data) > 100:
                return f"{context}：{data[:100]}..."
            else:
                return f"{context}：{data}"

        else:
            return f"{context}数据类型：{type(data).__name__}"

    async def _render_summary_text(self, data: Any, characteristics: Dict[str, Any], context: str) -> str:
        """渲染摘要文本"""
        if characteristics["is_empty"]:
            return f"{context}摘要：暂无数据"

        if isinstance(data, (list, tuple)):
            size = len(data)
            return f"{context}摘要：共 {size} 项，{'数据丰富' if size > 10 else '数据适中' if size > 3 else '数据较少'}"

        elif isinstance(data, (int, float)):
            category = characteristics["category"]
            value_desc = {"zero": "为零", "low": "偏低", "high": "较高", "normal": "正常"}
            return f"{context}摘要：数值{value_desc.get(category, '正常')}（{data}）"

        else:
            return f"{context}摘要：数据类型为{characteristics['data_type']}"

    async def _render_detail_text(self, data: Any, characteristics: Dict[str, Any], context: str) -> str:
        """渲染详细文本"""
        if characteristics["is_empty"]:
            return f"{context}详情：暂无任何相关数据记录，建议检查数据源配置或时间范围设置"

        if isinstance(data, (list, tuple)):
            size = len(data)
            detail_text = f"{context}详情：共包含 {size} 条记录。"

            if size > 0:
                # 尝试分析列表内容
                if all(isinstance(item, dict) for item in data[:3]):
                    sample_keys = set()
                    for item in data[:3]:
                        sample_keys.update(item.keys())
                    detail_text += f"记录包含字段：{', '.join(list(sample_keys)[:5])}"
                elif all(isinstance(item, (int, float)) for item in data):
                    total = sum(data)
                    avg = total / len(data)
                    detail_text += f"数值范围：{min(data)} - {max(data)}，平均值：{avg:.2f}"

            return detail_text

        elif isinstance(data, (int, float)):
            return f"{context}详情：具体数值为 {data}，{'符合预期范围' if not characteristics['is_low'] and not characteristics['is_high'] else '需要关注'}"

        else:
            return f"{context}详情：{data}"


class SmartTemplateRenderingTool(Tool):
    """智能模板渲染工具"""

    def __init__(self, container=None):
        super().__init__()
        self.name = "smart_template_rendering"
        self.description = "智能动态模板渲染，支持条件逻辑和数据感知"
        self.container = container

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行智能模板渲染

        Args:
            input_data: {
                "template": str,           # 模板字符串
                "data": Dict[str, Any],    # 数据字典
                "conditions": Dict,        # 条件配置
                "format_rules": Dict       # 格式化规则
            }
        """
        try:
            template = input_data.get("template", "")
            data = input_data.get("data", {})
            conditions = input_data.get("conditions", {})
            format_rules = input_data.get("format_rules", {})

            logger.info(f"开始智能模板渲染: 模板长度={len(template)}")

            # 预处理数据
            processed_data = self._preprocess_data(data, conditions, format_rules)

            # 渲染模板
            rendered_text = await self._render_template(template, processed_data, conditions)

            return {
                "success": True,
                "result": rendered_text,
                "processed_data": processed_data,
                "metadata": {
                    "template_length": len(template),
                    "data_keys": list(data.keys()),
                    "rendered_at": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"智能模板渲染失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "result": ""
            }

    def _preprocess_data(self, data: Dict[str, Any], conditions: Dict, format_rules: Dict) -> Dict[str, Any]:
        """预处理数据"""
        processed = {}

        for key, value in data.items():
            # 应用格式化规则
            if key in format_rules:
                rule = format_rules[key]
                if rule.get("type") == "number" and isinstance(value, (int, float)):
                    if rule.get("format") == "currency":
                        processed[key] = f"¥{value:,.2f}"
                    elif rule.get("format") == "percentage":
                        processed[key] = f"{value:.1f}%"
                    elif rule.get("format") == "comma":
                        processed[key] = f"{value:,}"
                    else:
                        processed[key] = value
                elif rule.get("type") == "date" and isinstance(value, str):
                    # 日期格式化逻辑
                    processed[key] = value
                else:
                    processed[key] = value
            else:
                processed[key] = value

            # 添加条件变量
            processed[f"{key}_exists"] = value is not None and value != ""
            processed[f"{key}_empty"] = value is None or value == "" or (isinstance(value, (list, dict)) and len(value) == 0)
            processed[f"{key}_zero"] = value == 0 if isinstance(value, (int, float)) else False

        return processed

    async def _render_template(self, template: str, data: Dict[str, Any], conditions: Dict) -> str:
        """渲染模板"""
        # 处理条件语句 {{#if condition}}...{{/if}}
        import re

        # 条件块正则
        condition_pattern = r'\{\{#if\s+([^}]+)\}\}(.*?)\{\{/if\}\}'

        def replace_condition(match):
            condition = match.group(1).strip()
            content = match.group(2)

            # 评估条件
            try:
                # 简单的条件评估
                if condition in data:
                    if data[condition]:
                        return content
                    else:
                        return ""
                else:
                    # 处理复杂条件如 "sales > 0"
                    for key, value in data.items():
                        condition = condition.replace(key, str(value))

                    # 安全的条件评估
                    if eval(condition):
                        return content
                    else:
                        return ""
            except:
                return ""

        # 替换条件块
        rendered = re.sub(condition_pattern, replace_condition, template, flags=re.DOTALL)

        # 替换普通变量 {{variable}}
        variable_pattern = r'\{\{([^}#/]+)\}\}'

        def replace_variable(match):
            var_name = match.group(1).strip()
            return str(data.get(var_name, f"[{var_name}]"))

        rendered = re.sub(variable_pattern, replace_variable, rendered)

        return rendered


# 注册工具到工具注册表
def register_text_rendering_tools():
    """注册文本渲染工具"""
    from .registry import ToolRegistry

    registry = ToolRegistry()
    registry.register("conditional_text_rendering", ConditionalTextRenderingTool)
    registry.register("smart_template_rendering", SmartTemplateRenderingTool)


# 快速创建工具实例的工厂函数
def create_conditional_text_tool(container=None) -> ConditionalTextRenderingTool:
    """创建条件文本渲染工具"""
    return ConditionalTextRenderingTool(container)


def create_smart_template_tool(container=None) -> SmartTemplateRenderingTool:
    """创建智能模板渲染工具"""
    return SmartTemplateRenderingTool(container)


# 模块导出
__all__ = [
    "ConditionalTextRenderingTool",
    "SmartTemplateRenderingTool",
    "create_conditional_text_tool",
    "create_smart_template_tool",
    "register_text_rendering_tools"
]