"""add_template_placeholders_tables

Revision ID: ee371844bf5c
Revises: 242196232698
Create Date: 2025-08-17 15:46:06.340707

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'ee371844bf5c'
down_revision: Union[str, Sequence[str], None] = '242196232698'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add template placeholders support tables."""
    
    # 首先检查表是否已存在，如果不存在则创建
    
    # 创建模板占位符配置表
    op.execute("""
        CREATE TABLE IF NOT EXISTS template_placeholders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id UUID NOT NULL REFERENCES templates(id) ON DELETE CASCADE,
            placeholder_name VARCHAR(255) NOT NULL,
            placeholder_text VARCHAR(500) NOT NULL,
            placeholder_type VARCHAR(50) NOT NULL,
            content_type VARCHAR(50) NOT NULL,
            
            -- Agent分析结果存储
            agent_analyzed BOOLEAN NOT NULL DEFAULT FALSE,
            target_database VARCHAR(100),
            target_table VARCHAR(100),
            required_fields JSONB,
            generated_sql TEXT,
            sql_validated BOOLEAN NOT NULL DEFAULT FALSE,
            
            -- 执行配置
            execution_order INTEGER NOT NULL DEFAULT 1,
            cache_ttl_hours INTEGER NOT NULL DEFAULT 24,
            is_required BOOLEAN NOT NULL DEFAULT TRUE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            
            -- Agent配置
            agent_workflow_id VARCHAR(100),
            agent_config JSONB DEFAULT '{}'::jsonb,
            
            -- 元数据
            description TEXT,
            confidence_score FLOAT NOT NULL DEFAULT 0.0,
            
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE,
            analyzed_at TIMESTAMP WITH TIME ZONE,
            
            CONSTRAINT uq_template_placeholder_name UNIQUE (template_id, placeholder_name)
        );
    """)

    # 创建占位符值存储表
    op.execute("""
        CREATE TABLE IF NOT EXISTS placeholder_values (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            placeholder_id UUID NOT NULL REFERENCES template_placeholders(id) ON DELETE CASCADE,
            data_source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
            
            -- 执行结果
            raw_query_result JSONB,
            processed_value JSONB,
            formatted_text TEXT,
            
            -- 执行元数据
            execution_sql TEXT,
            execution_time_ms INTEGER,
            row_count INTEGER NOT NULL DEFAULT 0,
            success BOOLEAN NOT NULL DEFAULT TRUE,
            error_message TEXT,
            
            -- 缓存管理
            cache_key VARCHAR(255),
            expires_at TIMESTAMP WITH TIME ZONE,
            hit_count INTEGER NOT NULL DEFAULT 0,
            last_hit_at TIMESTAMP WITH TIME ZONE,
            
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)

    # 创建模板执行历史表
    op.execute("""
        CREATE TABLE IF NOT EXISTS template_execution_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id UUID NOT NULL REFERENCES templates(id),
            data_source_id UUID NOT NULL REFERENCES data_sources(id),
            user_id UUID REFERENCES users(id),
            
            -- 执行信息
            execution_type VARCHAR(50) NOT NULL,
            status VARCHAR(50) NOT NULL,
            
            -- 阶段标记
            analysis_completed BOOLEAN NOT NULL DEFAULT FALSE,
            sql_validation_completed BOOLEAN NOT NULL DEFAULT FALSE,
            data_extraction_completed BOOLEAN NOT NULL DEFAULT FALSE,
            report_generation_completed BOOLEAN NOT NULL DEFAULT FALSE,
            
            -- 性能指标
            total_duration_ms INTEGER,
            analysis_duration_ms INTEGER,
            extraction_duration_ms INTEGER,
            generation_duration_ms INTEGER,
            
            -- 结果信息
            placeholders_analyzed INTEGER NOT NULL DEFAULT 0,
            placeholders_extracted INTEGER NOT NULL DEFAULT 0,
            cache_hit_rate FLOAT NOT NULL DEFAULT 0.0,
            output_file_path VARCHAR(500),
            output_file_size INTEGER,
            
            -- 错误信息
            error_details JSONB,
            failed_placeholders JSONB,
            
            start_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            end_time TIMESTAMP WITH TIME ZONE
        );
    """)

    # 创建索引以提高查询性能
    op.execute("CREATE INDEX IF NOT EXISTS ix_template_placeholders_template_id ON template_placeholders (template_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_template_placeholders_analyzed ON template_placeholders (agent_analyzed, is_active);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_template_placeholders_execution_order ON template_placeholders (template_id, execution_order);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placeholder_values_cache_key ON placeholder_values (cache_key);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placeholder_values_expires_at ON placeholder_values (expires_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placeholder_values_placeholder_datasource ON placeholder_values (placeholder_id, data_source_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_template_execution_history_template_time ON template_execution_history (template_id, start_time);")


def downgrade() -> None:
    """Remove template placeholders support tables."""
    
    # 删除索引
    op.execute("DROP INDEX IF EXISTS ix_template_execution_history_template_time;")
    op.execute("DROP INDEX IF EXISTS ix_placeholder_values_placeholder_datasource;")
    op.execute("DROP INDEX IF EXISTS ix_placeholder_values_expires_at;")
    op.execute("DROP INDEX IF EXISTS ix_placeholder_values_cache_key;")
    op.execute("DROP INDEX IF EXISTS ix_template_placeholders_execution_order;")
    op.execute("DROP INDEX IF EXISTS ix_template_placeholders_analyzed;")
    op.execute("DROP INDEX IF EXISTS ix_template_placeholders_template_id;")
    
    # 删除表
    op.execute("DROP TABLE IF EXISTS template_execution_history;")
    op.execute("DROP TABLE IF EXISTS placeholder_values;")
    op.execute("DROP TABLE IF EXISTS template_placeholders;")
