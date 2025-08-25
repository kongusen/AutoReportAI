#!/usr/bin/env python3
"""
测试Redis缓存优化
"""

import sys
import asyncio
sys.path.insert(0, '/Users/shan/work/me/AutoReportAI/backend')

async def test_redis_optimization():
    """测试Redis缓存优化和内存管理"""
    print("🧪 测试Redis缓存优化")
    print("=" * 50)
    
    try:
        from app.services.infrastructure.cache.unified_cache_system import (
            initialize_cache_manager, CacheType, CacheLevel
        )
        import redis
        
        # 连接Redis
        try:
            redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            redis_client.ping()
            print("✅ Redis连接成功")
        except Exception as e:
            print(f"❌ Redis连接失败: {e}")
            return
        
        # 初始化缓存管理器
        cache_manager = initialize_cache_manager(
            enable_memory=True,
            enable_redis=True,
            enable_database=False,
            redis_client=redis_client
        )
        
        if not cache_manager:
            print("❌ 缓存管理器初始化失败")
            return
        
        print("✅ 缓存管理器初始化成功")
        
        # 测试1：检查内存使用情况
        print("\n📊 检查Redis内存使用情况")
        memory_info = await cache_manager.check_memory_usage()
        if 'redis' in memory_info:
            redis_info = memory_info['redis']
            if 'error' not in redis_info:
                print(f"  当前内存使用: {redis_info.get('used_memory_human', 'N/A')}")
                print(f"  峰值内存使用: {redis_info.get('used_memory_peak_human', 'N/A')}")
                print(f"  最大内存限制: {redis_info.get('maxmemory_human', 'N/A')}")
                print(f"  内存使用率: {redis_info.get('used_memory_percent', 'N/A')}%")
            else:
                print(f"  内存信息获取错误: {redis_info['error']}")
        
        # 测试2：模拟大数据缓存
        print("\n💾 测试大数据缓存优化")
        
        # 创建一个大的模拟数据
        large_data = {
            "value": "测试占位符结果",
            "raw_data": [{"id": i, "data": f"大量数据_{i}" * 100} for i in range(1000)],  # 大数据
            "success": True,
            "confidence": 0.95,
            "metadata": {"sql_query": "SELECT * FROM large_table WHERE " + "condition " * 50}  # 长SQL
        }
        
        print(f"  原始数据大小估算: {len(str(large_data))} 字符")
        
        # 尝试设置大数据缓存
        success = await cache_manager.set(
            key="test:large_data",
            value=large_data,
            cache_type=CacheType.PLACEHOLDER_RESULT,
            cache_level=CacheLevel.REDIS,
            ttl_seconds=300
        )
        
        if success:
            print("  ✅ 大数据缓存设置成功（经过优化）")
        else:
            print("  ⚠️  大数据缓存被跳过（可能因为数据太大）")
        
        # 测试3：自动清理功能
        print("\n🧹 测试自动清理功能")
        cleanup_result = await cache_manager.auto_cleanup_if_needed()
        print(f"  清理结果: {cleanup_result}")
        
        # 测试4：手动清理过期缓存
        print("\n🗑️  测试手动清理过期缓存")
        expired_count = await cache_manager.cleanup_expired()
        print(f"  清理了 {expired_count} 个过期条目")
        
        # 测试5：最终内存状态
        print("\n📊 最终内存使用情况")
        final_memory_info = await cache_manager.check_memory_usage()
        if 'redis' in final_memory_info and 'error' not in final_memory_info['redis']:
            redis_info = final_memory_info['redis']
            print(f"  最终内存使用: {redis_info.get('used_memory_human', 'N/A')}")
            print(f"  最终使用率: {redis_info.get('used_memory_percent', 'N/A')}%")
        
        print("\n🎉 Redis缓存优化测试完成")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_redis_optimization())