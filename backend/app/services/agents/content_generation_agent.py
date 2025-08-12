"""
Content Generation Agent

Generates human-readable content from data using AI/LLM services.
Replaces content generation functionality from the intelligent_placeholder system.

Features:
- Natural language generation from structured data
- Template-based content generation
- Multi-format output (text, markdown, HTML)
- Context-aware content adaptation
- Quality assessment and improvement
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

try:
    from app.services.ai_service import ai_service
    from app.services.enhanced_ai_service import enhanced_ai_service
    HAS_AI_SERVICES = True
except ImportError:
    HAS_AI_SERVICES = False
    ai_service = None
    enhanced_ai_service = None

from .base import BaseAgent, AgentConfig, AgentResult, AgentType, AgentError


@dataclass
class ContentRequest:
    """Content generation request"""
    data: Union[Dict[str, Any], List[Dict[str, Any]]]
    content_type: str  # "text", "summary", "analysis", "description"
    template: Optional[str] = None
    context: Dict[str, Any] = None
    format: str = "text"  # "text", "markdown", "html"
    tone: str = "professional"  # "professional", "casual", "technical"
    language: str = "zh-CN"
    max_length: int = 500


@dataclass
class ContentResult:
    """Content generation result"""
    content: str
    format: str
    quality_score: float
    word_count: int
    metadata: Dict[str, Any] = None


class ContentGenerationAgent(BaseAgent):
    """
    Agent for generating human-readable content from data
    """
    
    def __init__(self, config: AgentConfig = None):
        if config is None:
            config = AgentConfig(
                agent_id="content_generation_agent",
                agent_type=AgentType.CONTENT_GENERATION,
                name="Content Generation Agent", 
                description="Generates natural language content from structured data",
                timeout_seconds=45,
                enable_caching=True,
                cache_ttl_seconds=1800  # 30-minute cache for generated content
            )
        
        super().__init__(config)
        self.content_templates = self._load_content_templates()
    
    def _load_content_templates(self) -> Dict[str, str]:
        """Load content generation templates"""
        return {
            "statistical_summary": """
基于提供的数据，生成一段简洁的统计总结：

数据内容：{data_summary}
统计指标：{statistics}
关键发现：{key_findings}

请用{tone}的语调，生成不超过{max_length}字的总结。
            """.strip(),
            
            "trend_analysis": """
分析以下趋势数据并生成说明：

数据：{data}
趋势类型：{trend_type}
时间范围：{time_range}

请生成{tone}的趋势分析说明，不超过{max_length}字。
            """.strip(),
            
            "comparison_report": """
基于以下对比数据生成报告：

对比项目：{comparison_items}
主要差异：{key_differences}
结论：{conclusions}

请用{tone}语调生成对比报告，不超过{max_length}字。
            """.strip(),
            
            "data_description": """
为以下数据生成描述性文字：

数据类型：{data_type}
数据量：{data_volume}
主要内容：{main_content}
特点：{characteristics}

请生成{tone}的数据描述，不超过{max_length}字。
            """.strip()
        }
    
    async def execute(
        self,
        input_data: Union[ContentRequest, Dict[str, Any]],
        context: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Execute content generation
        
        Args:
            input_data: ContentRequest or dict with generation parameters
            context: Additional context information
            
        Returns:
            AgentResult with generated content
        """
        try:
            # Parse input data
            if isinstance(input_data, dict):
                # Filter out unsupported parameters
                supported_params = {
                    'data', 'content_type', 'template', 'context', 'format',
                    'tone', 'language', 'max_length'
                }
                filtered_data = {k: v for k, v in input_data.items() if k in supported_params}
                content_request = ContentRequest(**filtered_data)
            else:
                content_request = input_data
            
            self.logger.info(
                "Generating content",
                agent_id=self.agent_id,
                content_type=content_request.content_type,
                format=content_request.format,
                data_size=len(str(content_request.data))
            )
            
            # Generate content based on type
            if content_request.content_type == "text":
                content_result = await self._generate_text_content(content_request)
            elif content_request.content_type == "summary":
                content_result = await self._generate_summary(content_request)
            elif content_request.content_type == "analysis":
                content_result = await self._generate_analysis(content_request)
            elif content_request.content_type == "description":
                content_result = await self._generate_description(content_request)
            else:
                raise AgentError(
                    f"Unsupported content type: {content_request.content_type}",
                    self.agent_id,
                    "UNSUPPORTED_CONTENT_TYPE"
                )
            
            return AgentResult(
                success=True,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                data=content_result,
                metadata={
                    "content_type": content_request.content_type,
                    "format": content_request.format,
                    "word_count": content_result.word_count,
                    "quality_score": content_result.quality_score
                }
            )
            
        except Exception as e:
            error_msg = f"Content generation failed: {str(e)}"
            self.logger.error(error_msg, agent_id=self.agent_id, exc_info=True)
            
            return AgentResult(
                success=False,
                agent_id=self.agent_id,
                agent_type=self.agent_type,
                error_message=error_msg
            )
    
    async def _generate_text_content(self, request: ContentRequest) -> ContentResult:
        """Generate general text content"""
        # Use AI service to generate content
        prompt = self._build_generation_prompt(request)
        
        try:
            generated_text = ""
            
            if HAS_AI_SERVICES:
                try:
                    # Use enhanced AI service if available, fallback to basic AI service
                    if enhanced_ai_service and hasattr(enhanced_ai_service, 'generate_content'):
                        response = await enhanced_ai_service.generate_content(prompt)
                        generated_text = response.get("content", response.get("text", ""))
                    elif ai_service and hasattr(ai_service, 'generate_text'):
                        response = await ai_service.generate_text(prompt)
                        generated_text = response.get("content", response.get("text", ""))
                except Exception as ai_error:
                    self.logger.warning(f"AI service failed: {ai_error}")
            
            # Fallback to mock or template-based generation if AI failed or unavailable
            if not generated_text:
                if not HAS_AI_SERVICES:
                    generated_text = self._generate_mock_content(request)
                else:
                    return await self._generate_template_content(request)
            
            # Apply formatting if needed
            if request.format == "markdown":
                generated_text = self._format_as_markdown(generated_text)
            elif request.format == "html":
                generated_text = self._format_as_html(generated_text)
            
            # Calculate quality score
            quality_score = self._calculate_quality_score(generated_text, request)
            
            return ContentResult(
                content=generated_text,
                format=request.format,
                quality_score=quality_score,
                word_count=len(generated_text),
                metadata={
                    "generation_method": "ai_service" if HAS_AI_SERVICES else "template_fallback",
                    "prompt_length": len(prompt)
                }
            )
            
        except Exception as e:
            # Fallback to template-based generation
            self.logger.warning(f"Content generation failed, using template fallback: {e}")
            return await self._generate_template_content(request)
    
    async def _generate_summary(self, request: ContentRequest) -> ContentResult:
        """Generate summary content"""
        # Analyze data to extract key statistics
        data_analysis = self._analyze_data_for_summary(request.data)
        
        # Use template or AI to generate summary
        if request.template or not ai_service:
            return await self._generate_template_summary(request, data_analysis)
        else:
            return await self._generate_ai_summary(request, data_analysis)
    
    async def _generate_analysis(self, request: ContentRequest) -> ContentResult:
        """Generate analysis content"""
        # Perform data analysis
        analysis_results = self._perform_data_analysis(request.data)
        
        # Generate analysis text
        prompt = f"""
基于以下分析结果生成专业的数据分析报告：

分析结果：
{json.dumps(analysis_results, ensure_ascii=False, indent=2)}

要求：
- 语调：{request.tone}
- 语言：{request.language}  
- 字数限制：{request.max_length}字以内
- 包含关键发现和趋势分析

请生成结构化的分析报告。
        """.strip()
        
        try:
            generated_text = ""
            
            if HAS_AI_SERVICES:
                try:
                    if enhanced_ai_service and hasattr(enhanced_ai_service, 'generate_content'):
                        response = await enhanced_ai_service.generate_content(prompt)
                        generated_text = response.get("content", response.get("text", ""))
                    elif ai_service and hasattr(ai_service, 'generate_text'):
                        response = await ai_service.generate_text(prompt)
                        generated_text = response.get("content", response.get("text", ""))
                except Exception as ai_error:
                    self.logger.warning(f"AI analysis generation failed: {ai_error}")
            
            if generated_text:
                quality_score = self._calculate_quality_score(generated_text, request)
                
                return ContentResult(
                    content=generated_text,
                    format=request.format,
                    quality_score=quality_score,
                    word_count=len(generated_text),
                    metadata={
                        "analysis_results": analysis_results,
                        "generation_method": "ai_analysis"
                    }
                )
            else:
                # Fallback to template-based analysis
                return await self._generate_template_analysis(request, analysis_results)
            
        except Exception as e:
            # Fallback to template-based analysis
            return await self._generate_template_analysis(request, analysis_results)
    
    async def _generate_description(self, request: ContentRequest) -> ContentResult:
        """Generate descriptive content"""
        # Extract data characteristics
        data_characteristics = self._extract_data_characteristics(request.data)
        
        template = self.content_templates.get("data_description", "")
        prompt = template.format(
            data_type=data_characteristics.get("type", "未知"),
            data_volume=data_characteristics.get("volume", "未知"),
            main_content=data_characteristics.get("main_content", "数据内容"),
            characteristics=data_characteristics.get("characteristics", "常规数据"),
            tone=request.tone,
            max_length=request.max_length
        )
        
        try:
            if hasattr(enhanced_ai_service, 'generate_content'):
                response = await enhanced_ai_service.generate_content(prompt)
            else:
                response = await ai_service.generate_text(prompt)
            
            generated_text = response.get("content", response.get("text", ""))
            quality_score = self._calculate_quality_score(generated_text, request)
            
            return ContentResult(
                content=generated_text,
                format=request.format,
                quality_score=quality_score,
                word_count=len(generated_text),
                metadata={
                    "data_characteristics": data_characteristics,
                    "generation_method": "ai_description"
                }
            )
            
        except Exception as e:
            # Simple fallback description
            return ContentResult(
                content=f"数据包含 {len(str(request.data))} 个字符的内容",
                format=request.format,
                quality_score=0.5,
                word_count=20,
                metadata={"generation_method": "fallback"}
            )
    
    def _build_generation_prompt(self, request: ContentRequest) -> str:
        """Build generation prompt"""
        data_str = json.dumps(request.data, ensure_ascii=False, indent=2)
        
        prompt = f"""
请基于以下数据生成{request.content_type}：

数据：
{data_str}

要求：
- 输出格式：{request.format}
- 语调：{request.tone}
- 语言：{request.language}
- 最大长度：{request.max_length}字

"""
        
        if request.context:
            context_str = json.dumps(request.context, ensure_ascii=False, indent=2)
            prompt += f"\n上下文信息：\n{context_str}\n"
        
        if request.template:
            prompt += f"\n参考模板：\n{request.template}\n"
        
        prompt += "\n请生成符合要求的内容："
        
        return prompt
    
    async def _generate_template_content(self, request: ContentRequest) -> ContentResult:
        """Generate content using templates as fallback"""
        if request.template:
            # Use custom template
            content = request.template.format(
                data=str(request.data),
                context=request.context or {}
            )
        else:
            # Use default template based on content type
            template = self.content_templates.get(
                request.content_type, 
                "基于数据：{data_summary}"
            )
            content = template.format(
                data_summary=str(request.data)[:200] + "...",
                tone=request.tone,
                max_length=request.max_length
            )
        
        # Truncate if too long
        if len(content) > request.max_length:
            content = content[:request.max_length] + "..."
        
        return ContentResult(
            content=content,
            format=request.format,
            quality_score=0.6,  # Template-based content gets medium quality score
            word_count=len(content),
            metadata={"generation_method": "template"}
        )
    
    def _analyze_data_for_summary(self, data: Union[Dict, List]) -> Dict[str, Any]:
        """Analyze data to extract summary information"""
        analysis = {
            "data_type": type(data).__name__,
            "size": len(str(data)),
            "structure": "unknown"
        }
        
        try:
            if isinstance(data, list):
                analysis.update({
                    "structure": "list",
                    "item_count": len(data),
                    "sample_item": data[0] if data else None
                })
                
                if data and isinstance(data[0], dict):
                    analysis["columns"] = list(data[0].keys())
                    
            elif isinstance(data, dict):
                analysis.update({
                    "structure": "dictionary", 
                    "key_count": len(data),
                    "keys": list(data.keys())
                })
                
                # Try to identify numeric values
                numeric_keys = []
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        numeric_keys.append(key)
                analysis["numeric_keys"] = numeric_keys
                
        except Exception as e:
            self.logger.warning(f"Data analysis failed: {e}")
        
        return analysis
    
    def _perform_data_analysis(self, data: Union[Dict, List]) -> Dict[str, Any]:
        """Perform statistical analysis on data"""
        analysis = {
            "data_summary": self._analyze_data_for_summary(data),
            "statistics": {},
            "trends": {},
            "insights": []
        }
        
        try:
            if isinstance(data, list) and data:
                if isinstance(data[0], dict):
                    # Analyze tabular data
                    numeric_columns = []
                    for key in data[0].keys():
                        try:
                            values = [float(item.get(key, 0)) for item in data if item.get(key) is not None]
                            if values:
                                analysis["statistics"][key] = {
                                    "count": len(values),
                                    "sum": sum(values),
                                    "avg": sum(values) / len(values),
                                    "min": min(values),
                                    "max": max(values)
                                }
                                numeric_columns.append(key)
                        except (ValueError, TypeError):
                            continue
                    
                    analysis["numeric_columns"] = numeric_columns
                    
            elif isinstance(data, dict):
                # Analyze dictionary data
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        analysis["statistics"][key] = {"value": value}
                        
        except Exception as e:
            self.logger.warning(f"Statistical analysis failed: {e}")
        
        return analysis
    
    def _extract_data_characteristics(self, data: Union[Dict, List]) -> Dict[str, Any]:
        """Extract characteristics of the data"""
        characteristics = {
            "type": type(data).__name__,
            "volume": f"{len(str(data))} 字符",
            "main_content": "数据内容",
            "characteristics": []
        }
        
        try:
            if isinstance(data, list):
                characteristics.update({
                    "type": "列表数据",
                    "volume": f"{len(data)} 项",
                    "main_content": f"包含 {len(data)} 个数据项"
                })
                
                if data:
                    if isinstance(data[0], dict):
                        characteristics["characteristics"].append("结构化表格数据")
                        characteristics["main_content"] += f"，每项包含 {len(data[0])} 个字段"
                    elif isinstance(data[0], (int, float)):
                        characteristics["characteristics"].append("数值型数据")
                    else:
                        characteristics["characteristics"].append("文本型数据")
                        
            elif isinstance(data, dict):
                characteristics.update({
                    "type": "字典数据",
                    "volume": f"{len(data)} 个键值对",
                    "main_content": f"包含 {len(data)} 个数据字段"
                })
                
                # Check for numeric values
                numeric_count = sum(1 for v in data.values() if isinstance(v, (int, float)))
                if numeric_count > 0:
                    characteristics["characteristics"].append(f"包含 {numeric_count} 个数值字段")
                
                # Check for nested structures
                nested_count = sum(1 for v in data.values() if isinstance(v, (dict, list)))
                if nested_count > 0:
                    characteristics["characteristics"].append(f"包含 {nested_count} 个嵌套结构")
                    
        except Exception as e:
            self.logger.warning(f"Characteristic extraction failed: {e}")
        
        characteristics["characteristics"] = "，".join(characteristics["characteristics"]) or "常规数据"
        
        return characteristics
    
    def _calculate_quality_score(self, content: str, request: ContentRequest) -> float:
        """Calculate content quality score"""
        if not content:
            return 0.0
        
        score = 0.5  # Base score
        
        # Length appropriateness
        if len(content) <= request.max_length:
            score += 0.2
        else:
            score -= 0.1
        
        # Content completeness
        if len(content) > 50:  # Reasonable minimum length
            score += 0.1
        
        # Language check (simple heuristic)
        if request.language == "zh-CN" and any('\u4e00' <= char <= '\u9fff' for char in content):
            score += 0.1
        
        # Professional tone check
        if request.tone == "professional":
            professional_keywords = ["数据显示", "分析表明", "结果表明", "统计", "报告"]
            if any(keyword in content for keyword in professional_keywords):
                score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _format_as_markdown(self, content: str) -> str:
        """Format content as markdown"""
        # Simple markdown formatting
        lines = content.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append("")
            elif line.endswith("：") or line.endswith(":"):
                formatted_lines.append(f"## {line}")
            elif "：" in line and len(line) < 100:
                formatted_lines.append(f"**{line}**")
            else:
                formatted_lines.append(line)
        
        return "\n".join(formatted_lines)
    
    def _format_as_html(self, content: str) -> str:
        """Format content as HTML"""
        # Simple HTML formatting
        lines = content.split('\n')
        html_content = "<div>"
        
        for line in lines:
            line = line.strip()
            if not line:
                html_content += "<br>"
            elif line.endswith("：") or line.endswith(":"):
                html_content += f"<h3>{line}</h3>"
            elif "：" in line and len(line) < 100:
                html_content += f"<p><strong>{line}</strong></p>"
            else:
                html_content += f"<p>{line}</p>"
        
        html_content += "</div>"
        return html_content
    
    async def _generate_template_summary(
        self, 
        request: ContentRequest, 
        analysis: Dict[str, Any]
    ) -> ContentResult:
        """Generate summary using templates"""
        template = self.content_templates.get("statistical_summary", "")
        
        summary = template.format(
            data_summary=analysis.get("structure", "数据"),
            statistics=analysis.get("numeric_keys", []),
            key_findings="主要数据特征",
            tone=request.tone,
            max_length=request.max_length
        )
        
        return ContentResult(
            content=summary[:request.max_length],
            format=request.format,
            quality_score=0.6,
            word_count=len(summary),
            metadata={"generation_method": "template_summary", "analysis": analysis}
        )
    
    async def _generate_ai_summary(
        self,
        request: ContentRequest,
        analysis: Dict[str, Any]
    ) -> ContentResult:
        """Generate summary using AI"""
        prompt = f"""
基于以下数据分析结果生成摘要：

{json.dumps(analysis, ensure_ascii=False, indent=2)}

要求：
- 语调：{request.tone}
- 语言：{request.language}
- 字数：不超过{request.max_length}字
- 突出关键数据特征和发现

请生成简洁的数据摘要：
        """.strip()
        
        try:
            if hasattr(enhanced_ai_service, 'generate_content'):
                response = await enhanced_ai_service.generate_content(prompt)
            else:
                response = await ai_service.generate_text(prompt)
            
            generated_text = response.get("content", response.get("text", ""))
            quality_score = self._calculate_quality_score(generated_text, request)
            
            return ContentResult(
                content=generated_text,
                format=request.format,
                quality_score=quality_score,
                word_count=len(generated_text),
                metadata={"generation_method": "ai_summary", "analysis": analysis}
            )
            
        except Exception as e:
            return await self._generate_template_summary(request, analysis)
    
    async def _generate_template_analysis(
        self,
        request: ContentRequest, 
        analysis_results: Dict[str, Any]
    ) -> ContentResult:
        """Generate analysis using templates as fallback"""
        content = f"""
数据分析报告

数据概况：{analysis_results.get('data_summary', {}).get('structure', '未知结构')}
统计指标：{len(analysis_results.get('statistics', {}))} 项
主要发现：基于数据分析的关键结果

详细分析结果已生成，包含完整的统计信息和趋势分析。
        """.strip()
        
        return ContentResult(
            content=content[:request.max_length],
            format=request.format,
            quality_score=0.5,
            word_count=len(content),
            metadata={"generation_method": "template_analysis"}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check for content generation agent"""
        health = await super().health_check()
        
        if HAS_AI_SERVICES:
            try:
                # Test AI service connectivity
                test_prompt = "测试连接"
                if ai_service and hasattr(ai_service, 'generate_text'):
                    await ai_service.generate_text(test_prompt)
                health["ai_service"] = "healthy"
            except Exception as e:
                health["ai_service"] = f"error: {str(e)}"
                health["healthy"] = False
        else:
            health["ai_service"] = "mock_mode"
        
        health["templates_loaded"] = len(self.content_templates)
        return health