"""
纯数据库驱动的增强模板解析器
基于纯数据库驱动架构实现的占位符解析和持久化功能
替代被禁用的IAOP/MCP版本
"""

import logging
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.template_placeholder import TemplatePlaceholder

logger = logging.getLogger(__name__)


class PureDatabaseEnhancedTemplateParser:
    """纯数据库驱动的增强模板解析器"""
    
    def __init__(self, db: Session, user_id: str):
        if not user_id:
            raise ValueError("user_id is required for Pure Database Enhanced Template Parser")
        
        self.db = db
        self.user_id = user_id
        logger.info(f"初始化纯数据库驱动模板解析器，用户: {user_id}")
    
    async def parse_template(self, template_content: str) -> Dict[str, Any]:
        """
        解析模板内容，提取占位符
        
        Args:
            template_content: 模板内容
            
        Returns:
            解析结果
        """
        try:
            # 使用正则表达式提取占位符
            import re
            
            # 支持多种占位符格式
            patterns = [
                r'\{\{([^}]+)\}\}',  # {{placeholder}}
                r'\$\{([^}]+)\}',    # ${placeholder}
                r'%([^%]+)%',        # %placeholder%
            ]
            
            placeholders = []
            placeholder_set = set()  # 用于去重
            
            for pattern in patterns:
                matches = re.findall(pattern, template_content)
                
                for match in matches:
                    placeholder_name = match.strip()
                    
                    # 跳过已处理的占位符
                    if placeholder_name in placeholder_set:
                        continue
                    
                    placeholder_set.add(placeholder_name)
                    
                    # 分析占位符类型和属性
                    placeholder_analysis = self._analyze_placeholder(placeholder_name, template_content)
                    
                    placeholder_info = {
                        "name": placeholder_name,
                        "text": f"{{{{{match}}}}}",  # 统一为{{}}格式
                        "type": placeholder_analysis["type"],
                        "complexity": placeholder_analysis["complexity"],
                        "execution_order": len(placeholders) + 1,
                        "requires_analysis": True,
                        "metadata": placeholder_analysis["metadata"]
                    }
                    placeholders.append(placeholder_info)
            
            # 根据依赖关系调整执行顺序
            placeholders = self._optimize_execution_order(placeholders)
            
            return {
                "success": True,
                "placeholders": placeholders,
                "total_count": len(placeholders),
                "unique_placeholders": len(placeholder_set),
                "parser_version": "pure_database_v1.0"
            }
            
        except Exception as e:
            logger.error(f"模板解析失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "placeholders": []
            }
    
    def _analyze_placeholder(self, placeholder_name: str, template_content: str) -> Dict[str, Any]:
        """分析占位符类型和属性"""
        name_lower = placeholder_name.lower()
        
        # 分析类型
        placeholder_type = "data"  # 默认类型
        complexity = "medium"
        metadata = {}
        
        # 时间相关
        if any(word in name_lower for word in ['date', 'time', '日期', '时间', '月份', '年份', 'year', 'month', 'day']):
            placeholder_type = "temporal"
            metadata["time_format"] = self._detect_time_format(placeholder_name)
            complexity = "simple"
        
        # 聚合相关
        elif any(word in name_lower for word in ['sum', 'count', 'avg', 'max', 'min', 'total', '总计', '平均', '最大', '最小', '求和']):
            placeholder_type = "aggregation"
            metadata["aggregation_type"] = self._detect_aggregation_type(placeholder_name)
            complexity = "complex"
        
        # 过滤相关
        elif any(word in name_lower for word in ['filter', 'where', 'condition', '筛选', '条件', '过滤']):
            placeholder_type = "filter"
            metadata["filter_logic"] = self._analyze_filter_logic(placeholder_name)
            complexity = "complex"
        
        # 计算相关
        elif any(word in name_lower for word in ['calc', 'compute', '计算', 'formula', '公式']):
            placeholder_type = "calculation"
            complexity = "complex"
        
        # 用户相关
        elif any(word in name_lower for word in ['user', 'name', '用户', '姓名', 'account', '账户']):
            placeholder_type = "user"
            complexity = "simple"
        
        # 配置相关
        elif any(word in name_lower for word in ['config', 'setting', '配置', '设置']):
            placeholder_type = "configuration"
            complexity = "simple"
        
        # 分析复杂度
        if any(char in placeholder_name for char in ['(', ')', '[', ']', ':', '|']):
            complexity = "complex"
        elif len(placeholder_name.split('_')) > 3 or len(placeholder_name.split('.')) > 2:
            complexity = "medium"
        
        # 检测参数
        if '(' in placeholder_name and ')' in placeholder_name:
            metadata["has_parameters"] = True
            metadata["parameters"] = self._extract_parameters(placeholder_name)
        
        return {
            "type": placeholder_type,
            "complexity": complexity,
            "metadata": metadata
        }
    
    def _detect_time_format(self, placeholder_name: str) -> str:
        """检测时间格式"""
        name_lower = placeholder_name.lower()
        if 'yyyy' in name_lower or 'year' in name_lower:
            return "YYYY"
        elif 'mm' in name_lower or 'month' in name_lower:
            return "YYYY-MM"
        elif 'dd' in name_lower or 'day' in name_lower:
            return "YYYY-MM-DD"
        else:
            return "YYYY-MM-DD HH:mm:ss"
    
    def _detect_aggregation_type(self, placeholder_name: str) -> str:
        """检测聚合类型"""
        name_lower = placeholder_name.lower()
        if any(word in name_lower for word in ['sum', '总计', '求和']):
            return "SUM"
        elif any(word in name_lower for word in ['count', '计数', '数量']):
            return "COUNT"
        elif any(word in name_lower for word in ['avg', '平均']):
            return "AVG"
        elif any(word in name_lower for word in ['max', '最大']):
            return "MAX"
        elif any(word in name_lower for word in ['min', '最小']):
            return "MIN"
        else:
            return "SUM"
    
    def _analyze_filter_logic(self, placeholder_name: str) -> Dict[str, Any]:
        """分析过滤逻辑"""
        return {
            "has_conditions": True,
            "estimated_complexity": "medium"
        }
    
    def _extract_parameters(self, placeholder_name: str) -> List[str]:
        """提取参数"""
        import re
        param_match = re.search(r'\(([^)]+)\)', placeholder_name)
        if param_match:
            params_str = param_match.group(1)
            return [p.strip() for p in params_str.split(',')]
        return []
    
    def _optimize_execution_order(self, placeholders: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化执行顺序"""
        # 简单的优先级排序：配置 > 用户 > 时间 > 数据 > 过滤 > 聚合 > 计算
        type_priority = {
            "configuration": 1,
            "user": 2,
            "temporal": 3,
            "data": 4,
            "filter": 5,
            "aggregation": 6,
            "calculation": 7
        }
        
        # 按类型优先级和复杂度排序
        sorted_placeholders = sorted(placeholders, key=lambda x: (
            type_priority.get(x["type"], 5),
            {"simple": 1, "medium": 2, "complex": 3}.get(x["complexity"], 2)
        ))
        
        # 重新分配执行顺序
        for i, placeholder in enumerate(sorted_placeholders):
            placeholder["execution_order"] = i + 1
        
        return sorted_placeholders
    
    async def parse_and_store_template_placeholders(
        self,
        template_id: str,
        template_content: str,
        force_reparse: bool = False
    ) -> Dict[str, Any]:
        """
        解析模板并持久化占位符
        
        Args:
            template_id: 模板ID
            template_content: 模板内容
            force_reparse: 是否强制重新解析
            
        Returns:
            解析结果统计
        """
        try:
            logger.info(f"开始解析模板占位符: {template_id}, 用户: {self.user_id}")
            
            # 1. 检查是否已存在占位符配置
            if not force_reparse:
                existing_count = await self._count_existing_placeholders(template_id)
                if existing_count > 0:
                    logger.info(f"模板已存在 {existing_count} 个占位符配置，跳过重新解析")
                    return await self._get_existing_placeholder_info(template_id)
            
            # 2. 清理现有配置（如果是强制重新解析）
            if force_reparse:
                await self._cleanup_existing_placeholders(template_id)
            
            # 3. 解析模板内容
            parse_result = await self.parse_template(template_content)
            
            if not parse_result["success"]:
                return parse_result
            
            # 4. 持久化占位符配置
            stored_count = 0
            new_placeholders = 0
            updated_placeholders = 0
            
            for placeholder_info in parse_result["placeholders"]:
                try:
                    # 生成内容哈希
                    content_hash = self._generate_content_hash(placeholder_info["text"])
                    
                    # 检查是否已存在相同的占位符
                    existing_placeholder = self.db.query(TemplatePlaceholder).filter(
                        TemplatePlaceholder.template_id == template_id,
                        TemplatePlaceholder.content_hash == content_hash
                    ).first()
                    
                    if existing_placeholder and not force_reparse:
                        # 更新为活跃状态并刷新配置
                        existing_placeholder.is_active = True
                        existing_placeholder.placeholder_type = placeholder_info["type"]
                        existing_placeholder.execution_order = placeholder_info["execution_order"]
                        existing_placeholder.agent_config = {
                            "complexity": placeholder_info["complexity"],
                            "priority": self._calculate_priority(placeholder_info),
                            "requires_analysis": placeholder_info["requires_analysis"],
                            "metadata": placeholder_info["metadata"],
                            "parser_version": "pure_database_v1.0",
                            "user_id": self.user_id
                        }
                        updated_placeholders += 1
                        stored_count += 1
                    else:
                        # 创建新的占位符记录
                        placeholder_record = TemplatePlaceholder(
                            template_id=template_id,
                            placeholder_name=placeholder_info["name"],
                            placeholder_text=placeholder_info["text"],
                            placeholder_type=placeholder_info["type"],
                            content_type="text",
                            content_hash=content_hash,
                            execution_order=placeholder_info["execution_order"],
                            is_active=True,
                            agent_analyzed=False,
                            sql_validated=False,
                            confidence_score=0.0,
                            agent_config={
                                "complexity": placeholder_info["complexity"],
                                "priority": self._calculate_priority(placeholder_info),
                                "requires_analysis": placeholder_info["requires_analysis"],
                                "metadata": placeholder_info["metadata"],
                                "parser_version": "pure_database_v1.0",
                                "user_id": self.user_id
                            },
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        self.db.add(placeholder_record)
                        new_placeholders += 1
                        stored_count += 1
                
                except Exception as e:
                    logger.error(f"保存占位符失败: {placeholder_info['name']}, 错误: {e}")
            
            # 5. 提交数据库更改
            self.db.commit()
            
            logger.info(f"模板解析完成: {template_id}, 存储 {stored_count} 个占位符 (新增: {new_placeholders}, 更新: {updated_placeholders})")
            
            return {
                "success": True,
                "template_id": template_id,
                "total_placeholders": parse_result["total_count"],
                "stored_placeholders": stored_count,
                "new_placeholders": new_placeholders,
                "updated_placeholders": updated_placeholders,
                "skipped_placeholders": parse_result["total_count"] - stored_count,
                "message": "模板占位符解析并存储成功",
                "parser_version": "pure_database_v1.0",
                "user_id": self.user_id
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"模板解析失败: {template_id}, 错误: {str(e)}")
            return {
                "success": False,
                "template_id": template_id,
                "error": str(e),
                "total_placeholders": 0,
                "stored_placeholders": 0,
                "user_id": self.user_id
            }
    
    def _calculate_priority(self, placeholder_info: Dict[str, Any]) -> int:
        """计算占位符优先级"""
        base_priority = 5
        
        # 根据类型调整
        type_adjustments = {
            "configuration": -2,  # 高优先级
            "user": -1,
            "temporal": 0,
            "data": 1,
            "filter": 1,
            "aggregation": 2,
            "calculation": 2  # 低优先级
        }
        
        # 根据复杂度调整
        complexity_adjustments = {
            "simple": -1,
            "medium": 0,
            "complex": 1
        }
        
        priority = base_priority
        priority += type_adjustments.get(placeholder_info["type"], 0)
        priority += complexity_adjustments.get(placeholder_info["complexity"], 0)
        
        return max(1, min(10, priority))  # 限制在1-10之间
    
    def _generate_content_hash(self, content: str) -> str:
        """生成内容哈希"""
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _count_existing_placeholders(self, template_id: str) -> int:
        """统计现有占位符数量"""
        return self.db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == template_id,
            TemplatePlaceholder.is_active == True
        ).count()
    
    async def _get_existing_placeholder_info(self, template_id: str) -> Dict[str, Any]:
        """获取现有占位符信息"""
        placeholders = self.db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == template_id,
            TemplatePlaceholder.is_active == True
        ).order_by(TemplatePlaceholder.execution_order).all()
        
        placeholder_list = []
        type_distribution = {}
        requires_analysis = 0
        
        for p in placeholders:
            placeholder_info = {
                "id": str(p.id),
                "name": p.placeholder_name,
                "text": p.placeholder_text,
                "type": p.placeholder_type,
                "content_type": p.content_type,
                "execution_order": p.execution_order,
                "agent_analyzed": p.agent_analyzed,
                "sql_validated": p.sql_validated,
                "confidence_score": p.confidence_score,
                "metadata": p.agent_config.get("metadata", {}) if p.agent_config else {}
            }
            placeholder_list.append(placeholder_info)
            
            # 统计类型分布
            ptype = p.placeholder_type
            type_distribution[ptype] = type_distribution.get(ptype, 0) + 1
            
            # 统计需要分析的数量
            if not p.agent_analyzed:
                requires_analysis += 1
        
        return {
            "success": True,
            "template_id": template_id,
            "total_placeholders": len(placeholder_list),
            "stored_placeholders": len(placeholder_list),
            "placeholders": placeholder_list,
            "type_distribution": type_distribution,
            "requires_agent_analysis": requires_analysis,
            "message": "使用现有占位符配置",
            "user_id": self.user_id
        }
    
    async def _cleanup_existing_placeholders(self, template_id: str):
        """清理现有占位符配置"""
        try:
            # 标记为非活跃而不是删除，保留历史数据
            self.db.query(TemplatePlaceholder).filter(
                TemplatePlaceholder.template_id == template_id
            ).update({
                "is_active": False,
                "updated_at": datetime.utcnow()
            })
            
            self.db.commit()
            logger.info(f"清理现有占位符配置: {template_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"清理占位符配置失败: {template_id}, 错误: {str(e)}")
            raise
    
    async def get_template_placeholder_configs(
        self,
        template_id: str,
        include_analysis_status: bool = True
    ) -> List[Dict[str, Any]]:
        """获取模板的占位符配置"""
        placeholders = self.db.query(TemplatePlaceholder).filter(
            TemplatePlaceholder.template_id == template_id,
            TemplatePlaceholder.is_active == True
        ).order_by(TemplatePlaceholder.execution_order).all()
        
        result = []
        for p in placeholders:
            placeholder_info = {
                "id": str(p.id),
                "name": p.placeholder_name,
                "text": p.placeholder_text,
                "type": p.placeholder_type,
                "content_type": p.content_type,
                "execution_order": p.execution_order,
                "target_database": p.target_database,
                "target_table": p.target_table,
                "required_fields": p.required_fields or [],
                "generated_sql": p.generated_sql,
                "confidence_score": p.confidence_score,
                "agent_config": p.agent_config or {},
                "metadata": p.agent_config.get("metadata", {}) if p.agent_config else {}
            }
            
            if include_analysis_status:
                placeholder_info.update({
                    "agent_analyzed": p.agent_analyzed,
                    "sql_validated": p.sql_validated,
                    "analyzed_at": p.analyzed_at.isoformat() if p.analyzed_at else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None
                })
            
            result.append(placeholder_info)
        
        return result


# 工厂函数
def create_pure_database_enhanced_template_parser(db: Session, user_id: str) -> PureDatabaseEnhancedTemplateParser:
    """创建纯数据库驱动增强模板解析器实例"""
    return PureDatabaseEnhancedTemplateParser(db, user_id)