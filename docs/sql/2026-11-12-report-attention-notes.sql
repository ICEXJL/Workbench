-- 在业务库中执行；先备份 daily_report。可重复执行，已有列时不修改历史数据。
-- MySQL DDL 隐式提交，建议低峰执行；不要同时启动多个迁移进程。
SET @notes_column_exists = (
  SELECT COUNT(*) FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='daily_report' AND COLUMN_NAME='attention_notes'
);
SET @notes_ddl = IF(@notes_column_exists=0,
  'ALTER TABLE daily_report ADD COLUMN attention_notes TEXT NULL AFTER falling_shop_names',
  'SELECT 1');
PREPARE notes_statement FROM @notes_ddl;
EXECUTE notes_statement;
DEALLOCATE PREPARE notes_statement;

-- 验证
SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='daily_report' AND COLUMN_NAME='attention_notes';

-- 回滚：先回退应用，优先保留可空列（旧版本可忽略），保留已录入内容。
-- 如确需删除，先备份 id/operator_id/report_date/attention_notes 并停止新版应用：
-- ALTER TABLE daily_report DROP COLUMN attention_notes;
