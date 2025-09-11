"""
极简AI系统 - 一个函数解决所有问题
=================================

推翻所有复杂设计，回到最简单有效的方案：
- 一个主函数 `solve()`
- 直接调用LLM，不绕弯子
- 最多2次迭代，避免无限循环
- 成功就返回，失败就认输
"""

import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SimpleResult:
    """简单结果"""
    success: bool
    data: Any = None
    error: str = ""
    took_seconds: float = 0.0


class SimpleAI:
    """
    极简AI系统 - 一个类解决所有问题
    
    设计原则：
    1. 不要工具链，直接写死几个核心功能
    2. 不要复杂编排，最多重试1次
    3. 不要安全检查，相信输入
    4. 成功就返回，失败就承认失败
    """
    
    def __init__(self):
        self.total_calls = 0
        self.successful_calls = 0
        
    async def solve(
        self, 
        what: str,  # 要解决什么问题
        context: Dict[str, Any] = None  # 上下文信息
    ) -> SimpleResult:
        """
        解决问题的唯一入口
        
        Args:
            what: 问题描述，比如 "分析占位符 {{开始日期}} 并生成SQL"
            context: 上下文，包含数据源信息等
            
        Returns:
            SimpleResult: 成功或失败的结果
        """
        
        start_time = datetime.now()
        self.total_calls += 1
        
        logger.info(f"🎯 解决问题: {what}")
        
        try:
            # 第一步：判断问题类型
            problem_type = self._classify_problem(what)
            
            # 第二步：直接解决，不要复杂的工具调用
            if problem_type == "sql_generation":
                result = await self._generate_sql_directly(what, context or {})
            elif problem_type == "placeholder_analysis":  
                result = await self._analyze_placeholder_directly(what, context or {})
            elif problem_type == "template_analysis":
                result = await self._analyze_template_directly(what, context or {})
            else:
                # 万能解决方案：直接问LLM
                result = await self._ask_llm_directly(what, context or {})
            
            # 第三步：检查结果，如果失败就重试一次
            if not result.success:
                logger.warning("首次尝试失败，重试一次")
                if problem_type == "sql_generation":
                    result = await self._generate_sql_directly(what, context or {}, retry=True)
                else:
                    result = await self._ask_llm_directly(what, context or {}, retry=True)
            
            # 记录统计
            if result.success:
                self.successful_calls += 1
                logger.info(f"✅ 问题解决成功")
            else:
                logger.error(f"❌ 问题解决失败: {result.error}")
            
            result.took_seconds = (datetime.now() - start_time).total_seconds()
            return result
            
        except Exception as e:
            logger.error(f"💥 解决问题时发生异常: {e}")
            return SimpleResult(
                success=False,
                error=f"系统异常: {str(e)}",
                took_seconds=(datetime.now() - start_time).total_seconds()
            )
    
    def _classify_problem(self, what: str) -> str:
        """简单分类问题类型"""
        what_lower = what.lower()
        
        if any(keyword in what_lower for keyword in ["sql", "查询", "select", "数据库"]):
            return "sql_generation"
        elif any(keyword in what_lower for keyword in ["占位符", "placeholder", "{{"]):
            return "placeholder_analysis"
        elif any(keyword in what_lower for keyword in ["模板", "template"]):
            return "template_analysis"
        else:
            return "general"
    
    async def _generate_sql_directly(
        self, 
        what: str, 
        context: Dict[str, Any],
        retry: bool = False
    ) -> SimpleResult:
        """直接生成SQL，不绕弯子"""
        
        # 构建简单直接的提示
        prompt = f"""请为以下需求生成SQL查询：

需求: {what}

上下文信息:
{self._format_context(context)}

要求:
1. 直接返回可执行的SQL语句
2. 不要解释，不要markdown格式
3. 使用合理的表名和字段名
4. 确保语法正确

SQL:"""

        if retry:
            prompt += "\n\n注意: 这是重试，请生成一个不同的、更简单的SQL语句。"
        
        try:
            # 直接调用LLM
            sql_response = await self._call_llm(prompt)
            
            # 清理SQL
            sql = self._clean_sql(sql_response)
            
            if sql and len(sql) > 10:  # 基本验证
                return SimpleResult(
                    success=True,
                    data={"sql": sql, "description": what}
                )
            else:
                return SimpleResult(
                    success=False,
                    error="生成的SQL为空或过短"
                )
                
        except Exception as e:
            return SimpleResult(
                success=False,
                error=f"SQL生成失败: {str(e)}"
            )
    
    async def _analyze_placeholder_directly(
        self, 
        what: str, 
        context: Dict[str, Any],
        retry: bool = False
    ) -> SimpleResult:
        """直接分析占位符，不绕弯子"""
        
        prompt = f"""分析以下占位符需求：

{what}

上下文:
{self._format_context(context)}

请分析这个占位符需要什么数据，并生成对应的SQL查询。

直接返回JSON格式结果：
{{
    "placeholder_name": "占位符名称",
    "data_type": "数值/文本/日期",
    "description": "业务含义",
    "sql": "SQL查询语句"
}}"""

        try:
            response = await self._call_llm(prompt)
            
            # 尝试解析JSON
            import json
            try:
                result_data = json.loads(response)
                if "sql" in result_data and result_data["sql"]:
                    return SimpleResult(success=True, data=result_data)
                else:
                    return SimpleResult(success=False, error="占位符分析结果缺少SQL")
            except json.JSONDecodeError:
                # JSON解析失败，尝试提取SQL
                sql = self._extract_sql_from_text(response)
                if sql:
                    return SimpleResult(
                        success=True,
                        data={
                            "placeholder_name": "解析的占位符",
                            "description": what,
                            "sql": sql
                        }
                    )
                else:
                    return SimpleResult(success=False, error="无法解析占位符分析结果")
                    
        except Exception as e:
            return SimpleResult(
                success=False,
                error=f"占位符分析失败: {str(e)}"
            )
    
    async def _analyze_template_directly(
        self, 
        what: str, 
        context: Dict[str, Any],
        retry: bool = False
    ) -> SimpleResult:
        """直接分析模板，不绕弯子"""
        
        template_content = context.get("template_content", "")
        
        prompt = f"""分析模板中的占位符：

任务: {what}
模板内容: {template_content[:500]}...

找出所有占位符（格式如 {{名称}}），分析每个占位符的含义。

返回JSON格式：
{{
    "placeholders": [
        {{
            "name": "占位符名称",
            "description": "业务含义",
            "data_type": "数据类型"
        }}
    ]
}}"""

        try:
            response = await self._call_llm(prompt)
            
            import json
            try:
                result_data = json.loads(response)
                return SimpleResult(success=True, data=result_data)
            except json.JSONDecodeError:
                return SimpleResult(
                    success=False,
                    error="无法解析模板分析结果为JSON"
                )
                
        except Exception as e:
            return SimpleResult(
                success=False,
                error=f"模板分析失败: {str(e)}"
            )
    
    async def _ask_llm_directly(
        self, 
        what: str, 
        context: Dict[str, Any],
        retry: bool = False
    ) -> SimpleResult:
        """万能方案：直接问LLM"""
        
        prompt = f"""请帮我解决这个问题：

{what}

上下文信息：
{self._format_context(context)}

请给出具体的解决方案或结果。"""

        if retry:
            prompt += "\n\n注意：这是重试，请提供一个更简单直接的答案。"
        
        try:
            response = await self._call_llm(prompt)
            
            if response and len(response.strip()) > 10:
                return SimpleResult(
                    success=True,
                    data={"answer": response, "question": what}
                )
            else:
                return SimpleResult(
                    success=False,
                    error="LLM返回空答案"
                )
                
        except Exception as e:
            return SimpleResult(
                success=False,
                error=f"LLM调用失败: {str(e)}"
            )
    
    async def _call_llm(self, prompt: str) -> str:
        """调用LLM的最简单封装"""
        try:
            # 这里应该调用实际的LLM接口
            # 暂时模拟调用
            from ..llm import ask_agent_for_user
            
            response = await ask_agent_for_user(
                user_id="simple_ai_user",
                question=prompt,
                agent_type="simple_solver",
                task_type="direct_solve",
                complexity="low"
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            raise
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """格式化上下文信息"""
        if not context:
            return "无特定上下文"
        
        lines = []
        for key, value in context.items():
            if value:
                lines.append(f"- {key}: {str(value)[:100]}")
        
        return "\n".join(lines) if lines else "无特定上下文"
    
    def _clean_sql(self, sql_text: str) -> str:
        """清理SQL语句"""
        if not sql_text:
            return ""
        
        # 去掉markdown格式
        sql = sql_text.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        
        return sql.strip()
    
    def _extract_sql_from_text(self, text: str) -> str:
        """从文本中提取SQL"""
        import re
        
        # 查找SELECT语句
        sql_patterns = [
            r'SELECT.*?;',
            r'select.*?;',
            r'SELECT.*',
            r'select.*'
        ]
        
        for pattern in sql_patterns:
            matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
            if matches:
                return matches[0].strip()
        
        return ""
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "success_rate": self.successful_calls / self.total_calls if self.total_calls > 0 else 0
        }


# 全局实例
_simple_ai: Optional[SimpleAI] = None


def get_simple_ai() -> SimpleAI:
    """获取简单AI实例"""
    global _simple_ai
    if _simple_ai is None:
        _simple_ai = SimpleAI()
    return _simple_ai


# 终极简化API
async def solve_it(what: str, context: Dict[str, Any] = None) -> SimpleResult:
    """
    解决问题的终极简化API
    
    用法:
        result = await solve_it("为占位符 {{开始日期}} 生成SQL")
        if result.success:
            print(result.data)
        else:
            print(f"失败: {result.error}")
    """
    ai = get_simple_ai()
    return await ai.solve(what, context)


# 流式版本（如果需要进度反馈）
async def solve_it_stream(what: str, context: Dict[str, Any] = None) -> AsyncGenerator[str, None]:
    """
    流式解决问题（提供进度反馈）
    """
    yield f"🎯 开始解决: {what}"
    
    ai = get_simple_ai()
    result = await ai.solve(what, context)
    
    if result.success:
        yield f"✅ 解决成功 ({result.took_seconds:.1f}s)"
        yield f"📊 结果: {result.data}"
    else:
        yield f"❌ 解决失败: {result.error}"
        
    stats = ai.get_stats()
    yield f"📈 统计: {stats['successful_calls']}/{stats['total_calls']} 成功"


# 导出
__all__ = [
    "SimpleAI",
    "SimpleResult", 
    "get_simple_ai",
    "solve_it",
    "solve_it_stream"
]