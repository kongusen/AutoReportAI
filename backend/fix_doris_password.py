#!/usr/bin/env python3
import sys
import os

# 添加项目路径
sys.path.insert(0, '/app')

from app.db.session import get_db_session
from app.crud.crud_data_source import crud_data_source
from app.core.security_utils import encrypt_data

def fix_doris_passwords():
    """修复现有的 Doris 密码，将明文密码加密"""
    try:
        with get_db_session() as db:
            # 获取所有 Doris 数据源
            data_sources = db.query(crud_data_source.model).filter(
                crud_data_source.model.source_type == "doris"
            ).all()
            
            print(f"找到 {len(data_sources)} 个 Doris 数据源")
            
            for data_source in data_sources:
                print(f"检查数据源: {data_source.name} (ID: {data_source.id})")
                
                # 检查密码是否已经是加密的
                if data_source.doris_password:
                    try:
                        # 尝试解密，如果失败说明是明文
                        from app.core.security_utils import decrypt_data
                        decrypt_data(data_source.doris_password)
                        print(f"  ✅ 密码已经是加密的")
                    except Exception:
                        # 解密失败，说明是明文，需要加密
                        print(f"  🔒 加密明文密码: {data_source.doris_password}")
                        data_source.doris_password = encrypt_data(data_source.doris_password)
                        print(f"  ✅ 密码已加密")
                else:
                    print(f"  ℹ️  无密码")
            
            # 提交更改
            db.commit()
            print("✅ 所有密码修复完成")
            
    except Exception as e:
        print(f"❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_doris_passwords() 