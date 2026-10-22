# 测试环境 SQL

用来自建一套与生产结构一致、但**不含任何真实数据**的测试库。

## 文件

| 文件 | 内容 |
| --- | --- |
| `01-schema.sql` | 13 张表的建表语句（从生产 `SHOW CREATE TABLE` 导出，去掉 AUTO_INCREMENT 当前值） |
| `02-seed.sql` | 最小可用种子数据，76 行，覆盖权限/区域/排序/状态机/物流五类场景 |

## 使用

**先确认执行账号有建库权限**（见下节），然后：

```bash
mysql -u root -p < docs/sql/01-schema.sql
mysql -u root -p < docs/sql/02-seed.sql
```

脚本自带 `DROP DATABASE IF EXISTS workbench_test`，**重复执行会清空并重建测试库**。
只想建表不清库时，删掉第一行 `DROP DATABASE` 即可。

## 权限要求

`01-schema.sql` 需要 `CREATE` 权限（要建库）。当前开发账号 `xjl@%` **只有
`东南亚运营数据` 单库的 ALL PRIVILEGES，没有全局 CREATE**，因此无法用它执行。

有两个选择：

```sql
-- 方案一：授权（需要 root）
GRANT CREATE ON *.* TO 'xjl'@'%';

-- 方案二：让 root 建好库，再把测试库授权给开发账号
CREATE DATABASE workbench_test DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON `workbench_test`.* TO 'xjl'@'%';
FLUSH PRIVILEGES;
```

建好后只需执行 `02-seed.sql`（或把 01 里的 DROP/CREATE 两行去掉再执行）。

## 让后端连测试库

不要改代码，用环境变量覆盖（环境变量优先级高于 `.env`，已实测）：

```bash
export DB_HOST=127.0.0.1
export DB_PORT=3306
export DB_USER=xjl
export DB_PASS='<密码>'
export DB_NAME=workbench_test
export SECRET_KEY='<至少32位的随机串>'
python main.py
```

或临时新建 `backend/.env.test` 并在启动前 `set -a; source .env.test; set +a`。

> 提醒：`init_business_tables()` 会在启动时检查 `denglu.must_change_password` 和
> `daily_report` 的四个列，缺失则 ALTER。本 SQL 已预先建好这些列，正常不会再改表。

## 测试账号

密码统一为 **`test123456`**。`must_change_password` 全部设为 0，避免登录后被强制跳改密页。

| 账号 | 角色 | 说明 |
| --- | --- | --- |
| `admin_test` | admin | 全量数据 |
| `mgr_test` | manager | 管 1 个组长（组长甲） |
| `lead_a` | leader | **组长甲**，带 4 名组员 + 自己 + 主管 = 6 人 |
| `lead_b` | leader | 组长乙，无组员 |
| `op_a` | operator | 运营A，东南亚区，7 天合计 7000 |
| `op_my` | operator | 运营MY，**MY 区**，7 天合计 14000（应排第 1） |
| `op_nodata` | operator | 有店铺、无销售 → `not_ready` |
| `op_nomap` | operator | 无店铺 → `mapping_missing` |

## 刻意保留的生产缺陷

测试环境的价值在于「能复现真实问题」，所以**没有修**这些结构问题，改动处都有 `⚠️` 注释：

| 表 | 缺陷 | 为什么保留 |
| --- | --- | --- |
| `denglu` | 无主键、username 无唯一约束 | 复现「同账号多行取 LIMIT 1 结果不确定」 |
| `dp_ry` | 无主键、无索引 | 复现全表扫描；复现「用姓名而非 id 关联」的根因 |
| `dny_data` | 无主键；金额/订单数/日期都是 varchar | 复现 CAST 转换、空串转 NULL 的真实行为 |
| `org_hierarchy` | `leader_id` / `manager_id` NOT NULL | 复现「没有组长的运营必须挂占位组长」 |
| `operation_security_audit` | 无改密审计 | 复现「改密不留痕」的已知缺口 |

## 种子数据覆盖的场景

| 场景 | 数据设计 | 怎么验证 |
| --- | --- | --- |
| 四角色权限 | 8 个账号覆盖 4 角色 | 各角色登录看菜单与 403 |
| **跨区域组员可见** | 运营MY 的店铺 `qy='MY'`，是组长甲的组员 | 组长甲的人员销售列表**必须**含运营MY；若消失说明 `qy='东南亚'` 过滤被重新引入 |
| 人员销售排序 | 运营MY 14000 > 运营A 7000 > 组长甲 3500 | 按 7 天累计降序 |
| 姓名归一化 | 存在 `组长甲代维护` 的店铺 | 不经 REPLACE 时分组出两行；经 REPLACE 合并为 4100 |
| 状态机 | 三种运营分别对应 available / not_ready / mapping_missing | 调 `/report/daily/mine` 看 `sales_summary.status` |
| 历史快照 | `daily_report` 有 10-18 两条 | 查历史日期应返回 `status=snapshot` |
| 物流五表组装 | SKU-TEST-001 关联 2 柜 / 2 补货 / 2 发货 / 2 映射 | 调 `/logistics/search?query=SKU-TEST-001` |
| 柜级海运量 | C001 的 `load_time=7.16下午` 与发货 `handover=7.16中午` 月日一致 | C001 的 `sea_qty` 应为 200；C002 为 null |
| 未匹配不丢数据 | 映射表里一条 `link_status=UNMATCHED` | 查询结果里该条应保留并标记未匹配 |

## 校验记录

生成后做了静态校验（无建库权限，未能实跑）：

- INSERT 列数 == VALUES 值数：全部一致
- INSERT 引用的列在 schema 中存在：全部一致
- schema 中 NOT NULL 且无默认值的列，INSERT 均已覆盖：全部一致
- 共 17 条 INSERT 语句、76 行数据
- 密码哈希经 `bcrypt.checkpw('test123456', hash)` 验证为 True

**首次在你自己的环境执行时，建议先跑一遍，把报错反馈回来。**
