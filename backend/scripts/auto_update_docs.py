#!/usr/bin/env python3
"""
API文档自动化更新脚本
监控API变更并自动更新文档，支持CI/CD集成
"""

import os
import sys
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
import argparse
import logging

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from generate_api_docs import APIDocGenerator
from update_api_docs import APIDocUpdater

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AutoDocUpdater:
    """自动化文档更新器"""
    
    def __init__(self, output_dir: str = "docs/api", watch_paths: List[str] = None):
        self.output_dir = Path(output_dir)
        self.watch_paths = watch_paths or [
            "app/api/endpoints/",
            "app/schemas/",
            "app/models/",
            "app/main.py"
        ]
        self.generator = APIDocGenerator(str(output_dir))
        self.updater = APIDocUpdater(str(output_dir))
        self.state_file = self.output_dir / ".auto_update_state.json"
        
    def get_files_hash(self) -> str:
        """获取监控文件的哈希值"""
        all_files = []
        
        for watch_path in self.watch_paths:
            path = Path(watch_path)
            if path.exists():
                if path.is_file():
                    all_files.append(path)
                else:
                    # 递归获取目录下所有Python文件
                    all_files.extend(path.rglob("*.py"))
        
        # 计算所有文件内容的哈希
        hasher = hashlib.md5()
        for file_path in sorted(all_files):
            try:
                with open(file_path, 'rb') as f:
                    hasher.update(f.read())
            except (IOError, OSError) as e:
                logger.warning(f"无法读取文件 {file_path}: {e}")
        
        return hasher.hexdigest()
    
    def load_state(self) -> Dict[str, Any]:
        """加载状态信息"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """保存状态信息"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def check_for_changes(self) -> bool:
        """检查是否有文件变更"""
        current_hash = self.get_files_hash()
        state = self.load_state()
        
        last_hash = state.get("last_files_hash")
        if last_hash != current_hash:
            logger.info(f"检测到文件变更: {last_hash} -> {current_hash}")
            return True
        
        return False
    
    def update_documentation(self, force: bool = False) -> bool:
        """更新文档"""
        if not force and not self.check_for_changes():
            logger.info("没有检测到变更，跳过文档更新")
            return False
        
        logger.info("开始更新API文档...")
        
        try:
            # 生成完整文档
            self.generator.run()
            
            # 更新状态
            current_hash = self.get_files_hash()
            state = {
                "last_files_hash": current_hash,
                "last_update": datetime.now().isoformat(),
                "update_count": self.load_state().get("update_count", 0) + 1
            }
            self.save_state(state)
            
            logger.info("API文档更新完成")
            return True
            
        except Exception as e:
            logger.error(f"文档更新失败: {e}")
            return False
    
    def generate_update_summary(self) -> Dict[str, Any]:
        """生成更新摘要"""
        state = self.load_state()
        
        # 获取API统计信息
        try:
            spec = self.generator.generate_openapi_spec()
            endpoint_count = len([
                path for path, methods in spec.get("paths", {}).items()
                for method in methods.keys()
                if method in ["get", "post", "put", "delete", "patch"]
            ])
            
            tag_count = len(spec.get("tags", []))
            
        except Exception as e:
            logger.warning(f"无法获取API统计信息: {e}")
            endpoint_count = 0
            tag_count = 0
        
        return {
            "update_time": datetime.now().isoformat(),
            "update_count": state.get("update_count", 0),
            "last_update": state.get("last_update"),
            "api_statistics": {
                "endpoint_count": endpoint_count,
                "tag_count": tag_count,
                "documentation_files": len(list(self.output_dir.rglob("*.md")))
            },
            "files_monitored": len([
                f for watch_path in self.watch_paths
                for f in Path(watch_path).rglob("*.py")
                if Path(watch_path).exists()
            ])
        }
    
    def validate_documentation(self) -> Dict[str, Any]:
        """验证文档完整性"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "files_checked": []
        }
        
        # 检查必需的文档文件
        required_files = [
            "README.md",
            "best-practices.md",
            "faq.md",
            "endpoints.md",
            "generated/openapi.json",
            "generated/postman-collection.json"
        ]
        
        for file_name in required_files:
            file_path = self.output_dir / file_name
            validation_result["files_checked"].append(str(file_path))
            
            if not file_path.exists():
                validation_result["valid"] = False
                validation_result["errors"].append(f"缺少必需文件: {file_name}")
            elif file_path.stat().st_size == 0:
                validation_result["warnings"].append(f"文件为空: {file_name}")
        
        # 检查OpenAPI规范有效性
        openapi_file = self.output_dir / "generated" / "openapi.json"
        if openapi_file.exists():
            try:
                with open(openapi_file, 'r') as f:
                    spec = json.load(f)
                
                # 基本结构检查
                required_keys = ["openapi", "info", "paths"]
                for key in required_keys:
                    if key not in spec:
                        validation_result["valid"] = False
                        validation_result["errors"].append(f"OpenAPI规范缺少必需字段: {key}")
                
                # 检查是否有API端点
                if not spec.get("paths"):
                    validation_result["warnings"].append("OpenAPI规范中没有定义API端点")
                
            except json.JSONDecodeError as e:
                validation_result["valid"] = False
                validation_result["errors"].append(f"OpenAPI规范JSON格式错误: {e}")
        
        return validation_result
    
    def generate_ci_report(self) -> str:
        """生成CI/CD报告"""
        summary = self.generate_update_summary()
        validation = self.validate_documentation()
        
        report = f"""
# API文档自动更新报告

## 更新摘要
- **更新时间**: {summary['update_time']}
- **累计更新次数**: {summary['update_count']}
- **上次更新**: {summary.get('last_update', 'N/A')}

## API统计
- **API端点数量**: {summary['api_statistics']['endpoint_count']}
- **API标签数量**: {summary['api_statistics']['tag_count']}
- **文档文件数量**: {summary['api_statistics']['documentation_files']}
- **监控文件数量**: {summary['files_monitored']}

## 文档验证结果
- **验证状态**: {'✅ 通过' if validation['valid'] else '❌ 失败'}
- **检查文件数**: {len(validation['files_checked'])}
- **错误数量**: {len(validation['errors'])}
- **警告数量**: {len(validation['warnings'])}

"""
        
        if validation['errors']:
            report += "### 错误详情\n"
            for error in validation['errors']:
                report += f"- ❌ {error}\n"
            report += "\n"
        
        if validation['warnings']:
            report += "### 警告详情\n"
            for warning in validation['warnings']:
                report += f"- ⚠️ {warning}\n"
            report += "\n"
        
        report += f"""
## 生成的文档文件
- OpenAPI规范: `docs/api/generated/openapi.json`
- Postman集合: `docs/api/generated/postman-collection.json`
- API使用指南: `docs/api/api-guide.md`
- 最佳实践: `docs/api/best-practices.md`
- 常见问题: `docs/api/faq.md`

---
*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return report
    
    def run_ci_mode(self) -> int:
        """CI/CD模式运行"""
        logger.info("运行CI/CD模式文档更新")
        
        # 强制更新文档
        success = self.update_documentation(force=True)
        
        # 验证文档
        validation = self.validate_documentation()
        
        # 生成报告
        report = self.generate_ci_report()
        
        # 保存报告
        report_file = self.output_dir / "ci_report.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"CI报告已保存到: {report_file}")
        
        # 输出摘要到控制台
        print("=" * 50)
        print("API文档更新摘要")
        print("=" * 50)
        print(f"文档更新: {'成功' if success else '失败'}")
        print(f"文档验证: {'通过' if validation['valid'] else '失败'}")
        
        if validation['errors']:
            print(f"错误数量: {len(validation['errors'])}")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print(f"警告数量: {len(validation['warnings'])}")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        # 返回退出码
        return 0 if success and validation['valid'] else 1


def main():
    parser = argparse.ArgumentParser(description="API文档自动化更新工具")
    parser.add_argument("--force", action="store_true", help="强制更新文档")
    parser.add_argument("--watch", action="store_true", help="持续监控模式")
    parser.add_argument("--interval", type=int, default=300, help="监控间隔（秒）")
    parser.add_argument("--ci", action="store_true", help="CI/CD模式")
    parser.add_argument("--validate", action="store_true", help="仅验证文档")
    parser.add_argument("--output-dir", default="docs/api", help="输出目录")
    parser.add_argument("--watch-paths", nargs="+", help="监控路径列表")
    
    args = parser.parse_args()
    
    # 创建更新器
    updater = AutoDocUpdater(
        output_dir=args.output_dir,
        watch_paths=args.watch_paths
    )
    
    if args.ci:
        # CI/CD模式
        exit_code = updater.run_ci_mode()
        sys.exit(exit_code)
    
    elif args.validate:
        # 仅验证模式
        validation = updater.validate_documentation()
        print("文档验证结果:")
        print(f"状态: {'通过' if validation['valid'] else '失败'}")
        
        if validation['errors']:
            print("错误:")
            for error in validation['errors']:
                print(f"  - {error}")
        
        if validation['warnings']:
            print("警告:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
        
        sys.exit(0 if validation['valid'] else 1)
    
    elif args.watch:
        # 持续监控模式
        import time
        
        logger.info(f"开始持续监控API变更（间隔：{args.interval}秒）...")
        
        while True:
            try:
                updater.update_documentation(args.force)
                time.sleep(args.interval)
            except KeyboardInterrupt:
                logger.info("停止监控")
                break
            except Exception as e:
                logger.error(f"监控过程中发生错误: {e}")
                time.sleep(args.interval)
    
    else:
        # 单次更新模式
        success = updater.update_documentation(args.force)
        
        if success:
            # 显示更新摘要
            summary = updater.generate_update_summary()
            print("文档更新完成!")
            print(f"API端点数量: {summary['api_statistics']['endpoint_count']}")
            print(f"文档文件数量: {summary['api_statistics']['documentation_files']}")
        else:
            print("文档更新失败或无需更新")
            sys.exit(1)


if __name__ == "__main__":
    main()