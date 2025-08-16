#!/usr/bin/env python3
"""
测试多库多表Agent功能
"""
import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from app.services.agents.multi_database_agent import MultiDatabaseAgent, AgentQueryRequest
from app.services.data_discovery.metadata_discovery_service import MetadataDiscoveryService
from app.db.session import get_db_session
from app.models.data_source import DataSource
from app.models.table_schema import Database, Table, TableColumn

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_metadata_discovery():
    """测试元数据发现功能"""
    logger.info("=== 测试元数据发现功能 ===")
    
    try:
        # 获取第一个数据源
        with get_db_session() as db:
            data_source = db.query(DataSource).first()
            if not data_source:
                logger.error("没有找到数据源")
                return False
            
            logger.info(f"发现数据源: {data_source.name} (ID: {data_source.id})")
        
        # 初始化元数据发现服务
        discovery_service = MetadataDiscoveryService()
        
        # 执行元数据发现
        logger.info("开始执行元数据发现...")
        result = await discovery_service.discover_data_source_metadata(
            str(data_source.id), 
            full_discovery=True
        )
        
        logger.info(f"元数据发现结果:")
        logger.info(f"  - 成功: {result.success}")
        logger.info(f"  - 数据库数量: {result.databases_found}")
        logger.info(f"  - 表数量: {result.tables_found}")
        logger.info(f"  - 字段数量: {result.columns_found}")
        logger.info(f"  - 关系数量: {result.relations_found}")
        logger.info(f"  - 发现时间: {result.discovery_time:.2f}秒")
        
        if result.errors:
            logger.warning(f"错误信息: {result.errors}")
        
        # 检查数据库中的结果
        with get_db_session() as db:
            databases = db.query(Database).filter(Database.data_source_id == data_source.id).all()
            logger.info(f"\n数据库中的数据库记录: {len(databases)}个")
            
            for database in databases[:3]:  # 只显示前3个
                logger.info(f"  - {database.name} ({database.display_name})")
                tables = db.query(Table).filter(Table.database_id == database.id).all()
                logger.info(f"    包含 {len(tables)} 个表")
                
                for table in tables[:3]:  # 只显示前3个表
                    columns = db.query(TableColumn).filter(TableColumn.table_id == table.id).all()
                    logger.info(f"      - {table.name}: {len(columns)} 个字段")
        
        return result.success
        
    except Exception as e:
        logger.error(f"元数据发现测试失败: {e}")
        return False

async def test_multi_database_agent():
    """测试多库Agent查询功能"""
    logger.info("\n=== 测试多库Agent查询功能 ===")
    
    try:
        # 获取第一个数据源
        with get_db_session() as db:
            data_source = db.query(DataSource).first()
            if not data_source:
                logger.error("没有找到数据源")
                return False
        
        # 初始化Agent
        agent = MultiDatabaseAgent()
        
        # 测试发现schema
        logger.info("测试发现schema...")
        schema_info = await agent.discover_schema(str(data_source.id))
        logger.info(f"Schema信息:")
        logger.info(f"  - 数据库数量: {schema_info['databases']}")
        logger.info(f"  - 表数量: {schema_info['tables']}")
        logger.info(f"  - 字段数量: {schema_info['columns']}")
        logger.info(f"  - 关系数量: {schema_info['relations']}")
        
        # 测试获取可用表
        logger.info("\n测试获取可用表...")
        tables = await agent.get_available_tables(str(data_source.id))
        logger.info(f"可用表数量: {len(tables)}")
        
        for table in tables[:5]:  # 只显示前5个
            logger.info(f"  - {table['name']} ({table['display_name']})")
            logger.info(f"    数据库: {table['database']}")
            logger.info(f"    行数: {table['row_count']}")
            logger.info(f"    大小: {table['size_mb']} MB")
        
        # 测试查询建议
        logger.info("\n测试查询建议...")
        suggestions = await agent.suggest_queries(str(data_source.id))
        logger.info(f"查询建议数量: {len(suggestions)}")
        
        for i, suggestion in enumerate(suggestions[:5], 1):
            logger.info(f"  {i}. {suggestion}")
        
        # 测试自然语言查询（如果有表的话）
        if tables:
            logger.info("\n测试自然语言查询...")
            test_queries = [
                "查询所有数据",
                "统计数据量",
                "查看表结构"
            ]
            
            for query in test_queries:
                try:
                    logger.info(f"\n执行查询: {query}")
                    request = AgentQueryRequest(
                        query=query,
                        data_source_id=str(data_source.id),
                        max_rows=10
                    )
                    
                    response = await agent.query(request)
                    logger.info(f"  查询结果:")
                    logger.info(f"    - 成功: {response.success}")
                    logger.info(f"    - 解释: {response.explanation}")
                    logger.info(f"    - SQL: {response.sql_queries}")
                    logger.info(f"    - 复杂度: {response.metadata.get('query_complexity', 'unknown')}")
                    
                    if response.errors:
                        logger.warning(f"    - 错误: {response.errors}")
                        
                except Exception as e:
                    logger.warning(f"  查询失败: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"多库Agent测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    logger.info("🚀 开始测试多库多表Agent系统")
    
    # 测试元数据发现
    discovery_success = await test_metadata_discovery()
    
    # 测试Agent功能
    agent_success = await test_multi_database_agent()
    
    logger.info(f"\n📊 测试结果:")
    logger.info(f"  - 元数据发现: {'✅ 成功' if discovery_success else '❌ 失败'}")
    logger.info(f"  - Agent查询: {'✅ 成功' if agent_success else '❌ 失败'}")
    
    if discovery_success and agent_success:
        logger.info("🎉 所有测试通过！多库多表Agent系统运行正常")
        return True
    else:
        logger.error("❌ 部分测试失败，请检查系统配置")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)