#!/usr/bin/env python3
"""
任务Cron调度执行情况分析脚本

分析任务是否按照配置的cron表达式时间进行执行
"""
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
import croniter

from app.db.session import SessionLocal
from app.models.task import Task, TaskExecution
from app.core.config import settings

# 确保加载环境变量
try:
    from dotenv import load_dotenv
    import os
    load_dotenv()
except ImportError:
    pass


class TaskCronAnalyzer:
    """任务Cron调度分析器"""
    
    def __init__(self, db: Session):
        self.db = db
        self.results: List[Dict[str, Any]] = []
        
    def analyze_all_tasks(self) -> List[Dict[str, Any]]:
        """分析所有任务的执行情况"""
        # 获取所有激活的、有cron表达式的任务
        tasks = self.db.query(Task).filter(
            and_(
                Task.is_active == True,
                Task.schedule.isnot(None),
                Task.schedule != ''
            )
        ).all()
        
        print(f"\n找到 {len(tasks)} 个配置了cron表达式的任务\n")
        print("=" * 100)
        
        for task in tasks:
            result = self.analyze_task(task)
            self.results.append(result)
            
        return self.results
    
    def analyze_task(self, task: Task) -> Dict[str, Any]:
        """分析单个任务的执行情况"""
        print(f"\n分析任务: {task.id} - {task.name}")
        print(f"Cron表达式: {task.schedule}")
        
        # 获取任务的执行记录
        executions = self.db.query(TaskExecution).filter(
            TaskExecution.task_id == task.id
        ).order_by(desc(TaskExecution.started_at)).limit(100).all()
        
        if not executions:
            print("  ⚠️  没有找到执行记录")
            return {
                "task_id": task.id,
                "task_name": task.name,
                "cron_expression": task.schedule,
                "status": "no_executions",
                "total_executions": 0,
                "issues": []
            }
        
        print(f"  找到 {len(executions)} 条执行记录")
        
        # 验证cron表达式
        try:
            cron = croniter.croniter(task.schedule, datetime.now())
        except Exception as e:
            print(f"  ❌ Cron表达式无效: {e}")
            return {
                "task_id": task.id,
                "task_name": task.name,
                "cron_expression": task.schedule,
                "status": "invalid_cron",
                "error": str(e),
                "total_executions": len(executions),
                "issues": [f"Cron表达式无效: {e}"]
            }
        
        # 分析执行时间偏差
        issues = []
        execution_analysis = []
        
        # 按时间倒序分析最近的执行记录
        sorted_executions = sorted(
            [e for e in executions if e.started_at],
            key=lambda x: x.started_at,
            reverse=True
        )
        
        if len(sorted_executions) < 2:
            print("  ⚠️  执行记录不足(少于2条)，无法进行时间偏差分析")
            return {
                "task_id": task.id,
                "task_name": task.name,
                "cron_expression": task.schedule,
                "status": "insufficient_data",
                "total_executions": len(executions),
                "valid_executions": len(sorted_executions),
                "issues": ["执行记录不足，无法进行时间偏差分析"]
            }
        
        # 计算预期执行时间和实际执行时间的偏差
        last_expected_time = None
        delays = []
        early_executions = []
        missed_executions = []
        
        for i, execution in enumerate(sorted_executions):
            actual_time = execution.started_at
            
            # 如果有上一条执行记录，计算预期时间
            if i < len(sorted_executions) - 1:
                previous_execution = sorted_executions[i + 1]
                previous_time = previous_execution.started_at
                
                # 从上次执行时间开始，计算下次预期执行时间
                try:
                    # 创建新的cron迭代器，从上次执行时间开始
                    cron = croniter.croniter(task.schedule, previous_time)
                    expected_time = cron.get_next(datetime)
                    
                    # 计算时间偏差(秒)
                    time_diff = (actual_time - expected_time).total_seconds()
                    
                    execution_analysis.append({
                        "execution_id": execution.id,
                        "actual_time": actual_time.isoformat(),
                        "expected_time": expected_time.isoformat(),
                        "previous_execution": previous_time.isoformat(),
                        "time_delay_seconds": time_diff,
                        "time_delay_minutes": time_diff / 60,
                        "status": execution.execution_status.value if execution.execution_status else "unknown"
                    })
                    
                    # 判断是否有问题
                    if abs(time_diff) > 300:  # 超过5分钟偏差认为有问题
                        if time_diff > 0:
                            delays.append({
                                "execution_id": execution.id,
                                "actual_time": actual_time.isoformat(),
                                "expected_time": expected_time.isoformat(),
                                "delay_minutes": time_diff / 60
                            })
                            issues.append(
                                f"执行延迟 {time_diff/60:.1f} 分钟 "
                                f"(预期: {expected_time.strftime('%Y-%m-%d %H:%M:%S')}, "
                                f"实际: {actual_time.strftime('%Y-%m-%d %H:%M:%S')})"
                            )
                        else:
                            early_executions.append({
                                "execution_id": execution.id,
                                "actual_time": actual_time.isoformat(),
                                "expected_time": expected_time.isoformat(),
                                "early_minutes": abs(time_diff) / 60
                            })
                            issues.append(
                                f"提前执行 {abs(time_diff)/60:.1f} 分钟 "
                                f"(预期: {expected_time.strftime('%Y-%m-%d %H:%M:%S')}, "
                                f"实际: {actual_time.strftime('%Y-%m-%d %H:%M:%S')})"
                            )
                    
                    # 检查是否有遗漏的执行
                    if i > 0 and time_diff > 3600:  # 偏差超过1小时，可能遗漏了执行
                        # 计算应该有多少次执行
                        missed_count = int(time_diff / 3600)
                        if missed_count > 0:
                            missed_executions.append({
                                "expected_time": expected_time.isoformat(),
                                "actual_time": actual_time.isoformat(),
                                "missed_count": missed_count
                            })
                            issues.append(
                                f"可能遗漏了约 {missed_count} 次执行 "
                                f"(从 {expected_time.strftime('%Y-%m-%d %H:%M:%S')} "
                                f"到 {actual_time.strftime('%Y-%m-%d %H:%M:%S')})"
                            )
                    
                    last_expected_time = expected_time
                    
                except Exception as e:
                    print(f"  ⚠️  计算预期时间失败: {e}")
                    issues.append(f"计算预期时间失败: {e}")
        
        # 计算统计信息
        if execution_analysis:
            avg_delay = sum(e["time_delay_seconds"] for e in execution_analysis) / len(execution_analysis)
            max_delay = max(e["time_delay_seconds"] for e in execution_analysis) if execution_analysis else 0
            min_delay = min(e["time_delay_seconds"] for e in execution_analysis) if execution_analysis else 0
            
            print(f"  平均时间偏差: {avg_delay/60:.1f} 分钟")
            print(f"  最大延迟: {max_delay/60:.1f} 分钟")
            print(f"  最小偏差: {min_delay/60:.1f} 分钟")
            
            if issues:
                print(f"  发现 {len(issues)} 个问题:")
                for issue in issues[:5]:  # 只显示前5个问题
                    print(f"    - {issue}")
                if len(issues) > 5:
                    print(f"    ... 还有 {len(issues) - 5} 个问题")
            else:
                print("  ✅ 执行时间基本符合预期")
        
        return {
            "task_id": task.id,
            "task_name": task.name,
            "cron_expression": task.schedule,
            "status": "ok" if not issues else "has_issues",
            "total_executions": len(executions),
            "valid_executions": len(sorted_executions),
            "analysis_count": len(execution_analysis),
            "average_delay_minutes": avg_delay / 60 if execution_analysis else 0,
            "max_delay_minutes": max_delay / 60 if execution_analysis else 0,
            "min_delay_minutes": min_delay / 60 if execution_analysis else 0,
            "delays": delays,
            "early_executions": early_executions,
            "missed_executions": missed_executions,
            "issues": issues,
            "execution_analysis": execution_analysis[:10]  # 只保留最近10条分析
        }
    
    def generate_report(self) -> str:
        """生成分析报告"""
        if not self.results:
            return "没有找到需要分析的任务"
        
        report = []
        report.append("\n" + "=" * 100)
        report.append("任务Cron调度执行情况分析报告")
        report.append("=" * 100)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"分析任务数: {len(self.results)}\n")
        
        # 按状态分组
        status_groups = defaultdict(list)
        for result in self.results:
            status = result.get("status", "unknown")
            status_groups[status].append(result)
        
        report.append("\n执行情况汇总:")
        report.append(f"  正常执行: {len(status_groups.get('ok', []))} 个任务")
        report.append(f"  存在问题: {len(status_groups.get('has_issues', []))} 个任务")
        report.append(f"  无执行记录: {len(status_groups.get('no_executions', []))} 个任务")
        report.append(f"  执行记录不足: {len(status_groups.get('insufficient_data', []))} 个任务")
        report.append(f"  Cron表达式无效: {len(status_groups.get('invalid_cron', []))} 个任务")
        
        # 详细问题列表
        if status_groups.get('has_issues'):
            report.append("\n" + "-" * 100)
            report.append("详细问题列表:")
            report.append("-" * 100)
            
            for result in status_groups['has_issues']:
                report.append(f"\n任务 {result['task_id']}: {result['task_name']}")
                report.append(f"  Cron表达式: {result['cron_expression']}")
                report.append(f"  总执行次数: {result['total_executions']}")
                report.append(f"  平均时间偏差: {result.get('average_delay_minutes', 0):.1f} 分钟")
                
                if result.get('delays'):
                    report.append(f"  延迟执行次数: {len(result['delays'])}")
                if result.get('early_executions'):
                    report.append(f"  提前执行次数: {len(result['early_executions'])}")
                if result.get('missed_executions'):
                    report.append(f"  可能遗漏执行: {len(result['missed_executions'])}")
                
                if result.get('issues'):
                    report.append("  问题详情:")
                    for issue in result['issues'][:3]:
                        report.append(f"    - {issue}")
        
        report.append("\n" + "=" * 100)
        
        return "\n".join(report)


def main():
    """主函数"""
    db = SessionLocal()
    try:
        analyzer = TaskCronAnalyzer(db)
        results = analyzer.analyze_all_tasks()
        
        # 生成报告
        report = analyzer.generate_report()
        print(report)
        
        # 保存报告到文件
        report_file = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "backend",
            "logs",
            f"task_cron_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n分析报告已保存到: {report_file}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 分析失败: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

