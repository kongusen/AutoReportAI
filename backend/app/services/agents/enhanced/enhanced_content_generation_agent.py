"""
增强版内容生成Agent

在原有ContentGenerationAgent基础上增加以下功能：
- 智能上下文管理
- 多轮对话支持
- 风格一致性控制
- 内容质量保证
- 个性化定制

Features:
- 对话历史跟踪
- 上下文连续性保持
- 风格自适应调整
- 内容事实核查
- 个性化推荐
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime, timedelta
from collections import deque

from ..base import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError
from ..content_generation_agent import ContentGenerationAgent, ContentRequest, ContentResult
from ..security import sandbox_manager, SandboxLevel
from ..tools import tool_registry


@dataclass
class ContextualContentRequest:
    """上下文内容生成请求"""
    content_type: str                           # 内容类型
    data: Union[Dict[str, Any], List[Dict[str, Any]]]  # 输入数据
    conversation_id: str = None                 # 对话ID
    context_history: List[Dict] = field(default_factory=list)  # 上下文历史
    user_preferences: Dict[str, Any] = field(default_factory=dict)  # 用户偏好
    style_requirements: Dict[str, Any] = field(default_factory=dict)  # 风格要求
    quality_criteria: Dict[str, Any] = field(default_factory=dict)   # 质量标准
    personalization: Dict[str, Any] = field(default_factory=dict)    # 个性化设置
    template: Optional[str] = None              # 自定义模板
    format: str = "text"                        # 输出格式
    language: str = "zh-CN"                     # 语言
    max_length: int = 500                       # 最大长度


@dataclass
class ConversationContext:
    """对话上下文"""
    conversation_id: str
    user_id: Optional[str] = None
    topic: Optional[str] = None
    messages: List[Dict] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    style_profile: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StyleProfile:
    """风格配置文件"""
    style_name: str
    tone: str = "professional"                  # 语调：professional, casual, technical, friendly
    formality: str = "medium"                   # 正式程度：low, medium, high
    complexity: str = "medium"                  # 复杂度：low, medium, high
    vocabulary: str = "standard"                # 词汇：simple, standard, advanced
    sentence_structure: str = "varied"          # 句式：simple, varied, complex
    cultural_context: str = "neutral"           # 文化背景：neutral, local, international
    domain_expertise: List[str] = field(default_factory=list)  # 专业领域
    preferences: Dict[str, Any] = field(default_factory=dict)


class ContextManager:
    """上下文管理器"""
    
    def __init__(self, max_context_length: int = 10, context_ttl: int = 3600):
        self.conversations: Dict[str, ConversationContext] = {}
        self.max_context_length = max_context_length  # 最大上下文长度
        self.context_ttl = context_ttl  # 上下文生存时间（秒）
        self.context_cache = {}
    
    async def get_context(self, conversation_id: str) -> Optional[ConversationContext]:
        """获取对话上下文"""
        if conversation_id in self.conversations:
            context = self.conversations[conversation_id]
            
            # 检查是否过期
            if (datetime.now() - context.last_updated).total_seconds() > self.context_ttl:
                await self.cleanup_context(conversation_id)
                return None
            
            return context
        
        return None
    
    async def create_context(
        self, 
        conversation_id: str, 
        user_id: str = None,
        topic: str = None
    ) -> ConversationContext:
        """创建新的对话上下文"""
        context = ConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
            topic=topic
        )
        
        self.conversations[conversation_id] = context
        return context
    
    async def update_context(
        self,
        conversation_id: str,
        message_type: str,  # "user", "assistant", "system"
        content: str,
        metadata: Dict[str, Any] = None
    ):
        """更新对话上下文"""
        context = await self.get_context(conversation_id)
        if not context:
            context = await self.create_context(conversation_id)
        
        # 添加新消息
        message = {
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        context.messages.append(message)
        
        # 维护上下文长度
        if len(context.messages) > self.max_context_length:
            # 移除最老的消息，但保留系统消息
            while len(context.messages) > self.max_context_length:
                removed = False
                for i, msg in enumerate(context.messages):
                    if msg["type"] != "system":
                        del context.messages[i]
                        removed = True
                        break
                if not removed:
                    break  # 如果只剩系统消息，停止删除
        
        context.last_updated = datetime.now()
    
    async def get_relevant_context(
        self,
        conversation_id: str,
        current_request: str,
        max_context_items: int = 5
    ) -> List[Dict]:
        """获取相关的上下文信息"""
        context = await self.get_context(conversation_id)
        if not context:
            return []
        
        # 简单的相关性排序：按时间倒序返回最近的消息
        recent_messages = context.messages[-max_context_items:]
        
        # 可以添加更复杂的相关性算法
        return recent_messages
    
    async def cleanup_context(self, conversation_id: str):
        """清理过期的上下文"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
    
    async def cleanup_expired_contexts(self):
        """清理所有过期的上下文"""
        current_time = datetime.now()
        expired_ids = []
        
        for conv_id, context in self.conversations.items():
            if (current_time - context.last_updated).total_seconds() > self.context_ttl:
                expired_ids.append(conv_id)
        
        for conv_id in expired_ids:
            await self.cleanup_context(conv_id)


class StyleAnalyzer:
    """风格分析器"""
    
    def __init__(self):
        # 风格特征关键词
        self.style_keywords = {
            "formal": ["因此", "综上所述", "据此", "鉴于", "基于上述", "经分析"],
            "casual": ["其实", "就是", "大概", "可能", "应该", "感觉"],
            "technical": ["算法", "系统", "架构", "实现", "配置", "性能", "优化"],
            "friendly": ["您好", "请", "谢谢", "希望", "建议", "欢迎"]
        }
        
        # 句式特征
        self.sentence_patterns = {
            "simple": r'^[^，。！？]{1,20}[。！？]$',
            "complex": r'[，；：][^。！？]*[，；：][^。！？]*[。！？]'
        }
    
    async def analyze_style(self, text: str) -> StyleProfile:
        """分析文本风格"""
        style_scores = {}
        
        # 分析风格关键词
        for style, keywords in self.style_keywords.items():
            score = 0
            for keyword in keywords:
                score += text.count(keyword)
            style_scores[style] = score / len(keywords) if keywords else 0
        
        # 确定主要风格
        primary_style = max(style_scores, key=style_scores.get) if style_scores else "neutral"
        
        # 分析句式复杂度
        import re
        simple_sentences = len(re.findall(self.sentence_patterns["simple"], text))
        complex_sentences = len(re.findall(self.sentence_patterns["complex"], text))
        
        if complex_sentences > simple_sentences:
            sentence_structure = "complex"
        elif simple_sentences > 0:
            sentence_structure = "simple"
        else:
            sentence_structure = "varied"
        
        # 分析正式程度
        formal_indicators = text.count("您") + text.count("敬请") + text.count("恳请")
        casual_indicators = text.count("你") + text.count("咱们") + text.count("嗯")
        
        if formal_indicators > casual_indicators:
            formality = "high"
        elif casual_indicators > formal_indicators:
            formality = "low"
        else:
            formality = "medium"
        
        return StyleProfile(
            style_name=primary_style,
            tone=primary_style,
            formality=formality,
            sentence_structure=sentence_structure,
            preferences={
                "style_scores": style_scores,
                "text_length": len(text)
            }
        )
    
    async def adapt_style(self, content: str, target_style: StyleProfile) -> str:
        """根据目标风格调整内容"""
        try:
            adapted_content = content
            
            # 根据正式程度调整
            if target_style.formality == "high":
                adapted_content = adapted_content.replace("你", "您")
                adapted_content = adapted_content.replace("可以", "能够")
            elif target_style.formality == "low":
                adapted_content = adapted_content.replace("您", "你")
                adapted_content = adapted_content.replace("能够", "可以")
            
            # 根据语调调整
            if target_style.tone == "friendly":
                if not any(word in adapted_content for word in ["请", "谢谢", "希望"]):
                    adapted_content = "希望这个分析对您有帮助。" + adapted_content
            
            return adapted_content
            
        except Exception as e:
            # 风格调整失败时返回原内容
            return content


class QualityChecker:
    """内容质量检查器"""
    
    def __init__(self):
        self.quality_criteria = {
            "length": {"min": 10, "max": 2000},
            "readability": {"min_score": 0.6},
            "coherence": {"min_score": 0.7},
            "accuracy": {"min_score": 0.8}
        }
    
    async def check_quality(self, content: str, criteria: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查内容质量"""
        if criteria:
            self.quality_criteria.update(criteria)
        
        quality_report = {
            "overall_score": 0.0,
            "issues": [],
            "suggestions": [],
            "metrics": {}
        }
        
        try:
            # 长度检查
            length_score = await self._check_length(content)
            quality_report["metrics"]["length"] = length_score
            
            # 可读性检查
            readability_score = await self._check_readability(content)
            quality_report["metrics"]["readability"] = readability_score
            
            # 连贯性检查
            coherence_score = await self._check_coherence(content)
            quality_report["metrics"]["coherence"] = coherence_score
            
            # 事实准确性检查（简化版）
            accuracy_score = await self._check_accuracy(content)
            quality_report["metrics"]["accuracy"] = accuracy_score
            
            # 计算总分
            scores = [length_score, readability_score, coherence_score, accuracy_score]
            quality_report["overall_score"] = sum(scores) / len(scores)
            
            # 生成建议
            quality_report["suggestions"] = await self._generate_suggestions(quality_report["metrics"])
            
        except Exception as e:
            quality_report["issues"].append(f"质量检查过程中发生错误: {str(e)}")
        
        return quality_report
    
    async def _check_length(self, content: str) -> float:
        """检查内容长度"""
        length = len(content)
        min_length = self.quality_criteria["length"]["min"]
        max_length = self.quality_criteria["length"]["max"]
        
        if length < min_length:
            return 0.3  # 内容过短
        elif length > max_length:
            return 0.7  # 内容过长但可接受
        else:
            return 1.0  # 长度合适
    
    async def _check_readability(self, content: str) -> float:
        """检查可读性"""
        # 简化的可读性检查
        sentences = content.split('。')
        if not sentences:
            return 0.0
        
        # 计算平均句长
        avg_sentence_length = sum(len(s.strip()) for s in sentences if s.strip()) / len([s for s in sentences if s.strip()])
        
        # 理想句长范围：15-25字符
        if 15 <= avg_sentence_length <= 25:
            return 1.0
        elif 10 <= avg_sentence_length <= 35:
            return 0.8
        else:
            return 0.6
    
    async def _check_coherence(self, content: str) -> float:
        """检查连贯性"""
        # 简化的连贯性检查
        # 检查连接词的使用
        connectors = ["因此", "所以", "然而", "但是", "而且", "另外", "首先", "其次", "最后"]
        connector_count = sum(content.count(connector) for connector in connectors)
        
        sentences = len([s for s in content.split('。') if s.strip()])
        if sentences == 0:
            return 0.0
        
        connector_ratio = connector_count / sentences
        
        # 理想的连接词密度：0.1-0.3
        if 0.1 <= connector_ratio <= 0.3:
            return 1.0
        elif 0.05 <= connector_ratio <= 0.5:
            return 0.8
        else:
            return 0.6
    
    async def _check_accuracy(self, content: str) -> float:
        """检查准确性（简化版）"""
        # 这里只做基础的准确性检查
        # 在实际应用中，可以集成事实核查服务
        
        # 检查是否包含明显的错误表述
        error_patterns = [
            r'100%确定', r'绝对不会', r'永远不可能',
            r'所有.*都', r'从来没有', r'全部.*都是'
        ]
        
        import re
        error_count = 0
        for pattern in error_patterns:
            if re.search(pattern, content):
                error_count += 1
        
        # 基于错误数量计算准确性分数
        if error_count == 0:
            return 1.0
        elif error_count <= 2:
            return 0.8
        else:
            return 0.6
    
    async def _generate_suggestions(self, metrics: Dict[str, float]) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        if metrics.get("length", 1.0) < 0.5:
            suggestions.append("内容长度偏短，建议增加更多细节和说明")
        
        if metrics.get("readability", 1.0) < 0.7:
            suggestions.append("句子偏长或偏短，建议调整句式结构以提高可读性")
        
        if metrics.get("coherence", 1.0) < 0.7:
            suggestions.append("内容连贯性不足，建议增加过渡词和逻辑连接")
        
        if metrics.get("accuracy", 1.0) < 0.8:
            suggestions.append("内容可能包含绝对化表述，建议使用更准确的表达")
        
        return suggestions


class PersonalizationEngine:
    """个性化引擎"""
    
    def __init__(self):
        self.user_profiles = {}
        self.learning_rate = 0.1
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户配置文件"""
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = {
                "preferences": {
                    "tone": "professional",
                    "formality": "medium",
                    "complexity": "medium",
                    "topics": []
                },
                "feedback_history": [],
                "content_history": [],
                "learning_data": {}
            }
        
        return self.user_profiles[user_id]
    
    async def update_user_feedback(
        self,
        user_id: str,
        content: str,
        feedback_score: float,
        feedback_comments: str = None
    ):
        """更新用户反馈"""
        profile = await self.get_user_profile(user_id)
        
        feedback_entry = {
            "content": content[:100] + "..." if len(content) > 100 else content,
            "score": feedback_score,
            "comments": feedback_comments,
            "timestamp": datetime.now().isoformat()
        }
        
        profile["feedback_history"].append(feedback_entry)
        
        # 基于反馈调整偏好
        await self._adjust_preferences(user_id, content, feedback_score)
    
    async def _adjust_preferences(self, user_id: str, content: str, feedback_score: float):
        """基于反馈调整用户偏好"""
        profile = await self.get_user_profile(user_id)
        
        # 分析内容风格
        style_analyzer = StyleAnalyzer()
        content_style = await style_analyzer.analyze_style(content)
        
        # 如果反馈积极，加强这种风格偏好
        if feedback_score > 0.7:
            current_tone = profile["preferences"]["tone"]
            if content_style.tone != current_tone:
                # 逐渐调整偏好
                profile["preferences"]["tone"] = content_style.tone
        
        # 更新学习数据
        profile["learning_data"][content_style.tone] = profile["learning_data"].get(content_style.tone, 0) + feedback_score
    
    async def personalize_request(
        self,
        user_id: str,
        request: ContextualContentRequest
    ) -> ContextualContentRequest:
        """个性化请求"""
        profile = await self.get_user_profile(user_id)
        
        # 应用用户偏好
        if not request.style_requirements.get("tone"):
            request.style_requirements["tone"] = profile["preferences"]["tone"]
        
        if not request.style_requirements.get("formality"):
            request.style_requirements["formality"] = profile["preferences"]["formality"]
        
        # 添加个性化设置
        request.personalization.update({
            "user_id": user_id,
            "preferences": profile["preferences"],
            "learning_weight": len(profile["feedback_history"]) * self.learning_rate
        })
        
        return request


class EnhancedContentGenerationAgent(ContentGenerationAgent):
    """增强版内容生成Agent"""
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="enhanced_content_generation_agent",
                agent_type=AgentType.CONTENT_GENERATION,
                name="Enhanced Content Generation Agent",
                description="增强版内容生成Agent，支持上下文管理和个性化定制",
                timeout_seconds=60,
                enable_caching=True,
                cache_ttl_seconds=1800
            )
        
        super().__init__(config)
        
        # 初始化增强组件
        self.context_manager = ContextManager()
        self.style_analyzer = StyleAnalyzer()
        self.quality_checker = QualityChecker()
        self.personalization_engine = PersonalizationEngine()
        
        # 启动定期清理任务
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        async def cleanup_loop():
            while True:
                try:
                    await self.context_manager.cleanup_expired_contexts()
                    await asyncio.sleep(300)  # 每5分钟清理一次
                except Exception as e:
                    self.logger.error(f"清理任务失败: {str(e)}")
                    await asyncio.sleep(60)
        
        self._cleanup_task = asyncio.create_task(cleanup_loop())
    
    async def execute_contextual(
        self,
        request: ContextualContentRequest,
        user_id: str = None
    ) -> AgentResult:
        """执行上下文内容生成"""
        try:
            self.logger.info(
                "执行上下文内容生成",
                agent_id=self.agent_id,
                conversation_id=request.conversation_id,
                content_type=request.content_type
            )
            
            # 个性化请求
            if user_id:
                request = await self.personalization_engine.personalize_request(user_id, request)
            
            # 获取上下文信息
            context_info = []
            if request.conversation_id:
                context_info = await self.context_manager.get_relevant_context(
                    request.conversation_id,
                    str(request.data)
                )
            
            # 构建增强的内容请求
            enhanced_request = await self._build_enhanced_request(request, context_info)
            
            # 生成内容
            result = await super().execute(enhanced_request)
            
            if result.success:
                # 增强内容质量
                enhanced_result = await self._enhance_content_quality(
                    result.data, request
                )
                
                # 更新上下文
                if request.conversation_id:
                    await self.context_manager.update_context(
                        request.conversation_id,
                        "assistant",
                        enhanced_result.content,
                        {
                            "content_type": request.content_type,
                            "quality_score": enhanced_result.quality_score
                        }
                    )
                
                result.data = enhanced_result
                result.metadata.update({
                    "contextual": True,
                    "conversation_id": request.conversation_id,
                    "personalized": user_id is not None,
                    "context_length": len(context_info)
                })
            
            return result
            
        except Exception as e:
            error_msg = f"上下文内容生成失败: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _build_enhanced_request(
        self,
        contextual_request: ContextualContentRequest,
        context_info: List[Dict]
    ) -> ContentRequest:
        """构建增强的内容请求"""
        # 构建上下文提示
        context_prompt = ""
        if context_info:
            context_messages = [
                f"之前的{msg['type']}: {msg['content'][:100]}..."
                for msg in context_info[-3:]  # 使用最近的3条消息
            ]
            context_prompt = f"对话上下文：{'; '.join(context_messages)}\n\n"
        
        # 构建风格指导
        style_guidance = ""
        if contextual_request.style_requirements:
            style_parts = []
            for key, value in contextual_request.style_requirements.items():
                style_parts.append(f"{key}: {value}")
            style_guidance = f"风格要求：{'; '.join(style_parts)}\n\n"
        
        # 组合模板
        enhanced_template = ""
        if contextual_request.template:
            enhanced_template = contextual_request.template
        else:
            enhanced_template = f"""
{context_prompt}{style_guidance}请根据以下数据生成{contextual_request.content_type}：

数据：{{data}}

要求：
- 保持与之前对话的连贯性
- 使用一致的语言风格和术语
- 确保内容准确和有价值
"""
        
        # 创建标准内容请求
        return ContentRequest(
            data=contextual_request.data,
            content_type=contextual_request.content_type,
            template=enhanced_template,
            context=contextual_request.context_history,
            format=contextual_request.format,
            tone=contextual_request.style_requirements.get("tone", "professional"),
            language=contextual_request.language,
            max_length=contextual_request.max_length
        )
    
    async def _enhance_content_quality(
        self,
        content_result: ContentResult,
        request: ContextualContentRequest
    ) -> ContentResult:
        """增强内容质量"""
        try:
            # 质量检查
            quality_report = await self.quality_checker.check_quality(
                content_result.content,
                request.quality_criteria
            )
            
            # 风格调整
            if request.style_requirements:
                target_style = StyleProfile(
                    style_name="custom",
                    tone=request.style_requirements.get("tone", "professional"),
                    formality=request.style_requirements.get("formality", "medium")
                )
                
                adjusted_content = await self.style_analyzer.adapt_style(
                    content_result.content,
                    target_style
                )
                content_result.content = adjusted_content
            
            # 更新质量分数
            content_result.quality_score = max(
                content_result.quality_score,
                quality_report["overall_score"]
            )
            
            # 添加质量报告到元数据
            if not content_result.metadata:
                content_result.metadata = {}
            
            content_result.metadata.update({
                "quality_report": quality_report,
                "style_adjusted": bool(request.style_requirements),
                "enhancement_applied": True
            })
            
            return content_result
            
        except Exception as e:
            self.logger.warning(f"内容质量增强失败: {str(e)}")
            return content_result
    
    async def update_user_feedback(
        self,
        user_id: str,
        conversation_id: str,
        feedback_score: float,
        feedback_comments: str = None
    ):
        """更新用户反馈"""
        try:
            # 获取最近的内容
            context = await self.context_manager.get_context(conversation_id)
            if context and context.messages:
                last_assistant_message = None
                for msg in reversed(context.messages):
                    if msg["type"] == "assistant":
                        last_assistant_message = msg
                        break
                
                if last_assistant_message:
                    await self.personalization_engine.update_user_feedback(
                        user_id,
                        last_assistant_message["content"],
                        feedback_score,
                        feedback_comments
                    )
        
        except Exception as e:
            self.logger.error(f"更新用户反馈失败: {str(e)}")
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """获取对话摘要"""
        try:
            context = await self.context_manager.get_context(conversation_id)
            if not context:
                return None
            
            return {
                "conversation_id": conversation_id,
                "message_count": len(context.messages),
                "topic": context.topic,
                "created_at": context.created_at.isoformat(),
                "last_updated": context.last_updated.isoformat(),
                "user_preferences": context.user_preferences,
                "style_profile": context.style_profile
            }
            
        except Exception as e:
            self.logger.error(f"获取对话摘要失败: {str(e)}")
            return None
    
    async def health_check(self) -> Dict[str, Any]:
        """执行健康检查"""
        health = await super().health_check()
        
        # 增加增强功能的健康检查
        health.update({
            "context_manager": {
                "healthy": True,
                "active_conversations": len(self.context_manager.conversations),
                "cache_size": len(self.context_manager.context_cache)
            },
            "style_analyzer": "healthy",
            "quality_checker": "healthy",
            "personalization_engine": {
                "healthy": True,
                "user_profiles": len(self.personalization_engine.user_profiles)
            },
            "cleanup_task": "running" if self._cleanup_task and not self._cleanup_task.done() else "stopped"
        })
        
        return health
    
    async def cleanup(self):
        """清理资源"""
        await super().cleanup()
        
        # 停止清理任务
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
        
        # 清理上下文
        self.context_manager.conversations.clear()