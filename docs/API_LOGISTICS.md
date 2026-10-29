# 物流查询 API

物流查询接口提供登录用户可用的只读物流视图。接口挂载在 `/api/v1` 下，不提供新增、修改、删除、导入或写回能力，也不会修改物流表或其他数据库数据。

## 仓库列表

### `GET /api/v1/logistics/warehouses`

返回当前物流资料中可用的发货仓库。仓库按 `logistics_sku.warehouse` 汇总，只返回非空仓库，并按仓库名称排序。

请求不需要业务参数，但必须携带当前登录用户的认证信息。

响应结构：

```json
{
  "warehouses": [
    {
      "warehouse": "PH-A",
      "sku_count": 123
    }
  ],
  "default_warehouse": null
}
```

`sku_count` 是该仓库中去重后的 SKU 数量。当前没有固定默认仓库，因此 `default_warehouse` 为 `null`。

## 物流搜索

### `GET /api/v1/logistics/search`

请求参数：

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `q` | string | 是 | SKU、自定义 SKU 或产品名关键词。多个查询词可使用反斜杠、换行或逗号分隔；最多处理 20 个非空查询词。 |
| `warehouse` | string | 否 | 仓库名称。省略或传空值表示全部仓库；传值时只能使用仓库列表接口返回的仓库。 |

查询规则：

- 一个或多个查询词先按 `sku` 或 `custom_sku` 精确匹配。
- 若系统 SKU 没有 `logistics_sku` 档案，仍可通过 `logistics_container.sku` 找到货柜记录；仅当货柜记录具有有效 `warehouse` 时才会纳入结果。
- 只有一个查询词且没有精确匹配时，才按 `product_name` 做包含匹配；产品名匹配最多解析 20 个 SKU。
- 返回结果按 SKU 去重，最多返回 20 个 SKU。
- 不传 `warehouse` 是全部仓库范围；传入仓库后只返回该单仓的数据。全部仓库查询会在同一个 SKU 下保留各仓库的独立资料。

成功响应的固定外层结构：

```json
{
  "items": [
    {
      "sku": "1001",
      "custom_sku": "C-1",
      "product_name": "示例产品",
      "warehouses": [
        {
          "warehouse": "PH-A",
          "profile": { "sku": "1001", "warehouse": "PH-A" },
          "profiles": [{ "sku": "1001", "warehouse": "PH-A" }],
          "containers": [],
          "replenish": [],
          "shipments": [
            {
              "sku": "1001",
              "warehouse": "PH-A",
              "badge_no": "B-1"
            }
          ]
        }
      ]
    }
  ],
  "query": "1001",
  "warehouse": null
}
```

`items` 下的 `warehouses` 是按仓库分组的结果。每个仓库组固定包含 `profile`、`profiles`、`containers`、`replenish` 和 `shipments`：

- `profile` 是按当前结果顺序选出的代表性首个产品资料行；`profiles` 保留该 SKU/仓库命中的全部产品资料行。接口不暗示或定义产品资料之间存在确定的业务优先级。
- `containers` 是货柜资料行，包含源表 J 列解析出的 `container_no`；旧记录或源字段无柜号时该字段为空字符串。每个货柜额外带 `sea_qty`，见下文说明。
- `replenish` 是补货资料行。
- `shipments` 是发货资料行。

> **2026-10-24 变更**：不再返回 `container_maps`。`logistics_shipment_container_map`
> 已移出查询链，原因见文末「映射表为何不在查询中」。

上述明细对象来自对应数据表的行，保留表中实际字段；接口保证的是外层分组和数组结构，不额外改名或推测业务字段。无匹配明细时使用空数组。

空查询且未指定仓库时不会读取物流表，返回：

```json
{
  "items": [],
  "query": "",
  "warehouse": null
}
```

## 数据来源与查询约束

接口只读以下四张表：

1. `logistics_sku`：产品资料、SKU、产品名、仓库和库存等档案信息。
2. `logistics_container`：货柜资料。
3. `logistics_replenish`：补货资料。
4. `logistics_shipment`：发货资料。

精确查询先在 `logistics_sku` 按 `sku` 或 `custom_sku` 确定结果。产品名 fallback 则先在 `logistics_sku` 按 `product_name` 和 `warehouse` 解析最多 20 个 SKU；随后只对 `logistics_container`、`logistics_replenish`、`logistics_shipment` 三张 detail 表分别执行带 `sku + warehouse` 条件的查询，最后在服务层按 `sku + warehouse` 组装结果。业务表之间禁止串联 `JOIN`，以避免一对多数据产生笛卡尔积和重复结果。全部仓库查询使用允许的空仓库参数表示全部范围。仓库列表接口单独按 `logistics_sku.warehouse` 汇总仓库和 SKU 数量。

物流查询不接入组织层级范围。所有登录角色都可查看全部仓库，也可切换到单仓范围；前端选择不能替代后端的仓库校验。

## 页面字段口径

- 一个 `logistics_container` 行显示为一张纵向货柜卡。标题使用 `箱号/柜号：<container_no>`，没有柜号时显示“未提供”，不再按页面序号命名；卡片内的跟单轨迹只读取本行 `tracking`，不会把不同货柜的轨迹合并。
- **货柜排序（2026-10-24 调整）**：未送仓的货柜整组排在已送仓之前；未送仓内部按 `stage_seq` 降序（已到「送仓」环节只差签收的排最前，其次到港、开船），同阶段按装柜时间倒序；已送仓内部按 `actual_in` 倒序（最近送仓的在前）。判断「已送仓」看 `actual_in` 是否有值或 `status` 含已签收/已送仓/已入仓，**不看 `stage_seq`**——因为存在 `stage_seq=5` 但状态仍为在途的记录。源日期只有月日时，优先从装柜时间推导年份。
  - 调整原因：全库 133,190 个货柜中 121,558 个（91%）已签收，原「已送仓优先」把在途柜压到列表底部，运营需要翻很多屏才能看到还没到的柜。
  - `logistics_container.sort_key` 列在全库均为 0（ETL 未维护），不再作为排序依据。
- 货柜阶段使用 ETL 预计算的 `stage_seq` 和 `stage_name`。阶段依次为装柜、开船、到港、清关、送仓；缺少预计算值时前端才从状态与轨迹文本回退判断。
- 补货区仅展示最近两个月的记录，并按 `reg_date` 从新到旧排列；无法解析日期格式的记录会保留在末尾，避免误隐藏原始数据。没有可展示的补货记录时，页面隐藏补货区。
- 货柜卡片中的“本柜海运备货数”来自同一 SKU、发货仓和装柜/给货日期匹配的 `EMITTED` 发货记录 `qty2`；例如装柜时间 `9.4` 会匹配给货时间 `2026-09-04`。无匹配发货记录时返回空值，前端显示 `-`。`logistics_replenish.sea_qty` 仍只用于补货记录表，不再重复显示为每个货柜的柜级数量。
- 卡片保留装柜时间、目的仓、货代、进度和本柜轨迹；预计送仓/实际送仓信息小模块不再单独显示，实际送仓时间仍用于排序。
- 未发货与已发货记录在页面合并为一个海运记录表，并保留 `record_type` 作为记录类型。
- 海运记录按 `reg_date` 从新到旧排序；登记时间为空或无法解析的记录稳定排在末尾。
- `logistics_shipment.qty2` 按记录类型显示：`PENDING` 为“入库数量”，`EMITTED` 为“发货总数”。`status_raw` 保留原始判定文本；`is_done` 的 `NULL` 显示为“未知”，不会误判成未完成。

## 映射表为何不在查询中

`logistics_shipment_container_map` 自 2026-10-24 起移出查询链，原因：

1. **前端从未渲染。** 该表数据经服务层挂到 `container_maps` 字段后返回给前端，
   但前端只在归一化函数里赋值一次，模板中没有任何消费方。
2. **柜级海运量不依赖它。** `sea_qty` 由 `logistics_container.load_time` 与
   `logistics_shipment.handover` 做月日匹配（跨年时比较年份）后汇总
   `EMITTED.qty2` 得出，与该映射表无关。移除后货柜卡上的数量不变。
3. **覆盖率低。** 全表 27,008 行，仅覆盖 25,178 / 154,887 个发货条码（16.3%）；
   其中 2,712 行本身标记为 `UNMATCHED`（关联失败）。展示价值有限。
4. **有查询成本。** 每次 `search_logistics` 都要额外扫这张表一遍。

如需恢复（例如 ETL 把映射覆盖率补齐后要在发货记录里显示所属柜）：

- 在 `logistics_service._LOGISTICS_TABLES` 中加回表名；
- 恢复 `_attach_container_maps()` 与 `_badge_no()`；
- 在 `_ensure_group()` 的分组结构里加回 `container_maps` 空数组；
- 前端在发货记录行增加对应渲染。

回归测试 `tests/test_logistics_service.py::test_search_does_not_query_container_map_table`
会拦住「把表加回查询」的改动，恢复时需同步调整该测试。

## 数据库升级

新增柜号字段及复合主键的人工升级脚本见 [2026-10-15-logistics-container-no.sql](2026-10-15-logistics-container-no.sql)。该脚本不是幂等迁移，不会在 FastAPI 启动时执行。上线顺序：先备份并执行升级 SQL，再部署后端/前端，最后由数据管理员按仓库运行 `物流数据仓库/etl/load_wh_generic.py` 导入柜号。该导入器会按仓库删除并重载物流记录，执行前必须确认目标仓库和备份；当前任务未运行导入器或 SQL。

## 错误码

| HTTP 状态 | 触发条件 | 响应 `detail` |
| --- | --- | --- |
| `400` | `warehouse` 不在仓库列表接口返回的范围内 | `未知仓库: <warehouse>` |
| `401` | 未登录或认证信息无效 | 由认证依赖返回 |
| `403` | JWT 有效，但账号仍处于 `mustChangePassword` 状态 | 需先完成首次改密后再访问物流查询 |
| `422` | 缺少必填参数 `q` 或参数格式无法通过 FastAPI 校验 | 由 FastAPI 返回参数校验详情 |
| `503` | 物流表缺失、数据库查询失败或物流数据暂时不可用 | `物流数据暂时不可用，请联系管理员` |

数据库异常不会直接返回给调用方。
