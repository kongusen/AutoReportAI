"""
智能选择器模块 - React Agent系统适配器
提供LLM选择所需的基础类型定义和服务类
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Optional, List, Any

class TaskType(str, Enum):
    """任务类型枚举"""
    REASONING = "reasoning"
    CODING = "coding"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    TRANSLATION = "translation"
    QA = "qa"
    SUMMARIZATION = "summarization"
    GENERAL = "general"

class TaskComplexity(str, Enum):
    """任务复杂度枚举"""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    EXPERT = "expert"

@dataclass
class TaskCharacteristics:
    """任务特征"""
    task_type: TaskType
    complexity: TaskComplexity
    context_length: Optional[int] = None
    requires_reasoning: bool = False
    requires_creativity: bool = False

@dataclass
class SelectionCriteria:
    """选择条件"""
    task_type: Optional[TaskType] = None
    complexity: Optional[TaskComplexity] = None
    max_cost: Optional[float] = None
    min_quality: Optional[float] = None
    prefer_fast: bool = False
    require_local: bool = False

@dataclass  
class ModelCapabilities:
    """模型能力评分"""
    reasoning_score: float = 0.5
    coding_score: float = 0.5
    creative_score: float = 0.5
    analysis_score: float = 0.5
    translation_score: float = 0.5
    qa_score: float = 0.5
    summarization_score: float = 0.5
    overall_score: float = 0.5

@dataclass
class ModelRecommendation:
    """模型推荐结果"""
    model_id: str
    confidence: float
    reasoning: str
    estimated_cost: Optional[float] = None
    estimated_time: Optional[float] = None


class IntelligentLLMSelector:
    """智能LLM选择器 - React Agent系统适配器"""
    
    def __init__(self, db_session=None, user_id=None):
        """初始化选择器"""
        self.db_session = db_session
        self.user_id = user_id
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "healthy",
            "message": "React Agent LLM Selector operational",
            "system": "React Agent"
        }
    
    def select_best_model(self, task_characteristics: TaskCharacteristics) -> ModelRecommendation:
        """选择最佳模型"""
        # 基于任务特征选择最合适的模型
        if task_characteristics.task_type == TaskType.REASONING:
            return ModelRecommendation(
                model_id="claude-3-5-sonnet-20241022",
                confidence=0.95,
                reasoning="Claude Sonnet最适合推理任务"
            )
        elif task_characteristics.task_type == TaskType.CODING:
            return ModelRecommendation(
                model_id="gpt-4",
                confidence=0.9,
                reasoning="GPT-4在代码生成方面表现优秀"
            )
        elif task_characteristics.complexity == TaskComplexity.SIMPLE:
            return ModelRecommendation(
                model_id="gpt-3.5-turbo",
                confidence=0.8,
                reasoning="简单任务使用GPT-3.5即可满足需求"
            )
        else:
            return ModelRecommendation(
                model_id="gpt-4",
                confidence=0.85,
                reasoning="默认使用GPT-4处理中等复杂度任务"
            )
    
    async def execute_task(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """执行任务"""
        try:
            from app.services.infrastructure.ai.agents import create_react_agent
            
            user_id = kwargs.get("user_id", self.user_id or "system")
            agent = create_react_agent(user_id)
            await agent.initialize()
            
            # 通过React Agent执行任务
            result = await agent.chat(prompt)
            
            return {
                "success": True,
                "result": result,
                "model": "react-agent",
                "user_id": user_id
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": "react-agent"
            }