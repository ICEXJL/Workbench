-- Manual one-time migration for logistics_container.
-- Do not execute automatically on application startup.
-- Back up the table first and confirm its current primary key is:
-- (sku, warehouse, load_time, warehouse_desc, carrier).

ALTER TABLE logistics_container
  ADD COLUMN container_no VARCHAR(32) NOT NULL DEFAULT ''
    COMMENT '货柜箱号/柜号，来源于海运表 J 列' AFTER warehouse,
  DROP PRIMARY KEY,
  ADD PRIMARY KEY (sku, warehouse, container_no, load_time, warehouse_desc, carrier);

-- Verify the column and primary-key order after applying the migration.
SHOW CREATE TABLE logistics_container;

-- Rollback preflight. This must return no rows before the rollback below is safe.
-- If the importer has loaded two containers with the same old key but different
-- container_no values, keep the new key or reconcile those rows before rollback.
-- SELECT sku, warehouse, load_time, warehouse_desc, carrier, COUNT(*) AS row_count
--   FROM logistics_container
--  GROUP BY sku, warehouse, load_time, warehouse_desc, carrier
-- HAVING COUNT(*) > 1;

-- Rollback, only after the preflight returns no rows:
-- ALTER TABLE logistics_container
--   DROP PRIMARY KEY,
--   DROP COLUMN container_no,
--   ADD PRIMARY KEY (sku, warehouse, load_time, warehouse_desc, carrier);
