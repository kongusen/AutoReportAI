"""migrate_user_id_to_uuid

Revision ID: 6285aa9d6358
Revises: d3e96ca7d9b1
Create Date: 2025-07-15 18:04:11.906707

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6285aa9d6358'
down_revision: Union[str, Sequence[str], None] = 'd3e96ca7d9b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 启用 uuid-ossp 扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    
    # 1. 添加新的UUID列
    op.add_column('users', sa.Column('id_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    
    # 2. 为现有用户生成UUID
    op.execute("""
        UPDATE users 
        SET id_uuid = uuid_generate_v4() 
        WHERE id_uuid IS NULL
    """)
    
    # 3. 设置新列为非空
    op.alter_column('users', 'id_uuid', nullable=False)
    
    # 4. 在相关表中添加新的UUID外键列
    op.add_column('user_profiles', sa.Column('user_id_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('templates', sa.Column('user_id_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('tasks', sa.Column('owner_id_uuid', postgresql.UUID(as_uuid=True), nullable=True))
    
    # 5. 更新外键表中的UUID值
    op.execute("""
        UPDATE user_profiles 
        SET user_id_uuid = users.id_uuid 
        FROM users 
        WHERE user_profiles.user_id = users.id
    """)
    
    op.execute("""
        UPDATE templates 
        SET user_id_uuid = users.id_uuid 
        FROM users 
        WHERE templates.user_id = users.id
    """)
    
    op.execute("""
        UPDATE tasks 
        SET owner_id_uuid = users.id_uuid 
        FROM users 
        WHERE tasks.owner_id = users.id
    """)
    
    # 6. 删除旧的外键约束
    op.drop_constraint('user_profiles_user_id_fkey', 'user_profiles', type_='foreignkey')
    op.drop_constraint('templates_user_id_fkey', 'templates', type_='foreignkey')
    op.drop_constraint('tasks_owner_id_fkey', 'tasks', type_='foreignkey')
    
    # 7. 删除旧的整数列
    op.drop_column('user_profiles', 'user_id')
    op.drop_column('templates', 'user_id')
    op.drop_column('tasks', 'owner_id')
    
    # 8. 重命名新列
    op.alter_column('user_profiles', 'user_id_uuid', new_column_name='user_id')
    op.alter_column('templates', 'user_id_uuid', new_column_name='user_id')
    op.alter_column('tasks', 'owner_id_uuid', new_column_name='owner_id')
    
    # 9. 删除旧的主键约束和序列
    op.drop_constraint('users_pkey', 'users', type_='primary')
    # 先删除列的默认值，然后删除序列
    op.alter_column('users', 'id', server_default=None)
    op.execute('DROP SEQUENCE IF EXISTS users_id_seq CASCADE')
    op.drop_column('users', 'id')
    
    # 10. 重命名新的UUID列为id
    op.alter_column('users', 'id_uuid', new_column_name='id')
    
    # 11. 创建新的主键约束
    op.create_primary_key('users_pkey', 'users', ['id'])
    
    # 12. 创建新的外键约束
    op.create_foreign_key('user_profiles_user_id_fkey', 'user_profiles', 'users', ['user_id'], ['id'])
    op.create_foreign_key('templates_user_id_fkey', 'templates', 'users', ['user_id'], ['id'])
    op.create_foreign_key('tasks_owner_id_fkey', 'tasks', 'users', ['owner_id'], ['id'])
    
    # 13. 重建索引
    op.create_index('ix_users_id', 'users', ['id'])
    
    # 14. 处理placeholder_mappings的外键约束（如果存在）
    try:
        op.drop_constraint('fk_placeholder_mappings_template_id', 'placeholder_mappings', type_='foreignkey')
    except:
        pass  # 如果约束不存在，忽略错误


def downgrade() -> None:
    """Downgrade schema."""
    # 注意：这个downgrade可能会丢失数据，因为UUID不能完全转换回原始的整数ID
    # 在生产环境中，应该谨慎使用
    
    # 1. 添加新的整数ID列
    op.add_column('users', sa.Column('id_int', sa.Integer(), nullable=True))
    
    # 2. 为现有用户生成新的整数ID
    op.execute("""
        UPDATE users 
        SET id_int = nextval('users_id_seq_new')
    """)
    
    # 这里省略了完整的downgrade逻辑，因为从UUID回到整数ID是一个复杂的过程
    # 在实际应用中，建议不要执行downgrade，或者实现更复杂的回滚逻辑
    
    raise NotImplementedError("Downgrade from UUID to integer ID is not fully implemented")
