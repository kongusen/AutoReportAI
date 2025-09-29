"""
占位符级别的智能文本处理器

专门处理Word模板中单个占位符的智能替换
在保持文档大结构不变的前提下，优化局部文本表述
"""

import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class PlaceholderIntelligentProcessor:
    """占位符智能处理器"""

    def __init__(self, container=None):
        self.container = container
        self.agent_facade = self._get_agent_facade()

    def _get_agent_facade(self):
        """获取Agent门面"""
        try:
            if self.container:
                return self.container.get_agent_facade()
            else:
                from .facade import AgentFacade
                return AgentFacade()
        except Exception as e:
            logger.warning(f"无法获取Agent门面: {e}")
            return None

    async def process_placeholder_data(
        self,
        placeholder_data: Dict[str, Any],
        template_context: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        处理占位符数据，返回智能优化后的文本

        Args:
            placeholder_data: ETL返回的占位符数据 {placeholder_name: data}
            template_context: 模板上下文信息 {placeholder_name: "surrounding_text"}

        Returns:
            智能处理后的占位符文本映射 {placeholder_name: "intelligent_text"}
        """

        logger.info(f"开始处理 {len(placeholder_data)} 个占位符的智能文本生成")

        processed_data = {}
        template_context = template_context or {}

        for placeholder_name, data_value in placeholder_data.items():
            try:
                # 获取模板上下文
                context_text = template_context.get(placeholder_name, "")

                # 处理单个占位符
                intelligent_text = await self._process_single_placeholder(
                    placeholder_name=placeholder_name,
                    data_value=data_value,
                    context_text=context_text
                )

                processed_data[placeholder_name] = intelligent_text

                logger.debug(f"占位符 {placeholder_name} 处理完成: {data_value} -> {intelligent_text}")

            except Exception as e:
                logger.error(f"占位符 {placeholder_name} 处理失败: {e}")
                # 降级到默认处理
                processed_data[placeholder_name] = self._fallback_process(data_value)

        logger.info(f"占位符智能处理完成，成功处理 {len(processed_data)} 个")
        return processed_data

    async def _process_single_placeholder(
        self,
        placeholder_name: str,
        data_value: Any,
        context_text: str
    ) -> str:
        """
        处理单个占位符的智能文本生成

        Args:
            placeholder_name: 占位符名称，如 "sales_total"
            data_value: 数据值，如 0, [], ["A", "B"]
            context_text: 上下文文本，如 "本期{{sales_total}}销售额..."

        Returns:
            智能生成的替换文本
        """

        # 分析数据特征
        data_analysis = self._analyze_placeholder_data(placeholder_name, data_value)

        # 如果Agent可用，使用Agent处理
        if self.agent_facade:
            agent_result = await self._process_with_agent(
                placeholder_name, data_value, context_text, data_analysis
            )
            if agent_result:
                return agent_result

        # 降级到规则处理
        return self._process_with_rules(placeholder_name, data_value, data_analysis)

    def _analyze_placeholder_data(self, placeholder_name: str, data_value: Any) -> Dict[str, Any]:
        """分析占位符数据特征"""

        analysis = {
            "name": placeholder_name,
            "value": data_value,
            "type": type(data_value).__name__,
            "is_empty": False,
            "is_zero": False,
            "is_list": False,
            "list_size": 0,
            "category": "normal"
        }

        # 空值检测
        if data_value is None or data_value == "" or data_value == []:
            analysis.update({
                "is_empty": True,
                "category": "empty"
            })

        # 零值检测
        elif isinstance(data_value, (int, float)) and data_value == 0:
            analysis.update({
                "is_zero": True,
                "category": "zero"
            })

        # 列表检测
        elif isinstance(data_value, (list, tuple)):
            size = len(data_value)
            analysis.update({
                "is_list": True,
                "list_size": size,
                "category": "empty" if size == 0 else "list"
            })

        # 业务语义推断
        business_type = self._infer_business_type(placeholder_name)
        analysis["business_type"] = business_type

        return analysis

    def _infer_business_type(self, placeholder_name: str) -> str:
        """推断业务类型"""

        name_lower = placeholder_name.lower()

        if any(keyword in name_lower for keyword in ["sales", "revenue", "income", "销售", "收入"]):
            return "sales"
        elif any(keyword in name_lower for keyword in ["product", "goods", "item", "产品", "商品"]):
            return "product"
        elif any(keyword in name_lower for keyword in ["customer", "client", "user", "客户", "用户"]):
            return "customer"
        elif any(keyword in name_lower for keyword in ["region", "area", "city", "地区", "区域", "城市"]):
            return "region"
        elif any(keyword in name_lower for keyword in ["order", "订单"]):
            return "order"
        elif any(keyword in name_lower for keyword in ["count", "num", "total", "数量", "总计"]):
            return "metric"
        else:
            return "general"

    async def _process_with_agent(
        self,
        placeholder_name: str,
        data_value: Any,
        context_text: str,
        data_analysis: Dict[str, Any]
    ) -> Optional[str]:
        """使用Agent处理占位符"""

        try:
            agent_prompt = self._build_agent_prompt(
                placeholder_name, data_value, context_text, data_analysis
            )

            from .data_model import AgentInput, TaskContext

            agent_input = AgentInput(
                user_prompt=agent_prompt,
                context=TaskContext(
                    task_time=int(datetime.now().timestamp()),
                    timezone="Asia/Shanghai"
                ),
                task_driven_context={
                    "task_type": "placeholder_text_generation",
                    "placeholder_name": placeholder_name,
                    "data_category": data_analysis["category"],
                    "business_type": data_analysis["business_type"]
                }
            )

            # 使用Agent门面执行
            result = await self.agent_facade.execute_task_validation(agent_input)

            if result.success and result.content:
                # 清理Agent返回的内容
                cleaned_text = self._clean_agent_output(result.content)
                return cleaned_text

            return None

        except Exception as e:
            logger.warning(f"Agent处理占位符 {placeholder_name} 失败: {e}")
            return None

    def _build_agent_prompt(
        self,
        placeholder_name: str,
        data_value: Any,
        context_text: str,
        data_analysis: Dict[str, Any]
    ) -> str:
        """构建Agent提示词"""

        category = data_analysis["category"]
        business_type = data_analysis["business_type"]

        prompt = f"""
你是专业的文档编辑专家，负责优化Word文档中占位符的文本表述。

## 任务背景
- 这是一个Word报告模板，整体结构不能改变
- 你只负责优化单个占位符的文本表述
- 要确保语义完整，不产生悬空表达

## 占位符信息
- 占位符名称: {placeholder_name}
- 数据值: {data_value}
- 数据类型: {data_analysis['type']}
- 业务类型: {business_type}
- 数据状态: {category}

## 模板上下文
{context_text}

## 文本生成要求

### 基本原则
1. **保持简洁**: 只返回替换文本，不要额外解释
2. **语义完整**: 确保替换后的句子语义完整
3. **自然表达**: 符合人类表达习惯
4. **避免悬空**: 不要产生"为："、"包括："后面没内容的情况

### 针对不同数据状态的处理

#### 空值/零值数据 (当前状态: {category})
- 零值: 直接表述"为零"、"暂无"等
- 空列表: 简单说明状态，不引入列举性表达

#### 正常数据
- 有具体内容时才展开详述
- 列表较长时适当概括

### 输出要求
- 只输出最终的替换文本
- 不要包含占位符符号 {{}}
- 不要包含解释说明
- 确保可以直接替换到模板中

请生成合适的替换文本：
"""

        return prompt

    def _clean_agent_output(self, agent_output: str) -> str:
        """清理Agent输出"""

        # 移除可能的占位符符号
        cleaned = re.sub(r'\{\{.*?\}\}', '', agent_output)

        # 移除多余的空白
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 移除可能的引号
        cleaned = cleaned.strip('"\'')

        return cleaned

    def _process_with_rules(
        self,
        placeholder_name: str,
        data_value: Any,
        data_analysis: Dict[str, Any]
    ) -> str:
        """使用规则处理占位符（降级方案）"""

        category = data_analysis["category"]
        business_type = data_analysis["business_type"]

        # 空值处理
        if category == "empty":
            if business_type == "sales":
                return "暂无销售数据"
            elif business_type == "product":
                return "暂无产品信息"
            elif business_type == "customer":
                return "暂无客户数据"
            elif business_type == "region":
                return "暂无区域数据"
            else:
                return "暂无数据"

        # 零值处理
        elif category == "zero":
            if business_type == "sales":
                return "为零"
            elif business_type == "metric":
                return "为0"
            else:
                return "为零"

        # 列表处理
        elif category == "list":
            size = data_analysis["list_size"]
            if size <= 3:
                # 小列表，展示详细
                if isinstance(data_value, list):
                    return "、".join(str(item) for item in data_value)
                else:
                    return str(data_value)
            else:
                # 大列表，概括表述
                preview_items = list(data_value)[:3]
                preview_text = "、".join(str(item) for item in preview_items)
                return f"{preview_text}等{size}项"

        # 正常值处理
        else:
            if isinstance(data_value, (int, float)):
                if business_type == "sales":
                    return f"{data_value:,.2f}元" if isinstance(data_value, float) else f"{data_value:,}元"
                else:
                    return f"{data_value:,.2f}" if isinstance(data_value, float) else f"{data_value:,}"
            else:
                return str(data_value)

    def _fallback_process(self, data_value: Any) -> str:
        """最终降级处理"""
        if data_value is None or data_value == [] or data_value == "":
            return "暂无数据"
        elif data_value == 0:
            return "为零"
        else:
            return str(data_value)

    def extract_template_context(self, doc_content: str) -> Dict[str, str]:
        """
        从Word文档内容中提取占位符的上下文

        Args:
            doc_content: Word文档的文本内容

        Returns:
            占位符上下文映射 {placeholder_name: "surrounding_context"}
        """

        context_map = {}

        # 查找所有占位符
        placeholder_pattern = r'\{\{([^}]+)\}\}'
        matches = re.finditer(placeholder_pattern, doc_content)

        for match in matches:
            placeholder_name = match.group(1).strip()
            start_pos = match.start()
            end_pos = match.end()

            # 提取前后各100个字符作为上下文
            context_start = max(0, start_pos - 100)
            context_end = min(len(doc_content), end_pos + 100)

            context_text = doc_content[context_start:context_end]
            context_map[placeholder_name] = context_text

        return context_map


# 快速创建实例的工厂函数
def create_placeholder_intelligent_processor(container=None) -> PlaceholderIntelligentProcessor:
    """创建占位符智能处理器"""
    return PlaceholderIntelligentProcessor(container)


# 模块导出
__all__ = [
    "PlaceholderIntelligentProcessor",
    "create_placeholder_intelligent_processor"
]