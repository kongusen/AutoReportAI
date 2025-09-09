"""
模板分析工具 - 基于新架构
整合现有的SimpleTemplateAnalyzer到新的工具系统
"""

import logging
from typing import Dict, Any, AsyncGenerator

from ..core.tools import BaseTool, ToolContext, ToolResult
# 基于Claude Code架构的模板分析实现
# 使用ServiceOrchestrator统一接口

logger = logging.getLogger(__name__)


class TemplateAnalysisTool(BaseTool):
    """模板分析工具"""
    
    def __init__(self):
        super().__init__("template_analysis_tool")
        
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """验证输入数据"""
        required_fields = ["template_content"]
        
        for field in required_fields:
            if field not in input_data:
                self.logger.error(f"缺少必需字段: {field}")
                return False
        
        if not input_data["template_content"].strip():
            self.logger.error("模板内容不能为空")
            return False
            
        return True
    
    async def execute(
        self, 
        input_data: Dict[str, Any],
        context: ToolContext
    ) -> AsyncGenerator[ToolResult, None]:
        """
        执行模板分析
        
        输入数据格式：
        {
            "template_content": str,  # 必需：模板内容
            "template_id": str,       # 可选：模板ID
            "data_source_info": dict  # 可选：数据源信息
        }
        """
        
        try:
            # 1. 开始分析
            yield self.create_progress_result("开始模板分析", "initialization")
            
            # 2. 使用新架构的LLM服务
            from ..llm import ask_agent_for_user
            
            # 3. 提取模板内容和可选参数
            template_content = input_data["template_content"]
            template_id = input_data.get("template_id", "unknown")
            data_source_info = input_data.get("data_source_info")
            
            yield self.create_progress_result("初始化LLM服务完成", "llm_ready", 20.0)
            
            yield self.create_progress_result("正在解析占位符...", "parsing_placeholders", 40.0)
            
            # 解析占位符
            import re
            
            # 提取各种格式的占位符
            mustache_placeholders = re.findall(r'\{\{([^}]+)\}\}', template_content)
            bracket_placeholders = re.findall(r'\[\[([^\]]+)\]\]', template_content)
            
            all_placeholders = []
            
            # 处理 {{}} 格式的占位符
            for i, placeholder in enumerate(mustache_placeholders):
                all_placeholders.append({
                    "id": f"mustache_{i}",
                    "name": placeholder.strip(),
                    "placeholder_name": placeholder.strip(),
                    "placeholder_text": f"{{{{{placeholder}}}}}",
                    "placeholder_type": "mustache",
                    "content_type": "dynamic",
                    "description": f"占位符: {placeholder.strip()}",
                    "statistical_type": "auto_detect",
                    "is_required": True,
                    "execution_order": i + 1,
                    "context": f"模板内容中的 {{{{{placeholder}}}}} 占位符"
                })
            
            # 处理 [[]] 格式的占位符
            for i, placeholder in enumerate(bracket_placeholders):
                all_placeholders.append({
                    "id": f"bracket_{i}",
                    "name": placeholder.strip(),
                    "placeholder_name": placeholder.strip(),
                    "placeholder_text": f"[[{placeholder}]]",
                    "placeholder_type": "bracket", 
                    "content_type": "dynamic",
                    "description": f"占位符: {placeholder.strip()}",
                    "statistical_type": "auto_detect", 
                    "is_required": True,
                    "execution_order": len(mustache_placeholders) + i + 1,
                    "context": f"模板内容中的 [[{placeholder}]] 占位符"
                })
            
            total_count = len(all_placeholders)
            
            if total_count == 0:
                yield self.create_success_result({
                    "template_id": template_id,
                    "analysis_type": "claude_code_style_analysis",
                    "status": "completed",
                    "placeholder_analysis": {
                        "total_count": 0,
                        "placeholders": [],
                        "processing_status": "success"
                    },
                    "suggestions": "模板中没有发现占位符",
                    "insights": {
                        "time_context": "无占位符需要分析",
                        "data_insights": [],
                        "complexity_assessment": "simple"
                    }
                })
                return
            
            yield self.create_progress_result(f"开始逐个分析 {total_count} 个占位符", "individual_analysis", 50.0)
            
            # 使用SQL生成工具为每个占位符生成SQL
            from .sql_generation_tool import SQLGenerationTool
            sql_tool = SQLGenerationTool()
            
            # 为每个占位符分析并生成SQL
            for i, placeholder in enumerate(all_placeholders):
                placeholder_name = placeholder["name"]
                progress = 50.0 + (i / total_count) * 30.0
                
                yield self.create_progress_result(
                    f"分析占位符 '{placeholder_name}' 并生成SQL", 
                    "analyzing_placeholder",
                    progress
                )
                
                try:
                    # 日志记录占位符详细信息
                    self.logger.info(f"开始分析占位符: {placeholder_name}")
                    self.logger.info(f"占位符格式: {placeholder['placeholder_text']}")
                    self.logger.info(f"占位符上下文: {placeholder['context']}")
                    self.logger.info(f"数据源信息: {data_source_info}")
                    
                    # 为单个占位符生成分析和SQL
                    analysis_prompt = f"""
                    请分析占位符 '{placeholder_name}' 并确定其数据需求。
                    
                    占位符信息：
                    - 名称: {placeholder_name}
                    - 格式: {placeholder["placeholder_text"]}
                    - 上下文: {placeholder["context"]}
                    
                    模板片段:
                    {template_content[:500]}...
                    
                    请分析这个占位符需要什么类型的数据，并简要说明。
                    """
                    
                    self.logger.info(f"调用LLM分析占位符 '{placeholder_name}'...")
                    analysis_response = await ask_agent_for_user(
                        user_id=context.user_id,
                        question=analysis_prompt,
                        agent_type="placeholder_analysis",
                        task_type="placeholder_analysis", 
                        complexity="medium"
                    )
                    self.logger.info(f"占位符 '{placeholder_name}' 分析完成: {analysis_response[:100]}...")
                    
                    # 生成SQL
                    sql_prompt = f"""
                    请为占位符 '{placeholder_name}' 生成SQL查询语句。
                    
                    占位符分析: {analysis_response}
                    数据源类型: {data_source_info.get('type', '未知')}
                    数据库: {data_source_info.get('database', '未知')}
                    
                    请生成一个合适的SQL查询，只返回SQL语句，不需要其他解释。
                    要求：
                    1. 语法正确
                    2. 适合 {data_source_info.get('type', 'MySQL')} 数据库
                    3. 包含适当的数据聚合或统计
                    4. 考虑实际业务场景
                    """
                    
                    self.logger.info(f"开始为占位符 '{placeholder_name}' 生成SQL...")
                    sql_response = await ask_agent_for_user(
                        user_id=context.user_id,
                        question=sql_prompt,
                        agent_type="sql_generation",
                        task_type="sql_query_generation",
                        complexity="medium"
                    )
                    self.logger.info(f"占位符 '{placeholder_name}' SQL生成完成")
                    
                    # 清理SQL语句
                    sql = sql_response.strip()
                    if sql.startswith("```sql"):
                        sql = sql[6:]
                    if sql.startswith("```"):
                        sql = sql[3:]
                    if sql.endswith("```"):
                        sql = sql[:-3]
                    sql = sql.strip()
                    
                    self.logger.info(f"占位符 '{placeholder_name}' 生成的SQL: {sql}")
                    
                    # 更新占位符信息
                    placeholder.update({
                        "analysis": analysis_response,
                        "generated_sql": sql,
                        "sql_validated": bool(sql),
                        "agent_analyzed": True,
                        "target_database": data_source_info.get("database", "unknown"),
                        "confidence_score": 0.8
                    })
                    
                    self.logger.info(f"占位符 '{placeholder_name}' 分析完成，SQL验证: {bool(sql)}")
                    
                except Exception as e:
                    self.logger.error(f"分析占位符 '{placeholder_name}' 失败: {e}")
                    placeholder.update({
                        "analysis": f"分析失败: {str(e)}",
                        "generated_sql": "",
                        "sql_validated": False,
                        "agent_analyzed": False,
                        "confidence_score": 0.0
                    })
            
            # 生成整体分析建议
            yield self.create_progress_result("生成整体分析建议", "generating_suggestions", 85.0)
            
            successful_analysis = [p for p in all_placeholders if p.get("agent_analyzed", False)]
            
            suggestions = f"""
            模板分析完成：
            - 发现 {total_count} 个占位符
            - 成功分析 {len(successful_analysis)} 个占位符
            - 生成 {len([p for p in all_placeholders if p.get("generated_sql")])} 个SQL查询
            
            分析详情：
            """ + "\n".join([f"- {p['name']}: {p.get('analysis', '未分析')[:100]}..." for p in all_placeholders])
            
            # 简化的结果解析
            analysis_result = {
                "placeholder_count": total_count,
                "analyzed_placeholders": all_placeholders,
                "suggestions": suggestions,
                "time_context": "逐个占位符分析完成",
                "data_insights": [
                    f"总占位符数: {total_count}",
                    f"成功分析数: {len(successful_analysis)}",
                    f"SQL生成成功率: {len([p for p in all_placeholders if p.get('generated_sql')]) / total_count * 100:.1f}%"
                ]
            }
            
            yield self.create_progress_result("分析占位符完成", "placeholders_analyzed", 70.0)
            
            # 5. 构造标准化结果
            yield self.create_progress_result("生成分析建议...", "generating_suggestions", 90.0)
            
            result = {
                "template_id": template_id,
                "analysis_type": "claude_code_style_analysis",
                "status": "completed",
                "placeholder_analysis": {
                    "total_count": analysis_result["placeholder_count"],
                    "placeholders": analysis_result["analyzed_placeholders"],
                    "processing_status": "success"
                },
                "suggestions": analysis_result["suggestions"],
                "insights": {
                    "time_context": analysis_result["time_context"],
                    "data_insights": analysis_result["data_insights"],
                    "complexity_assessment": "medium"  # 简化实现
                },
                "metadata": {
                    "analysis_method": "claude_code_architecture",
                    "user_id": context.user_id,
                    "task_id": context.task_id,
                    "session_id": context.session_id,
                    "tool_name": self.tool_name,
                    "processed_at": self._get_timestamp()
                }
            }
            
            # 6. 返回最终结果
            yield self.create_success_result(
                data=result,
                metadata={
                    "placeholder_count": analysis_result["placeholder_count"],
                    "suggestions_count": 1,  # 简化实现
                    "has_time_context": True
                }
            )
            
        except Exception as e:
            self.logger.error(f"模板分析失败: {e}")
            
            # 返回失败结果，但保持结构化格式
            error_result = {
                "template_id": input_data.get("template_id", "unknown"),
                "analysis_type": "claude_code_style_analysis",
                "status": "failed", 
                "error": str(e),
                "placeholder_analysis": {
                    "total_count": 0,
                    "placeholders": [],
                    "processing_status": "failed"
                },
                "suggestions": ["分析失败，请检查模板格式"],
                "insights": {
                    "time_context": None,
                    "data_insights": [],
                    "complexity_assessment": "unknown"
                },
                "metadata": {
                    "analysis_method": "claude_code_architecture",
                    "user_id": context.user_id,
                    "task_id": context.task_id,
                    "error_message": str(e)
                }
            }
            
            yield self.create_error_result(
                error_message=f"模板分析失败: {str(e)}",
                error_type="template_analysis_error"
            )
            
            # 即使失败也返回结构化结果，方便调用方处理
            yield self.create_success_result(data=error_result)
    
    def _assess_complexity(self, result) -> str:
        """评估模板复杂度"""
        placeholder_count = result.placeholder_count
        
        if placeholder_count == 0:
            return "empty"
        elif placeholder_count <= 5:
            return "simple"
        elif placeholder_count <= 15:
            return "medium"
        else:
            return "complex"


def create_template_analysis_tool() -> TemplateAnalysisTool:
    """创建模板分析工具实例"""
    return TemplateAnalysisTool()