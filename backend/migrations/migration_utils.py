"""
可复用的数据库迁移工具集

提供标准化的数据库迁移操作，包括：
- 表重命名和列重命名
- 外键约束更新
- 枚举类型管理
- 索引管理
- 数据迁移
"""

from typing import List, Dict, Any, Optional, Tuple
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


class MigrationHelper:
    """数据库迁移辅助工具类"""
    
    @staticmethod
    def rename_table_and_update_fks(
        old_table_name: str,
        new_table_name: str,
        foreign_key_mappings: List[Dict[str, Any]]
    ) -> None:
        """
        重命名表并更新所有相关的外键约束
        
        Args:
            old_table_name: 旧表名
            new_table_name: 新表名
            foreign_key_mappings: 外键映射配置列表
                每个配置包含:
                - table: 引用表名
                - column: 外键列名
                - constraint_name: 约束名（可选）
        """
        # 重命名表
        op.rename_table(old_table_name, new_table_name)
        
        # 更新外键约束
        for mapping in foreign_key_mappings:
            table = mapping['table']
            column = mapping['column']
            constraint_name = mapping.get('constraint_name', f"{table}_{column}_fkey")
            
            try:
                # 删除旧的外键约束
                op.drop_constraint(constraint_name, table, type_='foreignkey')
            except Exception:
                # 如果约束不存在，跳过
                pass
            
            # 创建新的外键约束
            op.create_foreign_key(
                constraint_name,
                table,
                new_table_name,
                [column],
                ['id']
            )
    
    @staticmethod
    def rename_column(
        table_name: str,
        old_column_name: str,
        new_column_name: str,
        update_constraints: bool = True
    ) -> None:
        """
        重命名列并更新相关约束
        
        Args:
            table_name: 表名
            old_column_name: 旧列名
            new_column_name: 新列名
            update_constraints: 是否更新约束
        """
        op.alter_column(
            table_name,
            old_column_name,
            new_column_name=new_column_name
        )
        
        if update_constraints:
            # 更新外键约束名
            old_fk_name = f"{table_name}_{old_column_name}_fkey"
            new_fk_name = f"{table_name}_{new_column_name}_fkey"
            
            try:
                op.drop_constraint(old_fk_name, table_name, type_='foreignkey')
                op.create_foreign_key(
                    new_fk_name,
                    table_name,
                    new_column_name.replace('_id', 's'),  # 假设表名是复数形式
                    [new_column_name],
                    ['id']
                )
            except Exception:
                pass
    
    @staticmethod
    def create_enum_type_if_not_exists(
        enum_name: str,
        values: List[str]
    ) -> None:
        """创建枚举类型（如果不存在）"""
        connection = op.get_bind()
        
        result = connection.execute(sa.text(f"""
            SELECT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = '{enum_name}'
            )
        """)).scalar()
        
        if not result:
            values_str = "', '".join(values)
            connection.execute(sa.text(f"""
                CREATE TYPE {enum_name} AS ENUM ('{values_str}')
            """))
    
    @staticmethod
    def create_indexes_if_not_exist(
        table_name: str,
        indexes: List[Dict[str, Any]]
    ) -> None:
        """
        创建索引（如果不存在）
        
        Args:
            table_name: 表名
            indexes: 索引配置列表
                每个配置包含:
                - columns: 列名或列名列表
                - name: 索引名（可选）
                - unique: 是否唯一（默认False）
        """
        connection = op.get_bind()
        
        for index_config in indexes:
            columns = index_config['columns']
            unique = index_config.get('unique', False)
            
            if isinstance(columns, str):
                columns = [columns]
            
            index_name = index_config.get('name') or f"ix_{table_name}_{'_'.join(columns)}"
            
            # 检查索引是否存在
            index_exists = connection.execute(sa.text(f"""
                SELECT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = '{index_name}'
                )
            """)).scalar()
            
            if not index_exists:
                try:
                    op.create_index(index_name, table_name, columns, unique=unique)
                except Exception as e:
                    print(f"Warning: Could not create index {index_name}: {e}")
    
    @staticmethod
    def table_exists(table_name: str) -> bool:
        """检查表是否存在"""
        connection = op.get_bind()
        result = connection.execute(sa.text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = '{table_name}'
            )
        """)).scalar()
        return result
    
    @staticmethod
    def column_exists(table_name: str, column_name: str) -> bool:
        """检查列是否存在"""
        connection = op.get_bind()
        result = connection.execute(sa.text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND column_name = '{column_name}'
            )
        """)).scalar()
        return result
    
    @staticmethod
    def constraint_exists(constraint_name: str) -> bool:
        """检查约束是否存在"""
        connection = op.get_bind()
        result = connection.execute(sa.text(f"""
            SELECT EXISTS (
                SELECT 1 FROM pg_constraint 
                WHERE conname = '{constraint_name}'
            )
        """)).scalar()
        return result
    
    @staticmethod
    def safe_drop_constraint(
        table_name: str,
        constraint_name: str,
        constraint_type: str = 'foreignkey'
    ) -> None:
        """安全删除约束（如果存在）"""
        try:
            op.drop_constraint(constraint_name, table_name, type_=constraint_type)
        except Exception:
            pass
    
    @staticmethod
    def safe_create_constraint(
        table_name: str,
        constraint_name: str,
        constraint_type: str,
        **kwargs
    ) -> None:
        """安全创建约束"""
        try:
            if constraint_type == 'foreignkey':
                op.create_foreign_key(
                    constraint_name,
                    table_name,
                    kwargs['referenced_table'],
                    kwargs['local_columns'],
                    kwargs['referenced_columns']
                )
        except Exception as e:
            print(f"Warning: Could not create constraint {constraint_name}: {e}")
    
    @staticmethod
    def batch_rename_columns(
        table_name: str,
        column_mappings: Dict[str, str]
    ) -> None:
        """
        批量重命名列
        
        Args:
            table_name: 表名
            column_mappings: 旧列名到新列名的映射
        """
        for old_name, new_name in column_mappings.items():
            MigrationHelper.rename_column(table_name, old_name, new_name)
    
    @staticmethod
    def migrate_data_between_tables(
        source_table: str,
        target_table: str,
        column_mapping: Dict[str, str],
        where_clause: Optional[str] = None
    ) -> None:
        """
        在表之间迁移数据
        
        Args:
            source_table: 源表名
            target_table: 目标表名
            column_mapping: 源列到目标列的映射
            where_clause: 可选的WHERE子句
        """
        connection = op.get_bind()
        
        columns_str = ", ".join(column_mapping.keys())
        values_str = ", ".join([f"source.{col}" for col in column_mapping.keys()])
        
        query = f"""
            INSERT INTO {target_table} ({", ".join(column_mapping.values())})
            SELECT {columns_str}
            FROM {source_table} source
        """
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        connection.execute(sa.text(query))


# 快捷函数
rename_table_and_fks = MigrationHelper.rename_table_and_update_fks
rename_column = MigrationHelper.rename_column
create_enum = MigrationHelper.create_enum_type_if_not_exists
create_indexes = MigrationHelper.create_indexes_if_not_exist
table_exists = MigrationHelper.table_exists
column_exists = MigrationHelper.column_exists
constraint_exists = MigrationHelper.constraint_exists
safe_drop_constraint = MigrationHelper.safe_drop_constraint
safe_create_constraint = MigrationHelper.safe_create_constraint
batch_rename_columns = MigrationHelper.batch_rename_columns
migrate_data = MigrationHelper.migrate_data_between_tables
