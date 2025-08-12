 #!/usr/bin/env python3
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, '/app')

from app.services.connectors.doris_connector import create_doris_connector
from app.db.session import get_db_session
from app.crud.crud_data_source import crud_data_source

async def test_doris_connection():
    try:
        with get_db_session() as db:
            data_source = crud_data_source.get(db, id='21a14b18-ff0b-46e1-a5ca-d37c3ad3e229')
            print(f'Data source: {data_source.name} ({data_source.source_type})')
            print(f'Doris config:')
            print(f'  FE hosts: {data_source.doris_fe_hosts}')
            print(f'  Query port: {data_source.doris_query_port}')
            print(f'  Database: {data_source.doris_database}')
            print(f'  Username: {data_source.doris_username}')
            print(f'  Password: {"***" if data_source.doris_password else "None"}')
            
            connector = create_doris_connector(data_source)
            print(f'Connector config: {connector.config}')
            
            async with connector:
                result = await connector.test_connection()
                print(f'Connection test result: {result}')
            
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_doris_connection())