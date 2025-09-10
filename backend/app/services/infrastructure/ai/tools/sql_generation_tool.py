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
        """为单个占位符生成SQL - 支持响应式验证和修复"""
        
        placeholder_name = placeholder.get("name", "未知占位符")
        placeholder_analysis = placeholder.get("analysis", "无分析信息")
        placeholder_context = placeholder.get("context", "")
        
        # 验证表结构信息
        if not data_source_info.get('tables'):
            raise Exception(f"数据源没有表结构信息，无法为占位符 '{placeholder_name}' 生成SQL。请先同步数据源的表结构。")
        
        # 响应式生成和验证循环
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                self.logger.info(f"第 {attempt + 1}/{max_attempts} 次尝试为占位符 '{placeholder_name}' 生成SQL")
                
                # 生成SQL
                sql = await self._generate_sql_with_llm(
                    placeholder_name, placeholder_analysis, placeholder_context,
                    data_source_info, template_context, context, attempt
                )
                
                # 验证SQL
                validation_result = self._validate_generated_sql(sql, data_source_info)
                
                if validation_result["valid"]:
                    self.logger.info(f"SQL生成成功 (尝试 {attempt + 1}): {placeholder_name}")
                    return sql
                else:
                    # 如果不是最后一次尝试，记录错误并准备重试
                    if attempt < max_attempts - 1:
                        self.logger.warning(f"SQL验证失败 (尝试 {attempt + 1}): {validation_result['error']}")
                        self.logger.info(f"准备重新生成SQL (尝试 {attempt + 2})")
                        # 将验证失败的信息传递给下一次生成
                        continue
                    else:
                        # 最后一次尝试失败
                        raise ValueError(f"经过 {max_attempts} 次尝试仍无法生成有效SQL: {validation_result['error']}")
                        
            except Exception as e:
                if attempt < max_attempts - 1:
                    self.logger.error(f"第 {attempt + 1} 次尝试失败: {e}")
                    continue
                else:
                    raise Exception(f"经过 {max_attempts} 次尝试仍无法生成SQL: {str(e)}")
        
        # 理论上不会到达这里
        raise Exception(f"未知错误：经过 {max_attempts} 次尝试后仍无法生成有效SQL")
    
    async def _generate_sql_with_llm(
        self,
        placeholder_name: str,
        placeholder_analysis: str,
        placeholder_context: str,
        data_source_info: Dict[str, Any],
        template_context: str,
        context: ToolContext,
        attempt: int
    ) -> str:
        """使用LLM生成SQL，支持多次尝试优化"""
        
        # 构建数据源表结构信息
        tables_info = self._build_tables_info(data_source_info)
        
        # 根据尝试次数调整提示词
        attempt_guidance = ""
        if attempt > 0:
            attempt_guidance = f"""
        
        ⚠️ 这是第 {attempt + 1} 次重试生成SQL，请从失败中学习并改进：
        - 前面的尝试可能因为使用了不存在的表名或字段名而失败
        - 请重新仔细阅读"可用的表列表"和"完整字段列表"
        - 严格按照列表中的确切拼写使用表名和字段名
        - 不要进行任何翻译、简化或推测，直接使用列表中的原始名称
        - 如果不确定某个字段是否存在，请优先选择明确列出的字段"""

        # 构建生成SQL的提示
        prompt = f"""
        请为以下占位符生成SQL查询：
        
        占位符名称: {placeholder_name}
        占位符分析: {placeholder_analysis}
        占位符上下文: {placeholder_context}
        
        数据源信息: {data_source_info.get('type', '未知')} - {data_source_info.get('database', '未知')}
        
        {tables_info}
        {attempt_guidance}
        
        模板上下文:
        {template_context[:300]}...
        
        重要约束：
        1. ⚠️ 严格限制：只能使用上述"可用的表列表"中的表名，绝对不要创造不存在的表名
        2. ⚠️ 表名要求：必须使用确切的表名（严格按照列表中的拼写）
        3. ⚠️ 字段名要求：必须使用确切的字段名（严格按照"完整字段列表"中的拼写）
        4. ⚠️ 字段选择：仔细查看"完整字段列表"中的字段名和类型，根据字段名称推断其业务含义
        5. ⚠️ 自主理解：基于字段名称和数据类型自主判断其业务用途（如时间、状态、类型、内容等）
        6. ⚠️ 表结构分析：根据字段组合和表名推断表的业务用途和数据内容
        7. 如果没有合适的表或字段，请返回错误信息而不是编造SQL
        8. 优先使用包含 time、date 等关键词的字段进行时间范围查询
        9. ⚠️ 验证要求：生成SQL后，请仔细确认所使用的表名和字段名都在提供的列表中完全匹配
        
        请生成一个合适的SQL查询，返回这个占位符所需的数据。
        只返回SQL语句，不需要其他解释。
        
        要求：
        1. 语法正确，适合{data_source_info.get('type', 'unknown')}数据库
        2. 只使用已列出的表和字段
        3. 包含适当的数据聚合
        4. 考虑时间范围（如果相关）
        5. 如果找不到合适的表，返回: ERROR: 没有找到合适的表来满足此查询需求
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
            sql = self._clean_sql_response(response)
            return sql
            
        except Exception as e:
            raise Exception(f"LLM生成SQL失败: {str(e)}")
    
    def _build_tables_info(self, data_source_info: Dict[str, Any]) -> str:
        """构建表结构信息字符串 - 让AI自主识别表的业务含义"""
        if not data_source_info.get('tables'):
            return "警告: 未找到表结构信息，无法生成SQL"
        
        tables_info = f"""
可用的表列表:
{', '.join(data_source_info.get('tables', []))}

详细表结构:"""
        
        for table_detail in data_source_info.get('table_details', []):
            table_name = table_detail.get('name')
            
            # 优先显示完整列信息，让AI自主理解表的业务含义
            all_columns = table_detail.get('all_columns', [])
            key_columns = table_detail.get('key_columns', [])
            
            if all_columns and len(all_columns) > 0:
                columns_info = f"""
  完整字段列表: {', '.join(all_columns)}"""
            elif key_columns and len(key_columns) > 0:
                columns_info = f"""
  主要字段: {', '.join(key_columns)}"""
            else:
                columns_info = """
  字段信息: 暂无详细字段信息"""
            
            # 添加业务分类信息（如果有的话）
            business_category = table_detail.get('business_category', '')
            category_info = f", 业务分类: {business_category}" if business_category and business_category != "未分类" else ""
            
            tables_info += f"""
- {table_name}: 列数={table_detail.get('columns_count', 0)}, 估计行数={table_detail.get('estimated_rows', 0)}{category_info}{columns_info}"""
        
        return tables_info
    
    def _clean_sql_response(self, response: str) -> str:
        """清理LLM返回的SQL语句"""
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
        
        # 检查是否返回了错误信息而不是SQL
        if sql.upper().startswith("ERROR:"):
            raise ValueError(sql)
        
        sql_lower = sql.lower()
        if not any(keyword in sql_lower for keyword in ["select", "with", "show"]):
            raise ValueError("生成的SQL不包含有效的查询语句")
        
        return sql
    
    def _validate_generated_sql(self, sql: str, data_source_info: Dict[str, Any]) -> Dict[str, Any]:
        """验证生成的SQL是否使用了正确的表名和字段名"""
        try:
            available_tables = data_source_info.get('tables', [])
            if not available_tables:
                return {"valid": True, "message": "无可用表列表，跳过验证"}
            
            import re
            sql_lower = sql.lower()
            
            # 1. 验证表名
            from_pattern = r'\bfrom\s+(?:[a-zA-Z_\u4e00-\u9fff][\w\u4e00-\u9fff]*\.)?([a-zA-Z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)'
            join_pattern = r'\bjoin\s+(?:[a-zA-Z_\u4e00-\u9fff][\w\u4e00-\u9fff]*\.)?([a-zA-Z_\u4e00-\u9fff][\w\u4e00-\u9fff]*)'
            
            used_tables = []
            used_tables.extend(re.findall(from_pattern, sql_lower, re.UNICODE))
            used_tables.extend(re.findall(join_pattern, sql_lower, re.UNICODE))
            
            available_tables_lower = [t.lower() for t in available_tables]
            invalid_tables = [table for table in used_tables if table not in available_tables_lower]
            
            if invalid_tables:
                return {
                    "valid": False,
                    "error": f"SQL使用了不存在的表: {', '.join(invalid_tables)}。可用的表: {', '.join(available_tables)}",
                    "used_tables": used_tables,
                    "invalid_tables": invalid_tables
                }
            
            # 2. 智能验证字段名（适用于所有使用的表）
            table_details = data_source_info.get('table_details', [])
            field_validation_errors = []
            
            for table_detail in table_details:
                table_name = table_detail.get('name', '').lower()
                if table_name in used_tables:
                    # 获取该表的所有可用字段
                    available_fields = []
                    for col_info in table_detail.get('all_columns', []):
                        # 从"column_name(type) [hint]"格式中提取字段名
                        field_name = col_info.split('(')[0].strip()
                        available_fields.append(field_name.lower())
                    
                    if not available_fields:  # 如果没有详细字段信息，跳过验证
                        continue
                    
                    # 提取SQL中使用的字段名
                    sql_fields = re.findall(r'\b([a-zA-Z_]\w*)\s*(?:[,\s]|$)', sql.replace('(', ' ').replace(')', ' '))
                    sql_keywords = {'select', 'from', 'where', 'group', 'by', 'order', 'count', 'sum', 'avg', 'max', 'min', 'case', 'when', 'then', 'end', 'as', 'and', 'or', 'not', 'null', 'timestampdiff', 'second', 'limit', 'having', 'distinct', 'inner', 'left', 'right', 'outer', 'join', 'on', 'union', 'all', 'exists', 'in', 'like', 'between', 'is'}
                    
                    used_fields = [f.lower() for f in sql_fields if f.lower() not in sql_keywords and not f.isdigit()]
                    
                    # 智能检查字段（通过字符串相似度检测可能的错误）
                    invalid_fields = []
                    for field in used_fields:
                        if field not in available_fields and len(field) > 2:  # 只检查有意义的字段名
                            # 使用编辑距离检测相似字段，提供智能建议
                            closest_field = self._find_closest_field(field, available_fields)
                            if closest_field:
                                invalid_fields.append(f"{field} (建议使用: {closest_field})")
                            else:
                                invalid_fields.append(field)
                    
                    if invalid_fields:
                        available_sample = available_fields[:15]  # 显示部分字段作为参考
                        field_validation_errors.append(f"表 {table_name} 中的字段错误: {', '.join(invalid_fields)}。可用字段示例: {', '.join(available_sample)}{'...' if len(available_fields) > 15 else ''}")
            
            if field_validation_errors:
                return {
                    "valid": False,
                    "error": f"字段验证失败: {'; '.join(field_validation_errors)}",
                    "used_tables": used_tables
                }
            
            return {
                "valid": True,
                "message": f"SQL验证通过，使用的表: {used_tables}",
                "used_tables": used_tables
            }
                
        except Exception as e:
            return {
                "valid": False,
                "error": f"SQL验证过程出错: {str(e)}"
            }
    
    def _find_closest_field(self, target_field: str, available_fields: list) -> str:
        """使用编辑距离算法找到最相似的字段名"""
        if not available_fields:
            return ""
        
        def edit_distance(s1: str, s2: str) -> int:
            """计算两个字符串的编辑距离"""
            if len(s1) < len(s2):
                return edit_distance(s2, s1)
            
            if len(s2) == 0:
                return len(s1)
            
            prev_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                curr_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = prev_row[j + 1] + 1
                    deletions = curr_row[j] + 1
                    substitutions = prev_row[j] + (c1 != c2)
                    curr_row.append(min(insertions, deletions, substitutions))
                prev_row = curr_row
            
            return prev_row[-1]
        
        # 找到编辑距离最小的字段
        closest_field = ""
        min_distance = float('inf')
        
        for field in available_fields:
            distance = edit_distance(target_field.lower(), field.lower())
            # 只有当距离足够小且字符串长度相近时才认为是相似的
            if distance < min_distance and distance <= max(len(target_field), len(field)) * 0.4:
                min_distance = distance
                closest_field = field
        
        # 如果编辑距离太大，不提供建议
        return closest_field if min_distance <= 3 else ""


def create_sql_generation_tool() -> SQLGenerationTool:
    """创建SQL生成工具实例"""
    return SQLGenerationTool()