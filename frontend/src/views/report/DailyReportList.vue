<template>
  <section class="list-page">
    <div class="page-head">
      <div><p>REPORT CONTROL CENTER</p><h2>运营日报进度</h2><span>按权限范围查看日报提交与目标完成情况。</span></div>
      <div class="head-actions"><a-button :loading="loading" @click="load">刷新数据</a-button></div>
    </div>

    <div class="metric-grid">
      <article><small>已提交日报</small><strong>{{ submittedCount }}</strong><span>当前筛选范围</span></article>
      <article><small>覆盖运营人数</small><strong>{{ operatorCount }}</strong><span>权限范围内</span></article>
      <article><small>平均完成率</small><strong>{{ averageRate }}%</strong><span>仅统计已配置目标</span></article>
      <article class="missing-card copyable" :title="`双击复制未提交名单（${unsubmittedCount} 人）`" @dblclick="copyUnsubmitted">
        <small>未提交日报</small>
        <strong :style="{ color: unsubmittedCount > 0 ? '#d64d45' : '#17243f' }">{{ unsubmittedCount }}</strong>
        <span>{{ unsubmittedCount > 0 ? '需要跟进 · 双击复制名单' : '需要跟进' }}</span>
      </article>
    </div>

    <div class="filter-card">
      <a-range-picker v-model:value="dateRange" value-format="YYYY-MM-DD" :allow-clear="false"/>
      <a-select v-model:value="department" allow-clear show-search option-filter-prop="label" placeholder="全部部门" style="min-width:150px" @change="onDepartmentChange">
        <a-select-option v-for="item in departmentOptions" :key="item" :value="item" :label="item">{{ item }}</a-select-option>
      </a-select>
      <a-select v-model:value="group" allow-clear show-search option-filter-prop="label" placeholder="全部组别" style="min-width:150px" @change="onGroupChange">
        <a-select-option v-for="item in groupOptions" :key="item" :value="item" :label="item">{{ item }}</a-select-option>
      </a-select>
      <a-select v-model:value="operator" allow-clear show-search option-filter-prop="label" placeholder="全部运营" style="min-width:180px">
        <a-select-option v-for="person in operatorOptions" :key="person.id" :value="person.id" :label="person.real_name">{{ person.real_name }}</a-select-option>
      </a-select>
      <a-button type="primary" @click="load">查询</a-button>
    </div>

    <section v-if="canSeeCompliance" class="insight-section">
      <div class="section-heading"><div><p>OPERATIONS INSIGHTS</p><h3>日报指标概览</h3><span>点击指标卡片，查看对应的日报记录</span></div><a-spin v-if="complianceLoading"/></div>
      <div class="insight-grid">
        <button v-for="card in insightCards" :key="card.key" type="button" class="insight-card" :class="{ selected: selectedMetric?.key === card.key, warning: card.key !== 'attention_notes' && card.issueCount > 0, 'notes-card': card.key === 'attention_notes' }" @click="selectMetric(card)">
          <div class="insight-card-top"><h4>{{ card.label }}</h4><span class="status-pill" :class="card.statusClass">{{ card.status }}</span></div>
          <div class="insight-number"><strong>{{ card.issueCount }}</strong><span>/ {{ card.total }} 人</span></div>
          <div class="insight-progress"><i :style="{ width: `${card.ratio}%` }"></i></div>
          <div class="insight-footer">{{ card.key === 'attention_notes' ? '有填写 · 点击查看注意事项' : card.issueCount ? `${card.issueLabel} · 点击查看异常日报` : card.total ? '全部正常 · 点击查看明细' : '当前筛选范围暂无数据' }}</div>
        </button>
      </div>
    </section>

    <section v-if="canSeeCompliance && selectedMetric" class="issue-section">
      <div class="section-heading issue-heading"><div><p>FILTERED REPORTS</p><h3>{{ selectedMetric.label }} · {{ selectedMetric.issueLabel }}</h3><span>{{ selectedMetric.key === 'attention_notes' ? '仅显示当前筛选范围内填写了注意事项的日报' : '仅显示当前筛选范围内命中的异常日报' }}</span></div><a-button type="text" @click="selectedMetric = null">清除筛选</a-button></div>
      <a-empty v-if="!problemRows.length" description="当前筛选范围暂无异常日报"/><div v-else class="table-card issue-table"><a-table :columns="columns" :data-source="problemRows" :loading="loading" row-key="row_key" :pagination="issuePagination" :scroll="{x:2100}" @change="handleIssueTableChange" :custom-row="rowEvents"><template #bodyCell="{column,record}"><ReportCell :column="column" :record="record"/></template></a-table></div>
    </section>

    <section class="all-reports-section"><div class="section-heading"><div><p>DAILY REPORT DATASET</p><h3>日报进度全量数据</h3><span>当前权限和日期范围内的全部日报记录，包含所有填报字段</span></div></div><div class="table-card"><a-table :columns="columns" :data-source="displayRows" :loading="loading" row-key="row_key" :pagination="allPagination" :scroll="allTableScroll" @change="handleAllTableChange" :custom-row="rowEvents"><template #bodyCell="{column,record}"><ReportCell :column="column" :record="record"/></template></a-table></div></section>

    <a-drawer v-model:open="drawerOpen" title="运营日报明细" width="520"><div v-if="selected" class="detail"><header><div><small>{{ selected.report_date }}</small><h3>{{ selected.operator_name }}</h3><p>{{ selected.department || '未配置部门' }}</p></div><span>{{ selected.completion_rate ?? 0 }}%</span></header><section class="detail-variation"><div class="detail-variation-title"><strong>店铺业绩波动</strong><span>达到 ±20% 的店铺</span></div><div class="detail-variation-grid"><div class="detail-variation-card rise"><span>上涨</span><strong>{{ selected.rising_shop_count || 0 }} 家</strong><p>{{ selected.rising_shop_names?.join('、') || '无' }}</p></div><div class="detail-variation-card fall"><span>下滑</span><strong>{{ selected.falling_shop_count || 0 }} 家</strong><p>{{ selected.falling_shop_names?.join('、') || '无' }}</p></div></div><p v-if="!selected.rising_shop_count && !selected.falling_shop_count && selected.volatile_store_count" class="legacy-variation">历史数据仅记录总数：{{ selected.volatile_store_count }} 家，未区分上涨/下滑。</p></section><dl><div v-for="item in detailItems" :key="item.key"><dt>{{ item.label }}</dt><dd v-if="item.key === 'listing_link_id'" class="link-copy" :title="selected.listing_link_id?.trim() ? '双击复制全部' : '未填写'" @dblclick="copyListingLink">{{ selected.listing_link_id?.trim() || '-' }}</dd><dd v-else>{{ display(selected[item.key],item.type) }}</dd></div></dl><section v-if="selected.attention_notes?.trim()" class="detail-notes"><h4>注意事项</h4><p class="attention-notes">{{ selected.attention_notes }}</p></section></div></a-drawer>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { getDailyReports, getReportPeople, getComplianceOverview } from '@/services/api'
import {
  getDepartmentOptions,
  getGroupOptions,
  filterReportPeople,
  pickUnsubmittedNames,
  buildNameListText,
  reportsWithAttentionNotes,
  buildAttentionNotesCard,
} from '@/utils/reportFilters'
import { message } from 'ant-design-vue'

const auth = useAuthStore()
const canSeeCompliance = computed(() => ['leader', 'manager', 'admin'].includes(auth.role))
const loading = ref(false)
const rows = ref([])
const people = ref([])
const operator = ref()
const department = ref()
const group = ref()
const selected = ref()
const drawerOpen = ref(false)
const compliance = ref({ metrics: [] })
const complianceLoading = ref(false)
const selectedMetric = ref(null)
const allPage = ref(1)
const allPageSize = ref(12)
const issuePage = ref(1)
const issuePageSize = ref(8)
// 日报是当天填报的，默认就看今天；用户提交后刷新即可看到自己的记录。
const today = dayjs().format('YYYY-MM-DD')
const dateRange = ref([today, today])

const allColumns = [
  { title: '运营', dataIndex: 'operator_name', fixed: 'left', width: 110 },
  { title: '部门', dataIndex: 'department', width: 130 },
  { title: '填报日期', dataIndex: 'report_date', width: 120 },
  { title: '累计销售额（USD）', key: 'sales', width: 150 },
  { title: '实际上架', dataIndex: 'listing_count', key: 'number', width: 105 },
  { title: '产品优化', dataIndex: 'optimization_count', key: 'number', width: 105 },
  { title: '产品反推', dataIndex: 'reverse_product_count', key: 'number', width: 105 },
  { title: '上架链接 ID', dataIndex: 'listing_link_id', key: 'link', width: 190 },
  { title: '备货审核及时率', dataIndex: 'stocking_audit_rate', key: 'percent', width: 135 },
  { title: '店铺业绩波动', key: 'variation', width: 245 },
  { title: '周延迟/取消', dataIndex: 'weekly_delay_exceeded', key: 'bool', width: 120 },
  { title: '周商责差评链接', dataIndex: 'weekly_bad_review_links', key: 'number', width: 145 },
  { title: '周错发/破损链接', dataIndex: 'weekly_wrong_damage_links', key: 'number', width: 155 },
  { title: '触发违规/扣分', dataIndex: 'violation_triggered', key: 'bool', width: 130 },
  { title: '链接侵权/禁售', dataIndex: 'infringement_triggered', key: 'bool', width: 130 },
  { title: '问题已解决', dataIndex: 'all_issues_resolved', key: 'resolved', width: 110 },
  { title: '注意事项', dataIndex: 'attention_notes', key: 'attention_notes', width: 260 },
  { title: '完成率', key: 'rate', width: 105 },
  { title: '状态', key: 'status', fixed: 'right', width: 100 },
]
const optionalWeeklyFields = new Set(['weekly_delay_exceeded', 'weekly_bad_review_links', 'weekly_wrong_damage_links'])
const columns = computed(() => allColumns.filter(column => column.key === 'attention_notes' ? reportsWithAttentionNotes(rows.value).length > 0 : !optionalWeeklyFields.has(column.dataIndex) || rows.value.some(row => row[column.dataIndex] !== null && row[column.dataIndex] !== undefined)))

const detailItems = [
  ['cumulative_sales', '累计销售额（USD）', 'money'], ['listing_count', '实际上架数量'], ['optimization_count', '产品优化数量'], ['reverse_product_count', '产品反推数量'], ['listing_link_id', '上架链接 ID'],
  ['stocking_audit_rate', '备货审核及时率', 'percent'], ['volatile_store_count', '店铺业绩波动总数'], ['weekly_delay_exceeded', '周延迟率 / 取消率超标', 'bool'],
  ['weekly_bad_review_links', '周商责差评 ≥3 的链接数'], ['weekly_wrong_damage_links', '周错发 / 破损 ≥3 的链接数'], ['violation_triggered', '触发违规 / 扣分', 'bool'],
  ['infringement_triggered', '链接侵权 / 禁售', 'bool'], ['all_issues_resolved', '当天问题是否都解决', 'bool'],
].map(([key, label, type]) => ({ key, label, type }))

const ReportCell = defineComponent({
  props: { column: Object, record: Object },
  setup(props) {
    return () => {
      const column = props.column
      const record = props.record
      if (column.key === 'attention_notes') return h('span', { class: 'attention-notes notes-cell', title: record.attention_notes?.trim() || '' }, record.attention_notes?.trim() ? record.attention_notes : '-')
      if (column.key === 'link') {
        const linkText = String(record[column.dataIndex] ?? '').trim()
        if (!record.submitted) return h('span', { class: 'muted' }, '-')
        return h('span', { class: 'link-id', title: linkText || '未填写' }, linkText || '-')
      }
      if (column.key === 'sales') return h('span', record.submitted ? money(record.cumulative_sales) : '-')
      if (column.key === 'variation') return record.submitted ? variationCell(record) : h('span', { class: 'muted' }, '-')
      if (column.key === 'number') return h('span', { class: record.submitted ? '' : 'muted' }, record.submitted ? formatNumber(record[column.dataIndex]) : '-')
      if (column.key === 'percent') return h('span', { class: record.submitted ? '' : 'muted' }, record.submitted ? `${record[column.dataIndex] ?? '-'}%` : '-')
      if (column.key === 'bool') return record.submitted ? h('span', { style: tagStyle(isTrue(record[column.dataIndex]) ? 'warning' : 'normal') }, boolText(record[column.dataIndex])) : h('span', { class: 'muted' }, '-')
      if (column.key === 'resolved') return record.submitted ? h('span', { style: resolvedTagStyle(record[column.dataIndex]) }, boolText(record[column.dataIndex])) : h('span', { class: 'muted' }, '-')
      if (column.key === 'rate') return h('span', { class: record.completion_rate !== null && record.submitted ? 'rate' : 'muted' }, record.completion_rate !== null && record.submitted ? `${record.completion_rate}%` : '-')
      if (column.key === 'status') return h('span', { style: tagStyle(record.submitted ? 'normal' : 'danger') }, record.submitted ? '已提交' : '未提交')
      return h('span', record[column.dataIndex] ?? '-')
    }
  },
})

/** 部门选项：来自全部可见人员的部门集合。 */
const departmentOptions = computed(() => getDepartmentOptions(people.value))

/** 组别选项：选了部门后只显示该部门下的组别。 */
const groupOptions = computed(() => getGroupOptions(people.value, department.value))

/** 运营选项：随部门与组别逐级收窄。 */
const operatorOptions = computed(() => filterReportPeople(people.value, {
  department: department.value,
  group_name: group.value,
}))

const scopedPeople = computed(() => operator.value
  ? operatorOptions.value.filter(person => person.id === operator.value)
  : operatorOptions.value)
const submittedIds = computed(() => new Set(rows.value.map(row => row.operator_id)))
const displayRows = computed(() => [
  ...rows.value.map(row => ({ ...row, submitted: true, row_key: `report-${row.id}` })),
  ...scopedPeople.value.filter(person => !submittedIds.value.has(person.id)).map(person => ({ row_key: `missing-${person.id}`, operator_id: person.id, operator_name: person.real_name, department: person.department, report_date: dateRange.value[1], submitted: false })),
])
const submittedCount = computed(() => rows.value.length)
const unsubmittedNames = computed(() => pickUnsubmittedNames(displayRows.value))
const unsubmittedCount = computed(() => unsubmittedNames.value.length)
const operatorCount = computed(() => scopedPeople.value.length)
const validRates = computed(() => rows.value.filter(row => row.completion_rate !== null))
const averageRate = computed(() => validRates.value.length ? (validRates.value.reduce((sum, row) => sum + Number(row.completion_rate), 0) / validRates.value.length).toFixed(1) : '0.0')
const allPagination = computed(() => ({ current: allPage.value, pageSize: allPageSize.value, total: displayRows.value.length, showSizeChanger: true, pageSizeOptions: ['12', '24', '48', '96'], showTotal: total => `共 ${total} 条` }))

/**
 * 全量表格的滚动配置。
 *
 * `x` 固定宽度用于横向滚动（列多）；`y` 是让 Ant Design 把表头与表体分离、
 * 表头保持固定的关键——只设 `x` 时往下滚动表头会一起滚走。
 * 行数较少（≤12 行）时不给 `y`，避免表格被撑成固定高度留下一片空白。
 */
const allTableScroll = computed(() => ({
  x: reportsWithAttentionNotes(rows.value).length ? 2350 : 2090,
  ...(displayRows.value.length > 12 ? { y: 'calc(100vh - 320px)' } : {}),
}))
const issuePagination = computed(() => ({ current: issuePage.value, pageSize: issuePageSize.value, total: problemRows.value.length, showSizeChanger: true, pageSizeOptions: ['8', '16', '32'], showTotal: total => `共 ${total} 条` }))

const insightCardOrder = ['violation', 'infringement', 'volatile_store', 'issues_resolved', 'weekly_delay', 'weekly_bad_review', 'weekly_wrong_damage']
const insightCards = computed(() => {
  const cards = insightCardOrder.map(key => compliance.value.metrics.find(metric => metric.key === key)).filter(Boolean).map(metric => {
  const resolvedMetric = metric.key === 'issues_resolved'
  const issueCount = resolvedMetric ? metric.no : metric.yes
  const total = metric.yes + metric.no
  return { ...metric, issueCount, total, problemPeople: resolvedMetric ? metric.no_people : metric.yes_people, issueLabel: resolvedMetric ? '未解决' : (metric.yes_label || '是'), ratio: total ? Math.round(issueCount / total * 100) : 0, status: total === 0 ? '暂无数据' : issueCount ? '需关注' : '正常', statusClass: total === 0 ? 'neutral' : issueCount ? 'warning' : 'normal' }
})
  const notesCard = buildAttentionNotesCard(rows.value)
  if (notesCard) cards.push(notesCard)
  return cards
})
const problemRows = computed(() => {
  if (!selectedMetric.value) return []
  if (selectedMetric.value.key === 'attention_notes') return reportsWithAttentionNotes(displayRows.value)
  const peopleSet = new Set(selectedMetric.value.problemPeople)
  return displayRows.value.filter(row => row.submitted && peopleSet.has(row.operator_name))
})

function isTrue(value) { return value === true || value === 1 || value === '1' }
function tagStyle(kind) { const colors = { normal: ['#318345', '#edf8df'], warning: ['#c8751d', '#fff0df'], danger: ['#d74242', '#fde9e9'] }; const [color, background] = colors[kind]; return { display: 'inline-block', padding: '3px 8px', borderRadius: '999px', color, background, fontSize: '12px', lineHeight: '1.3' } }
function resolvedTagStyle(value) { return tagStyle(isTrue(value) ? 'normal' : 'warning') }
function boolText(value) { return value === null || value === undefined ? '-' : isTrue(value) ? '是' : '否' }
function formatNumber(value) { return value === null || value === undefined ? '-' : Number(value).toLocaleString('zh-CN') }
function money(value) { return `$ ${Number(value || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}` }
function display(value, type) { if (type === 'money') return money(value); if (type === 'percent') return value === null || value === undefined ? '-' : `${value}%`; if (type === 'bool') return boolText(value); return value ?? '-' }

/**
 * 双击复制「上架链接 ID」全文。
 * 该字段可能存了多个 ID（空格或换行分隔），复制的是原始全文而不是屏幕上换行后的样子。
 */
async function copyListingLink() {
  const text = String(selected.value?.listing_link_id || '').trim()
  if (!text) { message.info('当前日报没有上架链接 ID'); return }
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      const area = document.createElement('textarea')
      area.value = text
      area.setAttribute('readonly', '')
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(area)
      if (!ok) throw new Error('execCommand 复制失败')
    }
    message.success('已复制上架链接 ID')
  } catch {
    message.error('复制失败，请检查浏览器剪贴板权限')
  }
}
function variationLine(kind, count, names) { return h('span', { class: ['variation-table-line', kind] }, [h('span', { class: 'variation-direction' }, kind === 'rise' ? '上涨' : '下滑'), h('strong', `${count} 家`), names.length ? h('span', { class: 'variation-names', title: names.join('、') }, names.join('、')) : null]) }
function variationCell(record) {
  const risingCount = Number(record.rising_shop_count || 0)
  const fallingCount = Number(record.falling_shop_count || 0)
  const risingNames = Array.isArray(record.rising_shop_names) ? record.rising_shop_names : []
  const fallingNames = Array.isArray(record.falling_shop_names) ? record.falling_shop_names : []
  const lines = []
  if (risingCount) lines.push(variationLine('rise', risingCount, risingNames))
  if (fallingCount) lines.push(variationLine('fall', fallingCount, fallingNames))
  if (!lines.length && Number(record.volatile_store_count || 0)) lines.push(h('span', { class: ['variation-table-line', 'legacy'] }, `历史未分类 ${record.volatile_store_count} 家`))
  return lines.length ? h('div', { class: 'variation-table-cell' }, lines) : h('span', { class: 'muted' }, '无')
}
function selectMetric(card) { issuePage.value = 1; selectedMetric.value = selectedMetric.value?.key === card.key ? null : card }
function rowEvents(record) { return { onClick: () => { if (record.submitted) { selected.value = record; drawerOpen.value = true } } } }
function updatePagination(pagination, page, pageSize) {
  page.value = Math.max(1, Number(pagination.current) || 1)
  if (pagination.pageSize && Number(pagination.pageSize) !== pageSize.value) {
    pageSize.value = Number(pagination.pageSize)
    page.value = 1
  }
}
function handleAllTableChange(pagination) { updatePagination(pagination, allPage, allPageSize) }
function handleIssueTableChange(pagination) { updatePagination(pagination, issuePage, issuePageSize) }

/** 换部门时，组别与运营可能已不在新范围内，需要清空。 */
function onDepartmentChange() {
  group.value = undefined
  operator.value = undefined
}
/** 换组别时，运营可能不在新组内，需要清空。 */
function onGroupChange() {
  operator.value = undefined
}

/**
 * 双击「未提交日报」卡片，复制当前筛选范围内的未提交人员名单。
 *
 * 名单来源是 `displayRows` 里 submitted=false 的行，这些行由 `scopedPeople`
 * 补出；而 `scopedPeople` 已经过两层收窄：
 *   1. 后端 `/report/people` 只返回当前用户权限范围内的人
 *   2. 前端再按部门/组别筛选
 * 所以组长复制到的是组内运营，admin 复制到的是全部运营。
 */
async function copyUnsubmitted() {
  const names = unsubmittedNames.value
  if (!names.length) {
    message.info('当前筛选范围暂无未提交人员')
    return
  }
  const text = buildNameListText(names)
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
    } else {
      // 非安全上下文（http 且非 localhost）时 clipboard API 不可用，走降级方案
      const area = document.createElement('textarea')
      area.value = text
      area.setAttribute('readonly', '')
      area.style.position = 'fixed'
      area.style.opacity = '0'
      document.body.appendChild(area)
      area.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(area)
      if (!ok) throw new Error('execCommand 复制失败')
    }
    message.success(`已复制 ${names.length} 位未提交人员`)
  } catch (err) {
    message.error('复制失败，请检查浏览器剪贴板权限')
  }
}

async function load() {
  loading.value = true
  allPage.value = 1
  issuePage.value = 1
  try {
    const params = {
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      operator_id: operator.value,
      department: department.value,
      group: group.value,
    }
    const tasks = [getDailyReports(params)]
    if (canSeeCompliance.value) { complianceLoading.value = true; tasks.push(getComplianceOverview(params)) }
    const result = await Promise.all(tasks)
    rows.value = result[0]
    if (canSeeCompliance.value) compliance.value = result[1] || { metrics: [] }
    if (selectedMetric.value) selectedMetric.value = insightCards.value.find(card => card.key === selectedMetric.value.key) || null
  } finally { loading.value = false; complianceLoading.value = false }
}

onMounted(async () => { people.value = await getReportPeople(); await load() })
</script>

<style scoped>
.attention-notes{display:block;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6}
/* 表格单元格：最多 4 行，超出省略，避免长文本把整行撑开；完整内容看悬停提示或详情抽屉 */
.attention-notes.notes-cell{display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.6;max-height:6.4em}.link-id{display:block;overflow:hidden;color:#35445f;font-variant-numeric:tabular-nums;text-overflow:ellipsis;white-space:nowrap}.detail-notes{margin-top:18px;padding:14px;border-radius:8px;background:#f1f7ff}.detail-notes h4{margin:0 0 8px}.notes-card .insight-progress i{background:#4d9cf7!important}

.list-page .insight-grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.list-page .insight-card{min-height:150px;padding:15px 16px;border-radius:12px}.list-page .insight-card h4{font-size:14px}.list-page .insight-number{margin:14px 0 10px}.list-page .insight-number strong{font-size:32px}.list-page .insight-footer{margin-top:11px;font-size:12px}
@media(max-width:1200px){.list-page .insight-grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media(max-width:900px){.list-page .insight-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.list-page .insight-grid{grid-template-columns:1fr}.list-page .insight-card{min-height:142px}}
</style>
<style scoped>
.variation-table-cell{display:flex;flex-direction:column;align-items:flex-start;gap:4px;max-width:225px;white-space:normal}.variation-table-line{display:inline-flex;align-items:center;gap:5px;max-width:100%;padding:3px 7px;border-radius:6px;font-size:11px;line-height:1.35}.variation-table-line .variation-direction{flex:none;font-weight:700}.variation-table-line strong{flex:none;font-weight:600;color:#24344d}.variation-table-line .variation-names{min-width:0;color:#71809a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.variation-table-line.rise{background:#eef8f2}.variation-table-line.fall{background:#fdf1f0}.variation-table-line.rise .variation-direction{color:#237b59}.variation-table-line.fall .variation-direction{color:#c24c48}.variation-table-line.legacy{color:#7d8794;background:#f1f3f5}.detail-variation{margin:18px 0 6px;padding:14px;border:1px solid #e4ebf4;border-radius:10px;background:#f8fbff}.detail-variation-title{display:flex;align-items:baseline;justify-content:space-between;margin-bottom:10px}.detail-variation-title strong{color:#24344d;font-size:13px}.detail-variation-title span{color:#8d99aa;font-size:11px}.detail-variation-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}.detail-variation-card{padding:11px;border-radius:8px;background:#fff}.detail-variation-card>span,.detail-variation-card>strong,.detail-variation-card>p{display:block}.detail-variation-card>span{font-size:11px}.detail-variation-card>strong{margin:4px 0;color:#24344d;font-size:18px}.detail-variation-card>p{min-height:18px;margin:0;color:#71809a;font-size:11px;line-height:1.45;word-break:break-all}.detail-variation-card.rise{border-left:3px solid #35a878}.detail-variation-card.rise>span{color:#25865f}.detail-variation-card.fall{border-left:3px solid #d95d58}.detail-variation-card.fall>span{color:#c44d49}.legacy-variation{margin:10px 0 0;color:#8d99aa;font-size:11px}@media(max-width:620px){.detail-variation-grid{grid-template-columns:1fr}}
</style>

<style scoped>
.list-page{max-width:1420px;margin:auto}.page-head,.head-actions,.section-heading{display:flex;align-items:center;justify-content:space-between}.page-head{margin-bottom:20px}.page-head p,.section-heading p{margin:0 0 5px;color:#2f7df4;font-size:10px;font-weight:700;letter-spacing:.16em}.page-head h2{margin:0 0 6px;font-size:24px}.page-head span,.section-heading span{color:#7e8ba1;font-size:13px}.head-actions{gap:10px}.missing-badge{padding:7px 11px;border:1px solid #ffd3cf;border-radius:7px;color:#d64d45;background:#fff4f2;font-weight:600}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-bottom:16px}.metric-grid article,.filter-card,.table-card{border:1px solid #dfe7f2;border-radius:10px;background:#fff}.metric-grid article{padding:18px}.metric-grid small,.metric-grid span{display:block;color:#8794a9}.metric-grid strong{display:block;margin:8px 0 4px;font-size:26px}.metric-grid span{font-size:10px}.missing-card strong{color:#d64d45}.missing-card.copyable{cursor:pointer;user-select:none;transition:border-color .18s,box-shadow .18s}.missing-card.copyable:hover{border-color:#f0ada6;box-shadow:0 0 0 3px #fff2f0}.filter-card{display:flex;gap:10px;margin-bottom:24px;padding:14px}.insight-section,.issue-section,.all-reports-section{margin-bottom:24px}.section-heading{align-items:flex-start;margin-bottom:12px}.section-heading h3{margin:0 0 4px;font-size:17px}.insight-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.insight-card{min-height:190px;padding:22px 20px;border:1px solid #dfe4e8;border-radius:16px;color:#5f6873;background:#fff;text-align:left;cursor:pointer;transition:.18s;box-shadow:0 3px 14px rgba(38,63,91,.03)}.insight-card:hover,.insight-card.selected{border-color:#4d9cf7;box-shadow:0 0 0 3px #eaf3ff,0 8px 22px rgba(38,98,170,.1);transform:translateY(-2px)}.insight-card.warning{border-color:#e6c7b9}.insight-card-top{display:flex;align-items:flex-start;justify-content:space-between;gap:12px}.insight-card h4{max-width:70%;margin:0;color:#636b75;font-size:16px;font-weight:500;line-height:1.45}.status-pill{flex:none;padding:6px 12px;border-radius:999px;font-size:12px}.status-pill.normal{color:#4d8e26;background:#edf8df}.status-pill.warning{color:#d74242;background:#fde9e9}.status-pill.neutral{color:#7d8794;background:#f0f2f4}.insight-number{display:flex;align-items:baseline;gap:6px;margin:22px 0 14px;color:#a1a6ad}.insight-number strong{color:#24282c;font-size:42px;font-weight:500;line-height:1}.insight-number span{font-size:15px}.insight-progress{height:8px;overflow:hidden;border-radius:99px;background:#f0f1f2}.insight-progress i{display:block;height:100%;border-radius:inherit;background:#e35052;transition:width .2s}.insight-card:not(.warning) .insight-progress i{background:#75b65e}.insight-footer{margin-top:17px;color:#9ba0a6;font-size:13px}.issue-section{padding:18px;border:1px solid #e7edf4;border-radius:12px;background:#fbfdff}.issue-heading{margin-bottom:14px}.table-card{padding:8px 12px}.table-card :deep(.ant-table-row){cursor:pointer}.table-card :deep(.ant-table-cell){white-space:nowrap}.issue-table{border-color:#dce9f8}.rate{color:#1767df;font-weight:650}.muted{color:#9aa6b9}.detail header{display:flex;justify-content:space-between;padding:20px;border-radius:10px;color:#fff;background:linear-gradient(135deg,#2879ed,#70a9ff)}.detail h3{margin:5px 0}.detail p,.detail small{margin:0;opacity:.8}.detail header>span{font-size:34px;font-weight:700}.detail dl div{display:flex;justify-content:space-between;gap:14px;padding:13px 4px;border-bottom:1px solid #e8edf4}.detail dt{flex:none;white-space:nowrap;color:#7e8ba1}.detail dd{flex:1;min-width:0;margin:0;text-align:right;overflow-wrap:anywhere;word-break:break-word}.detail dd.link-copy{padding:6px 8px;border-radius:6px;color:#35445f;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;line-height:1.7;white-space:pre-wrap;cursor:pointer;user-select:none;transition:background .15s}.detail dd.link-copy:hover{background:#eff5ff}@media(max-width:1000px){.metric-grid{grid-template-columns:repeat(2,1fr)}.insight-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.filter-card{flex-wrap:wrap}}@media(max-width:620px){.metric-grid,.insight-grid{grid-template-columns:1fr}.page-head{align-items:flex-start;gap:12px}.head-actions{align-items:flex-end;flex-direction:column}.insight-card{min-height:170px}}
</style>
