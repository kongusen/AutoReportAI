"""
数据库模式验证工具
检查模型定义与实际数据库结构的一致性
"""

import logging
from typing import Any, Dict, List, Tuple

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.base_class import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


class DatabaseSchemaValidator:
    """数据库模式验证器"""

    def __init__(self):
        self.inspector = inspect(engine)
        self.validation_errors = []
        self.validation_warnings = []

    def validate_all(self) -> Dict[str, Any]:
        """执行完整的数据库模式验证"""
        results = {
            "foreign_keys": self.validate_foreign_keys(),
            "unique_constraints": self.validate_unique_constraints(),
            "nullable_constraints": self.validate_nullable_constraints(),
            "data_types": self.validate_data_types(),
            "indexes": self.validate_indexes(),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
        }
        return results

    def validate_foreign_keys(self) -> Dict[str, List[str]]:
        """验证外键约束"""
        missing_fks = []
        existing_fks = []

        # 检查每个表的外键
        tables_fks = {
            "placeholder_mappings": [
                ("template_id", "templates", "id"),
                ("data_source_id", "data_sources", "id"),
            ],
            "tasks": [
                ("owner_id", "users", "id"),
                ("data_source_id", "data_sources", "id"),
                ("template_id", "templates", "id"),
            ],
            "templates": [("user_id", "users", "id")],
            "etl_jobs": [("enhanced_source_id", "enhanced_data_sources", "id")],
            "analytics_data": [("data_source_id", "data_sources", "id")],
            "report_history": [("task_id", "tasks", "id")],
            "user_profiles": [("user_id", "users", "id")],
        }

        for table, expected_fks in tables_fks.items():
            actual_fks = self.inspector.get_foreign_keys(table)
            actual_fk_map = {
                tuple(fk["constrained_columns"]): (
                    fk["referred_table"],
                    fk["referred_columns"],
                )
                for fk in actual_fks
            }

            for col, ref_table, ref_col in expected_fks:
                if (col,) not in actual_fk_map:
                    missing_fks.append(f"{table}.{col} -> {ref_table}.{ref_col}")
                else:
                    existing_fks.append(f"{table}.{col} -> {ref_table}.{ref_col}")

        return {"missing": missing_fks, "existing": existing_fks}

    def validate_unique_constraints(self) -> Dict[str, List[str]]:
        """验证唯一性约束"""
        expected_unique = {
            "users": ["email", "username"],
            "data_sources": ["name"],
            "enhanced_data_sources": ["name"],
            "ai_providers": ["provider_name"],
            "templates": [],  # 模板名称可以重复
            "user_profiles": ["user_id"],
        }

        missing_unique = []
        existing_unique = []

        for table, expected_cols in expected_unique.items():
            if table not in self.inspector.get_table_names():
                continue

            unique_constraints = self.inspector.get_unique_constraints(table)
            indexes = self.inspector.get_indexes(table)

            # 获取所有唯一约束的列
            unique_cols = set()
            for constraint in unique_constraints:
                unique_cols.update(constraint["column_names"])

            # 获取所有唯一索引的列
            for index in indexes:
                if index["unique"]:
                    unique_cols.update(index["column_names"])

            for col in expected_cols:
                if col in unique_cols:
                    existing_unique.append(f"{table}.{col}")
                else:
                    missing_unique.append(f"{table}.{col}")

        return {"missing": missing_unique, "existing": existing_unique}

    def validate_nullable_constraints(self) -> Dict[str, List[str]]:
        """验证非空约束"""
        expected_not_null = {
            "users": ["email", "hashed_password"],
            "templates": ["name", "user_id"],
            "data_sources": ["name", "source_type"],
            "enhanced_data_sources": ["name", "source_type"],
            "ai_providers": ["provider_name", "provider_type"],
            "tasks": ["name", "owner_id", "data_source_id", "template_id"],
            "etl_jobs": [
                "name",
                "enhanced_source_id",
                "destination_table_name",
                "source_query",
            ],
            "placeholder_mappings": [
                "template_id",
                "placeholder_name",
                "placeholder_type",
            ],
            "report_history": ["status", "task_id"],
            "user_profiles": ["user_id"],
        }

        nullable_issues = []
        correct_not_null = []

        for table, expected_cols in expected_not_null.items():
            if table not in self.inspector.get_table_names():
                continue

            columns = self.inspector.get_columns(table)
            col_dict = {col["name"]: col for col in columns}

            for col in expected_cols:
                if col in col_dict:
                    if col_dict[col]["nullable"]:
                        nullable_issues.append(f"{table}.{col} 应该是非空的")
                    else:
                        correct_not_null.append(f"{table}.{col}")

        return {"issues": nullable_issues, "correct": correct_not_null}

    def validate_data_types(self) -> Dict[str, List[str]]:
        """验证数据类型"""
        type_issues = []
        correct_types = []

        # 检查关键字段的数据类型
        expected_types = {
            "users": {
                "id": "INTEGER",
                "email": "VARCHAR",
                "is_active": "BOOLEAN",
                "is_superuser": "BOOLEAN",
            },
            "templates": {
                "id": "UUID",
                "name": "VARCHAR",
                "is_public": "BOOLEAN",
                "is_active": "BOOLEAN",
                "user_id": "INTEGER",
            },
            "tasks": {
                "id": "INTEGER",
                "template_id": "UUID",
                "data_source_id": "INTEGER",
                "owner_id": "INTEGER",
                "is_active": "BOOLEAN",
            },
            "etl_jobs": {
                "id": "UUID",
                "enhanced_source_id": "INTEGER",
                "enabled": "BOOLEAN",
            },
            "ai_providers": {"id": "INTEGER", "is_active": "BOOLEAN"},
        }

        for table, expected_cols in expected_types.items():
            if table not in self.inspector.get_table_names():
                continue

            columns = self.inspector.get_columns(table)
            col_dict = {col["name"]: col for col in columns}

            for col, expected_type in expected_cols.items():
                if col in col_dict:
                    actual_type = str(col_dict[col]["type"])
                    if expected_type.upper() in actual_type.upper():
                        correct_types.append(f"{table}.{col}: {actual_type}")
                    else:
                        type_issues.append(
                            f"{table}.{col}: 期望 {expected_type}, 实际 {actual_type}"
                        )

        return {"issues": type_issues, "correct": correct_types}

    def validate_indexes(self) -> Dict[str, List[str]]:
        """验证索引"""
        expected_indexes = {
            "users": ["email", "username"],
            "data_sources": ["name"],
            "enhanced_data_sources": ["name"],
            "ai_providers": ["provider_name"],
            "templates": ["name"],
            "tasks": ["name"],
            "etl_jobs": ["name"],
            "placeholder_mappings": ["placeholder_name"],
            "analytics_data": ["record_id"],
        }

        missing_indexes = []
        existing_indexes = []

        for table, expected_cols in expected_indexes.items():
            if table not in self.inspector.get_table_names():
                continue

            indexes = self.inspector.get_indexes(table)
            indexed_cols = set()
            for index in indexes:
                indexed_cols.update(index["column_names"])

            for col in expected_cols:
                if col in indexed_cols:
                    existing_indexes.append(f"{table}.{col}")
                else:
                    missing_indexes.append(f"{table}.{col}")

        return {"missing": missing_indexes, "existing": existing_indexes}

    def generate_migration_sql(self) -> List[str]:
        """生成修复SQL语句"""
        sql_statements = []

        # 添加缺失的外键约束
        fk_results = self.validate_foreign_keys()
        for fk in fk_results["missing"]:
            table, ref = fk.split(" -> ")
            table_name, col = table.split(".")
            ref_table, ref_col = ref.split(".")

            sql = f"ALTER TABLE {table_name} ADD CONSTRAINT fk_{table_name}_{col} FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col});"
            sql_statements.append(sql)

        # 添加缺失的唯一约束
        unique_results = self.validate_unique_constraints()
        for unique in unique_results["missing"]:
            table, col = unique.split(".")
            sql = f"ALTER TABLE {table} ADD CONSTRAINT uq_{table}_{col} UNIQUE ({col});"
            sql_statements.append(sql)

        # 添加非空约束
        nullable_results = self.validate_nullable_constraints()
        for issue in nullable_results["issues"]:
            table_col = issue.split(" 应该是非空的")[0]
            table, col = table_col.split(".")
            sql = f"ALTER TABLE {table} ALTER COLUMN {col} SET NOT NULL;"
            sql_statements.append(sql)

        # 添加缺失的索引
        index_results = self.validate_indexes()
        for index in index_results["missing"]:
            table, col = index.split(".")
            sql = f"CREATE INDEX idx_{table}_{col} ON {table}({col});"
            sql_statements.append(sql)

        return sql_statements


def validate_database_schema() -> Dict[str, Any]:
    """执行数据库模式验证"""
    validator = DatabaseSchemaValidator()
    return validator.validate_all()


def print_validation_results(results: Dict[str, Any]):
    """打印验证结果"""
    print("=== 数据库模式验证结果 ===\n")

    print("1. 外键约束:")
    fk_results = results["foreign_keys"]
    if fk_results["missing"]:
        print("  缺失的外键约束:")
        for fk in fk_results["missing"]:
            print(f"    - {fk}")
    else:
        print("  ✓ 所有外键约束都已存在")

    print("\n2. 唯一性约束:")
    unique_results = results["unique_constraints"]
    if unique_results["missing"]:
        print("  缺失的唯一约束:")
        for unique in unique_results["missing"]:
            print(f"    - {unique}")
    else:
        print("  ✓ 所有唯一约束都已存在")

    print("\n3. 非空约束:")
    nullable_results = results["nullable_constraints"]
    if nullable_results["issues"]:
        print("  非空约束问题:")
        for issue in nullable_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✓ 所有非空约束都正确")

    print("\n4. 数据类型:")
    type_results = results["data_types"]
    if type_results["issues"]:
        print("  数据类型问题:")
        for issue in type_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✓ 所有数据类型都正确")

    print("\n5. 索引:")
    index_results = results["indexes"]
    if index_results["missing"]:
        print("  缺失的索引:")
        for index in index_results["missing"]:
            print(f"    - {index}")
    else:
        print("  ✓ 所有索引都已存在")


if __name__ == "__main__":
    results = validate_database_schema()
    print_validation_results(results)

    # 生成修复SQL
    validator = DatabaseSchemaValidator()
    sql_statements = validator.generate_migration_sql()
    if sql_statements:
        print("\n=== 修复SQL语句 ===")
        for sql in sql_statements:
            print(sql)
