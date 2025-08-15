"""add_agent_orchestration_support_v2

Revision ID: f2de3ebc898b
Revises: 9a86d0156dca
Create Date: 2025-08-15 13:48:29.714104

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2de3ebc898b'
down_revision: Union[str, Sequence[str], None] = '9a86d0156dca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enum types are already created by init-db.sql script
    # No need to create them again
    
    # Create task_executions table using raw SQL to avoid enum creation issues
    op.execute("""
        CREATE TABLE task_executions (
            id SERIAL PRIMARY KEY,
            execution_id UUID,
            task_id INTEGER NOT NULL REFERENCES tasks(id),
            execution_status taskstatus,
            workflow_type agentworkflowtype,
            workflow_definition JSONB,
            agent_execution_plan JSONB,
            current_step VARCHAR(255),
            execution_context JSONB,
            input_parameters JSONB,
            processing_config JSONB,
            execution_result JSONB,
            output_artifacts JSONB,
            error_details TEXT,
            error_trace TEXT,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            total_duration INTEGER,
            agent_execution_times JSONB,
            progress_percentage INTEGER,
            progress_details JSONB,
            celery_task_id VARCHAR(255),
            worker_node VARCHAR(255),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    op.execute("CREATE UNIQUE INDEX ix_task_executions_execution_id ON task_executions (execution_id)")
    op.execute("CREATE INDEX ix_task_executions_id ON task_executions (id)")
    
    # Add new columns to tasks table using raw SQL
    op.execute("ALTER TABLE tasks ADD COLUMN status taskstatus")
    op.execute("ALTER TABLE tasks ADD COLUMN processing_mode processingmode")
    op.execute("ALTER TABLE tasks ADD COLUMN workflow_type agentworkflowtype")
    op.add_column('tasks', sa.Column('orchestration_config', sa.JSON(), nullable=True))
    op.add_column('tasks', sa.Column('max_context_tokens', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('enable_compression', sa.Boolean(), nullable=True))
    op.add_column('tasks', sa.Column('compression_threshold', sa.Float(), nullable=True))
    op.add_column('tasks', sa.Column('execution_count', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('success_count', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('failure_count', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('last_execution_at', sa.DateTime(), nullable=True))
    op.add_column('tasks', sa.Column('average_execution_time', sa.Float(), nullable=True))
    op.add_column('tasks', sa.Column('average_token_usage', sa.Integer(), nullable=True))
    op.add_column('tasks', sa.Column('last_execution_duration', sa.Float(), nullable=True))
    
    # Set default values for existing records
    op.execute("UPDATE tasks SET status = 'pending' WHERE status IS NULL")
    op.execute("UPDATE tasks SET processing_mode = 'intelligent' WHERE processing_mode IS NULL")
    op.execute("UPDATE tasks SET workflow_type = 'simple_report' WHERE workflow_type IS NULL")
    op.execute("UPDATE tasks SET execution_count = 0 WHERE execution_count IS NULL")
    op.execute("UPDATE tasks SET success_count = 0 WHERE success_count IS NULL")
    op.execute("UPDATE tasks SET failure_count = 0 WHERE failure_count IS NULL")
    op.execute("UPDATE tasks SET max_context_tokens = 32000 WHERE max_context_tokens IS NULL")
    op.execute("UPDATE tasks SET enable_compression = true WHERE enable_compression IS NULL")
    op.execute("UPDATE tasks SET compression_threshold = 0.8 WHERE compression_threshold IS NULL")


def downgrade() -> None:
    """Downgrade schema."""
    # Drop columns from tasks table
    op.drop_column('tasks', 'last_execution_duration')
    op.drop_column('tasks', 'average_token_usage')
    op.drop_column('tasks', 'average_execution_time')
    op.drop_column('tasks', 'last_execution_at')
    op.drop_column('tasks', 'failure_count')
    op.drop_column('tasks', 'success_count')
    op.drop_column('tasks', 'execution_count')
    op.drop_column('tasks', 'compression_threshold')
    op.drop_column('tasks', 'enable_compression')
    op.drop_column('tasks', 'max_context_tokens')
    op.drop_column('tasks', 'orchestration_config')
    op.drop_column('tasks', 'workflow_type')
    op.drop_column('tasks', 'processing_mode')
    op.drop_column('tasks', 'status')
    
    # Drop task_executions table
    op.drop_index(op.f('ix_task_executions_id'), table_name='task_executions')
    op.drop_index(op.f('ix_task_executions_execution_id'), table_name='task_executions')
    op.drop_table('task_executions')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS agentworkflowtype")
    op.execute("DROP TYPE IF EXISTS processingmode")
    op.execute("DROP TYPE IF EXISTS taskstatus")
