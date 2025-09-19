"""
文档装配工具（docxtpl 优先，提供 Markdown/HTML 预览降级）

将文本块、图表与上下文合成为 docx/markdown/html
注意：若 docxtpl 不可用或未提供模板，则返回可预览内容，不强制写盘
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from ..core.tools.registry import BaseTool
from ..types import ToolSafetyLevel

try:
    from docxtpl import DocxTemplate
    DOCXTPL_AVAILABLE = True
except Exception:
    DOCXTPL_AVAILABLE = False


def _is_safe_output_path(path_str: str) -> bool:
    try:
        p = Path(path_str).resolve()
        cwd = Path.cwd().resolve()
        home = Path.home().resolve()
        return str(p).startswith(str(cwd)) or str(p).startswith(str(home))
    except Exception:
        return False


class DocAssemblerTool(BaseTool):
    """文档装配工具（docxtpl/Markdown/HTML）"""

    def __init__(self):
        super().__init__(
            name="doc_assembler",
            description="将文本块/图表与上下文合成为文档（docx/md/html）"
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        fmt = (input_data.get("format") or "md").lower()
        template_path = input_data.get("template_path")
        output_path = input_data.get("output_path")
        context_blocks: List[Dict[str, Any]] = input_data.get("context_blocks", [])
        charts: List[Dict[str, Any]] = input_data.get("charts", [])
        extra_context: Dict[str, Any] = input_data.get("context", {})

        # 预览内容（Markdown）
        preview_lines: List[str] = []
        used_placeholders: List[str] = []
        for block in context_blocks:
            btype = block.get("type", "text")
            if btype == "text":
                title = block.get("title")
                if title:
                    preview_lines.append(f"\n## {title}")
                preview_lines.append(block.get("content", ""))
            elif btype == "chart":
                title = block.get("title", "图表")
                preview_lines.append(f"\n### {title}")
                preview_lines.append("(Chart rendered via ECharts on client)")
            elif btype == "placeholder":
                key = block.get("key")
                used_placeholders.append(key)
                preview_lines.append(f"{{{{ {key} }}}}")

        preview = "\n".join(preview_lines).strip()

        # docx 写盘（可选）
        if fmt == "docx" and DOCXTPL_AVAILABLE and template_path:
            try:
                tpl = DocxTemplate(template_path)
                # 组合上下文（将图表/块汇总为 context）
                doc_context = {
                    **extra_context,
                    "content_blocks": context_blocks,
                    "charts": charts,
                    "generated_at": datetime.now().isoformat()
                }
                tpl.render(doc_context)

                if output_path and _is_safe_output_path(output_path):
                    outp = Path(output_path)
                    outp.parent.mkdir(parents=True, exist_ok=True)
                    tpl.save(str(outp))
                    return {
                        "success": True,
                        "output_path": str(outp),
                        "used_placeholders": used_placeholders,
                        "format": "docx",
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    # 未提供安全路径，返回预览
                    return {
                        "success": True,
                        "content_preview": preview,
                        "used_placeholders": used_placeholders,
                        "format": "docx_preview",
                        "timestamp": datetime.now().isoformat(),
                        "warning": "No safe output_path provided, returned preview instead"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "content_preview": preview,
                    "format": "docx",
                    "timestamp": datetime.now().isoformat(),
                }

        # 非 docx 或无 docxtpl：返回 Markdown/HTML 预览
        if fmt == "html":
            # 极简 Markdown->HTML 包装（不做转换，交由前端/后续工具）
            html = preview.replace("\n", "<br/>\n")
            return {
                "success": True,
                "content_preview": html,
                "format": "html",
                "used_placeholders": used_placeholders,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "success": True,
                "content_preview": preview,
                "format": "md",
                "used_placeholders": used_placeholders,
                "timestamp": datetime.now().isoformat(),
            }

    def get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {"type": "string", "enum": ["md", "html", "docx"]},
                "template_path": {"type": "string"},
                "output_path": {"type": "string"},
                "context_blocks": {"type": "array", "items": {"type": "object"}},
                "charts": {"type": "array", "items": {"type": "object"}},
                "context": {"type": "object"},
            },
            "required": ["context_blocks"],
        }

    def get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "output_path": {"type": "string"},
                "content_preview": {"type": "string"},
                "used_placeholders": {"type": "array", "items": {"type": "string"}},
                "format": {"type": "string"},
            },
            "required": ["success", "format"],
        }

    def get_safety_level(self) -> ToolSafetyLevel:
        return ToolSafetyLevel.CAUTIOUS

    def get_capabilities(self) -> List[str]:
        return ["document_assembly", "docx_generation", "preview_generation"]

