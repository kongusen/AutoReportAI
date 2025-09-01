"""
Infrastructure层内容生成代理

提供内容生成相关的AI技术支撑：

核心职责：
1. 文本内容的AI生成
2. 模板内容的智能填充
3. 多种格式内容转换
4. 内容质量检查和优化

技术职责：
- 纯技术实现，不包含业务逻辑
- 可被Application/Domain层调用
- 提供稳定的内容生成服务
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ContentType(Enum):
    """内容类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    REPORT = "report"
    EMAIL = "email"


class GenerationMode(Enum):
    """生成模式"""
    CREATIVE = "creative"
    FACTUAL = "factual"
    TEMPLATE_FILL = "template_fill"
    SUMMARIZE = "summarize"
    TRANSLATE = "translate"


class ContentGenerationAgent:
    """
    Infrastructure层内容生成代理
    
    核心职责：
    1. 提供多种类型的内容生成能力
    2. 支持模板填充和格式转换
    3. 内容质量评估和优化
    4. 批量内容生成处理
    
    技术定位：
    - Infrastructure层技术基础设施
    - 为上层应用提供内容生成能力
    - 不包含具体业务逻辑
    """
    
    def __init__(self):
        # 生成统计
        self.generation_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "avg_generation_time": 0.0,
            "content_type_stats": {},
            "generation_mode_stats": {}
        }
        
        # 质量阈值
        self.quality_thresholds = {
            ContentType.TEXT: 0.7,
            ContentType.MARKDOWN: 0.8,
            ContentType.HTML: 0.8,
            ContentType.REPORT: 0.9,
            ContentType.EMAIL: 0.8
        }
        
        logger.info("内容生成代理初始化完成")
    
    async def generate_content(self,
                             prompt: str,
                             content_type: ContentType = ContentType.TEXT,
                             generation_mode: GenerationMode = GenerationMode.CREATIVE,
                             context: Dict[str, Any] = None,
                             max_length: Optional[int] = None,
                             temperature: float = 0.7,
                             user_id: str = "system") -> Dict[str, Any]:
        """
        生成内容
        
        Args:
            prompt: 生成提示词
            content_type: 内容类型
            generation_mode: 生成模式
            context: 上下文信息
            max_length: 最大长度限制
            temperature: 生成温度
            user_id: 用户ID
            
        Returns:
            生成结果
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            self.generation_stats["total_generations"] += 1
            
            # 构建生成请求
            generation_request = {
                "prompt": prompt,
                "content_type": content_type.value,
                "generation_mode": generation_mode.value,
                "context": context or {},
                "max_length": max_length,
                "temperature": temperature,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # 执行内容生成
            generated_content = await self._execute_generation(generation_request)
            
            # 质量评估
            quality_score = await self._assess_content_quality(
                generated_content, content_type, generation_request
            )
            
            # 后处理
            processed_content = await self._post_process_content(
                generated_content, content_type, quality_score
            )
            
            generation_time = asyncio.get_event_loop().time() - start_time
            
            # 更新统计
            self._update_generation_stats(
                content_type, generation_mode, generation_time, success=True
            )
            
            result = {
                "success": True,
                "content": processed_content,
                "content_type": content_type.value,
                "generation_mode": generation_mode.value,
                "quality_score": quality_score,
                "generation_time": generation_time,
                "word_count": len(processed_content.split()) if isinstance(processed_content, str) else 0,
                "character_count": len(str(processed_content)),
                "metadata": {
                    "temperature": temperature,
                    "max_length": max_length,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"内容生成成功: 类型={content_type.value}, 时长={generation_time:.2f}s")
            return result
            
        except Exception as e:
            generation_time = asyncio.get_event_loop().time() - start_time
            
            # 更新统计
            self._update_generation_stats(
                content_type, generation_mode, generation_time, success=False
            )
            
            logger.error(f"内容生成失败: {e}")
            
            return {
                "success": False,
                "error": str(e),
                "content_type": content_type.value,
                "generation_mode": generation_mode.value,
                "generation_time": generation_time
            }
    
    async def fill_template(self,
                          template: str,
                          variables: Dict[str, Any],
                          content_type: ContentType = ContentType.TEXT,
                          user_id: str = "system") -> Dict[str, Any]:
        """
        模板填充
        
        Args:
            template: 模板内容
            variables: 变量字典
            content_type: 内容类型
            user_id: 用户ID
            
        Returns:
            填充结果
        """
        try:
            # 模拟模板填充（实际应该使用模板引擎）
            filled_content = template
            
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                filled_content = filled_content.replace(placeholder, str(value))
            
            # 检查未填充的占位符
            import re
            unfilled_placeholders = re.findall(r'\{\{(\w+)\}\}', filled_content)
            
            result = {
                "success": True,
                "content": filled_content,
                "content_type": content_type.value,
                "variables_used": list(variables.keys()),
                "unfilled_placeholders": unfilled_placeholders,
                "fill_completeness": 1.0 - (len(unfilled_placeholders) / max(len(re.findall(r'\{\{\w+\}\}', template)), 1)),
                "metadata": {
                    "template_length": len(template),
                    "result_length": len(filled_content),
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"模板填充成功: 完整度={result['fill_completeness']:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"模板填充失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "content_type": content_type.value
            }
    
    async def convert_format(self,
                           content: str,
                           source_type: ContentType,
                           target_type: ContentType,
                           user_id: str = "system") -> Dict[str, Any]:
        """
        格式转换
        
        Args:
            content: 原始内容
            source_type: 源格式
            target_type: 目标格式
            user_id: 用户ID
            
        Returns:
            转换结果
        """
        try:
            # 模拟格式转换
            if source_type == ContentType.TEXT and target_type == ContentType.MARKDOWN:
                converted_content = self._text_to_markdown(content)
            elif source_type == ContentType.MARKDOWN and target_type == ContentType.HTML:
                converted_content = self._markdown_to_html(content)
            elif source_type == ContentType.TEXT and target_type == ContentType.HTML:
                converted_content = self._text_to_html(content)
            else:
                # 通用转换
                converted_content = content
            
            result = {
                "success": True,
                "content": converted_content,
                "source_type": source_type.value,
                "target_type": target_type.value,
                "conversion_ratio": len(converted_content) / max(len(content), 1),
                "metadata": {
                    "source_length": len(content),
                    "target_length": len(converted_content),
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"格式转换成功: {source_type.value} → {target_type.value}")
            return result
            
        except Exception as e:
            logger.error(f"格式转换失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "source_type": source_type.value,
                "target_type": target_type.value
            }
    
    async def summarize_content(self,
                              content: str,
                              summary_length: int = 200,
                              summary_style: str = "bullet_points",
                              user_id: str = "system") -> Dict[str, Any]:
        """
        内容摘要
        
        Args:
            content: 原始内容
            summary_length: 摘要长度
            summary_style: 摘要风格
            user_id: 用户ID
            
        Returns:
            摘要结果
        """
        try:
            # 模拟内容摘要
            content_words = content.split()
            if len(content_words) <= summary_length:
                summary = content
                compression_ratio = 1.0
            else:
                # 简单的摘要算法：取前N个词
                summary_words = content_words[:summary_length]
                
                if summary_style == "bullet_points":
                    # 转换为要点形式
                    sentences = '. '.join(summary_words).split('.')[:3]
                    summary = '\n'.join([f"• {sentence.strip()}" for sentence in sentences if sentence.strip()])
                else:
                    summary = ' '.join(summary_words)
                
                compression_ratio = len(summary) / len(content)
            
            result = {
                "success": True,
                "summary": summary,
                "original_length": len(content),
                "summary_length": len(summary),
                "compression_ratio": compression_ratio,
                "summary_style": summary_style,
                "word_count": len(summary.split()),
                "metadata": {
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"内容摘要成功: 压缩率={compression_ratio:.2%}")
            return result
            
        except Exception as e:
            logger.error(f"内容摘要失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def batch_generate(self,
                           prompts: List[str],
                           content_type: ContentType = ContentType.TEXT,
                           generation_mode: GenerationMode = GenerationMode.CREATIVE,
                           user_id: str = "system") -> Dict[str, Any]:
        """
        批量生成内容
        
        Args:
            prompts: 提示词列表
            content_type: 内容类型
            generation_mode: 生成模式
            user_id: 用户ID
            
        Returns:
            批量生成结果
        """
        try:
            batch_start_time = asyncio.get_event_loop().time()
            
            # 并发生成
            tasks = []
            for i, prompt in enumerate(prompts):
                task = self.generate_content(
                    prompt=prompt,
                    content_type=content_type,
                    generation_mode=generation_mode,
                    user_id=f"{user_id}_batch_{i}"
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 统计结果
            successful_results = []
            failed_results = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_results.append({
                        "index": i,
                        "prompt": prompts[i],
                        "error": str(result)
                    })
                elif result.get("success"):
                    successful_results.append(result)
                else:
                    failed_results.append({
                        "index": i,
                        "prompt": prompts[i],
                        "error": result.get("error", "Unknown error")
                    })
            
            batch_time = asyncio.get_event_loop().time() - batch_start_time
            
            batch_result = {
                "success": True,
                "total_prompts": len(prompts),
                "successful_count": len(successful_results),
                "failed_count": len(failed_results),
                "success_rate": len(successful_results) / len(prompts),
                "batch_time": batch_time,
                "avg_time_per_item": batch_time / len(prompts),
                "results": successful_results,
                "failures": failed_results,
                "metadata": {
                    "content_type": content_type.value,
                    "generation_mode": generation_mode.value,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"批量生成完成: 成功率={batch_result['success_rate']:.2%}")
            return batch_result
            
        except Exception as e:
            logger.error(f"批量生成失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "total_prompts": len(prompts)
            }
    
    # 私有方法
    
    async def _execute_generation(self, request: Dict[str, Any]) -> str:
        """执行内容生成"""
        # 模拟异步生成
        await asyncio.sleep(0.1)
        
        prompt = request["prompt"]
        content_type = request["content_type"]
        generation_mode = request["generation_mode"]
        
        # 根据模式和类型生成不同的内容
        if generation_mode == "creative":
            if content_type == "report":
                return f"# 报告标题\n\n基于提示 '{prompt}' 生成的创意报告内容...\n\n## 主要发现\n\n这是一个示例报告。"
            elif content_type == "email":
                return f"主题：关于 {prompt}\n\n亲爱的用户，\n\n这是基于您的需求生成的邮件内容...\n\n最好的问候"
            else:
                return f"基于提示 '{prompt}' 生成的创意内容。这是一个模拟的内容生成结果。"
        
        elif generation_mode == "factual":
            return f"关于 '{prompt}' 的事实性信息：这是一个模拟的事实性内容生成结果。"
        
        else:
            return f"针对 '{prompt}' 生成的内容：这是一个通用的内容生成结果。"
    
    async def _assess_content_quality(self,
                                    content: str,
                                    content_type: ContentType,
                                    request: Dict[str, Any]) -> float:
        """评估内容质量"""
        quality_score = 0.8  # 基础质量分数
        
        # 基于长度评估
        if len(content) < 10:
            quality_score -= 0.3
        elif len(content) > 100:
            quality_score += 0.1
        
        # 基于内容类型评估
        if content_type == ContentType.REPORT and "##" in content:
            quality_score += 0.1
        
        if content_type == ContentType.EMAIL and "主题：" in content:
            quality_score += 0.1
        
        # 应用质量阈值
        threshold = self.quality_thresholds.get(content_type, 0.7)
        return max(threshold, min(1.0, quality_score))
    
    async def _post_process_content(self,
                                  content: str,
                                  content_type: ContentType,
                                  quality_score: float) -> str:
        """内容后处理"""
        processed_content = content
        
        # 基于质量分数进行处理
        if quality_score < 0.7:
            processed_content += "\n\n[注：此内容由AI生成，建议人工审核]"
        
        # 基于类型进行格式化
        if content_type == ContentType.MARKDOWN and not processed_content.startswith('#'):
            processed_content = f"# 生成内容\n\n{processed_content}"
        
        elif content_type == ContentType.HTML and not processed_content.startswith('<'):
            processed_content = f"<div>{processed_content}</div>"
        
        return processed_content
    
    def _text_to_markdown(self, text: str) -> str:
        """文本转Markdown"""
        lines = text.split('\n')
        markdown_lines = []
        
        for line in lines:
            if line.strip():
                if len(line) < 50 and line.isupper():
                    # 短的全大写行作为标题
                    markdown_lines.append(f"# {line}")
                else:
                    markdown_lines.append(line)
            else:
                markdown_lines.append("")
        
        return '\n'.join(markdown_lines)
    
    def _markdown_to_html(self, markdown: str) -> str:
        """Markdown转HTML"""
        html = markdown.replace('# ', '<h1>').replace('\n', '</h1>\n<p>').replace('<p></p>', '') + '</p>'
        return f"<html><body>{html}</body></html>"
    
    def _text_to_html(self, text: str) -> str:
        """文本转HTML"""
        paragraphs = text.split('\n\n')
        br_tag = '<br>'
        html_paragraphs = [f"<p>{p.replace(chr(10), br_tag)}</p>" for p in paragraphs if p.strip()]
        return f"<html><body>{''.join(html_paragraphs)}</body></html>"
    
    def _update_generation_stats(self,
                               content_type: ContentType,
                               generation_mode: GenerationMode,
                               generation_time: float,
                               success: bool):
        """更新生成统计"""
        if success:
            self.generation_stats["successful_generations"] += 1
        else:
            self.generation_stats["failed_generations"] += 1
        
        # 更新平均时间
        total_generations = self.generation_stats["total_generations"]
        if total_generations > 1:
            current_avg = self.generation_stats["avg_generation_time"]
            new_avg = (current_avg * (total_generations - 1) + generation_time) / total_generations
            self.generation_stats["avg_generation_time"] = new_avg
        else:
            self.generation_stats["avg_generation_time"] = generation_time
        
        # 更新类型统计
        type_key = content_type.value
        if type_key not in self.generation_stats["content_type_stats"]:
            self.generation_stats["content_type_stats"][type_key] = 0
        self.generation_stats["content_type_stats"][type_key] += 1
        
        # 更新模式统计
        mode_key = generation_mode.value
        if mode_key not in self.generation_stats["generation_mode_stats"]:
            self.generation_stats["generation_mode_stats"][mode_key] = 0
        self.generation_stats["generation_mode_stats"][mode_key] += 1
    
    def get_agent_statistics(self) -> Dict[str, Any]:
        """获取代理统计信息"""
        return {
            "agent_name": "ContentGenerationAgent",
            "version": "1.0.0-infrastructure",
            "architecture": "DDD Infrastructure Layer",
            "generation_stats": self.generation_stats,
            "supported_content_types": [t.value for t in ContentType],
            "supported_generation_modes": [m.value for m in GenerationMode],
            "quality_thresholds": {k.value: v for k, v in self.quality_thresholds.items()},
            "capabilities": [
                "content_generation",
                "template_filling",
                "format_conversion",
                "content_summarization",
                "batch_processing"
            ]
        }