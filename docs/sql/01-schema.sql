-- =============================================================================
-- 经营数据工作台 · 测试环境建表脚本
-- =============================================================================
-- 用途：在测试/开发环境重建与生产一致的表结构（不含任何真实数据）。
-- 生成方式：从生产库 SHOW CREATE TABLE 导出，仅去除 AUTO_INCREMENT 当前值。
-- 生成日期：2026-10-22
--
-- 使用方式：
--   mysql -u root -p < 01-schema.sql
--   mysql -u root -p workbench_test < 02-seed.sql
--
-- 注意事项：
--   1. 库名默认 workbench_test。若沿用生产的中文库名「东南亚运营数据」，
--      请把下面的 CREATE DATABASE 与 USE 改掉。中文库名可用，
--      但必须由 SQLAlchemy URL.create() 构造连接串，不能手工拼（编码会出错）。
--   2. 本脚本**保留**了生产结构的已知缺陷（缺主键、金额用 varchar 等），
--      目的是让测试环境能复现真实问题。缺陷位置均有 ⚠️ 标注。
--   3. 后端启动会执行 init_business_tables()，可能对 denglu / daily_report
--      做 ALTER。因此这些表必须先由本脚本建好，且执行账号需要有 DDL 权限。
--   4. 字段顺序、字符集、排序规则、索引名均与生产一致，改动前请确认业务影响。
-- =============================================================================

DROP DATABASE IF EXISTS workbench_test;
CREATE DATABASE workbench_test
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE workbench_test;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- -----------------------------------------------------------------------------
-- 1. operator：人员与权限主档
-- -----------------------------------------------------------------------------
-- real_name 有唯一约束，因此姓名不可重复。这一点很重要：
-- 权限范围是用「姓名」关联 dp_ry.yy 的，重名会被合并计算。
CREATE TABLE `operator` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `real_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '姓名(唯一)',
  `staff_no` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '员工编号',
  `department` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '部门',
  `role` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'operator' COMMENT 'operator/leader/manager/admin',
  `status` tinyint NOT NULL COMMENT '1在职 0停用',
  `created_at` datetime NOT NULL COMMENT '创建时间',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_operator_real_name` (`real_name`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='运营人员档案';

-- -----------------------------------------------------------------------------
-- 2. denglu：登录账号
-- -----------------------------------------------------------------------------
-- ⚠️ 已知缺陷：此表**没有主键**，username 也没有唯一约束。
--    同一个 username 理论上可以插多行，find_user 用 LIMIT 1 取第一条，
--    结果不确定。测试环境保留该结构以复现问题，生产修复需评估迁移。
-- ⚠️ password 明文列在生产已清零（保留空字符串），认证只走 password_hash。
CREATE TABLE `denglu` (
  `username` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '登录账号',
  `password` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '明文密码（兼容旧逻辑，建议存hash）',
  `password_hash` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT 'bcrypt 密码哈希（实际认证用）',
  `operator_id` int unsigned DEFAULT NULL COMMENT '关联 operator.id',
  `must_change_password` tinyint(1) NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  ROW_FORMAT=DYNAMIC COMMENT='登录账号表（登录认证，经operator_id关联人员档案）';

-- -----------------------------------------------------------------------------
-- 3. org_hierarchy：运营-组长-主管组织归属
-- -----------------------------------------------------------------------------
-- 这张表是权限数据范围的唯一依据。
-- 注意 leader_id / manager_id 都 NOT NULL，所以「没有组长的运营」无法表达，
-- 必须挂一个占位组长。
CREATE TABLE `org_hierarchy` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `operator_id` int unsigned NOT NULL COMMENT '运营人员operator.id',
  `leader_id` int unsigned NOT NULL COMMENT '所属组长operator.id',
  `manager_id` int unsigned NOT NULL COMMENT '所属主管operator.id',
  `dept` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '所在部门',
  `effective_from` date DEFAULT NULL COMMENT '归属生效日期',
  `effective_to` date DEFAULT NULL COMMENT '归属失效日期(NULL=现行)',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_org_chain` (`operator_id`,`leader_id`,`manager_id`) USING BTREE,
  KEY `idx_org_oper` (`operator_id`) USING BTREE,
  KEY `idx_org_leader` (`leader_id`) USING BTREE,
  KEY `idx_org_manager` (`manager_id`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='运营-组长-主管组织归属';

-- -----------------------------------------------------------------------------
-- 4. dp_ry：店铺-人员映射（权限与销售的核心连接表）
-- -----------------------------------------------------------------------------
-- ⚠️ 已知缺陷：无主键、无索引。全表 1487 行级别，按 yy / dpbh 过滤时全表扫描。
-- ⚠️ 关键设计：本表用**姓名(varchar)** 关联 operator，不是 operator_id。
--    这是权限算法必须做姓名归一化（REPLACE '代维护'、_W/_N 别名）的根因。
-- ⚠️ qy 区域字段取值：东南亚 / TH / MY / BR / 墨西哥。
CREATE TABLE `dp_ry` (
  `xh` int NOT NULL COMMENT '序号',
  `dpbh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '店铺编号',
  `qy` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '区域',
  `fhck` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '发货仓库',
  `yy` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '运营',
  `zm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '组名',
  `zg` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '主管',
  `fgs` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '分公司',
  `bm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '部门',
  `jc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '简称',
  `fbs` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'FBS',
  `rzsj` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '入职时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='店铺-人员信息表';

-- -----------------------------------------------------------------------------
-- 5. dny_data：每日销售事实
-- -----------------------------------------------------------------------------
-- ⚠️ 已知缺陷：无主键（可重复导入）、金额与订单数是 varchar 而非 decimal。
--    代码里靠 CAST(NULLIF(TRIM(xse),'') AS DECIMAL) 转换，空串会变成 NULL。
--    测试环境必须保持 varchar，否则测不出真实的排序/聚合行为。
-- 索引：idx_dny_rq_dpbh 是唯一索引，复合 (rq, dpbh)，支撑按日期筛+店铺关联。
CREATE TABLE `dny_data` (
  `dpbh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '店铺编号',
  `dds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '订单数',
  `xse` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '订单销售额',
  `ckh` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '仓库号',
  `rq` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '日期',
  KEY `idx_dny_rq_dpbh` (`rq`,`dpbh`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
  ROW_FORMAT=DYNAMIC COMMENT='东南亚店铺实际销售数据（订单数/销售额/仓库/日期）';

-- -----------------------------------------------------------------------------
-- 6. daily_report：运营日报
-- -----------------------------------------------------------------------------
-- uk_report_user_date 是 upsert 的依据（operator_id + report_date）。
-- submitted_at 默认 CURRENT_TIMESTAMP，且 upsert 时会刷新——注意写路径验证会改它。
CREATE TABLE `daily_report` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `operator_id` int unsigned NOT NULL COMMENT '关联 operator.id',
  `report_date` date NOT NULL COMMENT '填报日期',
  `monthly_sales` decimal(18,2) NOT NULL DEFAULT '0.00' COMMENT '累计销售额',
  `actual_listings` int NOT NULL DEFAULT '0' COMMENT '实际上架数量',
  `optimized_products` int NOT NULL DEFAULT '0' COMMENT '产品优化数量',
  `weekly_late_exceed` tinyint DEFAULT NULL COMMENT '周延迟/取消率超标(周二,可空)',
  `violation_flag` tinyint NOT NULL DEFAULT '0' COMMENT '是否触发违规/扣分',
  `infringement_flag` tinyint NOT NULL DEFAULT '0' COMMENT '是否链接侵权/禁售',
  `weekly_badreview_links` int DEFAULT NULL COMMENT '周商责差评>=3链接数(周二)',
  `weekly_misship_links` int DEFAULT NULL COMMENT '周错发/破损>=3链接数(周二)',
  `review_ontime_rate` decimal(5,2) NOT NULL DEFAULT '0.00' COMMENT '备货审核及时率(%)',
  `reverse_product_cnt` int NOT NULL DEFAULT '0' COMMENT '产品反推数量',
  `fluctuate_shop_cnt` int NOT NULL DEFAULT '0' COMMENT '浮动>=20%店铺数',
  `rising_shop_count` int NOT NULL DEFAULT '0',
  `rising_shop_names` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `falling_shop_count` int NOT NULL DEFAULT '0',
  `falling_shop_names` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `attention_notes` text CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci,
  `all_issues_resolved` tinyint NOT NULL DEFAULT '0' COMMENT '当天问题是否都解决',
  `submitted_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '提交时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_report_user_date` (`operator_id`,`report_date`) USING BTREE,
  KEY `idx_report_date` (`report_date`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  ROW_FORMAT=DYNAMIC COMMENT='运营日报';

-- -----------------------------------------------------------------------------
-- 7. target_monthly：月度目标
-- -----------------------------------------------------------------------------
CREATE TABLE `target_monthly` (
  `id` int unsigned NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `operator_id` int unsigned NOT NULL COMMENT '关联 operator.id',
  `department` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL COMMENT '所属部门',
  `month` char(7) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '月份 YYYY-MM',
  `sales_target` decimal(18,2) NOT NULL DEFAULT '0.00' COMMENT '月销售额目标',
  `listing_target` int NOT NULL DEFAULT '0' COMMENT '上架数量目标',
  `status` tinyint NOT NULL COMMENT '1启用 0停用',
  `updated_at` datetime NOT NULL COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE KEY `uk_target_oper_month` (`operator_id`,`month`) USING BTREE,
  KEY `idx_target_month` (`month`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  ROW_FORMAT=DYNAMIC COMMENT='运营月度目标(按月更新,含部门)';

-- -----------------------------------------------------------------------------
-- 8. operation_security_audit：安全审计
-- -----------------------------------------------------------------------------
-- 由 init_business_tables() 自动创建，这里预建以保证测试可重复。
-- action 取值：login_failed / login_blocked_account / login_blocked_ip / deny_role_required
-- ⚠️ 没有改密审计（改密码不落此表），这是已知缺口。
CREATE TABLE `operation_security_audit` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `action` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `detail` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_audit_created_at` (`created_at`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  ROW_FORMAT=DYNAMIC;

-- -----------------------------------------------------------------------------
-- 9. logistics_sku：SKU 主档（仓内唯一）
-- -----------------------------------------------------------------------------
CREATE TABLE `logistics_sku` (
  `sku` varchar(64) NOT NULL COMMENT '系统SKU',
  `warehouse` varchar(64) NOT NULL DEFAULT 'PH-SAN-RAFAEL-3' COMMENT '发货仓（隔离键，仓内唯一）',
  `product_name` varchar(255) DEFAULT NULL COMMENT '产品中文名',
  `custom_sku` varchar(128) DEFAULT NULL COMMENT '自定义SKU',
  `product_status` varchar(32) DEFAULT NULL COMMENT '产品状态 正常/清库/停产',
  `available_qty` decimal(14,3) DEFAULT NULL COMMENT '可用库存数',
  `purchasing_qty` decimal(14,3) DEFAULT NULL COMMENT '采购中数',
  `price` decimal(14,4) DEFAULT NULL COMMENT '采购价',
  `snap_date` date DEFAULT NULL COMMENT '库存快照日',
  `container_cnt` int NOT NULL DEFAULT '0' COMMENT '关联货柜数',
  `replenish_cnt` int NOT NULL DEFAULT '0' COMMENT '补货记录数',
  `pending_cnt` int NOT NULL DEFAULT '0' COMMENT '未发货采购单数',
  `shipment_cnt` int NOT NULL DEFAULT '0' COMMENT '已发货记录数',
  PRIMARY KEY (`sku`,`warehouse`),
  KEY `idx_sku` (`sku`),
  KEY `idx_wh` (`warehouse`),
  KEY `idx_name` (`product_name`),
  KEY `idx_custom` (`custom_sku`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='SKU 主档（仓内唯一）';

-- -----------------------------------------------------------------------------
-- 10. logistics_container：货柜物流（SKU × 柜）
-- -----------------------------------------------------------------------------
-- 主键顺序含 container_no（2026-10-15 迁移后）。
-- 所有主键列都 NOT NULL 且有 DEFAULT 占位值（'未知' / '未填' / ''），
-- 因为源数据来自人工填写的 Excel，缺失很常见，不能因缺失丢行。
CREATE TABLE `logistics_container` (
  `sku` varchar(64) NOT NULL COMMENT '系统SKU',
  `warehouse` varchar(64) NOT NULL DEFAULT 'PH-SAN-RAFAEL-3' COMMENT '发货仓（隔离键）★ 注意与 warehouse_desc 区分：那是目的仓',
  `container_no` varchar(32) NOT NULL DEFAULT '' COMMENT '货柜箱号/柜号，来源于海运表 J 列',
  `load_time` varchar(64) NOT NULL DEFAULT '未知' COMMENT '★主键列，禁 NULL。装柜时间原文 「7.16下午」',
  `status` varchar(16) NOT NULL COMMENT '在途 / 已签收',
  `warehouse_desc` varchar(191) NOT NULL DEFAULT '未填' COMMENT '★主键列，禁 NULL。仓库 「三仓628+六仓265」',
  `carrier` varchar(64) NOT NULL DEFAULT '未填' COMMENT '★主键列，禁 NULL。货代',
  `stage_seq` tinyint NOT NULL DEFAULT '0' COMMENT '进度 1-5，装载期算好',
  `stage_name` varchar(16) DEFAULT NULL COMMENT '装柜/开船/到港/清关/送仓',
  `eta` varchar(64) DEFAULT NULL COMMENT '预计送仓',
  `actual_in` varchar(64) DEFAULT NULL COMMENT '实际送仓',
  `tracking` text COMMENT '跟单轨迹全文（保留原文，便于改词表重算）',
  `sort_key` int NOT NULL DEFAULT '1' COMMENT '页面排序序号（在途优先+时间倒序）',
  PRIMARY KEY (`sku`,`warehouse`,`container_no`,`load_time`,`warehouse_desc`,`carrier`),
  KEY `idx_sku` (`sku`),
  KEY `idx_wh` (`sku`,`warehouse`,`sort_key`),
  KEY `idx_status` (`status`),
  KEY `idx_stage` (`stage_seq`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='货柜物流（SKU×柜）';

-- -----------------------------------------------------------------------------
-- 11. logistics_replenish：补货记录
-- -----------------------------------------------------------------------------
CREATE TABLE `logistics_replenish` (
  `sku` varchar(64) NOT NULL,
  `warehouse` varchar(64) NOT NULL DEFAULT 'PH-SAN-RAFAEL-3' COMMENT '发货仓（隔离键）',
  `reg_date` varchar(32) NOT NULL DEFAULT '-' COMMENT '★主键列，禁止 NULL（缺失填 -）',
  `air_qty` decimal(14,3) DEFAULT NULL COMMENT '空运备货数量',
  `sea_qty` decimal(14,3) DEFAULT NULL COMMENT '海运备货数量',
  `operator_name` varchar(64) NOT NULL DEFAULT '未填' COMMENT '★主键列，禁止 NULL（缺失填「未填」）',
  PRIMARY KEY (`sku`,`warehouse`,`reg_date`,`operator_name`),
  KEY `idx_sku` (`sku`),
  KEY `idx_wh` (`sku`,`warehouse`,`reg_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='补货记录';

-- -----------------------------------------------------------------------------
-- 12. logistics_shipment：采购与发货记录（两阶段合一）
-- -----------------------------------------------------------------------------
-- record_type: PENDING 未发货 / EMITTED 已发货
-- 柜级海运量 = 按 handover 与货柜 load_time 做「月日匹配」后汇总 qty2。
CREATE TABLE `logistics_shipment` (
  `sku` varchar(64) NOT NULL,
  `warehouse` varchar(64) NOT NULL DEFAULT 'PH-SAN-RAFAEL-3' COMMENT '发货仓（隔离键）',
  `record_type` varchar(16) NOT NULL COMMENT 'PENDING 未发货 / EMITTED 已发货',
  `reg_date` varchar(32) NOT NULL DEFAULT '-' COMMENT '★主键列，禁止 NULL（缺失填 -）。原为 DATE，为主键去重改为 VARCHAR',
  `order_qty` decimal(14,3) DEFAULT NULL COMMENT '下单数量',
  `qty2` decimal(14,3) DEFAULT NULL COMMENT '已发货=发货总数 / 未发货=入库数量',
  `badge_no` varchar(64) NOT NULL DEFAULT '无条码' COMMENT '★主键列，禁止 NULL（缺失填「无条码」）',
  `is_done` tinyint DEFAULT NULL COMMENT '1完成/0未完成/NULL未知（#N/A 等错误值转 NULL，不猜）',
  `status_raw` varchar(32) DEFAULT NULL COMMENT '原始状态值（是/否/True/#N/A/已判定…原样保留）',
  `handover` varchar(191) NOT NULL DEFAULT '-' COMMENT '★主键列，禁止 NULL（缺失填 -）。给货时间可能多值 「8.25中午+8.26中午」',
  `carrier` varchar(191) DEFAULT NULL COMMENT '货代（与给货时间按 + 位置对齐）',
  PRIMARY KEY (`sku`,`warehouse`,`record_type`,`reg_date`,`badge_no`,`handover`),
  KEY `idx_sku` (`sku`),
  KEY `idx_wh` (`sku`,`warehouse`,`record_type`),
  KEY `idx_badge` (`badge_no`),
  KEY `idx_date` (`reg_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='采购与发货记录（两阶段合一）';

-- -----------------------------------------------------------------------------
-- 13. logistics_shipment_container_map：发货批次 ↔ 货柜映射
-- -----------------------------------------------------------------------------
CREATE TABLE `logistics_shipment_container_map` (
  `sku` varchar(64) NOT NULL,
  `warehouse` varchar(64) NOT NULL DEFAULT 'PH-SAN-RAFAEL-3' COMMENT '发货仓（隔离键）',
  `badge_no` varchar(64) NOT NULL DEFAULT '无条码' COMMENT '★主键列，禁 NULL',
  `handover` varchar(64) NOT NULL DEFAULT '-',
  `carrier` varchar(64) DEFAULT NULL,
  `container_key` varchar(191) NOT NULL COMMENT '装柜时间|货代|仓库',
  `link_status` varchar(16) NOT NULL DEFAULT 'MATCHED' COMMENT 'MATCHED / UNMATCHED（找不到柜时写「未匹配|...」占位，不丢数据）',
  PRIMARY KEY (`sku`,`warehouse`,`badge_no`,`container_key`),
  KEY `idx_sku` (`sku`),
  KEY `idx_wh` (`sku`,`warehouse`),
  KEY `idx_badge` (`badge_no`),
  KEY `idx_status` (`link_status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='发货批次↔货柜 映射（27,008 行）';

SET FOREIGN_KEY_CHECKS = 1;

-- =============================================================================
-- 建表完成。下一步执行 02-seed.sql 灌入最小测试数据。
-- =============================================================================
