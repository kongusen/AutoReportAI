#!/usr/bin/env python3
"""
API文档自动化更新脚本
监控API变更并自动更新文档
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from generate_api_docs import APIDocGenerator


class APIDocUpdater:
    """API文档更新器"""
    
    def __init__(self, output_dir: str = "docs/api"):
        self.output_dir = Path(output_dir)
        self.cache_file = self.output_dir / ".api_cache.json"
        self.generator = APIDocGenerator(output_dir)
        
    def get_api_fingerprint(self, spec: Dict[str, Any]) -> str:
        """获取API规范的指纹"""
        # 移除不影响API结构的字段
        cleaned_spec = {
            "info": {k: v for k, v in spec["info"].items() if k != "description"},
            "paths": spec["paths"],
            "components": spec.get("components", {})
        }
        
        spec_str = json.dumps(cleaned_spec, sort_keys=True)
        return hashlib.md5(spec_str.encode()).hexdigest()
    
    def load_cache(self) -> Optional[Dict[str, Any]]:
        """加载缓存信息"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None
    
    def save_cache(self, fingerprint: str, timestamp: str) -> None:
        """保存缓存信息"""
        cache_data = {
            "last_fingerprint": fingerprint,
            "last_update": timestamp,
            "update_count": self.load_cache().get("update_count", 0) + 1 if self.load_cache() else 1
        }
        
        with open(self.cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
    
    def check_for_changes(self) -> bool:
        """检查API是否有变更"""
        current_spec = self.generator.generate_openapi_spec()
        current_fingerprint = self.get_api_fingerprint(current_spec)
        
        cache = self.load_cache()
        if not cache:
            return True
        
        return cache.get("last_fingerprint") != current_fingerprint
    
    def update_docs(self, force: bool = False) -> bool:
        """更新API文档"""
        if not force and not self.check_for_changes():
            print("🔄 API没有变更，跳过文档更新")
            return False
        
        print("📝 检测到API变更，开始更新文档...")
        
        # 生成新的文档
        spec = self.generator.generate_openapi_spec()
        self.generator.save_openapi_json(spec)
        self.generator.save_openapi_yaml(spec)
        self.generator.generate_postman_collection(spec)
        self.generator.generate_api_guide(spec)
        
        # 更新缓存
        fingerprint = self.get_api_fingerprint(spec)
        timestamp = datetime.now().isoformat()
        self.save_cache(fingerprint, timestamp)
        
        print("✅ API文档更新完成！")
        return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="API文档自动更新")
    parser.add_argument("--force", action="store_true", help="强制更新文档")
    parser.add_argument("--watch", action="store_true", help="持续监控模式")
    parser.add_argument("--interval", type=int, default=300, help="监控间隔（秒）")
    
    args = parser.parse_args()
    
    updater = APIDocUpdater()
    
    if args.watch:
        print(f"🔄 开始持续监控API变更（间隔：{args.interval}秒）...")
        import time
        
        while True:
            try:
                updater.update_docs(args.force)
                time.sleep(args.interval)
            except KeyboardInterrupt:
                print("\n🛑 停止监控")
                break
            except Exception as e:
                print(f"❌ 更新失败: {e}")
                time.sleep(args.interval)
    else:
        updater.update_docs(args.force) 