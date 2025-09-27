"""
SQL模板参数填充服务

基于提供的Python脚本思想，实现稳定的模板化SQL执行机制
比Agent直接生成带时间的SQL更稳定可靠
"""

import logging
import decimal
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Union
import re
import json

logger = logging.getLogger(__name__)


class SQLTemplateService:
    """SQL模板参数填充服务"""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def build_template_parameters(
        self,
        base_date: str,
        timezone_offset: int = 8,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        构建模板参数字典

        Args:
            base_date: 基准日期 YYYY-MM-DD
            timezone_offset: 时区偏移（小时）
            additional_params: 额外的自定义参数

        Returns:
            参数字典
        """
        try:
            base_date_obj = datetime.strptime(base_date, '%Y-%m-%d')

            # 基础时间参数
            params = {
                # 标准时间参数
                'start_date': base_date,
                'end_date': base_date,
                'base_date': base_date,

                # 相对时间参数
                'prev_date': (base_date_obj - timedelta(days=1)).strftime('%Y-%m-%d'),
                'prev_start_date': (base_date_obj - timedelta(days=1)).strftime('%Y-%m-%d'),
                'prev_end_date': (base_date_obj - timedelta(days=1)).strftime('%Y-%m-%d'),

                # 周期参数
                'week_start': (base_date_obj - timedelta(days=base_date_obj.weekday())).strftime('%Y-%m-%d'),
                'week_end': (base_date_obj + timedelta(days=6-base_date_obj.weekday())).strftime('%Y-%m-%d'),

                'month_start': base_date_obj.replace(day=1).strftime('%Y-%m-%d'),
                'month_end': (base_date_obj.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1),

                # 格式化时间参数
                'date_cn': base_date_obj.strftime('%Y年%m月%d日'),
                'date_short': base_date_obj.strftime('%m月%d日'),

                # 系统时间参数
                'current_time': datetime.now(timezone.utc).isoformat(),
                'execution_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # 处理月末日期
            if isinstance(params['month_end'], datetime):
                params['month_end'] = params['month_end'].strftime('%Y-%m-%d')

            # 合并额外参数
            if additional_params:
                params.update(additional_params)

            self.logger.debug(f"✅ 构建模板参数成功: {len(params)} 个参数")
            return params

        except ValueError as e:
            self.logger.error(f"❌ 无效的基准日期格式 '{base_date}': {e}")
            raise ValueError(f"基准日期必须是 YYYY-MM-DD 格式: {e}")

    def fill_template(self, sql_template: str, parameters: Dict[str, Any]) -> str:
        """
        填充SQL模板

        Args:
            sql_template: 包含占位符的SQL模板
            parameters: 参数字典

        Returns:
            填充后的SQL
        """
        try:
            # 检查是否包含占位符
            if not re.search(r'{{[^}]+}}', sql_template):
                self.logger.debug("SQL模板不包含占位符，直接返回")
                return sql_template

            filled_sql = sql_template
            missing_params = []

            # 查找所有占位符
            placeholders = re.findall(r'{{([^}]+)}}', sql_template)

            for placeholder in placeholders:
                placeholder_key = placeholder.strip()

                if placeholder_key in parameters:
                    # 参数值处理
                    param_value = parameters[placeholder_key]

                    # 如果是字符串且不是已经带引号的，添加引号
                    if isinstance(param_value, str) and not param_value.startswith("'"):
                        param_value = f"'{param_value}'"
                    elif isinstance(param_value, (int, float, decimal.Decimal)):
                        param_value = str(param_value)

                    # 替换占位符
                    filled_sql = filled_sql.replace(f'{{{{{placeholder_key}}}}}', param_value)
                    self.logger.debug(f"  ✅ 替换参数: {placeholder_key} -> {param_value}")
                else:
                    missing_params.append(placeholder_key)

            if missing_params:
                self.logger.warning(f"⚠️ 缺少模板参数: {missing_params}")
                # 可以选择抛出异常或使用默认值
                # raise ValueError(f"缺少必需的模板参数: {missing_params}")

            self.logger.info(f"✅ SQL模板填充完成，替换了 {len(placeholders) - len(missing_params)} 个参数")
            return filled_sql

        except Exception as e:
            self.logger.error(f"❌ SQL模板填充失败: {e}")
            raise

    def validate_template_sql(self, sql_template: str) -> Dict[str, Any]:
        """
        验证SQL模板的格式和占位符

        Args:
            sql_template: SQL模板

        Returns:
            验证结果
        """
        try:
            result = {
                "valid": True,
                "issues": [],
                "warnings": [],
                "placeholders": [],
                "required_params": []
            }

            # 检查基本SQL格式
            if not sql_template.strip().upper().startswith(('SELECT', 'WITH')):
                result["issues"].append("SQL模板必须以SELECT或WITH开头")
                result["valid"] = False

            # 提取所有占位符
            placeholders = re.findall(r'{{([^}]+)}}', sql_template)
            result["placeholders"] = list(set(placeholders))

            # 检查时间相关占位符
            time_placeholders = [p for p in placeholders if any(
                keyword in p.lower() for keyword in ['date', 'time', 'start', 'end', 'prev']
            )]
            result["required_params"] = time_placeholders

            # 检查是否有悬空的花括号
            unmatched_braces = re.findall(r'(?:^|[^{]){(?:[^{}]|$)', sql_template)
            if unmatched_braces:
                result["warnings"].append("检测到可能不匹配的花括号")

            # 检查SQL注入风险
            dangerous_patterns = ['--', ';', 'drop', 'delete', 'update', 'insert', 'exec']
            for pattern in dangerous_patterns:
                if pattern.lower() in sql_template.lower():
                    result["warnings"].append(f"检测到潜在风险关键词: {pattern}")

            self.logger.debug(f"✅ SQL模板验证完成: {'通过' if result['valid'] else '失败'}")
            return result

        except Exception as e:
            self.logger.error(f"❌ SQL模板验证失败: {e}")
            return {
                "valid": False,
                "issues": [f"验证过程异常: {e}"],
                "warnings": [],
                "placeholders": [],
                "required_params": []
            }

    def process_placeholder_map(
        self,
        placeholder_sql_map: Dict[str, str],
        base_date: str,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        批量处理占位符-SQL映射，类似用户提供的Python脚本

        Args:
            placeholder_sql_map: 占位符名称到SQL模板的映射
            base_date: 基准日期
            additional_params: 额外参数

        Returns:
            占位符名称到可执行SQL的映射
        """
        try:
            # 构建参数字典
            template_params = self.build_template_parameters(base_date, additional_params=additional_params)

            executable_sql_map = {}

            for placeholder_name, sql_template in placeholder_sql_map.items():
                try:
                    if not sql_template or not sql_template.strip():
                        self.logger.warning(f"⚠️ 占位符 '{placeholder_name}' 无SQL模板，跳过")
                        executable_sql_map[placeholder_name] = None
                        continue

                    # 验证模板
                    validation_result = self.validate_template_sql(sql_template)
                    if not validation_result["valid"]:
                        self.logger.error(f"❌ 占位符 '{placeholder_name}' SQL模板验证失败: {validation_result['issues']}")
                        executable_sql_map[placeholder_name] = f"ERROR: 模板验证失败"
                        continue

                    # 填充模板
                    executable_sql = self.fill_template(sql_template, template_params)
                    executable_sql_map[placeholder_name] = executable_sql

                    self.logger.debug(f"✅ 处理占位符 '{placeholder_name}' 成功")

                except Exception as e:
                    self.logger.error(f"❌ 处理占位符 '{placeholder_name}' 失败: {e}")
                    executable_sql_map[placeholder_name] = f"ERROR: {e}"

            self.logger.info(f"🎉 批量处理完成: {len(executable_sql_map)} 个占位符")
            return executable_sql_map

        except Exception as e:
            self.logger.error(f"❌ 批量处理失败: {e}")
            raise

    def calculate_period_value(self, placeholder: str, base_date: str) -> str:
        """
        计算周期性占位符的值，类似用户脚本中的逻辑

        Args:
            placeholder: 周期性占位符名称
            base_date: 基准日期

        Returns:
            计算出的值
        """
        try:
            base_date_obj = datetime.strptime(base_date, '%Y-%m-%d')

            # 周期值计算规则
            if "任务发起时间" in placeholder:
                return datetime.now(timezone.utc).isoformat()
            elif "任务时间-2天" in placeholder or "-2天" in placeholder:
                two_days_ago = base_date_obj - timedelta(days=2)
                return two_days_ago.strftime('%Y-%m-%d')
            elif "统计周期" in placeholder and "年" in placeholder and "月" in placeholder and "日" in placeholder:
                return base_date_obj.strftime('%Y年%m月%d日')
            elif "统计周期" in placeholder and "月" in placeholder and "日" in placeholder:
                return base_date_obj.strftime('%m月%d日')
            elif "昨天" in placeholder or "前一天" in placeholder:
                yesterday = base_date_obj - timedelta(days=1)
                return yesterday.strftime('%Y-%m-%d')
            elif "明天" in placeholder or "后一天" in placeholder:
                tomorrow = base_date_obj + timedelta(days=1)
                return tomorrow.strftime('%Y-%m-%d')
            else:
                return f"未识别的周期占位符: {placeholder}"

        except Exception as e:
            self.logger.error(f"❌ 计算周期值失败: {e}")
            return f"ERROR: {e}"

    def process_report_placeholders(
        self,
        placeholder_data_map: Dict[str, Any],
        base_date: str,
        period_type: str = "daily"
    ) -> Dict[str, Any]:
        """
        处理报告中的占位符数据，包括周期性占位符和百分比格式化

        Args:
            placeholder_data_map: 原始占位符数据映射
            base_date: 基准日期
            period_type: 周期类型 (daily/weekly/monthly)

        Returns:
            处理后的占位符数据
        """
        try:
            base_date_obj = datetime.strptime(base_date, '%Y-%m-%d')
            processed_data = {}

            # 计算周期日期范围
            start_date, end_date, prev_start_date, prev_end_date = self._calculate_period_dates(
                base_date_obj, period_type
            )

            for placeholder, value in placeholder_data_map.items():
                try:
                    if placeholder.startswith("{{周期："):
                        # 处理周期占位符
                        if "统计周期，示例：" in placeholder:
                            processed_data[placeholder] = f"{start_date.strftime('%Y年%m月%d日')} 至 {end_date.strftime('%Y年%m月%d日')}"
                        elif "统计周期" in placeholder:
                            processed_data[placeholder] = end_date.strftime('%Y年%m月%d日')
                        else:
                            processed_data[placeholder] = str(value) if value is not None else ""
                    elif value is not None:
                        # 处理百分比占位符
                        is_percentage = ("占比" in placeholder or "百分比" in placeholder) and "图表" not in placeholder
                        if is_percentage and isinstance(value, (int, float, decimal.Decimal)):
                            processed_data[placeholder] = f"{value}%"
                        else:
                            processed_data[placeholder] = value
                    else:
                        processed_data[placeholder] = ""

                except Exception as e:
                    self.logger.warning(f"⚠️ 处理占位符 '{placeholder}' 时出错: {e}")
                    processed_data[placeholder] = f"ERROR: {e}"

            self.logger.info(f"✅ 报告占位符处理完成: {len(processed_data)} 个占位符")
            return processed_data

        except Exception as e:
            self.logger.error(f"❌ 报告占位符处理失败: {e}")
            raise

    def _calculate_period_dates(self, base_date_obj: datetime, period_type: str) -> tuple:
        """计算周期日期范围"""
        if period_type == 'daily':
            end_date = base_date_obj
            start_date = end_date
            prev_end_date = end_date - timedelta(days=1)
            prev_start_date = prev_end_date
        elif period_type == 'weekly':
            # 上周末为结束日期
            end_date = base_date_obj - timedelta(days=base_date_obj.weekday() + 1)
            start_date = end_date - timedelta(days=6)
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date - timedelta(days=6)
        elif period_type == 'monthly':
            # 上个月末为结束日期
            end_date = base_date_obj.replace(day=1) - timedelta(days=1)
            start_date = end_date.replace(day=1)
            prev_end_date = start_date - timedelta(days=1)
            prev_start_date = prev_end_date.replace(day=1)
        else:
            # 默认为日周期
            end_date = base_date_obj
            start_date = end_date
            prev_end_date = end_date - timedelta(days=1)
            prev_start_date = prev_end_date

        return start_date, end_date, prev_start_date, prev_end_date


# 全局服务实例
sql_template_service = SQLTemplateService()