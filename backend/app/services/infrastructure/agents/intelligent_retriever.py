"""
智能检索器 - LLM 增强版

基于 LLM 的智能 Schema 检索
使用大语言模型进行语义理解和表名匹配
"""

from __future__ import annotations

import logging
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """检索配置"""
    # LLM 配置
    use_llm_judgment: bool = True
    llm_model: str = "gpt-4o-mini"
    
    # 缓存配置
    enable_caching: bool = True
    cache_ttl: int = 3600  # 1小时
    
    # 评分权重
    llm_weight: float = 0.8
    keyword_weight: float = 0.2


class IntelligentSchemaRetriever:
    """
    智能 Schema 检索器

    使用 LLM 进行语义理解和表名匹配
    不再依赖算法，完全基于大语言模型的判断能力
    """

    def __init__(
        self,
        schema_cache: Dict[str, Dict[str, Any]],
        config: Optional[RetrievalConfig] = None,
        container: Optional[Any] = None
    ):
        """
        Args:
            schema_cache: Schema 缓存字典
            config: 检索配置
            container: 服务容器，用于获取LLM服务
        """
        self.schema_cache = schema_cache
        self.config = config or RetrievalConfig()
        self.container = container

        # 缓存
        self._retrieval_cache: Dict[str, List[Tuple[str, float]]] = {}

        # 初始化
        self._initialized = False

        logger.info("🔍 [IntelligentSchemaRetriever] 初始化完成")
        logger.info(f"   LLM判断: {'启用' if self.config.use_llm_judgment else '禁用'}")
        logger.info(f"   模型: {self.config.llm_model}")

    async def initialize(self):
        """初始化检索器"""
        if self._initialized:
            return

        logger.info("🔧 [IntelligentSchemaRetriever] 初始化LLM检索器")
        
        # 验证容器和LLM服务
        if self.container is None:
            logger.error("❌ [IntelligentSchemaRetriever] 容器未提供，无法使用LLM判断")
            raise RuntimeError("容器未提供，无法使用LLM判断")
        
        # 检查LLM服务是否可用
        try:
            llm_service = self.container.llm
            if llm_service is None:
                logger.error("❌ [IntelligentSchemaRetriever] LLM服务不可用")
                raise RuntimeError("LLM服务不可用")
            
            logger.info("✅ [IntelligentSchemaRetriever] LLM服务验证成功")
        except Exception as e:
            logger.error(f"❌ [IntelligentSchemaRetriever] LLM服务验证失败: {e}")
            raise RuntimeError(f"LLM服务验证失败: {e}")

        self._initialized = True
        logger.info("✅ [IntelligentSchemaRetriever] LLM检索器初始化完成")

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        stage: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """
        使用LLM进行智能检索

        Args:
            query: 查询文本
            top_k: 返回数量
            stage: 执行阶段

        Returns:
            List[Tuple[table_name, score]]: 表名和相似度评分列表
        """
        if not self._initialized:
            await self.initialize()

        # 检查缓存
        cache_key = self._get_cache_key(query, top_k, stage)
        if self.config.enable_caching and cache_key in self._retrieval_cache:
            logger.debug(f"✅ 使用检索缓存: {query[:50]}...")
            return self._retrieval_cache[cache_key]

        # 使用LLM进行智能检索
        results = await self._retrieve_with_llm(query, top_k, stage)

        # 更新缓存
        if self.config.enable_caching:
            self._retrieval_cache[cache_key] = results
            # 限制缓存大小
            if len(self._retrieval_cache) > 100:
                # 删除最旧的缓存
                oldest_key = next(iter(self._retrieval_cache))
                del self._retrieval_cache[oldest_key]

        return results

    async def _retrieve_with_llm(
        self,
        query: str,
        top_k: int,
        stage: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """使用LLM进行智能表名匹配"""
        try:
            # 获取LLM服务
            llm_service = self.container.llm
            if llm_service is None:
                raise RuntimeError("LLM服务不可用")

            # 构建表名列表
            table_names = list(self.schema_cache.keys())
            if not table_names:
                logger.warning("⚠️ 没有可用的表名")
                return []

            # 构建LLM提示词
            prompt = self._build_llm_prompt(query, table_names, top_k, stage)
            
            logger.info(f"🤖 [LLM检索] 查询: {query[:100]}...")
            logger.info(f"🤖 [LLM检索] 候选表数量: {len(table_names)}")

            # 🔥 调用LLM - 使用当前用户ID
            # 从container中获取当前用户ID，如果没有则使用默认值
            current_user_id = getattr(self.container, '_current_user_id', None)
            if not current_user_id:
                # 尝试从context variable获取
                try:
                    from app.services.infrastructure.agents.llm_adapter import _CURRENT_USER_ID
                    current_user_id = _CURRENT_USER_ID.get()
                except:
                    current_user_id = None
            
            if not current_user_id:
                raise RuntimeError("无法获取当前用户ID，请确保在请求中提供有效的用户ID")
            
            response = await llm_service.ask(
                user_id=current_user_id,
                prompt=prompt,
                response_format="json"
            )

            # 解析LLM响应
            results = self._parse_llm_response(response, table_names)
            
            logger.info(f"✅ [LLM检索] 返回 {len(results)} 个表")
            return results

        except Exception as e:
            logger.error(f"❌ [LLM检索] 失败: {e}")
            # 不进行回退，直接抛出异常让主流程处理
            raise RuntimeError(f"LLM检索失败: {e}")

    def _build_llm_prompt(
        self,
        query: str,
        table_names: List[str],
        top_k: int,
        stage: Optional[str] = None
    ) -> str:
        """构建LLM提示词"""
        stage_context = f"当前执行阶段: {stage}" if stage else "通用查询"
        
        prompt = f"""你是一个数据库专家，需要根据用户查询找到最相关的数据库表。

{stage_context}

用户查询: {query}

可用的数据库表:
{', '.join(table_names)}

请分析用户查询的语义，找出最相关的 {top_k} 个表，并按相关性从高到低排序。

返回JSON格式:
{{
  "reasoning": "你的分析过程",
  "tables": [
    {{"name": "表名1", "score": 0.95, "reason": "为什么这个表相关"}},
    {{"name": "表名2", "score": 0.85, "reason": "为什么这个表相关"}}
  ]
}}

评分标准:
- 1.0: 完全匹配
- 0.8-0.9: 高度相关
- 0.6-0.7: 中度相关
- 0.4-0.5: 低度相关
- 0.0-0.3: 不相关

请确保返回的表名在可用表列表中，评分在0.0-1.0之间。"""

        return prompt

    def _parse_llm_response(
        self,
        response: str,
        available_tables: List[str]
    ) -> List[Tuple[str, float]]:
        """解析LLM响应"""
        try:
            # 尝试解析JSON
            if isinstance(response, str):
                # 提取JSON部分
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx != -1 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    data = json.loads(json_str)
                else:
                    raise ValueError("响应中未找到有效的JSON")
            else:
                data = response

            # 🔥 增强响应格式验证：支持多种格式
            if not isinstance(data, dict):
                raise ValueError("响应不是有效的字典格式")
            
            # 🔥 处理嵌套JSON格式
            if "response" in data and isinstance(data["response"], str):
                # 尝试解析嵌套的JSON字符串
                try:
                    nested_data = json.loads(data["response"])
                    data = nested_data
                except json.JSONDecodeError:
                    pass
            
            # 支持多种响应格式
            tables = None
            if "tables" in data:
                tables = data["tables"]
            elif "matched_tables" in data:
                # 兼容旧格式
                tables = data["matched_tables"]
                if isinstance(tables, list) and all(isinstance(t, str) for t in tables):
                    # 转换为标准格式
                    tables = [{"name": t, "score": 0.8} for t in tables]
            elif "results" in data:
                tables = data["results"]
            
            if tables is None:
                raise ValueError("响应中未找到tables、matched_tables或results字段")

            if not isinstance(tables, list):
                raise ValueError("tables字段不是列表")

            # 🔥 增强表信息解析：支持多种格式
            results = []
            for table_info in tables:
                if isinstance(table_info, str):
                    # 简单字符串格式
                    table_name = table_info
                    score = 0.8
                elif isinstance(table_info, dict):
                    # 标准格式
                    table_name = table_info.get("name", "")
                    score = table_info.get("score", 0.0)
                else:
                    continue
                
                # 验证表名是否在可用列表中
                if table_name not in available_tables:
                    logger.warning(f"⚠️ LLM返回了不存在的表名: {table_name}")
                    continue
                
                # 验证评分范围
                if not isinstance(score, (int, float)) or score < 0.0 or score > 1.0:
                    logger.warning(f"⚠️ LLM返回了无效评分: {score}")
                    score = 0.5  # 默认评分
                
                results.append((table_name, float(score)))

            # 按评分排序
            results.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"📊 [LLM检索] 解析结果: {len(results)} 个表")
            for table_name, score in results:
                logger.debug(f"   {table_name}: {score:.2f}")
            
            return results

        except Exception as e:
            logger.error(f"❌ [LLM检索] 解析响应失败: {e}")
            # 🔥 安全地记录响应内容
            try:
                if isinstance(response, str):
                    logger.error(f"   原始响应: {response[:200]}...")
                else:
                    logger.error(f"   原始响应类型: {type(response)}, 内容: {str(response)[:200]}...")
            except Exception as log_e:
                logger.error(f"   无法记录响应内容: {log_e}")
            raise RuntimeError(f"LLM响应解析失败: {e}")

    def _get_cache_key(self, query: str, top_k: int, stage: Optional[str]) -> str:
        """生成缓存键"""
        key_data = f"{query}:{top_k}:{stage or 'default'}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def clear_cache(self):
        """清空缓存"""
        self._retrieval_cache.clear()
        logger.info("🧹 [IntelligentSchemaRetriever] 清空检索缓存")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "cached_queries": len(self._retrieval_cache),
            "cache_size": f"{len(self._retrieval_cache)} queries"
        }


# 工厂函数
def create_intelligent_retriever(
    schema_cache: Dict[str, Dict[str, Any]],
    config: Optional[RetrievalConfig] = None,
    container: Optional[Any] = None
) -> IntelligentSchemaRetriever:
    """创建智能检索器"""
    return IntelligentSchemaRetriever(schema_cache, config, container)


def create_llm_retriever(
    schema_cache: Dict[str, Dict[str, Any]],
    container: Any,
    llm_model: str = "gpt-4o-mini"
) -> IntelligentSchemaRetriever:
    """创建启用LLM的检索器"""
    config = RetrievalConfig(
        use_llm_judgment=True,
        llm_model=llm_model,
        llm_weight=0.8,
        keyword_weight=0.2
    )
    return IntelligentSchemaRetriever(schema_cache, config, container)