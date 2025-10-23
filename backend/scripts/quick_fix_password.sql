-- 快速修复数据源密码
-- 使用方法: psql -U postgres -d autoreport -f scripts/quick_fix_password.sql

-- 查看当前所有数据源
SELECT
    id,
    name,
    source_type,
    doris_username,
    LENGTH(doris_password) as password_length,
    SUBSTRING(doris_password, 1, 10) as password_prefix
FROM data_sources
WHERE source_type = 'doris';

-- 示例：更新数据源密码为明文
-- 请根据实际情况修改 'your_actual_password' 和数据源ID
-- UPDATE data_sources
-- SET doris_password = 'your_actual_password'
-- WHERE id = 'your-datasource-id';

-- 提示：如果不确定密码，请检查数据源创建时的配置
