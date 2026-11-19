-- 2026-11-16 日报表新增「上架链接 ID」字段
--
-- 背景：运营日报填报页「销售与上架」模块需要记录当天的上架链接 ID，
--       该字段也需要在日报进度列表中展示。
--
-- 影响面：daily_report 表新增 1 个可空列，不改动任何现有列和数据。
-- 执行方式：手工执行，不由 FastAPI 启动时自动运行。
--
-- 类型说明：使用 TEXT 而非 VARCHAR(255)。
--   一个运营每天可能要填十几个上架链接 ID（19 位或 11 位数字，空格分隔），
--   255 字符只够 12 个左右，会造成静默截断。TEXT 上限 65535 字节，
--   应用层限制为 4000 字符，足够日常使用。
--
-- 回滚：
--   ALTER TABLE daily_report DROP COLUMN listing_link_id;

ALTER TABLE daily_report
  ADD COLUMN listing_link_id TEXT NULL COMMENT '上架链接ID（质量与审核模块填写）'
  AFTER reverse_product_cnt;

-- 若已按 VARCHAR(255) 建过该字段，用下面这条加宽（不会丢数据）：
-- ALTER TABLE daily_report MODIFY COLUMN listing_link_id TEXT NULL
--   COMMENT '上架链接ID（质量与审核模块填写）';

-- 验证
-- SHOW COLUMNS FROM daily_report LIKE 'listing_link_id';
