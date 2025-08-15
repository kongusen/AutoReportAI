"""
数据类型标准化工具
负责将不同数据库的数据类型标准化为统一格式
"""

import re
from typing import Optional
from app.models.table_schema import ColumnType


class TypeNormalizer:
    """数据类型标准化工具"""
    
    def normalize_type(self, column_type: str) -> ColumnType:
        """
        标准化列数据类型
        
        Args:
            column_type: 原始数据类型字符串
            
        Returns:
            标准化的数据类型枚举
        """
        type_lower = column_type.lower()
        
        # 数值类型
        if any(t in type_lower for t in ["int", "integer"]):
            return ColumnType.INT
        elif "bigint" in type_lower:
            return ColumnType.BIGINT
        elif "float" in type_lower:
            return ColumnType.FLOAT
        elif "double" in type_lower:
            return ColumnType.DOUBLE
        elif "decimal" in type_lower:
            return ColumnType.DECIMAL
        
        # 字符串类型
        elif "varchar" in type_lower:
            return ColumnType.VARCHAR
        elif "char" in type_lower:
            return ColumnType.CHAR
        elif "text" in type_lower:
            return ColumnType.TEXT
        
        # 日期时间类型
        elif "date" in type_lower:
            return ColumnType.DATE
        elif "datetime" in type_lower:
            return ColumnType.DATETIME
        elif "timestamp" in type_lower:
            return ColumnType.TIMESTAMP
        
        # 布尔类型
        elif "bool" in type_lower:
            return ColumnType.BOOLEAN
        
        # 其他类型
        elif "json" in type_lower:
            return ColumnType.JSON
        elif "array" in type_lower:
            return ColumnType.ARRAY
        else:
            return ColumnType.UNKNOWN
    
    def extract_column_size(self, column_type: str) -> Optional[int]:
        """
        从列类型中提取大小信息
        
        Args:
            column_type: 列类型字符串
            
        Returns:
            列大小，如果没有则返回None
        """
        match = re.search(r'\((\d+)\)', column_type)
        return int(match.group(1)) if match else None
    
    def extract_precision(self, column_type: str) -> Optional[int]:
        """
        从decimal类型中提取精度
        
        Args:
            column_type: 列类型字符串
            
        Returns:
            精度，如果不是decimal类型则返回None
        """
        match = re.search(r'decimal\((\d+)', column_type)
        return int(match.group(1)) if match else None
    
    def extract_scale(self, column_type: str) -> Optional[int]:
        """
        从decimal类型中提取小数位数
        
        Args:
            column_type: 列类型字符串
            
        Returns:
            小数位数，如果不是decimal类型则返回None
        """
        match = re.search(r'decimal\(\d+,(\d+)\)', column_type)
        return int(match.group(1)) if match else None
    
    def is_numeric_type(self, column_type: ColumnType) -> bool:
        """
        判断是否为数值类型
        
        Args:
            column_type: 标准化的数据类型
            
        Returns:
            是否为数值类型
        """
        numeric_types = [
            ColumnType.INT,
            ColumnType.BIGINT,
            ColumnType.FLOAT,
            ColumnType.DOUBLE,
            ColumnType.DECIMAL
        ]
        return column_type in numeric_types
    
    def is_string_type(self, column_type: ColumnType) -> bool:
        """
        判断是否为字符串类型
        
        Args:
            column_type: 标准化的数据类型
            
        Returns:
            是否为字符串类型
        """
        string_types = [
            ColumnType.VARCHAR,
            ColumnType.CHAR,
            ColumnType.TEXT
        ]
        return column_type in string_types
    
    def is_datetime_type(self, column_type: ColumnType) -> bool:
        """
        判断是否为日期时间类型
        
        Args:
            column_type: 标准化的数据类型
            
        Returns:
            是否为日期时间类型
        """
        datetime_types = [
            ColumnType.DATE,
            ColumnType.DATETIME,
            ColumnType.TIMESTAMP
        ]
        return column_type in datetime_types
    
    def get_type_category(self, column_type: ColumnType) -> str:
        """
        获取数据类型分类
        
        Args:
            column_type: 标准化的数据类型
            
        Returns:
            数据类型分类
        """
        if self.is_numeric_type(column_type):
            return "numeric"
        elif self.is_string_type(column_type):
            return "string"
        elif self.is_datetime_type(column_type):
            return "datetime"
        elif column_type == ColumnType.BOOLEAN:
            return "boolean"
        elif column_type == ColumnType.JSON:
            return "json"
        elif column_type == ColumnType.ARRAY:
            return "array"
        else:
            return "unknown"
