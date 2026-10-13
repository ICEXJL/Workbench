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
              "badge_no": "B-1",
              "container_maps": []
            }
          ],
          "container_maps": []
        }
      ]
    }
  ],
  "query": "1001",
  "warehouse": null
}
```

`items` 下的 `warehouses` 是按仓库分组的结果。每个仓库组固定包含 `profile`、`profiles`、`containers`、`replenish`、`shipments` 和 `container_maps`：

- `profile` 是该 SKU/仓库的主产品资料；`profiles` 保留该 SKU/仓库命中的全部产品资料行。
- `containers` 是货柜资料行。
- `replenish` 是补货资料行。
- `shipments` 是发货资料行。每条发货记录包含 `container_maps`，其中放置通过 `badge_no` 或 `shipment_badge_no` 关联到该发货记录的映射行。
- `container_maps` 是无法关联到具体发货记录、但属于该 SKU/仓库的映射行。

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

接口只读以下五张表：

1. `logistics_sku`：产品资料、SKU、产品名、仓库和库存等档案信息。
2. `logistics_container`：货柜资料。
3. `logistics_replenish`：补货资料。
4. `logistics_shipment`：发货资料。
5. `logistics_shipment_container_map`：发货批次与货柜的映射资料。

服务先读取 `logistics_sku` 确定 SKU 与仓库，再对其余四张表分别执行带参数的查询，最后在服务层按 `sku + warehouse` 组装结果。五张业务表之间禁止串联 `JOIN`，以避免一对多数据产生笛卡尔积和重复结果。搜索阶段对五张业务表的查询都带 SKU 条件和仓库条件；全部仓库查询使用允许的空仓库参数表示全部范围。仓库列表接口单独按 `logistics_sku.warehouse` 汇总仓库和 SKU 数量。

物流查询不接入组织层级范围。所有登录角色都可查看全部仓库，也可切换到单仓范围；前端选择不能替代后端的仓库校验。

## 错误码

| HTTP 状态 | 触发条件 | 响应 `detail` |
| --- | --- | --- |
| `400` | `warehouse` 不在仓库列表接口返回的范围内 | `未知仓库: <warehouse>` |
| `401` | 未登录或认证信息无效 | 由认证依赖返回 |
| `422` | 缺少必填参数 `q` 或参数格式无法通过 FastAPI 校验 | 由 FastAPI 返回参数校验详情 |
| `503` | 物流表缺失、数据库查询失败或物流数据暂时不可用 | `物流数据暂时不可用，请联系管理员` |

数据库异常不会直接返回给调用方。
