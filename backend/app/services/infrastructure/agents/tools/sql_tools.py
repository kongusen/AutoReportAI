"""
SQL相关工具集合

提供SQL生成、验证、执行、策略检查等功能
适配backup系统的数据源和LLM服务
"""

import logging
from typing import Dict, Any, List, Optional
from ..auth_context import auth_manager
from ..config_context import config_manager
from ..llm_strategy_manager import llm_strategy_manager
from ..data_source_security_service import data_source_security_service

from .base import Tool


# SQLDraftTool 已删除 - 破坏式重构
# LLM应该直接生成SQL，而不是通过工具调用另一个LLM
# 这个类的存在违反了正确的Agent架构原则


class SQLValidateTool(Tool):
    """SQL验证工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.validate"
        self.description = "验证SQL语句的正确性"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

        # Compare强校验配置（支持环境变量配置）
        import os
        self.compare_strict_validation = os.getenv('AGENT_COMPARE_STRICT_VALIDATION', 'true').lower() in ('true', '1', 'yes')
        self.compare_enforce_column_names = os.getenv('AGENT_COMPARE_ENFORCE_COLUMN_NAMES', 'false').lower() in ('true', '1', 'yes')
        self.required_compare_columns = ["baseline", "compare", "diff", "pct_change"]  # 必需列名
        self.required_compare_concepts = ["baseline", "compare", "difference", "percentage"]  # 必需概念

        # SQL安全策略配置
        self.enable_table_scan_protection = os.getenv('AGENT_ENABLE_TABLE_SCAN_PROTECTION', 'true').lower() in ('true', '1', 'yes')
        self.max_table_scan_size = int(os.getenv('AGENT_MAX_TABLE_SCAN_SIZE', '10000'))  # 允许无WHERE条件的最大表行数
        self.scan_whitelist_tables = set(os.getenv('AGENT_SCAN_WHITELIST_TABLES', 'metadata,config,lookup').split(','))
        self.scan_exempt_patterns = ['LIMIT', 'TOP', 'ROWNUM', 'SAMPLE']  # 豁免模式

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """智能SQL验证 - 结合规则验证和Agent智能检查"""
        try:
            # 调试：检查输入数据
            self._logger.debug(f"🔧 [SQL验证] 输入数据键: {list(input_data.keys())}")

            sql = input_data.get("current_sql") or input_data.get("sql", "")
            self._logger.debug(f"🔧 [SQL验证] 提取的SQL: '{sql}' (类型: {type(sql)})")

            if not sql:
                self._logger.warning(f"🔧 [SQL验证] SQL为空，输入数据: {input_data}")
                return {"success": False, "error": "SQL语句为空"}

            # 🚨 防护：检查是否收到了描述文本而不是实际SQL
            if self._is_description_text(sql):
                self._logger.error(f"🚨 [SQL验证] 收到描述文本而非SQL: '{sql}'")
                return {
                    "success": False,
                    "error": "收到描述文本而非SQL语句",
                    "issues": ["传递给验证器的不是SQL代码，而是描述文本"],
                    "warnings": ["请检查SQL生成过程，确保传递实际的SQL语句"]
                }

            # 🚀 快速通道：对于明显正确的SQL，直接通过验证
            if self._is_obviously_valid_sql(sql):
                self._logger.info("✅ SQL通过快速验证通道")
                return {
                    "success": True,
                    "sql": sql,
                    "issues": [],
                    "warnings": [],
                    "error": None,
                    "agent_validated": False,
                    "validation_decision": "快速通道验证通过"
                }

            # 第一阶段：基础语法验证
            validation_result = self._validate_sql_syntax(sql)

            # 第二阶段：语义类型特定验证
            semantic_type = (input_data.get("semantic_type") or "").lower() or None
            top_n = input_data.get("top_n")
            issues_extra = []
            warnings_extra = []

            # Compare强校验
            if semantic_type == "compare":
                compare_validation = self._validate_compare_sql(sql, input_data)
                if not compare_validation["valid"]:
                    issues_extra.extend(compare_validation["issues"])
                warnings_extra.extend(compare_validation.get("warnings", []))

            # Ranking验证
            elif semantic_type == "ranking" and top_n:
                ranking_validation = self._validate_ranking_sql(sql, top_n)
                if not ranking_validation["valid"]:
                    issues_extra.extend(ranking_validation["issues"])
                warnings_extra.extend(ranking_validation.get("warnings", []))

            # Chart验证
            elif semantic_type == "chart":
                chart_validation = self._validate_chart_sql(sql, input_data)
                warnings_extra.extend(chart_validation.get("warnings", []))

            # SQL安全策略验证（表扫描保护）
            if self.enable_table_scan_protection:
                security_validation = self._validate_table_scan_security(sql, input_data)
                if not security_validation["valid"]:
                    issues_extra.extend(security_validation["issues"])
                warnings_extra.extend(security_validation.get("warnings", []))

            # 新增：Schema一致性检查与自动修复（表/时间列）
            schema_fix = self._check_and_fix_schema_consistency(sql, input_data)
            if not schema_fix["valid"]:
                issues_extra.extend(schema_fix.get("issues", []))
            if schema_fix.get("corrected_sql"):
                # 如果生成了修正SQL，放到验证结果里，供执行器采用
                validation_result["corrected_sql"] = schema_fix["corrected_sql"]
                warnings_extra.extend(schema_fix.get("warnings", []))

            # 合并规则验证结果
            if issues_extra:
                validation_result["issues"] = (validation_result.get("issues") or []) + issues_extra
                validation_result["valid"] = False

            if warnings_extra:
                validation_result["warnings"] = (validation_result.get("warnings", [])) + warnings_extra

            # 第三阶段：真实数据源验证（核心验证）
            database_validation_done = False
            database_validation = {"success": True, "issues": [], "warnings": []}
            validation_sql_with_dates = None  # 🔧 初始化变量

            # 如果基础验证通过，进行真实数据库验证
            if validation_result.get("valid", True):
                database_validation = await self._validate_sql_against_database(sql, input_data)
                database_validation_done = True
                # 🔧 提取验证用的SQL
                validation_sql_with_dates = database_validation.get("validation_sql_with_dates")

                # 数据库验证失败时，更新整体验证状态
                if not database_validation.get("success", True):
                    validation_result["issues"] = (validation_result.get("issues", []) +
                                                 database_validation.get("issues", []))
                    validation_result["valid"] = False

                validation_result["warnings"] = (validation_result.get("warnings", []) +
                                               database_validation.get("warnings", []))

            # 第四阶段：Agent智能语法检查（仅在数据库验证失败或需要深度检查时）
            agent_validation_done = False
            agent_correction_available = False
            if not validation_result["valid"] or self._should_do_deep_validation(sql):
                agent_validation = await self._agent_validate_sql(sql, input_data)
                agent_validation_done = True

                if not agent_validation.get("success", True):
                    validation_result["issues"] = (validation_result.get("issues", []) +
                                                 agent_validation.get("issues", []))
                    validation_result["valid"] = False

                validation_result["warnings"] = (validation_result.get("warnings", []) +
                                               agent_validation.get("warnings", []))

                # 检查是否有Agent提供的修正建议
                agent_analysis = agent_validation.get("agent_analysis", {})
                if agent_analysis.get("corrected_sql"):
                    agent_correction_available = True

            # 🔄 新增：智能容错决策机制
            final_decision = self._make_validation_decision(
                validation_result,
                sql,
                input_data,
                agent_correction_available
            )

            return {
                "success": final_decision["success"],
                "sql": sql,  # ⚠️ 关键修复：返回原始带占位符的SQL，不是验证用的SQL
                "validated_sql": validation_sql_with_dates if database_validation_done else None,  # 新增：实际验证执行的SQL
                "issues": final_decision.get("issues", []),
                "warnings": final_decision.get("warnings", []),
                "error": final_decision.get("error"),
                "agent_validated": agent_validation_done,
                "database_validated": database_validation_done,
                "validation_decision": final_decision.get("decision_reason"),
                "corrected_sql": final_decision.get("corrected_sql")  # 如果有修正建议
            }

        except Exception as e:
            self._logger.error(f"SQL验证失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _check_and_fix_schema_consistency(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查SQL是否引用了未知表/不合适的时间列；必要时给出修正SQL。

        - 允许表集合取自 input_data['selected_tables'] 优先，否则 input_data['tables']。
        - 若发现未知表，尝试基于关键词/相似度匹配到允许表并替换。
        - 若发现时间列不匹配且存在 recommended_time_column，则尝试替换常见时间列名为推荐列。
        - 进一步：若SQL中使用的时间列不属于目标表，但目标表存在 dt 或其他常见时间列，则自动替换为该可用列。
        """
        try:
            sql_text = sql or ""
            allowed = set()
            sel = input_data.get("selected_tables") or []
            if isinstance(sel, list):
                allowed.update(sel)
            tabs = input_data.get("tables") or []
            if isinstance(tabs, list):
                allowed.update(tabs)
            allowed = {str(t) for t in allowed if t}

            referenced = self._find_referenced_tables(sql_text)
            unknown = [t for t in referenced if t not in allowed and t]
            issues = []
            warnings = []
            corrected = sql_text

            # 表修复
            replaced_any = False
            for unk in unknown:
                best = self._match_best_table(unk, list(allowed))
                if best:
                    # 粗略替换（考虑边界）
                    import re
                    pattern = rf"\b{re.escape(unk)}\b"
                    corrected_new = re.sub(pattern, best, corrected)
                    if corrected_new != corrected:
                        corrected = corrected_new
                        replaced_any = True
                        issues.append(f"表名不存在: {unk} → 已替换为 {best}")
                else:
                    issues.append(f"表名不存在且无法修复: {unk}")

            # 不再硬编码时间列修复，让Agent重新生成更准确的SQL
            # 如果时间列有问题，Agent会通过查看表结构重新生成正确的SQL
            self._logger.info("📋 [Schema修复] 跳过硬编码时间列修复，建议Agent重新生成SQL")

                # 硬编码时间列替换逻辑已移除 - 让Agent智能判断时间字段
                # 使用 SHOW FULL COLUMNS FROM table_name 和 Agent 智能决策代替算法逻辑

            # 返回结果
            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "corrected_sql": corrected if (replaced_any or warnings) and corrected != sql_text else None
            }
        except Exception as e:
            return {"valid": True, "issues": [f"schema_check_error: {str(e)}"], "warnings": []}

    def _find_referenced_tables(self, sql: str) -> List[str]:
        """简易SQL解析：提取 FROM/JOIN 后的表名（不含别名/库前缀）。"""
        import re
        up = sql
        tokens = []
        # 匹配 FROM xxx 或 JOIN xxx
        for m in re.finditer(r"\b(FROM|JOIN)\s+([`\w\.]+)", up, flags=re.IGNORECASE):
            raw = m.group(2).strip('`')
            # 去掉库名前缀
            if '.' in raw:
                raw = raw.split('.')[-1]
            # 去掉尾部逗号
            raw = raw.rstrip(',')
            tokens.append(raw)
        return list(dict.fromkeys(tokens))

    def _match_best_table(self, unk: str, allowed: List[str]) -> Optional[str]:
        """基于关键词与相似度选择最匹配的允许表。"""
        import difflib
        target = (unk or "").lower()
        # 先关键词命中
        pri = ["refund", "return", "退货", "退款"]
        candidates = []
        for a in allowed:
            la = a.lower()
            score = 0
            if any(k in la for k in pri):
                score += 5
            # 简单相似度
            score += int(difflib.SequenceMatcher(None, target, la).ratio() * 10)
            candidates.append((score, a))
        candidates.sort(key=lambda x: (-x[0], x[1]))
        return candidates[0][1] if candidates else None

    def _validate_sql_syntax(self, sql: str) -> Dict[str, Any]:
        """增强的SQL语法验证"""
        sql_upper = sql.upper().strip()
        issues = []

        self._logger.debug(f"[SQL验证] 验证SQL: {sql[:100]}...")
        self._logger.debug(f"[SQL验证] SQL长度: {len(sql)}, 大写后: {sql_upper[:100]}...")

        # 检查基本SQL结构
        if not sql_upper.startswith("SELECT"):
            issues.append("SQL必须以SELECT开头")
            self._logger.warning(f"[SQL验证] SELECT检查失败，SQL开头: {sql_upper[:20]}")

        if "FROM" not in sql_upper:
            issues.append("SQL必须包含FROM子句")
            self._logger.warning(f"[SQL验证] FROM检查失败，SQL内容: {sql_upper}")

        # 检查危险操作 - 使用词边界匹配，避免误报字段名
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "INSERT", "ALTER"]
        import re
        for keyword in dangerous_keywords:
            # 使用词边界匹配，确保只匹配完整的SQL关键词，不匹配字段名中的子串
            # 例如：匹配 "DELETE FROM" 但不匹配 "e_is_deleted"
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                issues.append(f"SQL包含危险关键词: {keyword}")

        # 特殊处理UPDATE - 检查是否在合法上下文中（如字段名update_time）
        if "UPDATE" in sql_upper:
            # 检查是否是合法的字段名引用
            import re
            # 匹配常见的合法UPDATE使用场景
            legal_patterns = [
                r'\bupdate_time\b',
                r'\bupdate_date\b',
                r'\bupdated_at\b',
                r'\blast_update\b',
                r'DATE\(update_time\)',
                r'WHERE\s+.*update_time',
                r'ORDER\s+BY\s+.*update_time'
            ]

            is_legal_usage = any(re.search(pattern, sql_upper) for pattern in legal_patterns)

            if is_legal_usage:
                # 从issues中移除UPDATE相关的错误
                issues = [issue for issue in issues if "UPDATE" not in issue]
                self._logger.info("✅ UPDATE检测：发现合法的update_time字段使用，移除危险关键词警报")

        # 新增：检查括号匹配
        parentheses_issues = self._check_parentheses_balance(sql)
        issues.extend(parentheses_issues)

        # 新增：检查SQL语句结束（警告而非错误）
        # 注释掉强制分号要求，因为很多SQL执行环境不需要分号
        # if not sql.strip().endswith(';'):
        #     issues.append("SQL语句应以分号(;)结尾")

        # 新增：检查常见语法错误
        syntax_issues = self._check_common_syntax_errors(sql)
        issues.extend(syntax_issues)

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "error": "; ".join(issues) if issues else None
        }

    def _check_parentheses_balance(self, sql: str) -> List[str]:
        """检查括号平衡 - SQL特定优化版本"""
        issues = []
        stack = []
        pairs = {'(': ')'}  # 只检查圆括号，方括号在SQL中用途特殊

        # 先移除SQL字符串字面量，避免误报
        import re
        sql_cleaned = re.sub(r"'[^']*'", "''", sql)  # 移除单引号字符串
        sql_cleaned = re.sub(r'"[^"]*"', '""', sql_cleaned)  # 移除双引号字符串
        sql_cleaned = re.sub(r'`[^`]*`', '``', sql_cleaned)  # 移除反引号标识符

        for i, char in enumerate(sql_cleaned):
            if char in pairs:
                stack.append((char, i))
            elif char in pairs.values():
                if not stack:
                    # 检查是否在字符串或注释中
                    context = sql[max(0, i-20):i+20]
                    if "'" in context or '"' in context or '--' in context:
                        continue  # 可能在字符串中，跳过
                    issues.append(f"多余的右括号 '{char}' 在位置 {i+1}")
                else:
                    left_char, left_pos = stack.pop()
                    expected = pairs[left_char]
                    if char != expected:
                        issues.append(f"括号不匹配: 在位置 {left_pos+1} 的 '{left_char}' 应该与 '{expected}' 匹配，但找到了 '{char}'")

        # 检查未匹配的左括号 - 更智能的检查
        for left_char, left_pos in stack:
            # 检查是否可能是SQL函数调用的一部分
            preceding_context = sql[max(0, left_pos-10):left_pos].strip()
            if any(func in preceding_context.upper() for func in ['DATE_SUB', 'DATE_ADD', 'COUNT', 'SUM', 'AVG']):
                # 可能是SQL函数，给出更具体的错误信息
                issues.append(f"SQL函数调用缺少右括号: 在位置 {left_pos+1} 的 '{left_char}' 没有匹配的右括号")
            else:
                issues.append(f"缺少右括号: 在位置 {left_pos+1} 的 '{left_char}' 没有匹配的右括号")

        return issues

    def _check_common_syntax_errors(self, sql: str) -> List[str]:
        """检查常见SQL语法错误 - 改进版，减少误报"""
        issues = []
        sql_upper = sql.upper()

        # 检查常见的MySQL函数语法 - 更精确的验证
        if 'DATE_SUB' in sql_upper or 'DATE_ADD' in sql_upper:
            import re

            # 更精确的DATE_SUB/DATE_ADD检查
            date_func_pattern = r'(DATE_SUB|DATE_ADD)\s*\(\s*[^,]+\s*,\s*INTERVAL\s+\d+\s+\w+\s*\)'

            if 'INTERVAL' in sql_upper:
                if not re.search(date_func_pattern, sql_upper):
                    # 检查是否可能是正确的但格式稍有不同
                    loose_pattern = r'(DATE_SUB|DATE_ADD)\s*\([^)]+INTERVAL[^)]+\)'
                    if re.search(loose_pattern, sql_upper):
                        # 格式可能正确但不标准，给出建议而非错误
                        pass
                    else:
                        issues.append("DATE_SUB/DATE_ADD函数需要正确的参数格式: DATE_SUB(date, INTERVAL value unit)")

        return issues

    def _should_do_deep_validation(self, sql: str) -> bool:
        """判断是否需要深度Agent验证"""
        # 检查复杂SQL模式
        complex_patterns = ['JOIN', 'UNION', 'SUBQUERY', 'CASE', 'WINDOW', 'CTE', 'DATE_SUB', 'DATE_ADD']
        sql_upper = sql.upper()
        return any(pattern in sql_upper for pattern in complex_patterns)

    async def _validate_sql_against_database(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        针对真实数据库执行SQL验证 - Plan-Tool-Active-Validate核心机制

        这是真正的验证：通过实际执行SQL（带LIMIT保护）来确认SQL的正确性
        重要：验证阶段将占位符替换为真实日期进行测试，但返回给前端的仍是占位符版本
        """
        validation_sql_with_dates = None  # 🔧 初始化变量，确保在所有返回路径中都可用

        try:
            self._logger.info(f"🔍 [数据库验证] 开始验证SQL: {sql[:100]}...")

            # 获取数据源执行器
            data_source = input_data.get("data_source")
            if not data_source:
                return {
                    "success": False,
                    "issues": ["数据源信息缺失，无法进行数据库验证"],
                    "warnings": [],
                    "validation_sql_with_dates": None
                }

            # 🔄 关键修复：验证阶段需要将占位符替换为真实日期进行测试
            validation_sql_with_dates = self._replace_placeholders_for_validation(sql, input_data)
            self._logger.info(f"📅 [占位符替换] 验证用SQL: {validation_sql_with_dates[:100]}...")

            # 创建安全的验证SQL - 添加LIMIT保护
            validation_sql = self._make_sql_safe_for_validation(validation_sql_with_dates)
            self._logger.info(f"🛡️ [安全SQL] {validation_sql}")

            # 尝试执行SQL进行验证
            try:
                # 使用数据源的查询方法
                if hasattr(data_source, 'execute_query'):
                    result = await data_source.execute_query(validation_sql, max_rows=10)
                elif hasattr(data_source, 'query'):
                    result = await data_source.query(validation_sql, limit=10)
                else:
                    # 适配：支持传入连接配置字典，使用容器数据源适配器执行
                    conn_cfg = None
                    if isinstance(data_source, dict):
                        if data_source.get("connection_config"):
                            conn_cfg = data_source.get("connection_config")
                        else:
                            # 粗略判断是否为直接的连接配置
                            keys = {"source_type", "database", "connection_string", "fe_hosts", "http_port", "query_port", "username"}
                            if any(k in data_source for k in keys):
                                conn_cfg = data_source

                    if conn_cfg:
                        adapter = getattr(self.container, 'data_source', None)
                        if not adapter:
                            return {
                                "success": False,
                                "issues": ["数据源适配器不可用"],
                                "warnings": [],
                                "validation_sql_with_dates": validation_sql_with_dates  # 🔧 添加验证用的SQL
                            }
                        result = await adapter.run_query(conn_cfg, validation_sql, limit=10)
                    else:
                        # 尝试调用容器中的旧式数据库服务
                        db_service = getattr(self.container, 'db_service', None)
                        if not db_service:
                            return {
                                "success": False,
                                "issues": ["数据库服务不可用"],
                                "warnings": [],
                                "validation_sql_with_dates": validation_sql_with_dates  # 🔧 添加验证用的SQL
                            }

                        user_id = input_data.get("user_id", "system")
                        result = await db_service.execute_query(user_id, validation_sql, limit=10)

                # 解析执行结果
                # 统一解析结果
                rows, columns = [], []
                if result:
                    try:
                        # 字典格式
                        if isinstance(result, dict):
                            rows = result.get("rows") or result.get("data") or []
                            columns = result.get("columns") or result.get("column_names") or []
                        else:
                            # 对象属性格式
                            if hasattr(result, 'rows'):
                                rows = getattr(result, 'rows', [])
                            elif hasattr(result, 'data'):
                                rows = getattr(result, 'data', [])
                            if hasattr(result, 'columns'):
                                columns = getattr(result, 'columns', [])
                            elif hasattr(result, 'column_names'):
                                columns = getattr(result, 'column_names', [])
                    except Exception:
                        rows, columns = [], []

                if rows is not None or columns is not None:
                    self._logger.info(f"✅ [数据库验证成功] 获得 {len(rows or [])} 行数据，{len(columns or [])} 列")

                    # 验证数据质量
                    quality_issues = self._validate_result_quality(rows, columns, sql, input_data)

                    return {
                        "success": True,
                        "issues": [],
                        "warnings": quality_issues,  # 质量问题作为警告而非错误
                        "validation_sql_with_dates": validation_sql_with_dates,  # 🔧 添加验证用的SQL
                        "validation_result": {
                            "row_count": len(rows or []),
                            "column_count": len(columns or []),
                            "columns": columns or [],
                            "sample_data": (rows or [])[:3]  # 返回前3行作为样本
                        }
                    }
                else:
                    # SQL执行成功但无结果
                    self._logger.warning("⚠️ [数据库验证] SQL执行成功但无数据返回")
                    return {
                        "success": True,
                        "issues": [],
                        "warnings": ["SQL执行成功但未返回数据，请检查查询条件"],
                        "validation_sql_with_dates": validation_sql_with_dates,  # 🔧 添加验证用的SQL
                        "validation_result": {
                            "row_count": 0,
                            "column_count": 0,
                            "columns": [],
                            "sample_data": []
                        }
                    }

            except Exception as exec_error:
                # 数据库执行错误 - 这是真正的SQL问题
                error_msg = str(exec_error).lower()
                self._logger.error(f"❌ [数据库验证失败] {exec_error}")

                # 分析错误类型并提供具体建议
                error_analysis = self._analyze_database_error(error_msg, sql, input_data)

                return {
                    "success": False,
                    "issues": [f"数据库执行错误: {error_analysis['error_message']}"],
                    "warnings": error_analysis.get("suggestions", []),
                    "validation_sql_with_dates": validation_sql_with_dates,  # 🔧 添加验证用的SQL
                    "database_error": {
                        "original_error": str(exec_error),
                        "error_type": error_analysis["error_type"],
                        "recommendations": error_analysis.get("suggestions", [])
                    }
                }

        except Exception as e:
            self._logger.error(f"🚨 [数据库验证异常] {e}")
            return {
                "success": False,
                "issues": [f"数据库验证过程异常: {str(e)}"],
                "warnings": [],
                "validation_sql_with_dates": validation_sql_with_dates  # 🔧 即使异常也返回（可能为None）
            }

    def _replace_placeholders_for_validation(self, sql: str, input_data: Dict[str, Any]) -> str:
        """
        为验证目的将占位符替换为真实日期

        验证阶段需要执行真实的SQL查询，所以要将{{start_date}}和{{end_date}}替换为具体日期
        但最终返回给前端的仍然是带占位符的版本
        """
        try:
            validation_sql = sql

            # 从input_data中获取时间窗口信息
            window = input_data.get("window") or input_data.get("time_window")
            if window and isinstance(window, dict):
                start_date = window.get("start_date")
                end_date = window.get("end_date")

                if start_date:
                    validation_sql = validation_sql.replace("{{start_date}}", f"'{start_date}'")
                    self._logger.info(f"🔄 替换 {{{{start_date}}}} -> '{start_date}'")

                if end_date:
                    validation_sql = validation_sql.replace("{{end_date}}", f"'{end_date}'")
                    self._logger.info(f"🔄 替换 {{{{end_date}}}} -> '{end_date}'")

            # 如果没有从window获取到日期，尝试从其他字段获取
            if "{{start_date}}" in validation_sql or "{{end_date}}" in validation_sql:
                # 检查是否有直接的日期字段
                start_date = input_data.get("start_date")
                end_date = input_data.get("end_date")

                if start_date and "{{start_date}}" in validation_sql:
                    validation_sql = validation_sql.replace("{{start_date}}", f"'{start_date}'")
                    self._logger.info(f"🔄 备用替换 {{{{start_date}}}} -> '{start_date}'")

                if end_date and "{{end_date}}" in validation_sql:
                    validation_sql = validation_sql.replace("{{end_date}}", f"'{end_date}'")
                    self._logger.info(f"🔄 备用替换 {{{{end_date}}}} -> '{end_date}'")

            # 如果仍有占位符未替换，使用默认测试日期
            if "{{start_date}}" in validation_sql or "{{end_date}}" in validation_sql:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                yesterday = today - timedelta(days=1)

                default_date = yesterday.strftime('%Y-%m-%d')

                if "{{start_date}}" in validation_sql:
                    validation_sql = validation_sql.replace("{{start_date}}", f"'{default_date}'")
                    self._logger.info(f"🔄 默认替换 {{{{start_date}}}} -> '{default_date}'")

                if "{{end_date}}" in validation_sql:
                    validation_sql = validation_sql.replace("{{end_date}}", f"'{default_date}'")
                    self._logger.info(f"🔄 默认替换 {{{{end_date}}}} -> '{default_date}'")

            return validation_sql

        except Exception as e:
            self._logger.error(f"❌ 占位符替换失败: {e}")
            return sql  # 失败时返回原始SQL

    def _make_sql_safe_for_validation(self, sql: str) -> str:
        """为验证目的制作安全的SQL。

        策略：
        - 已包含 LIMIT/TOP/ROWNUM/SAMPLE：不改动。
        - 明确聚合/分组（GROUP BY 或含 COUNT/SUM/AVG/MIN/MAX）：不加 LIMIT，避免误伤口径与类别完整性。
        - 其余查询：末尾添加 LIMIT 10（验证小样本）。
        """
        original = sql or ""
        sql = (original.strip() or "")

        # 移除末尾分号
        if sql.endswith(';'):
            sql = sql[:-1]

        up = sql.upper()
        # 已有样本限制
        if any(tok in up for tok in [" LIMIT ", " TOP ", "ROWNUM", " SAMPLE "]):
            return sql

        # 聚合/分组查询不过度加 LIMIT（以免误伤比例/类别完整性）
        has_group_by = " GROUP BY " in up
        has_agg = any(fn in up for fn in ["COUNT(", "SUM(", "AVG(", "MIN(", "MAX("])
        if has_group_by or has_agg:
            return sql

        # 其他情况加入LIMIT 10
        return f"{sql} LIMIT 10"

    def _validate_result_quality(self, rows: List, columns: List, sql: str, input_data: Dict[str, Any]) -> List[str]:
        """验证查询结果的数据质量"""
        warnings = []

        # 检查列数和数据完整性
        if not columns:
            warnings.append("查询结果缺少列信息")

        if not rows:
            warnings.append("查询未返回数据行，请检查时间范围或过滤条件")
        elif len(rows) < 3:
            warnings.append(f"查询结果较少（仅{len(rows)}行），可能需要调整查询条件")

        # 检查语义类型特定的质量要求
        semantic_type = input_data.get("semantic_type", "").lower()

        if semantic_type == "compare":
            # 对比查询应该有baseline, compare, diff, pct_change等列
            required_concepts = ["基准", "对比", "差值", "百分比", "baseline", "compare", "diff", "pct", "change"]
            has_compare_structure = any(any(concept in str(col).lower() for concept in required_concepts)
                                      for col in columns)
            if not has_compare_structure:
                warnings.append("对比查询结果中未发现对比结构（基准值、对比值、差值、变化率）")

        elif semantic_type == "ranking":
            # 排名查询应该有排序结构
            if len(rows) > 1:
                # 简单检查：如果有数值列，检查是否有排序趋势
                numeric_cols = []
                for i, col in enumerate(columns):
                    try:
                        if rows[0] and i < len(rows[0]) and isinstance(rows[0][i], (int, float)):
                            numeric_cols.append(i)
                    except:
                        pass

                if not numeric_cols:
                    warnings.append("排名查询结果中未发现数值列用于排序")

        return warnings

    def _analyze_database_error(self, error_msg: str, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据库错误并提供修复建议"""
        error_analysis = {
            "error_type": "unknown",
            "error_message": error_msg,
            "suggestions": []
        }

        # 表/列不存在错误
        if any(keyword in error_msg for keyword in ["table", "column", "field", "doesn't exist", "not found", "unknown"]):
            error_analysis["error_type"] = "schema_mismatch"
            error_analysis["suggestions"] = [
                "检查表名和列名是否正确",
                "确认使用的表和列在数据库schema中存在",
                "建议重新获取schema信息"
            ]

        # 语法错误
        elif any(keyword in error_msg for keyword in ["syntax", "parse", "grammar", "invalid"]):
            error_analysis["error_type"] = "syntax_error"
            error_analysis["suggestions"] = [
                "检查SQL语法是否正确",
                "确认括号、引号是否匹配",
                "检查关键字拼写是否正确"
            ]

        # 权限错误
        elif any(keyword in error_msg for keyword in ["permission", "access", "denied", "unauthorized"]):
            error_analysis["error_type"] = "permission_error"
            error_analysis["suggestions"] = [
                "检查数据库访问权限",
                "确认用户有查询相关表的权限"
            ]

        # 数据类型错误
        elif any(keyword in error_msg for keyword in ["type", "conversion", "cast", "format"]):
            error_analysis["error_type"] = "data_type_error"
            error_analysis["suggestions"] = [
                "检查数据类型转换是否正确",
                "确认日期、数值格式是否符合要求"
            ]

        return error_analysis

    async def _agent_validate_sql(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """使用Agent进行智能SQL语法验证"""
        try:
            # 构建智能验证提示词
            prompt = self._build_agent_validation_prompt(sql, input_data)

            # 调用LLM进行验证
            llm_service = getattr(self.container, 'llm_service', None) or getattr(self.container, 'llm', None)
            if not llm_service:
                self._logger.warning("LLM service not available for agent validation")
                return {"success": True, "issues": [], "warnings": []}

            # 获取用户ID
            user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"

            # 设置LLM策略，要求返回JSON格式
            llm_policy = {
                "stage": "tool",
                "step": "sql.validate",
                "complexity": "medium",
                "output_kind": "sql_validation"
            }

            # 请求JSON格式响应
            response_format = {"type": "json_object"}

            # 调用LLM
            response = await llm_service.ask(
                user_id=user_id,
                prompt=prompt,
                response_format=response_format,
                llm_policy=llm_policy
            )

            # 解析LLM响应
            import json
            try:
                validation_response = json.loads(response.get("response", "{}"))
            except json.JSONDecodeError:
                self._logger.warning("LLM返回非JSON格式，使用基础验证")
                return {"success": True, "issues": [], "warnings": []}

            # 提取验证结果
            is_valid = validation_response.get("is_valid", True)
            syntax_errors = validation_response.get("syntax_errors", [])
            suggestions = validation_response.get("suggestions", [])

            self._logger.info(f"🤖 Agent SQL验证完成: valid={is_valid}, errors={len(syntax_errors)}, suggestions={len(suggestions)}")

            return {
                "success": is_valid,
                "issues": syntax_errors if not is_valid else [],
                "warnings": suggestions,
                "agent_analysis": validation_response
            }

        except Exception as e:
            self._logger.error(f"Agent SQL验证失败: {e}")
            # 失败时不影响主流程
            return {"success": True, "issues": [], "warnings": []}

    def _build_agent_validation_prompt(self, sql: str, input_data: Dict[str, Any]) -> str:
        """构建Agent验证提示词"""
        semantic_type = input_data.get("semantic_type", "")
        user_prompt = input_data.get("user_prompt", "")

        # 预检查：如果SQL看起来是正确的，给Agent一个提示
        confidence_hint = ""
        if self._is_likely_valid_sql(sql):
            confidence_hint = "\n⚠️ 提示：此SQL语句通过了基础模式匹配验证，请谨慎判断是否存在真正的语法错误。"

        return f"""
你是一个专业的SQL语法检查专家。请仔细检查以下SQL语句的语法正确性。

原始需求: {user_prompt}
占位符类型: {semantic_type}
SQL语句:
```sql
{sql}
```
{confidence_hint}

请检查以下方面：
1. 语法正确性（括号匹配、关键字拼写、函数调用格式）
2. 查询逻辑合理性
3. 潜在的性能问题
4. 数据类型兼容性

⚠️ 重要提示：
- 对于DATE_SUB(CURDATE(), INTERVAL 1 YEAR)这样的标准MySQL函数调用，如果括号匹配正确，应判定为有效
- 请区分真正的语法错误和格式偏好问题
- 只有确实无法执行的SQL才应标记为无效
- 🕐 测试环境说明：允许使用未来日期进行测试，不要因为日期超出当前范围而判定为无效
- 日期范围检查不是语法错误，即使查询结果可能为空也应该允许执行
- ✅ 同一日期的BETWEEN查询（如 BETWEEN '2025-09-26' AND '2025-09-26'）是完全有效的语法
- ✅ DATE()函数查询（如 WHERE DATE(column) = '2025-09-26'）也是有效的

返回JSON格式结果：
{{
    "is_valid": true/false,
    "syntax_errors": ["具体的语法错误描述"],
    "suggestions": ["改进建议"],
    "confidence": 0.95,
    "corrected_sql": "如果有错误，提供修正后的SQL"
}}
"""

    def _validate_compare_sql(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare查询强校验"""
        issues = []
        warnings = []
        valid = True

        if not self.compare_strict_validation:
            self._logger.info("Compare强校验已禁用，跳过验证")
            return {"valid": True, "issues": [], "warnings": []}

        sql_upper = sql.upper()
        self._logger.info(f"🔍 [CompareValidation] 开始Compare强校验，enforce_column_names={self.compare_enforce_column_names}")

        # 1. 强制检查必需列名（如果启用）
        if self.compare_enforce_column_names:
            missing_columns = []
            for required_col in self.required_compare_columns:
                if required_col.upper() not in sql_upper:
                    missing_columns.append(required_col)

            if missing_columns:
                issues.append(f"Compare查询必须包含以下列名: {', '.join(missing_columns)}")
                valid = False
                self._logger.warning(f"⚠️ [CompareValidation] 缺少必需列名: {missing_columns}")

        # 2. 必须包含基准期和对比期的概念（更严格）
        baseline_keywords = ["BASELINE", "BASE", "PREVIOUS", "LAST", "PRIOR", "BEFORE", "OLD"]
        compare_keywords = ["COMPARE", "CURRENT", "NEW", "NOW", "AFTER", "RECENT"]

        has_baseline = any(keyword in sql_upper for keyword in baseline_keywords)
        has_compare = any(keyword in sql_upper for keyword in compare_keywords)

        if not has_baseline:
            issues.append(f"Compare查询必须包含基准期概念 (关键词: {', '.join(baseline_keywords[:3])}...)")
            valid = False

        if not has_compare:
            issues.append(f"Compare查询必须包含对比期概念 (关键词: {', '.join(compare_keywords[:3])}...)")
            valid = False

        # 3. 强制要求包含差值计算（更精确检查）
        diff_patterns = ["DIFF", "DIFFERENCE", "CHANGE", "DELTA", "MINUS", "SUBTRACT", "VARIANCE"]
        has_diff = any(pattern in sql_upper for pattern in diff_patterns)
        has_arithmetic_diff = " - " in sql or "(-" in sql  # 算术差值

        if not (has_diff or has_arithmetic_diff):
            issues.append("Compare查询必须包含差值计算 (使用 DIFF/CHANGE 列名或算术运算 '-')")
            valid = False

        # 4. 强制要求包含百分比变化（更精确检查）
        pct_patterns = ["PCT", "PERCENT", "PERCENTAGE", "RATE", "RATIO", "GROWTH"]
        has_pct = any(pattern in sql_upper for pattern in pct_patterns)
        has_pct_formula = "*100" in sql.replace(" ", "") or "/100" in sql.replace(" ", "")  # 百分比公式

        if not (has_pct or has_pct_formula):
            issues.append("Compare查询必须包含百分比变化 (使用 PCT_CHANGE/PERCENTAGE 列名或百分比计算)")
            valid = False

        # 5. 检查是否有时间维度（升级为强制要求）
        time_keywords = ["DATE", "TIME", "YEAR", "MONTH", "DAY", "PERIOD", "WEEK", "QUARTER"]
        has_time_dimension = any(keyword in sql_upper for keyword in time_keywords)

        if not has_time_dimension:
            issues.append("Compare查询必须包含时间维度以明确对比期间")
            valid = False

        # 6. 检查是否有适当的分组和排序
        has_group_by = "GROUP BY" in sql_upper
        has_order_by = "ORDER BY" in sql_upper

        if not has_group_by:
            warnings.append("Compare查询建议使用 GROUP BY 进行适当分组")

        if not has_order_by:
            warnings.append("Compare查询建议使用 ORDER BY 按变化幅度排序")

        # 7. 检查潜在的数据质量问题
        if "WHERE" not in sql_upper:
            warnings.append("Compare查询建议添加 WHERE 条件限制数据范围，避免全表扫描")

        result = {
            "valid": valid,
            "issues": issues,
            "warnings": warnings
        }

        if valid:
            self._logger.info("✅ [CompareValidation] Compare查询通过强校验")
        else:
            self._logger.warning(f"🚨 [CompareValidation] Compare查询未通过强校验，发现 {len(issues)} 个问题")

        return result

    def _validate_ranking_sql(self, sql: str, top_n: int) -> Dict[str, Any]:
        """排名查询验证"""
        issues = []
        warnings = []
        valid = True

        sql_upper = sql.upper()

        # 检查是否有排序和限制
        has_order_by = "ORDER BY" in sql_upper
        has_limit = "LIMIT" in sql_upper or f"LIMIT {top_n}" in sql_upper
        has_rank_function = any(func in sql_upper for func in [
            "RANK()", "DENSE_RANK()", "ROW_NUMBER()", "NTILE("
        ])

        if not has_order_by and not has_rank_function:
            issues.append("排名查询必须包含 ORDER BY 子句或窗口排名函数")
            valid = False

        if not has_limit and not has_rank_function:
            warnings.append(f"排名查询建议使用 LIMIT {top_n} 或窗口函数限制结果数量")

        return {
            "valid": valid,
            "issues": issues,
            "warnings": warnings
        }

    def _validate_chart_sql(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """图表查询验证"""
        warnings = []

        chart_type = input_data.get("chart_type", "").lower()
        sql_upper = sql.upper()

        # 根据图表类型给出建议
        if chart_type == "pie":
            if "GROUP BY" not in sql_upper:
                warnings.append("饼图建议使用 GROUP BY 对类别进行分组")
        elif chart_type == "line":
            has_time = any(keyword in sql_upper for keyword in [
                "DATE", "TIME", "YEAR", "MONTH", "DAY"
            ])
            if not has_time:
                warnings.append("折线图建议包含时间维度数据")
        elif chart_type == "bar":
            if "ORDER BY" not in sql_upper:
                warnings.append("柱状图建议使用 ORDER BY 对结果排序")

        return {
            "valid": True,
            "warnings": warnings
        }

    def _validate_table_scan_security(self, sql: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """SQL表扫描安全验证 - 防止无WHERE条件的大表扫描"""
        issues = []
        warnings = []
        valid = True

        if not self.enable_table_scan_protection:
            self._logger.info("表扫描保护已禁用，跳过验证")
            return {"valid": True, "issues": [], "warnings": []}

        sql_upper = sql.upper()
        self._logger.info(f"🔐 [TableScanSecurity] 开始表扫描安全验证")

        # 检查是否有WHERE条件
        has_where = "WHERE" in sql_upper
        has_limit = any(pattern in sql_upper for pattern in self.scan_exempt_patterns)

        if not has_where and not has_limit:
            # 提取表名进行白名单检查
            tables = self._extract_table_names(sql)
            blocked_tables = []
            whitelisted_tables = []

            for table in tables:
                table_clean = table.lower().strip()
                if table_clean in self.scan_whitelist_tables:
                    whitelisted_tables.append(table)
                else:
                    blocked_tables.append(table)

            if blocked_tables:
                self._logger.warning(f"🚨 [TableScanSecurity] 检测到大表扫描风险: {blocked_tables}")

                # 尝试获取表大小信息（如果可用）
                table_size_info = self._get_table_size_info(blocked_tables, input_data)
                large_tables = []

                for table, size_info in table_size_info.items():
                    estimated_size = size_info.get("estimated_rows", 0)
                    if estimated_size > self.max_table_scan_size:
                        large_tables.append(f"{table}(~{estimated_size}行)")

                if large_tables:
                    issues.append(
                        f"禁止无WHERE条件扫描大表: {', '.join(large_tables)}。"
                        f"请添加WHERE条件限制数据范围，或使用LIMIT限制返回行数"
                    )
                    valid = False
                else:
                    warnings.append(
                        f"检测到无WHERE条件的表扫描: {', '.join(blocked_tables)}。"
                        f"建议添加WHERE条件或LIMIT子句以提升性能"
                    )

            if whitelisted_tables:
                self._logger.info(f"✅ [TableScanSecurity] 白名单表允许扫描: {whitelisted_tables}")

        # 检查JOIN操作的安全性
        if "JOIN" in sql_upper and not has_where:
            warnings.append("多表JOIN操作建议使用WHERE条件限制结果集大小")

        # 检查聚合操作
        has_aggregation = any(func in sql_upper for func in ["COUNT", "SUM", "AVG", "MAX", "MIN", "GROUP BY"])
        if has_aggregation and not has_where and not has_limit:
            warnings.append("聚合查询建议添加WHERE条件或时间范围限制")

        result = {
            "valid": valid,
            "issues": issues,
            "warnings": warnings
        }

        if valid:
            self._logger.info("✅ [TableScanSecurity] SQL表扫描安全验证通过")
        else:
            self._logger.warning(f"🚨 [TableScanSecurity] SQL存在安全风险，发现 {len(issues)} 个问题")

        return result

    def _extract_table_names(self, sql: str) -> list:
        """从SQL中提取表名"""
        import re

        # 简化的表名提取（可以根据需要改进）
        sql_clean = re.sub(r'--.*', '', sql)  # 移除注释
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)  # 移除多行注释

        # 查找FROM和JOIN后的表名
        tables = set()

        # FROM子句
        from_pattern = r'\bFROM\s+(\w+)'
        for match in re.finditer(from_pattern, sql_clean, re.IGNORECASE):
            tables.add(match.group(1))

        # JOIN子句
        join_pattern = r'\bJOIN\s+(\w+)'
        for match in re.finditer(join_pattern, sql_clean, re.IGNORECASE):
            tables.add(match.group(1))

        return list(tables)

    def _get_table_size_info(self, tables: list, input_data: Dict[str, Any]) -> Dict[str, Dict]:
        """获取表大小信息（如果可用）"""
        # 简化实现，实际可以从数据源或元数据服务获取
        size_info = {}

        # 默认表大小估算（实际应该从数据库统计信息获取）
        default_estimates = {
            "users": {"estimated_rows": 50000},
            "orders": {"estimated_rows": 100000},
            "transactions": {"estimated_rows": 500000},
            "logs": {"estimated_rows": 1000000},
            "events": {"estimated_rows": 2000000},
        }

        for table in tables:
            table_lower = table.lower()
            if table_lower in default_estimates:
                size_info[table] = default_estimates[table_lower]
            else:
                # 保守估计
                size_info[table] = {"estimated_rows": self.max_table_scan_size + 1}

        return size_info

    def _make_validation_decision(self, validation_result: Dict[str, Any], sql: str, input_data: Dict[str, Any], agent_correction_available: bool = False) -> Dict[str, Any]:
        """智能容错决策机制 - 判断是否应该通过验证"""
        issues = validation_result.get("issues", [])
        warnings = validation_result.get("warnings", [])
        original_valid = validation_result.get("valid", True)

        # 🚨 严重错误：必须阻止通过
        critical_keywords = [
            "DROP", "DELETE", "TRUNCATE", "INSERT", "UPDATE", "ALTER",
            "多余的右括号", "SQL函数调用缺少右括号"
        ]

        has_critical_issues = any(
            any(keyword in issue for keyword in critical_keywords)
            for issue in issues
        )

        if has_critical_issues:
            return {
                "success": False,
                "issues": issues,
                "warnings": warnings,
                "error": "; ".join(issues),
                "decision_reason": "发现严重语法错误，必须修复"
            }

        # 🟡 轻微问题：可以容忍的错误类型
        tolerable_issues = [
            "缺少右括号",  # 但不是函数调用的
            "DATE_SUB/DATE_ADD函数需要正确的参数格式",
            "SQL语句应以分号(;)结尾"
        ]

        # 分离严重和轻微问题
        serious_issues = []
        minor_issues = []

        for issue in issues:
            is_tolerable = any(tolerable in issue for tolerable in tolerable_issues)

            # 特殊处理：如果是函数调用的括号问题，视为严重
            if "缺少右括号" in issue and any(func in issue for func in ['DATE_SUB', 'DATE_ADD', 'COUNT', 'SUM']):
                serious_issues.append(issue)
            elif is_tolerable:
                minor_issues.append(issue)
            else:
                serious_issues.append(issue)

        # 🔍 新增：智能SQL语法检查 - 对于常见的正确SQL模式进行白名单验证
        if not serious_issues and self._is_likely_valid_sql(sql):
            # 使用SQL模式匹配进行最后验证
            return {
                "success": True,
                "issues": [],
                "warnings": warnings + minor_issues,  # 轻微问题转为警告
                "error": None,
                "decision_reason": f"通过智能模式验证，{len(minor_issues)}个轻微问题转为警告"
            }

        # 决策逻辑
        if not serious_issues:
            # 没有严重问题，可以通过，但保留警告
            return {
                "success": True,
                "issues": [],
                "warnings": warnings + minor_issues,  # 轻微问题转为警告
                "error": None,
                "decision_reason": f"通过容错验证，{len(minor_issues)}个轻微问题转为警告"
            }

        elif len(serious_issues) == 1 and agent_correction_available:
            # 只有一个严重问题且有Agent修正建议，可以提供修正建议
            return {
                "success": False,
                "issues": serious_issues,
                "warnings": warnings + minor_issues,
                "error": "; ".join(serious_issues),
                "decision_reason": "发现可修复的语法错误，已提供修正建议"
            }

        else:
            # 多个严重问题，必须修复
            return {
                "success": False,
                "issues": serious_issues + minor_issues,
                "warnings": warnings,
                "error": "; ".join(serious_issues + minor_issues),
                "decision_reason": f"发现{len(serious_issues)}个严重错误，需要修复"
            }

    def _is_likely_valid_sql(self, sql: str) -> bool:
        """智能SQL模式检查 - 识别常见的正确SQL模式"""
        sql_clean = sql.strip().upper()

        # 检查常见的正确SQL模式
        valid_patterns = [
            # 标准COUNT查询模式
            r'^SELECT\s+COUNT\(\*\)\s+AS\s+\w+\s+FROM\s+\w+\s+WHERE\s+.+;?$',
            # 带DATE_SUB的查询模式
            r'^SELECT\s+.+\s+FROM\s+\w+\s+WHERE\s+.+DATE_SUB\(CURDATE\(\),\s*INTERVAL\s+\d+\s+\w+\)\s*;?$',
            # 基本SELECT模式
            r'^SELECT\s+.+\s+FROM\s+\w+(\s+WHERE\s+.+)?(\s+ORDER\s+BY\s+.+)?(\s+LIMIT\s+\d+)?\s*;?$'
        ]

        import re
        for pattern in valid_patterns:
            if re.match(pattern, sql_clean, re.DOTALL):
                self._logger.info(f"✅ SQL匹配有效模式: {pattern[:50]}...")
                return True

        # 额外检查：DATE_SUB函数格式
        if 'DATE_SUB' in sql_clean:
            # 验证DATE_SUB函数是否格式正确
            date_sub_pattern = r'DATE_SUB\s*\(\s*CURDATE\s*\(\s*\)\s*,\s*INTERVAL\s+\d+\s+\w+\s*\)'
            if re.search(date_sub_pattern, sql_clean):
                self._logger.info("✅ DATE_SUB函数格式验证通过")
                return True

        # 简单括号平衡检查
        if self._simple_parentheses_check(sql):
            self._logger.info("✅ 简单括号平衡检查通过")
            return True

        return False

    def _simple_parentheses_check(self, sql: str) -> bool:
        """简单的括号平衡检查 - 更宽松的验证"""
        count = 0
        in_string = False
        quote_char = None

        for i, char in enumerate(sql):
            # 处理字符串
            if char in ('"', "'", '`') and not in_string:
                in_string = True
                quote_char = char
            elif char == quote_char and in_string:
                in_string = False
                quote_char = None
            elif in_string:
                continue

            # 计算括号
            if char == '(':
                count += 1
            elif char == ')':
                count -= 1

            # 如果括号数量为负，说明有多余的右括号
            if count < 0:
                return False

        # 最终括号数量应该为0
        return count == 0

    def _is_description_text(self, sql: str) -> bool:
        """检测是否为描述文本而非SQL"""
        if not sql or not isinstance(sql, str):
            return False

        sql_lower = sql.lower().strip()

        # 明显的描述性关键词
        description_keywords = [
            "当前候选", "候选sql", "sql内容", "已有sql", "现有sql",
            "待验证", "等待", "请", "需要", "建议", "应该",
            "候选的", "当前的", "生成的", "提供的", "返回的"
        ]

        # 如果包含描述性关键词但不包含SQL关键词，可能是描述文本
        has_description = any(keyword in sql_lower for keyword in description_keywords)
        has_sql_keywords = any(keyword in sql_lower for keyword in ["select", "from", "where", "insert", "update", "delete"])

        if has_description and not has_sql_keywords:
            self._logger.warning(f"🔍 [描述检测] 发现描述性关键词但无SQL关键词: {sql[:50]}")
            return True

        # 如果是很短的文本且不包含SQL关键词，可能是描述
        if len(sql.strip()) < 50 and not has_sql_keywords:
            self._logger.warning(f"🔍 [描述检测] 文本过短且无SQL关键词: {sql}")
            return True

        # 如果包含中文描述性词语
        chinese_description = ["当前", "候选", "内容", "描述", "信息", "数据", "结果"]
        has_chinese_desc = any(keyword in sql for keyword in chinese_description)
        if has_chinese_desc and not has_sql_keywords:
            self._logger.warning(f"🔍 [描述检测] 发现中文描述但无SQL关键词: {sql[:50]}")
            return True

        return False

    def _is_obviously_valid_sql(self, sql: str) -> bool:
        """快速检查明显正确的SQL - 用于绕过复杂验证"""
        sql_clean = sql.strip()
        sql_upper = sql_clean.upper()

        # 检查是否包含危险操作
        dangerous_keywords = ["DROP", "DELETE", "TRUNCATE", "UPDATE", "INSERT", "ALTER"]
        if any(keyword in sql_upper for keyword in dangerous_keywords):
            return False

        # 必须是SELECT查询
        if not sql_upper.startswith("SELECT"):
            return False

        # 必须有FROM子句
        if "FROM" not in sql_upper:
            return False

        # 特殊模式：标准的COUNT查询与DATE_SUB
        count_date_sub_pattern = (
            sql_upper.startswith("SELECT COUNT(*) AS") and
            "FROM" in sql_upper and
            "WHERE" in sql_upper and
            "DATE_SUB(CURDATE(), INTERVAL" in sql_upper
        )

        if count_date_sub_pattern:
            # 进行简单的括号检查
            if self._simple_parentheses_check(sql_clean):
                self._logger.info("✅ 识别为标准COUNT+DATE_SUB模式，快速通过")
                return True

        # 其他明显正确的简单模式
        simple_patterns = [
            # 简单的SELECT * FROM table;
            r'^SELECT\s+\*\s+FROM\s+\w+\s*;?$',
            # SELECT column FROM table WHERE condition;
            r'^SELECT\s+\w+\s+FROM\s+\w+\s+WHERE\s+.+\s*;?$',
        ]

        import re
        for pattern in simple_patterns:
            if re.match(pattern, sql_upper):
                if self._simple_parentheses_check(sql_clean):
                    self._logger.info(f"✅ 匹配简单SQL模式，快速通过")
                    return True

        return False


class SQLExecuteTool(Tool):
    """SQL执行工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.execute"
        self.description = "执行SQL查询获取数据"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            sql = input_data.get("current_sql") or input_data.get("sql", "")
            if not sql:
                return {"success": False, "error": "SQL语句为空"}

            # 🔄 关键修复：执行前需要将占位符替换为真实日期
            executable_sql = self._replace_placeholders_for_execution(sql, input_data)
            self._logger.info(f"🚀 [SQL执行] 原始SQL: {sql[:100]}...")
            self._logger.info(f"📅 [SQL执行] 执行SQL: {executable_sql[:100]}...")

            # 获取用户ID和数据源ID
            user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"
            data_source_config = input_data.get("data_source", {})
            data_source_id = data_source_config.get("id")

            # 数据源权限验证
            if user_id != "system" and data_source_id:
                self._logger.info(f"验证用户 {user_id} 对数据源 {data_source_id} 的访问权限")

                access_validation = data_source_security_service.validate_data_source_access(
                    user_id=user_id,
                    data_source_id=data_source_id
                )

                if not access_validation.get("allowed"):
                    self._logger.warning(f"数据源访问被拒绝: {access_validation}")
                    return {
                        "success": False,
                        "error": f"数据源访问权限验证失败: {access_validation.get('reason', '未知错误')}",
                        "error_code": access_validation.get("error_code", "ACCESS_DENIED")
                    }

                self._logger.info("数据源权限验证通过")

            # 获取数据源服务
            data_source_service = getattr(self.container, 'data_source_service', None) or getattr(self.container, 'data_source', None)
            if not data_source_service:
                return {"success": False, "error": "Data source service not available"}

            # 执行SQL (使用替换后的可执行SQL)
            result = await self._execute_sql(data_source_service, executable_sql, input_data)

            return {
                "success": True,
                "sql": sql,
                "rows": result.get("rows", []),
                "columns": result.get("columns", []),
                "row_count": len(result.get("rows", []))
            }

        except Exception as e:
            self._logger.error(f"SQL执行失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _execute_sql(self, data_source_service, sql: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL查询"""
        try:
            # 构建数据源配置
            data_source_config = context.get("data_source", {}) or {}

            # 若 data_source 中仅有 id/type/database 等简要信息，尝试通过 user_data_source_service 获取完整连接配置
            container = getattr(self, 'container', None)
            user_id = context.get("user_id")
            ds_id = data_source_config.get("id")
            resolved_cfg = None

            if container and hasattr(container, 'user_data_source_service') and user_id and ds_id:
                try:
                    uds = await container.user_data_source_service.get_user_data_source(user_id=user_id, data_source_id=ds_id)
                    if uds and getattr(uds, 'connection_config', None):
                        resolved_cfg = uds.connection_config
                except Exception:
                    resolved_cfg = None

            final_cfg = resolved_cfg or data_source_config

            # 兼容类型映射（mysql/postgres → sql）
            t = (final_cfg.get("source_type") or final_cfg.get("type") or "").lower()
            if t in ("mysql", "postgres", "postgresql", "mariadb"):
                final_cfg["source_type"] = "sql"

            # 尝试不同的执行方法
            if hasattr(data_source_service, 'execute_query'):
                result = await data_source_service.execute_query(sql, final_cfg)
            elif hasattr(data_source_service, 'run_query'):
                result = await data_source_service.run_query(final_cfg, sql)
            elif callable(data_source_service):
                result = await data_source_service(sql, final_cfg)
            else:
                raise ValueError("Unsupported data source service interface")

            return {
                "rows": result.get("rows", result.get("data", [])),
                "columns": result.get("columns", result.get("column_names", []))
            }

        except Exception as e:
            self._logger.error(f"SQL执行异常: {str(e)}")
            return {"rows": [], "columns": []}

    def _replace_placeholders_for_execution(self, sql: str, input_data: Dict[str, Any]) -> str:
        """
        为执行目的将占位符替换为真实日期

        执行阶段需要运行真实的SQL查询，所以要将{{start_date}}和{{end_date}}替换为具体日期
        """
        try:
            executable_sql = sql

            # 从input_data中获取时间窗口信息
            window = input_data.get("window") or input_data.get("time_window")
            if window and isinstance(window, dict):
                start_date = window.get("start_date")
                end_date = window.get("end_date")

                if start_date:
                    executable_sql = executable_sql.replace("{{start_date}}", f"'{start_date}'")
                    self._logger.info(f"🔄 [执行替换] {{{{start_date}}}} -> '{start_date}'")

                if end_date:
                    executable_sql = executable_sql.replace("{{end_date}}", f"'{end_date}'")
                    self._logger.info(f"🔄 [执行替换] {{{{end_date}}}} -> '{end_date}'")

            # 如果没有从window获取到日期，尝试从其他字段获取
            if "{{start_date}}" in executable_sql or "{{end_date}}" in executable_sql:
                start_date = input_data.get("start_date")
                end_date = input_data.get("end_date")

                if start_date and "{{start_date}}" in executable_sql:
                    executable_sql = executable_sql.replace("{{start_date}}", f"'{start_date}'")
                    self._logger.info(f"🔄 [执行替换-备用] {{{{start_date}}}} -> '{start_date}'")

                if end_date and "{{end_date}}" in executable_sql:
                    executable_sql = executable_sql.replace("{{end_date}}", f"'{end_date}'")
                    self._logger.info(f"🔄 [执行替换-备用] {{{{end_date}}}} -> '{end_date}'")

            # 如果仍有占位符未替换，使用默认测试日期
            if "{{start_date}}" in executable_sql or "{{end_date}}" in executable_sql:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                yesterday = today - timedelta(days=1)

                default_date = yesterday.strftime('%Y-%m-%d')

                if "{{start_date}}" in executable_sql:
                    executable_sql = executable_sql.replace("{{start_date}}", f"'{default_date}'")
                    self._logger.info(f"🔄 [执行替换-默认] {{{{start_date}}}} -> '{default_date}'")

                if "{{end_date}}" in executable_sql:
                    executable_sql = executable_sql.replace("{{end_date}}", f"'{default_date}'")
                    self._logger.info(f"🔄 [执行替换-默认] {{{{end_date}}}} -> '{default_date}'")

            return executable_sql

        except Exception as e:
            self._logger.error(f"❌ [执行] 占位符替换失败: {e}")
            return sql  # 失败时返回原始SQL


class SQLRefineTool(Tool):
    """
    SQL修正工具 - 简化职责版本

    单一职责：应用Agent提供的SQL修正建议
    不再调用LLM，只执行Agent指定的修正操作
    遵循Agent架构原则：Agent思考决策，工具执行操作
    """

    def __init__(self, container):
        super().__init__()
        self.name = "sql.refine"
        self.description = "应用Agent提供的SQL修正建议"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用SQL修正 - 支持智能修复和Agent修正两种模式

        期望输入：
        - current_sql: 当前的SQL
        - corrected_sql: Agent提供的修正SQL（可选）
        - issues: 要解决的问题列表

        如果没有Agent提供的修正SQL，会基于问题智能生成修正
        """
        try:
            current_sql = input_data.get("current_sql") or input_data.get("sql", "")
            corrected_sql = input_data.get("corrected_sql", "")
            issues = input_data.get("issues", [])

            if not current_sql:
                return {"success": False, "error": "当前SQL语句为空，无法进行修正"}

            # 如果没有Agent提供的修正SQL，尝试智能修复
            if not corrected_sql and issues:
                self._logger.info(f"🤖 [智能修复] 基于{len(issues)}个问题生成修正SQL")
                corrected_sql = self._apply_intelligent_fixes(current_sql, issues)

            if not corrected_sql:
                # 既没有Agent修正也无法智能修复
                return {
                    "success": False,
                    "error": "无法生成修正SQL",
                    "suggestion": "需要Agent提供corrected_sql或提供更具体的问题描述",
                    "current_sql": current_sql,
                    "issues": issues
                }

            # 简单验证修正SQL的基本合法性
            if not self._basic_sql_validation(corrected_sql):
                return {
                    "success": False,
                    "error": "修正SQL不符合基本格式要求",
                    "current_sql": current_sql,
                    "attempted_correction": corrected_sql
                }

            self._logger.info(f"🔧 [SQL修正] 应用修正: {len(corrected_sql)} 字符")
            self._logger.info(f"📋 [修正问题] 解决 {len(issues)} 个问题: {', '.join(issues[:3])}...")

            return {
                "success": True,
                "current_sql": corrected_sql,  # 新的当前SQL
                "sql": corrected_sql,  # 兼容性字段
                "original_sql": current_sql,
                "issues_addressed": issues,
                "refinement_applied": True,
                "message": f"已应用修正，解决{len(issues)}个问题"
            }

        except Exception as e:
            self._logger.error(f"SQL修正工具执行失败: {str(e)}")
            return {"success": False, "error": f"工具执行异常: {str(e)}"}

    def _basic_sql_validation(self, sql: str) -> bool:
        """基本SQL格式验证 - 不深入语义，只检查最基本的格式"""
        if not sql or not isinstance(sql, str):
            return False

        sql_upper = sql.strip().upper()

        # 必须以SELECT开头
        if not sql_upper.startswith('SELECT'):
            return False

        # 必须包含FROM
        if 'FROM' not in sql_upper:
            return False

        # 不能包含危险操作
        dangerous_ops = ['DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER']
        if any(op in sql_upper for op in dangerous_ops):
            return False

        return True

    def _apply_intelligent_fixes(self, sql: str, issues: List[str]) -> str:
        """基于问题列表智能修复SQL"""
        try:
            fixed_sql = sql

            for issue in issues:
                issue_lower = issue.lower()

                # 修复危险关键词误报（UPDATE字段名）
                if "sql包含危险关键词: update" in issue_lower:
                    # 这通常是update_time字段导致的误报，无需修改SQL
                    continue

                # 修复括号不匹配
                elif "括号" in issue_lower and "匹配" in issue_lower:
                    fixed_sql = self._fix_parentheses_mismatch(fixed_sql)

                # 修复DATE_SUB函数格式
                elif "date_sub" in issue_lower and "参数格式" in issue_lower:
                    fixed_sql = self._fix_date_sub_format(fixed_sql)

                # 修复分号问题
                elif "分号" in issue_lower:
                    if not fixed_sql.strip().endswith(';'):
                        fixed_sql = fixed_sql.strip() + ';'

            return fixed_sql

        except Exception as e:
            self._logger.error(f"智能修复失败: {e}")
            return sql

    def _fix_parentheses_mismatch(self, sql: str) -> str:
        """修复括号不匹配问题"""
        try:
            # 简单的括号修复：确保每个左括号都有对应的右括号
            count = 0
            for char in sql:
                if char == '(':
                    count += 1
                elif char == ')':
                    count -= 1

            # 如果缺少右括号，在末尾添加
            if count > 0:
                sql += ')' * count
                self._logger.info(f"🔧 括号修复：添加了{count}个右括号")

            return sql
        except Exception:
            return sql

    def _fix_date_sub_format(self, sql: str) -> str:
        """修复DATE_SUB函数格式"""
        try:
            import re
            # 查找并修复DATE_SUB函数调用
            pattern = r'DATE_SUB\s*\(\s*([^,]+)\s*,\s*INTERVAL\s+(\d+)\s+(\w+)\s*\)'

            def replace_date_sub(match):
                date_expr = match.group(1).strip()
                interval_num = match.group(2)
                interval_unit = match.group(3)
                return f'DATE_SUB({date_expr}, INTERVAL {interval_num} {interval_unit})'

            fixed_sql = re.sub(pattern, replace_date_sub, sql, flags=re.IGNORECASE)

            if fixed_sql != sql:
                self._logger.info("🔧 DATE_SUB格式修复：规范化函数调用格式")

            return fixed_sql
        except Exception:
            return sql

    def _build_refine_prompt(self, sql: str, issues: list, input_data: Dict[str, Any] = None) -> str:
        """构建智能SQL优化提示词"""
        issues_str = "\n".join([f"- {issue}" for issue in issues])

        # 获取用户原始需求和语义类型
        user_prompt = input_data.get("user_prompt", "") if input_data else ""
        semantic_type = input_data.get("semantic_type", "") if input_data else ""

        # 获取schema信息 - 关键修复！
        schema_summary = input_data.get("schema_summary", "") if input_data else ""
        tables = input_data.get("tables", []) if input_data else []
        columns = input_data.get("columns", {}) if input_data else {}

        # 如果没有schema_summary但有tables和columns，构建基本schema描述
        if not schema_summary and (tables or columns):
            schema_parts = []
            for table in tables:
                table_columns = columns.get(table, [])
                if table_columns:
                    schema_parts.append(f"**{table}**: {', '.join(table_columns[:10])}{'...' if len(table_columns) > 10 else ''}")
                else:
                    schema_parts.append(f"**{table}**: (列信息待查询)")
            schema_summary = f"可用数据表:\n" + "\n".join(schema_parts)

        # 检查是否有Agent验证结果
        agent_analysis = input_data.get("agent_analysis") if input_data else None
        corrected_sql = ""
        if agent_analysis and agent_analysis.get("corrected_sql"):
            corrected_sql = f"\n智能修正建议:\n{agent_analysis.get('corrected_sql')}\n"

        return f"""
你是一个专业的SQL优化专家。请修复以下SQL语句中的问题。

用户原始需求: {user_prompt}
占位符类型: {semantic_type}

**数据库结构**:
{schema_summary}

问题SQL:
```sql
{sql}
```

发现的问题:
{issues_str}
{corrected_sql}
请修复上述问题并返回优化后的SQL语句。

要求:
1. **必须使用上述数据库结构中的真实表名和列名**
2. 保持原有查询逻辑不变
3. 修复所有语法错误（特别注意括号匹配）
4. 确保函数调用格式正确
5. 优化查询性能
6. 只返回修复后的完整SQL语句，不要其他内容

特别注意:
- **严格匹配数据库结构中的表名（如ods_complain, ods_refund等）**
- **不要虚构不存在的表名（如return_requests等）**
- 检查所有括号是否正确匹配
- 确保DATE_SUB、DATE_ADD等函数的INTERVAL语法完整
- 验证SQL语句以分号结尾
"""

    async def _call_llm(self, llm_service, prompt: str, user_id: str = "system") -> str:
        """调用LLM优化SQL"""
        try:
            if hasattr(llm_service, 'ask'):
                result = await llm_service.ask(user_id=user_id, prompt=prompt)
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif hasattr(llm_service, 'generate_response'):
                result = await llm_service.generate_response(prompt=prompt, user_id=user_id)
                return result.get("response", "") if isinstance(result, dict) else str(result)
            elif callable(llm_service):
                return await llm_service(prompt)
            else:
                raise ValueError("Unsupported LLM service interface")
        except Exception as e:
            self._logger.error(f"LLM调用失败: {str(e)}")
            return ""


class SQLPolicyTool(Tool):
    """SQL策略检查工具"""

    def __init__(self, container):
        super().__init__()
        self.name = "sql.policy"
        self.description = "执行SQL策略检查并添加LIMIT"
        self.container = container
        self._logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行SQL策略检查"""
        try:
            sql = input_data.get("current_sql") or input_data.get("sql", "")
            if not sql:
                return {"success": False, "error": "SQL语句为空"}

            # 获取用户信息
            user_id = input_data.get("user_id") or auth_manager.get_current_user_id() or "system"
            data_source_config = input_data.get("data_source", {})
            data_source_id = data_source_config.get("id")

            # 确定用户是否为超级用户
            is_superuser = False
            if user_id != "system":
                auth_context = auth_manager.get_context()
                is_superuser = auth_context.is_superuser if auth_context else False

            # 使用DataSourceSecurityService进行SQL安全策略检查
            security_result = data_source_security_service.apply_sql_security_policy(
                sql=sql,
                user_id=user_id,
                data_source_id=data_source_id,
                is_superuser=is_superuser
            )

            if not security_result.get("allowed"):
                self._logger.warning(f"SQL策略检查失败: {security_result}")
                return {
                    "success": False,
                    "error": f"SQL安全策略检查失败: {'; '.join(security_result.get('issues', []))}",
                    "issues": security_result.get("issues", [])
                }

            # 使用经过安全策略处理的SQL
            processed_sql = security_result.get("modified_sql", sql)

            return {
                "success": True,
                "sql": processed_sql,
                "original_sql": sql,
                "policies_applied": security_result.get("modifications", []),
                "warnings": security_result.get("warnings", []),
                "issues": security_result.get("issues", [])
            }

        except Exception as e:
            self._logger.error(f"SQL策略检查失败: {str(e)}")
            return {"success": False, "error": str(e)}
