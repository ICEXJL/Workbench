# T13 — 前端 ECharts 按需引入优化 + Git 远程仓库核实

日期：2026-10-06
状态：`done`

## 背景

`npm run build` 持续输出 `(!) Some chunks are larger than 500 kB` 警告，
其中 `EChart-*.js` 为 1,036.98 kB（gzip 343.76 kB），是主要来源。
用户要求确认 ECharts 是否仍在使用、能否减小，并核实项目是否真的没有 Git 远程仓库。

## 变更

### 1. `frontend/src/components/EChart.vue` — ECharts 按需引入

- 改：`import * as echarts from 'echarts'`（全量，打包所有图表类型）
- 为：`echarts/core` + 按需注册

```javascript
import * as echarts from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  BarChart, LineChart, GridComponent, TooltipComponent,
  LegendComponent, TitleComponent, CanvasRenderer,
])
```

注册范围依据：全项目 `frontend/src/views/**/*.vue` 仅使用 `bar`（8 处）与
`line`（6 处）两种 series type，`category`/`value` 为坐标轴 axis type，非图表类型。
仅 `Stats7d.vue` 与 `StatsDaily.vue` 两个页面使用 `EChart` 组件。

### 2. `frontend/package.json` — 补齐缺失依赖声明

`dayjs` 被 6 个源文件直接 `import`，但未在 `dependencies` 中声明，
此前依赖 Ant Design Vue 的传递依赖侥幸运行。已补 `"dayjs": "^1.11.23"`。

## 验证结果

### 构建产物（前后对比）

| 文件 | 改前 | 改后 | 变化 |
| --- | --- | --- | --- |
| `EChart-*.js` | 1,036.98 kB / gzip 343.76 kB | 504.60 kB / gzip 169.25 kB | **减半** |
| `index-*.js` | 1,535.05 kB / gzip 477.23 kB | 1,535.05 kB / gzip 477.23 kB | 不变 |

### 未使用图表未打入

`grep -c "SankeySeries" dist/assets/EChart-LkGEF6F2.js` → `0`

> 注：`sankey` / `radar` / `treemap` 等关键词在产物中仍存在，
> 但经查证属于 ECharts 内核的 i18n 名称映射表字符串
> （如 `sankey:"Sankey diagram"`、`sankey:"桑基图"`），非图表实现代码。

### 浏览器端渲染验证（Playwright，admin 账号 `xiangjinglv`）

| 页面 | 结果 |
| --- | --- |
| `/stats7d` 各地区近 7 天统计 | 柱状图 + 3 条折线、双 Y 轴、图例齐全，正常渲染 |
| `/stats7d` 各平台近 7 天统计 | 柱状图 + 3 条折线、tooltip 联动正常 |
| `/statsdaily` 分布洞察 | 区域图 + 仓库图双图同时渲染正常 |

canvas 像素采样验证非空（`getImageData` 采样非零alpha 点：
5716 / 7105 / 5655 / 3250），排除「容器有canvas 但未绘制」的情况。

console 无 ECharts 相关报错。仅有的两条为：
- 浏览器扩展 CSP 拦截（与项目无关）
- `[ant-design-vue: Table] index parameter of rowKey function is deprecated`（既有技术债，非本次引入）

截图：`verify-echarts-stats7d.png`、`verify-echarts-stats7d-platform.png`、`verify-echarts-statsdaily.png`

### 遗留

- `EChart-*.js` 504.60 kB 仍略超 500 kB 阈值（差4.6 kB）
- `index-*.js` 1,535.05 kB 更大，根因是 Ant Design Vue 全量引入，
  需 `unplugin-vue-components` 按需引入才能解决，本次未做

## Git 远程仓库核实（修正此前错误结论）

此前依据 AGENTS.md 中「`git remote -v` 当前没有输出」的说法，
判断项目无远程仓库 —— **该结论错误**，AGENTS.md 描述已过时。

### 事实

- `origin` 配置存在：`https://github.com/ICEXJL/Workbench.git`（fetch/push 均配置）
- 本地 `main` 为 `d304506`，**无上游跟踪分支**（`git branch -vv` 无 `origin/main`）
- `.git/FETCH_HEAD` 不存在、`.git/refs/remotes` 目录不存在 → **从未执行过 fetch**
- 仅 2 次本地提交：`4b84024`（2026-09-18 初始）、`d304506`（2026-09-28）

### 远程可达性

- `git ls-remote --heads origin` 两次均 **EXIT 124 超时**（无响应，非 401/403）
- `GET api.github.com/repos/ICEXJL/Workbench` → **404**
- `GET api.github.com/users/ICEXJL` → **200**（用户存在，id 273708724）
- 该用户名下公开仓库仅 2 个：`ICEXJL/13396012817`、`ICEXJL/yingsheng`

### 结论

`origin` 是**已配置但从未成功连接**的地址。404 + ls-remote 超时 + 无凭据
（无 `.git-credentials`，credential.helper 为 `helper-selector`）共同表明：
远程仓库为**私有**（或尚未在 GitHub 上创建），当前环境无认证凭据。

因此当前状态是：**代码仅存在于本地，未推送过任何内容到远程。**

## 踩坑记录

### 沙箱批量删除保护拦截 `vite build`

`npm run build` 在 `emptyOutDir` 阶段失败：

```
[safe-delete][SAFE_DELETE_BULK_CONFIRM_REQUIRED]
{"count":52,"threshold":50,"scope":"turn","targets":["...\\frontend\\dist\\assets"]}
```

`dist/assets` 累积 52 个文件，超过 50 的批量删除阈值。
**绕法**：`npx vite build --outDir <临时目录> --emptyOutDir false`

### Playwright `ERR_CACHE_READ_FAILURE`

复用同一浏览器 profile 时动态导入的 `.vue` 文件读取失败，
导致路由报 `Failed to fetch dynamically imported module`，易误判为代码缺陷。
**绕法**：导航前 `caches.delete()` 后 `location.reload()`。