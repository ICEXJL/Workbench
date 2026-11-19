<template>
  <div>
    <a-card :loading="loading">
      <a-space wrap>
        <a-date-picker v-model:value="cxrq" value-format="YYYY-MM-DD" @change="load" />
        <a-select v-model:value="jc" style="width: 140px" placeholder="部门简称" show-search option-filter-prop="label" @change="onJcChange">
          <a-select-option value="全部" label="全部">全部</a-select-option>
          <a-select-option v-for="s in jcList" :key="s" :value="s" :label="s">{{ s }}</a-select-option>
        </a-select>
        <a-select v-model:value="zm" style="width: 140px" placeholder="组别" show-search option-filter-prop="label" @change="onZmChange">
          <a-select-option value="全部" label="全部">全部</a-select-option>
          <a-select-option v-for="s in zmList" :key="s" :value="s" :label="s">{{ s }}</a-select-option>
        </a-select>
        <a-select v-model:value="yy" style="width: 140px" placeholder="运营" show-search option-filter-prop="label" @change="filtersChanged">
          <a-select-option value="全部" label="全部">全部</a-select-option>
          <a-select-option v-for="s in yyList" :key="s" :value="s" :label="s">{{ s }}</a-select-option>
        </a-select>
      </a-space>
      <a-divider />
      <a-table
        row-key="yy"
        :data-source="rows"
        :columns="columns"
        :pagination="pagination"
        :scroll="{ x: 2235 }"
        :locale="{ emptyText: `基准日期 ${cxrq} 无销售业绩数据` }"
        size="middle"
        bordered
        @change="tableChanged"
      >
        <template #summary>
          <Table.Summary fixed="bottom">
            <Table.Summary.Row class="personnel-summary-row">
              <Table.Summary.Cell :index="0" :col-span="6">
                <strong>汇总（全部运营）</strong>
              </Table.Summary.Cell>
              <Table.Summary.Cell :index="6" :col-span="15">
                <div class="personnel-summary-metrics">
                  <span><strong>7天订单总数</strong>{{ formatInteger(summary.total_orders) }}</span>
                  <span><strong>7天销售额</strong>{{ formatMoney(summary.total_sales) }}</span>
                </div>
              </Table.Summary.Cell>
            </Table.Summary.Row>
          </Table.Summary>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { computed, h, onMounted, ref } from 'vue'
import { Popover, Table } from 'ant-design-vue'
import dayjs from 'dayjs'
import { getPersonnelSales, getPersonnelStoreSales } from '@/services/api'

const loading = ref(false)
const cxrq = ref(dayjs().subtract(1, 'day').format('YYYY-MM-DD'))
const rows = ref([])
const summary = ref({ total_orders: 0, total_sales: 0 })
const options = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const pageCache = new Map()
const pending = new Map()
let requestVersion = 0
const jcList = computed(() => [...new Set(options.value.map((d) => String(d.jc)).filter(Boolean))])
const jc = ref('全部')
const zm = ref('全部')
const yy = ref('全部')
const popoverState = ref({ key: '', operator: '', date: '', open: false, locked: false, loading: false, items: [] })

const zmList = computed(() => {
  const filtered = options.value.filter((d) => jc.value === '全部' || String(d.jc) === jc.value)
  return [...new Set(filtered.map((d) => String(d.zm)).filter(Boolean))]
})

const yyList = computed(() => {
  const filtered = options.value.filter(
    (d) =>
      (jc.value === '全部' || String(d.jc) === jc.value) &&
      (zm.value === '全部' || String(d.zm) === zm.value)
  )
  return [...new Set(filtered.map((d) => String(d.yy)).filter(Boolean))]
})

const dayHeaders = computed(() => {
  const headers = []
  for (let i = 0; i < 7; i++) {
    const d = dayjs(cxrq.value).subtract(i, 'day')
    headers.push(`${d.month() + 1}月${d.date()}日`)
  }
  return headers
})

const columns = computed(() => {
  const base = [
    { title: '部门简称', dataIndex: 'jc', key: 'jc', fixed: 'left', width: 80, ellipsis: true },
    { title: '组别', dataIndex: 'zm', key: 'zm', fixed: 'left', width: 80, ellipsis: true },
    { title: '运营', dataIndex: 'yy', key: 'yy', fixed: 'left', width: 100, ellipsis: true },
    { title: '入职时间', dataIndex: 'rzsj', key: 'rzsj', width: 100 },
    { title: '店铺编号', dataIndex: 'dpbh', key: 'dpbh', width: 240, ellipsis: true },
    { title: '平台', dataIndex: 'fl', key: 'fl', width: 130, ellipsis: true },
    { title: '七日日均（USD）', dataIndex: 'avg_sales', key: 'avg_sales', width: 135, align: 'right', customRender: ({ text }) => formatMoney(text) },
  ]
  const dayCols = []
  dayHeaders.value.forEach((h, idx) => {
    const n = 7 - idx
    dayCols.push({
      title: h,
      children: [
        {
          title: '订单数',
          dataIndex: `dd${n}`,
          key: `dd${n}`,
          width: 75,
          align: 'right',
          customRender: ({ text }) => formatInteger(text),
        },
        {
          title: '销售额（USD）',
          dataIndex: `xs${n}`,
          key: `xs${n}`,
          width: 120,
          align: 'right',
          customRender: ({ text, record }) => renderSalesCell(text, record.yy, dayHeaders.value[idx] ? dayjs(cxrq.value).subtract(idx, 'day').format('YYYY-MM-DD') : cxrq.value),
        },
      ],
    })
  })
  return [...base, ...dayCols]
})

function renderSalesCell(value, operator, date) {
  const key = `${operator}|${date}`
  const state = popoverState.value
  const content = () => h('div', { class: 'sales-popover-card' }, [
    h('div', { class: 'sales-popover-head' }, [h('strong', {}, operator), h('span', {}, date), h('button', { class: 'sales-popover-close', onClick: () => closePopover() }, '×')]),
    state.loading && state.key === key ? h('div', { class: 'sales-popover-loading' }, '加载中…') : h('div', {}, [
      h('div', { class: 'sales-popover-total' }, [h('span', {}, formatMoney(value)), h('span', {}, `${formatInteger(state.items.reduce((sum, item) => sum + Number(item.total_orders || 0), 0))} 单`)]),
      h('div', { class: 'sales-popover-list' }, [
        h('div', { class: 'sales-store-header' }, [h('span', {}, '店铺'), h('span', {}, '销售额'), h('span', {}, '占比')]),
        ...(state.key === key ? state.items : []).map((item, index) => {
          const totalSales = state.items.reduce((sum, store) => sum + Number(store.total_sales || 0), 0)
          const share = totalSales > 0 ? Number(item.total_sales || 0) / totalSales * 100 : 0
          return h('div', { class: 'sales-store-row', key: item.dpbh }, [
            h('span', { class: 'sales-store-bar', style: { width: `${Math.min(100, share)}%` } }),
            h('span', { class: 'sales-store-rank' }, String(index + 1)),
            h('span', { class: 'sales-store-name' }, item.dpbh),
            h('span', { class: 'sales-store-sales' }, formatMoney(item.total_sales)),
            h('span', { class: 'sales-store-share' }, `${share.toFixed(1)}%`),
          ])
        }),
      ])
    ])
  ])
  return h(Popover, { trigger: 'hover', open: state.key === key ? state.open : undefined, placement: 'bottom', overlayClassName: 'personnel-sales-popover', onOpenChange: (open) => handlePopoverOpen(open, operator, date, key) }, { default: () => h('span', { class: 'sales-cell-trigger', onClick: () => lockPopover(operator, date, key) }, [formatMoney(value), h('span', { class: 'sales-cell-caret' }, '▾')]), content })
}

async function handlePopoverOpen(open, operator, date, key) {
  if (!open && popoverState.value.locked) return
  if (!open) { popoverState.value = { ...popoverState.value, open: false }; return }
  popoverState.value = { key, operator, date, open: true, locked: false, loading: true, items: [] }
  // 鼠标快速划过多个单元格时，先发出的请求可能后返回。
  // 必须校验 key 仍是当前目标，否则会把别人的店铺明细写到这一行上，
  // 表现为「标题是甲、明细是乙的店」，占比也会和本行总额对不上。
  try {
    const data = await getPersonnelStoreSales(operator, date)
    if (popoverState.value.key !== key) return
    popoverState.value = { ...popoverState.value, loading: false, items: data.items || [] }
  } catch {
    if (popoverState.value.key !== key) return
    popoverState.value = { ...popoverState.value, loading: false }
  }
}
function lockPopover(operator, date, key) {
  if (popoverState.value.key === key && popoverState.value.locked) { closePopover(); return }
  popoverState.value = { key, operator, date, open: true, locked: true, loading: true, items: [] }
  getPersonnelStoreSales(operator, date).then((data) => { if (popoverState.value.key === key) popoverState.value = { ...popoverState.value, loading: false, items: data.items || [] } }).catch(() => { if (popoverState.value.key === key) popoverState.value = { ...popoverState.value, loading: false } })
}
function closePopover() { popoverState.value = { key: '', operator: '', date: '', open: false, locked: false, loading: false, items: [] } }

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: total.value,
  showSizeChanger: true,
  pageSizeOptions: ['10', '20', '50'],
  showTotal: (count) => `共 ${count} 名运营`,
}))
const cacheKey = (targetPage, targetSize = pageSize.value) =>
  [cxrq.value, jc.value, zm.value, yy.value, targetPage, targetSize].join('|')

function fetchPage(targetPage, targetSize = pageSize.value) {
  const key = cacheKey(targetPage, targetSize)
  if (pageCache.has(key)) return Promise.resolve(pageCache.get(key))
  if (pending.has(key)) return pending.get(key)

  const task = getPersonnelSales({
    cxrq: cxrq.value,
    department: jc.value === '全部' ? undefined : jc.value,
    group: zm.value === '全部' ? undefined : zm.value,
    operator: yy.value === '全部' ? undefined : yy.value,
    page: targetPage,
    page_size: targetSize,
  })
    .then((data) => {
      pageCache.set(key, data)
      return data
    })
    .finally(() => pending.delete(key))
  pending.set(key, task)
  return task
}

async function showPage(targetPage = 1, targetSize = pageSize.value) {
  const version = ++requestVersion
  loading.value = true
  try {
    const data = await fetchPage(targetPage, targetSize)
    if (version !== requestVersion) return
    page.value = targetPage
    pageSize.value = targetSize
    rows.value = data.items
    total.value = data.total
    summary.value = data.summary || { total_orders: 0, total_sales: 0 }
    options.value = data.options
    prefetch(targetPage, targetSize, data.total)
  } finally {
    if (version === requestVersion) loading.value = false
  }
}

function prefetch(current, size, count) {
  const lastPage = Math.ceil(count / size)
  const nextPages = [current + 1, current + 2].filter((targetPage) => targetPage <= lastPage)
  nextPages.forEach((targetPage) => fetchPage(targetPage, size).catch(() => {}))
}

function filtersChanged() {
  pageCache.clear()
  showPage(1)
}

function onJcChange() {
  zm.value = '全部'
  yy.value = '全部'
  filtersChanged()
}

function onZmChange() {
  yy.value = '全部'
  filtersChanged()
}

function tableChanged(paginationState) {
  if (paginationState.pageSize !== pageSize.value) pageCache.clear()
  showPage(paginationState.current, paginationState.pageSize)
}

function load() {
  pageCache.clear()
  showPage(1)
}

function formatInteger(value) {
  if (value === null || value === undefined || value === '') return '-'
  const number = Number(value)
  return Number.isFinite(number)
    ? number.toLocaleString('en-US', { maximumFractionDigits: 0 })
    : '-'
}

function formatMoney(value) {
  if (value === null || value === undefined || value === '') return '-'
  const number = Number(value)
  if (!Number.isFinite(number)) return '-'

  const formatted = number.toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  return `$ ${formatted}`
}

onMounted(load)
</script>

<style>
.sales-cell-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #1677ff;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: transparent;
  text-underline-offset: 3px;
  padding: 3px 6px;
  border-radius: 4px;
  transition: background-color .15s ease, text-decoration-color .15s ease;
}
.sales-cell-trigger:hover {
  background: #e6f4ff;
  text-decoration-color: #1677ff;
}
.sales-cell-caret {
  color: #1677ff;
  font-size: 11px;
  line-height: 1;
}
.personnel-sales-popover .ant-popover-inner {
  padding: 0;
  border-radius: 12px;
}
.sales-popover-card {
  width: 430px;
  padding: 16px;
}
.sales-popover-head {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 15px;
}
.sales-popover-head strong { font-size: 20px; }
.sales-popover-head span { color: #666; }
.sales-popover-close {
  margin-left: auto;
  border: 0;
  background: transparent;
  color: #999;
  font-size: 22px;
  cursor: pointer;
}
.sales-popover-total {
  display: flex;
  align-items: baseline;
  gap: 14px;
  margin: 14px 0;
  font-size: 14px;
  color: #777;
}
.sales-popover-total span:first-child { font-size: 28px; color: #222; }
.sales-popover-list { border-top: 1px solid #eee; padding-top: 8px; max-height: 310px; overflow: auto; }
.sales-store-header { display: grid; grid-template-columns: 1fr 110px 52px; gap: 8px; padding: 0 4px 6px 34px; color: #999; font-size: 12px; }
.sales-store-row { position: relative; display: grid; grid-template-columns: 26px 1fr 110px 52px; gap: 8px; align-items: center; padding: 8px 4px; overflow: hidden; }
.sales-store-bar { position: absolute; z-index: 0; inset: 2px auto 2px 0; max-width: calc(100% - 70px); background: #dcecff; border-radius: 6px; pointer-events: none; }
.sales-store-rank { color: #999; }
.sales-store-rank, .sales-store-name, .sales-store-sales, .sales-store-share { position: relative; z-index: 1; }
.sales-store-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sales-store-sales, .sales-store-share { color: #444; font-variant-numeric: tabular-nums; text-align: right; }
.sales-store-share { color: #999; }
.sales-popover-loading { padding: 28px 0; text-align: center; color: #999; }
.personnel-summary-row { font-variant-numeric: tabular-nums; }
.personnel-summary-row strong { color: #1677ff; }
.personnel-summary-metrics { display: flex; justify-content: flex-start; gap: 32px; min-width: 260px; }
.personnel-summary-metrics span { display: inline-flex; align-items: center; gap: 12px; white-space: nowrap; }
</style>
