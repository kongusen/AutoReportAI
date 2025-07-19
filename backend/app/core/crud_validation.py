"""
CRUD 操作类型一致性验证工具
检查所有 CRUD 方法的参数类型是否正确
"""

import inspect
import logging
from typing import Any, Dict, List, get_type_hints

from app.crud import *
from app.models import *
from app.schemas import *

logger = logging.getLogger(__name__)


class CRUDTypeValidator:
    """CRUD类型一致性验证器"""

    def __init__(self):
        self.validation_errors = []
        self.validation_warnings = []

        # CRUD实例映射
        self.crud_instances = {
            "user": user,
            "user_profile": user_profile,
            "template": template,
            "data_source": data_source,
            "etl_job": etl_job,
            "ai_provider": ai_provider,
            "analytics_data": analytics_data,
            "placeholder_mapping": placeholder_mapping,
            "report_history": report_history,
            "task": task,
        }

        # 模型到主键类型的映射
        self.model_pk_types = {
            "User": int,
            "UserProfile": int,
            "Template": str,  # UUID
            "DataSource": int,
            "ETLJob": str,  # UUID
            "AIProvider": int,
            "AnalyticsData": int,
            "PlaceholderMapping": int,
            "ReportHistory": int,
            "Task": int,
        }

    def validate_all(self) -> Dict[str, Any]:
        """执行完整的CRUD类型一致性验证"""
        results = {
            "get_methods": self.validate_get_methods(),
            "create_methods": self.validate_create_methods(),
            "update_methods": self.validate_update_methods(),
            "delete_methods": self.validate_delete_methods(),
            "custom_methods": self.validate_custom_methods(),
            "errors": self.validation_errors,
            "warnings": self.validation_warnings,
        }
        return results

    def validate_get_methods(self) -> Dict[str, List[str]]:
        """验证get方法的参数类型"""
        issues = []
        correct = []

        for name, crud_instance in self.crud_instances.items():
            # 检查get方法
            if hasattr(crud_instance, "get"):
                method = getattr(crud_instance, "get")
                try:
                    sig = inspect.signature(method)
                    params = sig.parameters

                    # 检查id参数类型
                    if "id" in params:
                        param = params["id"]
                        if param.annotation != inspect.Parameter.empty:
                            # 获取模型类名
                            model_name = crud_instance.__class__.__name__.replace(
                                "CRUD", ""
                            )
                            expected_type = self.model_pk_types.get(model_name, int)

                            if param.annotation != expected_type:
                                issues.append(
                                    f"{name}.get(id): 期望 {expected_type.__name__}, 实际 {param.annotation}"
                                )
                            else:
                                correct.append(f"{name}.get(id): {param.annotation}")
                        else:
                            issues.append(f"{name}.get(id): 缺少类型注解")

                    # 检查返回类型
                    if sig.return_annotation != inspect.Parameter.empty:
                        correct.append(
                            f"{name}.get() 返回类型: {sig.return_annotation}"
                        )
                    else:
                        issues.append(f"{name}.get(): 缺少返回类型注解")

                except Exception as e:
                    issues.append(f"{name}.get(): 检查失败 - {str(e)}")

        return {"issues": issues, "correct": correct}

    def validate_create_methods(self) -> Dict[str, List[str]]:
        """验证create方法的参数类型"""
        issues = []
        correct = []

        for name, crud_instance in self.crud_instances.items():
            if hasattr(crud_instance, "create"):
                method = getattr(crud_instance, "create")
                try:
                    sig = inspect.signature(method)
                    params = sig.parameters

                    # 检查obj_in参数类型
                    if "obj_in" in params:
                        param = params["obj_in"]
                        if param.annotation != inspect.Parameter.empty:
                            # 检查是否是Create schema类型
                            annotation_str = str(param.annotation)
                            if "Create" in annotation_str:
                                correct.append(
                                    f"{name}.create(obj_in): {param.annotation}"
                                )
                            else:
                                issues.append(
                                    f"{name}.create(obj_in): 应该使用Create schema类型"
                                )
                        else:
                            issues.append(f"{name}.create(obj_in): 缺少类型注解")

                    # 检查返回类型
                    if sig.return_annotation != inspect.Parameter.empty:
                        correct.append(
                            f"{name}.create() 返回类型: {sig.return_annotation}"
                        )
                    else:
                        issues.append(f"{name}.create(): 缺少返回类型注解")

                except Exception as e:
                    issues.append(f"{name}.create(): 检查失败 - {str(e)}")

        return {"issues": issues, "correct": correct}

    def validate_update_methods(self) -> Dict[str, List[str]]:
        """验证update方法的参数类型"""
        issues = []
        correct = []

        for name, crud_instance in self.crud_instances.items():
            if hasattr(crud_instance, "update"):
                method = getattr(crud_instance, "update")
                try:
                    sig = inspect.signature(method)
                    params = sig.parameters

                    # 检查obj_in参数类型
                    if "obj_in" in params:
                        param = params["obj_in"]
                        if param.annotation != inspect.Parameter.empty:
                            # 检查是否是Update schema类型或Union类型
                            annotation_str = str(param.annotation)
                            if "Update" in annotation_str or "Union" in annotation_str:
                                correct.append(
                                    f"{name}.update(obj_in): {param.annotation}"
                                )
                            else:
                                issues.append(
                                    f"{name}.update(obj_in): 应该使用Update schema类型或Union类型"
                                )
                        else:
                            issues.append(f"{name}.update(obj_in): 缺少类型注解")

                    # 检查db_obj参数类型
                    if "db_obj" in params:
                        param = params["db_obj"]
                        if param.annotation != inspect.Parameter.empty:
                            correct.append(f"{name}.update(db_obj): {param.annotation}")
                        else:
                            issues.append(f"{name}.update(db_obj): 缺少类型注解")

                    # 检查返回类型
                    if sig.return_annotation != inspect.Parameter.empty:
                        correct.append(
                            f"{name}.update() 返回类型: {sig.return_annotation}"
                        )
                    else:
                        issues.append(f"{name}.update(): 缺少返回类型注解")

                except Exception as e:
                    issues.append(f"{name}.update(): 检查失败 - {str(e)}")

        return {"issues": issues, "correct": correct}

    def validate_delete_methods(self) -> Dict[str, List[str]]:
        """验证delete/remove方法的参数类型"""
        issues = []
        correct = []

        for name, crud_instance in self.crud_instances.items():
            # 检查remove方法
            if hasattr(crud_instance, "remove"):
                method = getattr(crud_instance, "remove")
                try:
                    sig = inspect.signature(method)
                    params = sig.parameters

                    # 检查id参数类型
                    if "id" in params:
                        param = params["id"]
                        if param.annotation != inspect.Parameter.empty:
                            # 获取模型类名
                            model_name = crud_instance.__class__.__name__.replace(
                                "CRUD", ""
                            )
                            expected_type = self.model_pk_types.get(model_name, int)

                            if param.annotation != expected_type:
                                issues.append(
                                    f"{name}.remove(id): 期望 {expected_type.__name__}, 实际 {param.annotation}"
                                )
                            else:
                                correct.append(f"{name}.remove(id): {param.annotation}")
                        else:
                            issues.append(f"{name}.remove(id): 缺少类型注解")

                    # 检查返回类型
                    if sig.return_annotation != inspect.Parameter.empty:
                        correct.append(
                            f"{name}.remove() 返回类型: {sig.return_annotation}"
                        )
                    else:
                        issues.append(f"{name}.remove(): 缺少返回类型注解")

                except Exception as e:
                    issues.append(f"{name}.remove(): 检查失败 - {str(e)}")

        return {"issues": issues, "correct": correct}

    def validate_custom_methods(self) -> Dict[str, List[str]]:
        """验证自定义方法的参数类型"""
        issues = []
        correct = []

        # 检查常见的自定义方法
        custom_methods = [
            "get_by_name",
            "get_by_email",
            "get_by_username",
            "get_by_user_id",
            "get_active",
            "get_by_provider_name",
            "get_multi_by_owner",
            "authenticate",
            "is_active",
            "is_superuser",
            "get_or_create",
        ]

        for name, crud_instance in self.crud_instances.items():
            for method_name in custom_methods:
                if hasattr(crud_instance, method_name):
                    method = getattr(crud_instance, method_name)
                    try:
                        sig = inspect.signature(method)

                        # 检查是否有类型注解
                        if sig.return_annotation != inspect.Parameter.empty:
                            correct.append(
                                f"{name}.{method_name}() 返回类型: {sig.return_annotation}"
                            )
                        else:
                            issues.append(f"{name}.{method_name}(): 缺少返回类型注解")

                        # 检查参数类型注解
                        for param_name, param in sig.parameters.items():
                            if (
                                param_name not in ["self", "db"]
                                and param.annotation == inspect.Parameter.empty
                            ):
                                issues.append(
                                    f"{name}.{method_name}({param_name}): 缺少类型注解"
                                )
                            elif param_name not in ["self", "db"]:
                                correct.append(
                                    f"{name}.{method_name}({param_name}): {param.annotation}"
                                )

                    except Exception as e:
                        issues.append(f"{name}.{method_name}(): 检查失败 - {str(e)}")

        return {"issues": issues, "correct": correct}

    def check_schema_consistency(self) -> Dict[str, List[str]]:
        """检查Schema与模型的一致性"""
        issues = []
        correct = []

        # 检查Schema字段与模型字段的一致性
        schema_model_mapping = {
            "UserCreate": "User",
            "UserUpdate": "User",
            "TemplateCreate": "Template",
            "TemplateUpdate": "Template",
            "TaskCreate": "Task",
            "TaskUpdate": "Task",
            "DataSourceCreate": "DataSource",
            "DataSourceUpdate": "DataSource",
            "ETLJobCreate": "ETLJob",
            "ETLJobUpdate": "ETLJob",
            "AIProviderCreate": "AIProvider",
            "AIProviderUpdate": "AIProvider",
        }

        # 这里可以添加更详细的Schema一致性检查
        # 由于涉及到复杂的类型比较，暂时跳过

        return {"issues": issues, "correct": correct}


def validate_crud_types() -> Dict[str, Any]:
    """执行CRUD类型一致性验证"""
    validator = CRUDTypeValidator()
    return validator.validate_all()


def print_crud_validation_results(results: Dict[str, Any]):
    """打印CRUD验证结果"""
    print("=== CRUD 类型一致性验证结果 ===\n")

    print("1. GET 方法:")
    get_results = results["get_methods"]
    if get_results["issues"]:
        print("  类型问题:")
        for issue in get_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✓ 所有GET方法类型正确")

    print("\n2. CREATE 方法:")
    create_results = results["create_methods"]
    if create_results["issues"]:
        print("  类型问题:")
        for issue in create_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✓ 所有CREATE方法类型正确")

    print("\n3. UPDATE 方法:")
    update_results = results["update_methods"]
    if update_results["issues"]:
        print("  类型问题:")
        for issue in update_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✓ 所有UPDATE方法类型正确")

    print("\n4. DELETE 方法:")
    delete_results = results["delete_methods"]
    if delete_results["issues"]:
        print("  类型问题:")
        for issue in delete_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✓ 所有DELETE方法类型正确")

    print("\n5. 自定义方法:")
    custom_results = results["custom_methods"]
    if custom_results["issues"]:
        print("  类型问题:")
        for issue in custom_results["issues"]:
            print(f"    - {issue}")
    else:
        print("  ✓ 所有自定义方法类型正确")


if __name__ == "__main__":
    results = validate_crud_types()
    print_crud_validation_results(results)
