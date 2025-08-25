"""
混合占位符管理器
结合实时解析和持久化存储的优势
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from uuid import uuid4
import hashlib
import logging

from app.services.domain.reporting.document_pipeline import TemplateParser
from app.models.template_placeholder import TemplatePlaceholder
from app.crud.crud_template_placeholder import template_placeholder as crud_placeholder


class HybridPlaceholderManager:
    """
    混合占位符管理器
    
    工作流程：
    1. 重新解析：从模板内容实时解析 → 存储/更新数据库
    2. Agent分析：基于存储的占位符 → 生成SQL → 验证
    3. 数据连接：执行SQL → 获取真实数据 → 渲染图表/表格
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.parser = TemplateParser()
        self.logger = logging.getLogger(__name__)
    
    def parse_and_store_placeholders(
        self, 
        template_id: str, 
        template_content: str,
        force_reparse: bool = False
    ) -> Dict[str, Any]:
        """
        解析模板内容并存储占位符到数据库
        
        Args:
            template_id: 模板ID
            template_content: 模板内容（可能是十六进制）
            force_reparse: 是否强制重新解析
            
        Returns:
            解析结果和存储状态
        """
        try:
            # 1. 检查是否需要重新解析
            if not force_reparse:
                existing_placeholders = crud_placeholder.get_by_template(self.db, template_id)
                if existing_placeholders:
                    self.logger.info(f"模板 {template_id} 已有 {len(existing_placeholders)} 个占位符，跳过解析")
                    return {
                        "success": True,
                        "action": "skipped",
                        "placeholders_count": len(existing_placeholders),
                        "message": "占位符已存在，使用现有数据"
                    }
            
            # 2. 实时解析占位符
            self.logger.info(f"开始解析模板 {template_id} 的占位符")
            parsed_placeholders = self.parser.extract_placeholders(template_content)
            
            if not parsed_placeholders:
                return {
                    "success": False,
                    "error": "未从模板中提取到任何占位符",
                    "placeholders_count": 0
                }
            
            # 3. 清理旧数据（如果强制重新解析）
            if force_reparse:
                crud_placeholder.delete_by_template(self.db, template_id)
                self.logger.info(f"清理模板 {template_id} 的旧占位符配置")
            
            # 4. 转换并存储占位符
            stored_count = 0
            stored_placeholders = []
            
            for index, parsed in enumerate(parsed_placeholders):
                # 生成稳定的占位符标识
                placeholder_key = self._generate_stable_key(parsed)
                
                # 检查是否已存在（基于内容hash）
                existing = crud_placeholder.get_by_content_hash(
                    self.db, template_id, placeholder_key
                )
                
                if existing and not force_reparse:
                    stored_placeholders.append(existing)
                    continue
                
                # 创建新的占位符配置
                placeholder_data = {
                    "id": str(uuid4()),
                    "template_id": template_id,
                    "placeholder_name": self._generate_friendly_name(parsed),
                    "placeholder_text": parsed.get("full_text", parsed.get("name", "")),
                    "placeholder_type": parsed.get("type", "text"),
                    "content_type": parsed.get("content_type", "text"),
                    "description": parsed.get("description", ""),
                    "content_hash": placeholder_key,
                    
                    # 解析状态
                    "agent_analyzed": False,
                    "sql_validated": False,
                    "confidence_score": parsed.get("confidence", 0.8),
                    
                    # ETL配置
                    "execution_order": index + 1,
                    "cache_ttl_hours": 24,
                    "is_active": True,
                    
                    # 元数据
                    "original_type": parsed.get("type", "text"),
                    "extracted_description": parsed.get("description", ""),
                    "parsing_metadata": {
                        "parser_version": "v2.0",
                        "extraction_method": "enhanced_parser",
                        "confidence_score": parsed.get("confidence", 0.8),
                        "content_type": parsed.get("content_type", "text")
                    }
                }
                
                if existing:
                    # 更新现有记录
                    updated = crud_placeholder.update(self.db, db_obj=existing, obj_in=placeholder_data)
                    stored_placeholders.append(updated)
                else:
                    # 创建新记录
                    created = crud_placeholder.create(self.db, obj_in=placeholder_data)
                    stored_placeholders.append(created)
                    stored_count += 1
            
            self.logger.info(f"模板 {template_id} 解析完成：{len(parsed_placeholders)} 个占位符，{stored_count} 个新增")
            
            return {
                "success": True,
                "action": "parsed" if not force_reparse else "reparsed",
                "total_parsed": len(parsed_placeholders),
                "newly_stored": stored_count,
                "total_stored": len(stored_placeholders),
                "placeholders": [self._serialize_placeholder(p) for p in stored_placeholders],
                "message": f"成功解析并存储 {len(parsed_placeholders)} 个占位符"
            }
            
        except Exception as e:
            self.logger.error(f"解析模板占位符失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "placeholders_count": 0
            }
    
    def get_template_placeholders(
        self, 
        template_id: str,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """获取模板的所有占位符配置"""
        try:
            placeholders = crud_placeholder.get_by_template(
                self.db, 
                template_id, 
                include_inactive=include_inactive
            )
            
            return [self._serialize_placeholder(p) for p in placeholders]
            
        except Exception as e:
            self.logger.error(f"获取模板占位符失败: {e}")
            return []
    
    def _generate_stable_key(self, parsed_placeholder: Dict[str, Any]) -> str:
        """生成稳定的占位符标识键"""
        # 基于占位符的核心内容生成稳定的hash
        key_content = f"{parsed_placeholder.get('type', '')}_" + \
                     f"{parsed_placeholder.get('description', '')}_" + \
                     f"{parsed_placeholder.get('name', '')}"
        
        return hashlib.md5(key_content.encode()).hexdigest()[:16]
    
    def _generate_friendly_name(self, parsed_placeholder: Dict[str, Any]) -> str:
        """生成用户友好的占位符名称"""
        # 优先使用描述，其次是名称，最后使用类型
        description = parsed_placeholder.get("description", "")
        name = parsed_placeholder.get("name", "")
        ptype = parsed_placeholder.get("type", "占位符")
        
        if description and description not in ["", "N/A"]:
            # 如果描述包含"变量:"这样的前缀，去掉它
            clean_description = description.replace("变量: ", "").replace("简单变量: ", "")
            if len(clean_description) <= 50:  # 合理长度
                return clean_description
        
        if name and not name.startswith(ptype + "_"):
            return name
        
        # 最后降级到类型
        return f"{ptype}占位符"
    
    def _serialize_placeholder(self, placeholder: TemplatePlaceholder) -> Dict[str, Any]:
        """序列化占位符配置为API响应格式"""
        return {
            "id": placeholder.id,
            "template_id": placeholder.template_id,
            "placeholder_name": placeholder.placeholder_name,
            "placeholder_text": placeholder.placeholder_text,
            "placeholder_type": placeholder.placeholder_type,
            "content_type": placeholder.content_type,
            "description": placeholder.description or placeholder.extracted_description,
            
            # 分析状态
            "agent_analyzed": placeholder.agent_analyzed,
            "sql_validated": placeholder.sql_validated,
            "confidence_score": placeholder.confidence_score,
            "generated_sql": placeholder.generated_sql,
            
            # ETL配置
            "execution_order": placeholder.execution_order,
            "cache_ttl_hours": placeholder.cache_ttl_hours,
            "is_active": placeholder.is_active,
            
            # 时间戳
            "created_at": placeholder.created_at.isoformat() if placeholder.created_at else None,
            "updated_at": placeholder.updated_at.isoformat() if placeholder.updated_at else None,
            "analyzed_at": placeholder.analyzed_at.isoformat() if placeholder.analyzed_at else None,
            
            # 元数据
            "parsing_metadata": placeholder.parsing_metadata or {}
        }


def create_hybrid_placeholder_manager(db: Session) -> HybridPlaceholderManager:
    """创建混合占位符管理器实例"""
    return HybridPlaceholderManager(db)