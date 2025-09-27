"""
Dependency injection container for the agent system integrated with real LLM services
and real data source/DB session in the current application.
"""

import logging
from typing import Optional, Any, Dict


class DataSourceAdapter:
    """Adapter exposing a simple `run_query(connection_config, sql, limit)` API for agents tools.

    Internally uses connector factory create_connector_from_config to execute queries.
    """

    async def run_query(self, connection_config: Dict[str, Any], sql: str, limit: int = 1000) -> Dict[str, Any]:
        from app.services.data.connectors import create_connector_from_config
        logger = logging.getLogger(__name__)

        if not connection_config:
            return {"success": False, "error": "missing_connection_config"}

        # Normalize
        cfg = dict(connection_config)
        src_type = cfg.get("source_type") or cfg.get("type") or cfg.get("database_type")
        name = cfg.get("name") or cfg.get("database") or "data_source"
        if not src_type:
            return {"success": False, "error": "missing_source_type"}

        # Normalize source type
        type_map = {
            "mysql": "sql",
            "postgres": "sql",
            "postgresql": "sql",
            "mariadb": "sql",
        }
        if src_type:
            src_type_norm = type_map.get(src_type.lower(), src_type)
            cfg["source_type"] = src_type_norm
        else:
            src_type_norm = src_type

        # Create connector and execute
        try:
            connector = create_connector_from_config(src_type_norm, name, cfg)
            async with connector:
                q = sql
                # 排除不支持LIMIT的语句（特别是Doris的SHOW命令）
                sql_upper = (sql or "").upper().strip()
                skip_limit_patterns = ["SHOW FULL COLUMNS", "SHOW COLUMNS", "DESC ", "DESCRIBE "]
                should_skip_limit = any(sql_upper.startswith(pattern) for pattern in skip_limit_patterns)

                if limit and "LIMIT" not in sql_upper and not should_skip_limit:
                    q = f"{sql.strip()} LIMIT {limit}"
                    logger.debug(f"添加LIMIT到查询: {sql.strip()[:50]}...")
                elif should_skip_limit:
                    logger.debug(f"跳过LIMIT (Doris兼容): {sql.strip()[:50]}...")
                result = await connector.execute_query(q, cfg)

                # 兼容不同数据库的结果格式
                rows, cols = [], []

                try:
                    if hasattr(result, 'get') and callable(result.get):
                        # 标准字典格式 (MySQL等)
                        rows = result.get("rows") or result.get("data") or []
                        cols = result.get("columns") or result.get("column_names") or []
                        logger.debug(f"使用字典格式解析: {len(rows)}行")
                    elif hasattr(result, 'rows'):
                        # Doris等特殊对象格式 - 直接访问属性
                        rows = getattr(result, 'rows', [])
                        cols = getattr(result, 'columns', []) or getattr(result, 'column_names', [])
                        logger.debug(f"使用对象属性解析: {len(rows)}行")
                    elif isinstance(result, (list, tuple)):
                        # 直接返回行数据的格式
                        rows = result
                        cols = []
                        logger.debug(f"使用列表格式解析: {len(rows)}行")
                    else:
                        # 尝试所有可能的属性访问
                        for attr in ['rows', 'data']:
                            if hasattr(result, attr):
                                rows = getattr(result, attr, [])
                                break
                        for attr in ['columns', 'column_names', 'fields']:
                            if hasattr(result, attr):
                                cols = getattr(result, attr, [])
                                break
                        logger.debug(f"使用属性扫描解析: {len(rows)}行, {len(cols)}列")

                except Exception as parse_error:
                    logger.warning(f"结果解析失败: {parse_error}, 使用空结果")
                    rows, cols = [], []

                # 最终DataFrame安全检查
                import pandas as pd
                if isinstance(rows, pd.DataFrame):
                    if not rows.empty:
                        rows = rows.to_dict('records')
                        logger.debug(f"Container最终转换DataFrame为字典列表: {len(rows)}行")
                    else:
                        rows = []

                return {"success": True, "rows": rows, "columns": cols}
        except Exception as e:
            logger.error(f"run_query failed: {e}")
            return {"success": False, "error": str(e)}


class RealLLMServiceAdapter:
    """Adapter for real LLM service to match agent system interface"""

    def __init__(self):
        self._llm_manager = None

    async def _get_llm_manager(self):
        """Get the real LLM manager"""
        if self._llm_manager is None:
            from app.services.infrastructure.llm import get_llm_manager
            self._llm_manager = await get_llm_manager()
        return self._llm_manager

    async def ask(self, user_id: str, prompt: str, response_format=None, llm_policy: Dict[str, Any] = None):
        """Ask real LLM service with JSON parsing fallback and model selection policy"""
        import time
        import logging

        logger = logging.getLogger(__name__)
        start_time = time.time()

        try:
            from app.services.infrastructure.llm import ask_agent, select_best_model_for_user, get_model_executor
            import json
            import re

            policy = llm_policy or {}

            # 默认统一启用结构化JSON输出
            if response_format is None:
                response_format = {"type": "json_object"}
            stage = policy.get("stage", "general")
            step = policy.get("step", "unknown")  # 工具名称，如 sql.draft
            complexity = policy.get("complexity", "medium")
            output_kind = policy.get("output_kind", "text")
            preferred_model_type = policy.get("preferred_model_type", "default")
            constraints = {"json": bool(response_format and response_format.get("type") == "json_object")}

            # 🔍 开始模型选择日志
            logger.info(f"🤖 [ModelSelection] user_id={user_id}, stage={stage}, step={step}, "
                       f"complexity={complexity}, output_kind={output_kind}, "
                       f"preferred_type={preferred_model_type}, json_required={constraints['json']}")

            # 1) Model selection via DB
            selected_model = None
            model_selection_method = "fallback"

            try:
                # 修正模型选择调用，只传递支持的参数
                sel = await select_best_model_for_user(
                    user_id=user_id,
                    task_type=stage,
                    complexity=complexity,
                    constraints=constraints,
                    agent_id=policy.get("agent_id")
                )

                model_id = sel.get("model_id")
                if model_id and sel.get("model"):  # 使用 'model' 而不是 'model_name'
                    selected_model = {
                        "model_id": model_id,
                        "model_name": sel.get("model"),
                        "server_name": sel.get("server_name", "unknown"),
                        "provider_name": sel.get("provider", "unknown"),
                        "model_type": sel.get("model_type", "unknown"),
                        "confidence": sel.get("confidence", 0.0),
                        "reasoning": sel.get("reasoning", ""),
                        "fallback_used": sel.get("fallback_used", False)
                    }
                    model_selection_method = "db_selection"

                    # 🎯 记录详细的模型选择结果
                    selection_context = sel.get("selection_context", {})
                    logger.info(f"✅ [ModelSelected] server={selected_model['server_name']}, "
                               f"model={selected_model['model_name']}, type={selected_model['model_type']}, "
                               f"confidence={selected_model['confidence']:.2f}, "
                               f"fallback={selected_model['fallback_used']}, "
                               f"context={selection_context}")

                    # 如果使用了回退，记录警告
                    if selected_model['fallback_used']:
                        logger.warning(f"⚠️ [ModelFallback] 使用了回退模型选择，原因: {selected_model['reasoning']}")
                else:
                    logger.warning(f"⚠️ [ModelSelection] 模型选择未返回有效结果: {sel}")

            except Exception as e:
                logger.warning(f"⚠️ [ModelSelection] DB selection failed: {e}")
                selected_model = None

            # 2) Execute with selected model or fallback
            execution_start = time.time()

            if selected_model and selected_model.get("model_id"):
                # Execute with specific model
                execu = get_model_executor()
                result = await execu.execute_with_specific_model(
                    model_id=selected_model["model_id"],
                    prompt=prompt,
                    response_format=response_format
                )
                text = result.get("result", "") if isinstance(result, dict) else str(result)

                execution_time = int((time.time() - execution_start) * 1000)
                logger.info(f"🚀 [ModelExecution] {selected_model['model_name']} executed in {execution_time}ms")

            else:
                # Fallback: basic ask_agent without explicit model
                logger.info(f"🔄 [ModelExecution] Using fallback ask_agent for stage={stage}")

                text = await ask_agent(
                    user_id=user_id,
                    question=prompt,
                    agent_type=stage,
                    task_type=stage,
                    complexity=complexity
                )

                execution_time = int((time.time() - execution_start) * 1000)
                selected_model = {"model_name": "fallback_agent", "model_type": "fallback"}
                logger.info(f"🔄 [ModelExecution] Fallback agent executed in {execution_time}ms")

            # 3) Handle JSON response format requirement
            json_processing_time = 0
            if response_format and response_format.get("type") == "json_object":
                json_start = time.time()
                processed_response = self._ensure_json_response(text, user_id)
                json_processing_time = int((time.time() - json_start) * 1000)

                logger.info(f"📋 [JSONProcessing] JSON validation/fixing completed in {json_processing_time}ms")
                response_text = processed_response
            else:
                response_text = text

            # 🎊 总体执行统计
            total_time = int((time.time() - start_time) * 1000)
            response_length = len(str(response_text))

            logger.info(f"🏁 [ExecutionComplete] stage={stage}, step={step}, "
                       f"model={selected_model['model_name'] if selected_model else 'unknown'}, "
                       f"total_time={total_time}ms, response_length={response_length}chars")

            return {"response": response_text}

        except Exception as e:
            total_time = int((time.time() - start_time) * 1000)
            logger.error(f"❌ [ExecutionError] stage={stage}, step={step}, "
                        f"total_time={total_time}ms, error={str(e)}")

            # Fallback response
            return {
                "response": '{"success": true, "result": "SELECT COUNT(*) as count FROM users", "reasoning": "Fallback query due to error", "quality_score": 0.5}'
            }

    def _ensure_json_response(self, response: str, user_id: str) -> str:
        """Ensure response is valid JSON, with fallback mechanisms"""
        import json
        import re
        import logging

        logger = logging.getLogger(__name__)
        response_preview = response[:100] + "..." if len(response) > 100 else response

        logger.info(f"🔍 [JSONValidation] Validating JSON for user={user_id}, response_length={len(response)}, preview={response_preview}")

        # Step 1: Try to parse as JSON directly
        try:
            json.loads(response)
            logger.info(f"✅ [JSONValidation] Response is already valid JSON for user={user_id}")
            return response
        except (json.JSONDecodeError, TypeError) as e:
            logger.info(f"🔧 [JSONValidation] Direct JSON parsing failed: {str(e)[:50]}...")

        # Step 2: Try to extract JSON substring
        try:
            # Look for JSON-like patterns in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response)
            if json_match:
                json_candidate = json_match.group()
                json.loads(json_candidate)  # Validate
                logger.info(f"✅ [JSONValidation] Extracted valid JSON substring for user={user_id}, length={len(json_candidate)}")
                return json_candidate
        except (json.JSONDecodeError, AttributeError) as e:
            logger.info(f"🔧 [JSONValidation] JSON extraction failed: {str(e)[:50]}...")

        # Step 3: Check if it's SQL and create JSON wrapper
        if self._looks_like_sql(response):
            logger.info(f"🔄 [JSONValidation] Converting SQL to JSON wrapper for user={user_id}")
            sql_response = {
                "success": True,
                "result": response.strip(),
                "quality_score": 0.7,
                "reasoning": "SQL generated but wrapped due to format requirement",
                "fallback_used": "sql_to_json_wrapper"
            }
            wrapped_json = json.dumps(sql_response, ensure_ascii=False)
            logger.info(f"✅ [JSONValidation] SQL wrapped in JSON successfully, length={len(wrapped_json)}")
            return wrapped_json

        # Step 4: Ultimate fallback - create error JSON
        logger.warning(f"⚠️ [JSONValidation] Could not convert response to JSON for user={user_id}, using error fallback")
        error_response = {
            "success": False,
            "error": "response_format_invalid",
            "original_response": response[:200] + "..." if len(response) > 200 else response,
            "fallback_used": "error_json_wrapper"
        }
        error_json = json.dumps(error_response, ensure_ascii=False)
        logger.warning(f"🚨 [JSONValidation] Error JSON fallback created, length={len(error_json)}")
        return error_json

    def _looks_like_sql(self, text: str) -> bool:
        """Check if text looks like SQL"""
        if not text:
            return False

        text_upper = text.upper().strip()
        sql_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH', 'CREATE']
        return any(text_upper.startswith(keyword) for keyword in sql_keywords)


class Container:
    """
    Dependency injection container for the agent system integrated with real LLM services.
    """

    def __init__(self):
        self._llm_service = None
        self._data_source_service = None
        self._user_ds_service = None

    @property
    def llm(self):
        """Get real LLM service"""
        if self._llm_service is None:
            self._llm_service = RealLLMServiceAdapter()
        return self._llm_service

    @property
    def data_source(self):
        """Get data source adapter for agent tools"""
        if self._data_source_service is None:
            self._data_source_service = DataSourceAdapter()
        return self._data_source_service

    @property
    def user_data_source_service(self):
        """Adapter that returns user-specific data source connection config for context builder."""
        if self._user_ds_service is None:
            self._user_ds_service = _UserDataSourceServiceAdapter()
        return self._user_ds_service

    def get_db(self):
        """Yield DB session (for TemplateContextBuilder)"""
        from app.db.session import get_db
        return get_db()


class _UserDataSourceServiceAdapter:
    """Provide get_user_data_source(user_id, data_source_id) -> object with connection_config/source_type/name.

    This adapter reads the DataSource ORM and maps it to a minimal config that
    DataSourceContextBuilder can use via Container.data_source.run_query.
    """

    async def get_user_data_source(self, user_id: str, data_source_id: str):
        from app.db.session import get_db_session
        from app import crud
        from app.models.data_source import DataSourceType
        from app.core.data_source_utils import DataSourcePasswordManager

        with get_db_session() as db:
            ds = crud.data_source.get_user_data_source(db, data_source_id=data_source_id, user_id=user_id)
            if not ds:
                raise ValueError("Data source not found")

            # Build connection_config for connector factory
            cfg: Dict[str, Any] = {"name": ds.name}
            if ds.source_type == DataSourceType.doris:
                cfg.update({
                    "source_type": "doris",
                    "fe_hosts": ds.doris_fe_hosts or ["localhost"],
                    "be_hosts": ds.doris_be_hosts or ["localhost"],
                    "http_port": ds.doris_http_port or 8030,
                    "query_port": ds.doris_query_port or 9030,
                    "database": ds.doris_database or "default",
                    "username": ds.doris_username or "root",
                    "password": DataSourcePasswordManager.get_password(ds.doris_password) if ds.doris_password else "",
                    "timeout": 30,
                })
            elif ds.source_type == DataSourceType.sql:
                from app.core.security_utils import decrypt_data
                conn_str = ds.connection_string
                try:
                    if conn_str:
                        conn_str = decrypt_data(conn_str)
                except Exception:
                    # 若解密失败，保留原值以便报错信息清晰
                    pass
                cfg.update({
                    "source_type": "sql",
                    "connection_string": conn_str,
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_pre_ping": True,
                })
            elif ds.source_type == DataSourceType.api:
                cfg.update({
                    "source_type": "api",
                    "api_url": ds.api_url,
                    "method": ds.api_method or "GET",
                    "headers": ds.api_headers,
                    "body": ds.api_body,
                })
            elif ds.source_type == DataSourceType.csv:
                cfg.update({
                    "source_type": "csv",
                    "file_path": getattr(ds, "file_path", None),
                })
            else:
                cfg.update({"source_type": str(ds.source_type)})

            # Return minimal object expected by DataSourceContextBuilder
            class _DS:
                def __init__(self, name, source_type, connection_config):
                    self.name = name
                    self.source_type = str(source_type)
                    self.connection_config = connection_config

            return _DS(ds.name, ds.source_type, cfg)


# 全局容器实例
container = Container()
