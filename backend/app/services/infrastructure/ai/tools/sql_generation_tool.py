"""
SQL生成工具 - 基于新架构
"""

import logging
from typing import Dict, Any, AsyncGenerator, List

from ..core.tools import BaseTool, ToolContext, ToolResult
from ..llm import ask_agent_for_user

logger = logging.getLogger(__name__)


class SQLGenerationTool(BaseTool):
    """SQL生成工具"""
    
    def __init__(self):
        super().__init__("sql_generation_tool")
        
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["placeholders"]
        
        for field in required_fields:
            if field not in input_data:
                self.logger.error(f"缺少必需字段: {field}")
                return False
        
        if not isinstance(input_data["placeholders"], list):
            self.logger.error("占位符必须是列表格式")
            return False
            
        return True
    
    async def execute(
        self, 
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行SQL生成
        
        输入数据格式：
        {
            "placeholders": list,        # 必需：占位符列表
            "data_source_info": dict,   # 可选：数据源信息
            "template_context": str     # 可选：模板上下文
        }
        """
        
        try:
            # 1. 开始SQL生成
            yield self.create_progress_result("开始SQL生成", "initialization")
            
            placeholders = input_data["placeholders"]
            data_source_info = input_data.get("data_source_info", {})
            template_context = input_data.get("template_context", "")
            
            if not placeholders:
                yield self.create_success_result({
                    "generated_sqls": {},
                    "status": "completed",
                    "message": "没有需要生成SQL的占位符"
                })
                return
            
            yield self.create_progress_result(
                f"准备为 {len(placeholders)} 个占位符生成SQL", 
                "preparation", 
                10.0
            )
            
            # 2. 为每个占位符生成SQL
            generated_sqls = {}
            failed_sqls = []
            
            for i, placeholder in enumerate(placeholders):
                placeholder_name = placeholder.get("name", f"placeholder_{i}")
                
                yield self.create_progress_result(
                    f"生成占位符 '{placeholder_name}' 的SQL",
                    "generating_sql",
                    20.0 + (i / len(placeholders)) * 60.0
                )
                
                try:
                    sql = await self._generate_sql_for_placeholder(
                        placeholder=placeholder,
                        data_source_info=data_source_info,
                        template_context=template_context,
                        context=context
                    )
                    
                    generated_sqls[placeholder_name] = sql
                    
                except Exception as e:
                    self.logger.error(f"为占位符 '{placeholder_name}' 生成SQL失败: {e}")
                    failed_sqls.append({
                        "placeholder_name": placeholder_name,
                        "error": str(e)
                    })
            
            # 3. 生成结果摘要
            yield self.create_progress_result("生成SQL摘要", "summarizing", 90.0)
            
            result = {
                "generated_sqls": generated_sqls,
                "failed_sqls": failed_sqls,
                "status": "completed" if not failed_sqls else "partial_success",
                "summary": {
                    "total_placeholders": len(placeholders),
                    "successful_generations": len(generated_sqls),
                    "failed_generations": len(failed_sqls),
                    "success_rate": len(generated_sqls) / len(placeholders) * 100 if placeholders else 0
                },
                "metadata": {
                    "user_id": context.user_id,
                    "task_id": context.task_id,
                    "session_id": context.session_id,
                    "tool_name": self.tool_name,
                    "generated_at": self._get_timestamp()
                }
            }
            
            # 4. 返回最终结果
            yield self.create_success_result(data=result)
            
        except Exception as e:
            self.logger.error(f"SQL生成失败: {e}")
            yield self.create_error_result(
                error_message=f"SQL生成失败: {str(e)}",
                error_type="sql_generation_error"
            )
    
    async def _generate_sql_for_placeholder(
        self,
        placeholder: Dict[str, Any],
        data_source_info: Dict[str, Any],
        template_context: str,
        context: ToolContext
    ) -> str:
        """为单个占位符生成SQL"""
        
        placeholder_name = placeholder.get("name", "未知占位符")
        placeholder_analysis = placeholder.get("analysis", "无分析信息")
        placeholder_context = placeholder.get("context", "")
        
        # 构建生成SQL的提示
        prompt = f"""
        请为以下占位符生成SQL查询：
        
        占位符名称: {placeholder_name}
        占位符分析: {placeholder_analysis}
        占位符上下文: {placeholder_context}
        
        数据源信息: {data_source_info.get('type', '未知')} - {data_source_info.get('database', '未知')}
        
        模板上下文:
        {template_context[:300]}...
        
        请生成一个合适的SQL查询，返回这个占位符所需的数据。
        只返回SQL语句，不需要其他解释。
        
        要求：
        1. 语法正确
        2. 适合数据源类型
        3. 包含适当的数据聚合
        4. 考虑时间范围（如果相关）
        """
        
        try:
            response = await ask_agent_for_user(
                user_id=context.user_id,
                question=prompt,
                agent_type="sql_generation",
                task_type="sql_query_generation",
                complexity="medium"
            )
            
            # 清理SQL语句
            sql = response.strip()
            
            # 移除可能的markdown代码块标记
            if sql.startswith("```sql"):
                sql = sql[6:]
            if sql.startswith("```"):
                sql = sql[3:]
            if sql.endswith("```"):
                sql = sql[:-3]
                
            sql = sql.strip()
            
            # 基本验证
            if not sql:
                raise ValueError("生成的SQL为空")
            
            sql_lower = sql.lower()
            if not any(keyword in sql_lower for keyword in ["select", "with", "show"]):
                raise ValueError("生成的SQL不包含有效的查询语句")
            
            return sql
            
        except Exception as e:
            raise Exception(f"LLM生成SQL失败: {str(e)}")


def create_sql_generation_tool() -> SQLGenerationTool:
    """创建SQL生成工具实例"""
    return SQLGenerationTool()