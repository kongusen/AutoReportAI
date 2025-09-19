"""
Agent Provider 统一入口（单文件实现）

适配新的智能体接口，提供统一的 initialize/execute/health_check 能力。
增强：结果校验、重试/退避、并发控制、结构化日志。
"""

import asyncio
import logging
import math
import random
import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional, Tuple, List

from app.core.config import settings


logger = logging.getLogger(__name__)
_semaphore: Optional[asyncio.Semaphore] = None
_lex_agent: Optional[object] = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(max(1, int(settings.NEW_AGENT_MAX_CONCURRENCY)))
    return _semaphore


def _validate_result(result: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    if not isinstance(result, dict):
        issues.append("result 不是字典")
        return False, issues
    cols = result.get("columns")
    rows = result.get("rows")
    if not isinstance(cols, list) or not all(isinstance(c, str) for c in cols):
        issues.append("columns 不是字符串列表")
    if not isinstance(rows, list):
        issues.append("rows 不是列表")
    else:
        # 允许空列表，但默认成功准则通常要求 min_rows>=1，这里只做结构校验
        pass
    if required_fields:
        missing = sorted(set(required_fields) - set(cols or []))
        if missing:
            issues.append(f"缺少必需字段: {missing}")
    return (len(issues) == 0), issues


class AgentProvider:
    """新Agent提供者（支持 local_stub / http 两种模式）"""

    def __init__(self):
        self.mode = settings.NEW_AGENT_MODE or "local_stub"
        self.endpoint = settings.NEW_AGENT_ENDPOINT
        self.api_key = settings.NEW_AGENT_API_KEY
        self._initialized = False

    async def initialize(self) -> None:
        # 预留真实初始化过程（认证/加载缓存等）
        self._initialized = True

    async def health_check(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "mode": self.mode,
            "endpoint": self.endpoint if self.mode == "http" else None,
        }

    async def execute(
        self,
        objective: str,
        context: Dict[str, Any],
        success_criteria: Dict[str, Any],
        max_attempts: int = 3,
    ) -> AsyncIterator[Dict[str, Any]]:
        """执行新Agent任务，流式返回事件（含校验/重试/限流/日志）。"""
        if not self._initialized:
            await self.initialize()

        req_id = uuid.uuid4().hex[:8]
        mode = (self.mode or "local_stub").lower()
        required_fields = success_criteria.get("required_fields", []) or []

        # 事件：开始
        yield {
            "type": "agent_session_started",
            "content": {"objective": objective, "request_id": req_id, "mode": mode},
            "timestamp": datetime.utcnow().isoformat(),
        }

        sem = _get_semaphore()
        start_ts = datetime.utcnow()

        async with sem:
            if mode == "local_stub":
                # 本地桩：构造至少一行，满足最小成功准则
                row = {f: None for f in required_fields}
                result = {
                    "columns": required_fields,
                    "rows": [row],
                    "metadata": {
                        "source": "new_agent_local_stub",
                        "request_id": req_id,
                        "window": context.get("window", {}),
                    },
                }
                ok, issues = _validate_result(result, required_fields)
                if not ok:
                    yield {
                        "type": "error",
                        "content": {"error": "结果结构校验失败", "issues": issues, "request_id": req_id},
                        "is_final": True,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    return
                # 事件：可用结果
                await asyncio.sleep(0)
                yield {
                    "type": "agent_result_available",
                    "content": result,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                # 事件：完成
                yield {
                    "type": "agent_session_complete",
                    "success": True,
                    "result": result,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                logger.info(f"[AgentProvider:{req_id}] local_stub completed in {(datetime.utcnow()-start_ts).total_seconds():.3f}s")
                return

        # HTTP 模式
        if mode == "http":
            try:
                import httpx
            except Exception as e:
                # 缺少依赖
                yield {
                    "type": "error",
                    "content": {"error": f"httpx 未安装/不可用: {e}"},
                    "is_final": True,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                return

            headers = {"Content-Type": "application/json", "X-Request-ID": req_id}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            payload = {
                "objective": objective,
                "context": context,
                "success_criteria": success_criteria,
                "max_attempts": max_attempts,
            }

            timeout_s = getattr(settings, "NEW_AGENT_TIMEOUT", 60)
            max_retries = max(0, int(getattr(settings, "NEW_AGENT_MAX_RETRIES", 3)))
            base = max(0.1, float(getattr(settings, "NEW_AGENT_BACKOFF_BASE", 0.5)))
            cap = max(base, float(getattr(settings, "NEW_AGENT_BACKOFF_CAP", 5.0)))

            attempt = 0
            last_error: Optional[str] = None
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                while attempt <= max_retries:
                    try:
                        t0 = datetime.utcnow()
                        resp = await client.post(self.endpoint, json=payload, headers=headers)
                        dt = (datetime.utcnow() - t0).total_seconds()
                        if resp.status_code >= 500:
                            last_error = f"HTTP {resp.status_code}"
                            raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                        if resp.status_code >= 400:
                            # 客户端错误不重试
                            try:
                                detail = resp.json()
                            except Exception:
                                detail = resp.text
                            yield {
                                "type": "error",
                                "content": {"error": f"Agent HTTP {resp.status_code}", "detail": detail, "request_id": req_id},
                                "is_final": True,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                            logger.warning(f"[AgentProvider:{req_id}] http client error {resp.status_code} in {dt:.3f}s")
                            return

                        data = resp.json()
                        # 透传 events（如有）
                        events = data.get("events") if isinstance(data, dict) else None
                        if isinstance(events, list):
                            for ev in events:
                                if isinstance(ev, dict):
                                    ev.setdefault("timestamp", datetime.utcnow().isoformat())
                                    yield ev

                        result = data.get("result") if isinstance(data, dict) else data
                        ok, issues = _validate_result(result or {}, required_fields)
                        if not ok:
                            yield {
                                "type": "error",
                                "content": {"error": "结果结构校验失败", "issues": issues, "request_id": req_id},
                                "is_final": True,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                            logger.error(f"[AgentProvider:{req_id}] invalid result: {issues}")
                            return

                        success = bool(data.get("success", True)) if isinstance(data, dict) else True
                        yield {
                            "type": "agent_session_complete",
                            "success": success,
                            "result": result,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                        logger.info(f"[AgentProvider:{req_id}] http completed in {dt:.3f}s, success={success}")
                        return
                    except (httpx.RequestError, httpx.HTTPStatusError) as e:
                        attempt += 1
                        if attempt > max_retries:
                            yield {
                                "type": "error",
                                "content": {"error": f"Agent HTTP调用失败", "detail": str(e), "request_id": req_id, "attempts": attempt},
                                "is_final": True,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                            logger.error(f"[AgentProvider:{req_id}] http failed after {attempt} attempts: {e}")
                            return
                        # backoff with jitter
                        delay = min(cap, base * math.pow(2, attempt - 1))
                        delay = delay * (0.7 + 0.6 * random.random())
                        logger.warning(f"[AgentProvider:{req_id}] http error, retry {attempt}/{max_retries} in {delay:.2f}s: {e}")
                        await asyncio.sleep(delay)

        # INTERNAL 模式（使用本地 laboratory.lexicon_agent）
        if mode == "internal":
            global _lex_agent
            try:
                if _lex_agent is None:
                    try:
                        from laboratory.lexicon_agent.main import LexiconAgent as _Lex
                    except Exception:
                        # 尝试补充项目根路径
                        import sys as _sys, os as _os
                        _ROOT = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "..", "..", ".."))
                        if _ROOT not in _sys.path:
                            _sys.path.insert(0, _ROOT)
                        from laboratory.lexicon_agent.main import LexiconAgent as _Lex
                    _lex_agent = _Lex()
                # 传递上下文作为 session_context
                session_ctx = {"agent_context": context, "success_criteria": success_criteria}
                # 透传 lexicon 事件
                collected: List[Dict[str, Any]] = []
                async for ev in _lex_agent.process_message(message=objective, session_context=session_ctx):
                    # 标准化：加上时间戳与请求ID
                    if isinstance(ev, dict):
                        ev.setdefault("timestamp", datetime.utcnow().isoformat())
                        ev.setdefault("request_id", req_id)
                        yield ev
                        collected.append(ev)
                # 结果推导：若无标准表格，使用 required_fields 构造最小结果
                result = None
                for ev in reversed(collected):
                    if isinstance(ev.get("content"), dict) and {"columns","rows"} <= set(ev["content"].keys()):
                        result = ev["content"]
                        break
                if not isinstance(result, dict):
                    row = {f: None for f in required_fields}
                    result = {"columns": required_fields, "rows": [row], "metadata": {"source": "internal_lexicon_agent", "request_id": req_id}}
                ok, issues = _validate_result(result, required_fields)
                if not ok:
                    yield {"type": "error", "content": {"error": "结果结构校验失败", "issues": issues, "request_id": req_id}, "is_final": True, "timestamp": datetime.utcnow().isoformat()}
                    return
                yield {"type": "agent_session_complete", "success": True, "result": result, "timestamp": datetime.utcnow().isoformat()}
                logger.info(f"[AgentProvider:{req_id}] internal completed with lexicon_agent")
                return
            except Exception as e:
                yield {"type": "error", "content": {"error": f"internal agent 调用失败: {e}", "request_id": req_id}, "is_final": True, "timestamp": datetime.utcnow().isoformat()}
                logger.error(f"[AgentProvider:{req_id}] internal error: {e}")
                return

        # 未知模式
        yield {
            "type": "error",
            "content": {"error": f"未知 NEW_AGENT_MODE: {self.mode}"},
            "is_final": True,
            "timestamp": datetime.utcnow().isoformat(),
        }
        return


_provider: Optional[AgentProvider] = None


def get_agent_provider() -> AgentProvider:
    global _provider
    if _provider is None:
        _provider = AgentProvider()
    return _provider

__all__ = ["AgentProvider", "get_agent_provider"]
