# 人员销售日期范围与店铺明细

- 人员销售页默认日期范围为昨天至昨天，可自定义开始和结束日期。
- 汇总接口按闭区间返回运营累计订单、累计销售额和区间日均销售额。
- 点击累计销售额可查看该运营名下全部店铺；无销售记录的店铺仍展示为 0，并按销售额从高到低排序。
- 后端店铺明细接口复用销售可见范围，越权请求由后端拦截。

验证：`python -m compileall -q backend`、`$env:PYTHONPATH='backend'; python -m pytest -q tests/test_personnel_sales.py tests/test_region_scope.py`（10 passed）、`npm run build`。
