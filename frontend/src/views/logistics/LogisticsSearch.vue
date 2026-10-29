<template>
  <div class="logistics-page">
    <section class="control-strip">
      <div>
        <p class="eyebrow">CROSS-BORDER LOGISTICS</p>
        <h2>物流查询</h2>
        <p>按 SKU、定制 SKU 或产品名称查看库存、采购与出货进度</p>
      </div>
      <form class="search-form" @submit.prevent="search">
        <a-input v-model:value="state.query" class="query-input" allow-clear placeholder="输入 SKU、定制 SKU 或产品名称" />
        <a-select v-model:value="state.warehouse" class="warehouse-select" allow-clear placeholder="全部仓库">
          <a-select-option v-for="warehouse in state.warehouses" :key="warehouse.warehouse" :value="warehouse.warehouse">
            {{ display(warehouse.warehouse) }}<span class="option-count">{{ formatNumber(warehouse.sku_count) }} 个 SKU</span>
          </a-select-option>
        </a-select>
        <a-button type="primary" html-type="submit" :loading="state.loading">查询</a-button>
      </form>
    </section>

    <section v-if="state.loading" class="state-panel loading-panel"><a-spin /><span>正在查询物流资料...</span></section>
    <section v-else-if="state.error && !state.items.length" class="state-panel error-panel"><strong>{{ state.errorScope === 'warehouse' ? '仓库列表加载失败' : '查询失败' }}</strong><span>{{ state.error }}</span><a-button size="small" @click="retry">{{ state.errorScope === 'warehouse' ? '重新加载仓库' : '重新查询' }}</a-button></section>
    <div v-if="!state.loading && state.error && state.items.length" class="error-banner"><strong>{{ state.errorScope === 'warehouse' ? '仓库列表加载失败' : '本次查询失败' }}</strong><span>{{ state.error }}</span><a-button size="small" @click="retry">{{ state.errorScope === 'warehouse' ? '重新加载仓库' : '重新查询' }}</a-button></div>
    <section v-if="!state.loading && !state.error && !state.searched" class="state-panel empty-panel"><strong>输入条件开始查询</strong><span>支持跨仓汇总，也可以选择单个仓库缩小范围</span></section>
    <section v-if="!state.loading && !state.error && state.searched && state.items.length === 0" class="empty-result">
      <div class="result-bar"><span>命中 <strong>0</strong> 个 SKU</span><span v-if="state.query">关键词：{{ state.query }}</span><span>{{ state.warehouse || '全部仓库' }}</span></div>
      <div class="state-panel empty-panel"><strong>未找到匹配 SKU</strong><span>请调整关键词或仓库范围后重试</span></div>
    </section>

    <template v-if="!state.loading && state.items.length">
      <div class="result-bar"><span>命中 <strong>{{ formatNumber(state.items.length) }}</strong> 个 SKU</span><span v-if="state.query">关键词：{{ state.query }}</span><span>{{ state.warehouse || '全部仓库' }}</span></div>
      <section v-for="item in state.items" :key="item.sku || item.custom_sku || item.product_name" class="sku-block">
        <header class="sku-header">
          <div class="sku-title"><span class="sku-code">{{ display(item.sku) }}</span><span v-if="item.custom_sku" class="custom-code">{{ display(item.custom_sku) }}</span><h3>{{ item.product_name || '未命名产品' }}</h3></div>
          <span class="warehouse-count">{{ formatNumber(item.warehouses?.length) }} 个仓库</span>
        </header>

        <div v-for="group in normalizedWarehouses(item)" :key="group.warehouse || 'all'" class="warehouse-group">
          <div class="group-heading"><div><span class="eyebrow">WAREHOUSE PROFILE</span><h4>{{ display(group.warehouse) }}</h4></div><span v-if="group.profile.product_status" class="status-tag done">{{ display(group.profile.product_status) }}</span></div>
          <div class="profile-grid">
            <div class="profile-cell"><span>可用库存数</span><strong>{{ formatAmount(group.profile.available_qty) }}</strong></div>
            <div class="profile-cell"><span>采购中数</span><strong>{{ formatAmount(group.profile.purchasing_qty) }}</strong></div>
            <div class="profile-cell"><span>采购价</span><strong>{{ formatPrice(group.profile.price) }}</strong></div>
            <div class="profile-cell profile-text"><span>该 SKU 所在仓</span><strong>{{ warehouseNames(item) }}</strong></div>
          </div>
          <div v-if="!group.profiles.length" class="profile-note">当前仓没有产品档案，以下仅展示关联到该仓的物流记录。</div>

          <section class="detail-section">
            <div class="section-title"><h5>货柜物流状态</h5><span>{{ group.containers.length }} 个货柜</span></div>
            <div v-if="group.containers.length" class="container-list">
              <article v-for="(container, index) in group.containers" :key="containerKey(container)" class="container-card">
                <header class="container-heading">
                  <div class="container-heading-main"><span class="container-index">{{ getContainerIdentifier(container) }}</span><span class="status-tag" :class="containerStatus(container).tone">{{ containerStatus(container).label }}</span></div>
                  <div class="container-heading-meta">
                    <div><span>装柜时间</span><strong>{{ display(container.load_time) }}</strong></div>
                    <span class="meta-divider" aria-hidden="true">|</span>
                    <div><span>目的仓</span><strong>{{ display(container.warehouse_desc) }}</strong></div>
                    <span class="meta-divider" aria-hidden="true">|</span>
                    <div><span>货代</span><strong>{{ display(container.carrier) }}</strong></div>
                  </div>
                </header>
                <div class="container-quantity"><span>本柜海运备货数</span><strong>{{ formatAmount(getContainerSeaQuantity(container)) }}</strong></div>
                <div class="container-progress" aria-label="货柜物流进度">
                  <div class="progress-head"><strong>物流进度</strong><span>{{ containerProgress(container).percent }}%</span><span>{{ containerProgress(container).current }}/5 · {{ containerProgress(container).label }}</span></div>
                  <div class="progress-track"><i :style="{ width: `${containerProgress(container).percent}%` }"></i></div>
                  <div class="progress-nodes">
                    <span v-for="step in containerProgress(container).stages" :key="step.label" :class="{ done: step.active, current: step.current }" :style="{ '--stage-color': step.color }"><b>{{ step.percent / 20 }}</b><small>{{ step.label }}</small></span>
                  </div>
                  <p v-if="containerProgress(container).current < 5" class="progress-caption">后续节点：{{ containerProgress(container).stages.filter(step => !step.active).map(step => step.label).join(' → ') }}</p>
                </div>
                <details v-if="container.tracking" class="tracking-details">
                  <summary>查看该货柜的跟单轨迹</summary>
                  <pre>{{ display(container.tracking) }}</pre>
                </details>
                <div v-else class="tracking-empty">暂无跟单轨迹</div>
              </article>
            </div>
            <div v-else class="sub-empty">暂无货柜进度</div>
          </section>

          <DataTable v-if="group.replenishRecords" title="补货记录（最近 2 个月）" :rows="group.replenishRecords" :columns="replenishColumns" />
          <DataTable title="海运记录（未发货 / 已发货）" :rows="shipmentRows(group.shipments)" :columns="shipmentColumns" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { defineComponent, h, onMounted, reactive } from 'vue'
import { getLogisticsWarehouses, searchLogistics } from '@/services/api'
import {
  getContainerProgress,
  getContainerStatus,
  getOceanShipmentCompletion,
  getOceanShipmentQuantity,
  getOceanShipmentStatus,
  getReplenishmentRecordsForDisplay,
  getContainerIdentifier,
  getContainerSeaQuantity,
} from '@/utils/logistics'

const state = reactive({ query: '', warehouse: '', warehouses: [], items: [], searched: false, loading: false, error: '', errorScope: '' })
const replenishColumns = [
  { key: 'date', label: '登记日期', fields: ['reg_date'] },
  { key: 'air', label: '空运数量', fields: ['air_qty', 'air_quantity'] },
  { key: 'sea', label: '海运数量', fields: ['sea_qty', 'sea_quantity'] },
  { key: 'operator', label: '运营', fields: ['operator_name'] },
]
const shipmentColumns = [
  { key: 'type', label: '记录类型', fields: ['record_type_label'] },
  { key: 'date', label: '登记时间', fields: ['reg_date'] },
  { key: 'orderQty', label: '下单数量', fields: ['order_qty'] },
  { key: 'badge', label: '销单 / SKU 条码', fields: ['badge_no'] },
  { key: 'qty2', label: '数量明细', fields: ['quantity_detail'] },
  { key: 'statusRaw', label: '判定', fields: ['status_raw'] },
  { key: 'done', label: '是否完成', fields: ['completion_label'] },
  { key: 'handover', label: '给货时间', fields: ['handover'] },
  { key: 'carrier', label: '货代', fields: ['carrier'] },
]

const DataTable = defineComponent({
  props: { title: String, rows: { type: Array, default: () => [] }, columns: { type: Array, default: () => [] } },
  setup(props) {
    return () => h('section', { class: 'detail-section data-section' }, [
      h('div', { class: 'section-title' }, [h('h5', props.title), h('span', `${props.rows.length} 条记录`)]),
      props.rows.length ? h('div', { class: 'table-wrap' }, [h('table', { class: props.columns.length > 4 ? 'wide-table' : 'compact-table' }, [
        h('thead', [h('tr', props.columns.map(column => h('th', { key: column.key }, column.label)))]),
        h('tbody', props.rows.map((row, index) => h('tr', { key: `${props.title}-${index}` }, props.columns.map(column => h('td', { key: column.key }, valueFrom(row, column.fields)))))),
      ])]) : h('div', { class: 'sub-empty' }, '暂无记录'),
    ])
  },
})

function display(value) {
  if (value === null || value === undefined || value === '') return '-'
  if (Array.isArray(value)) return value.join('、') || '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
function formatNumber(value) {
  const number = Number(value)
  return value === null || value === undefined || value === '' || !Number.isFinite(number) ? '0' : number.toLocaleString('zh-CN')
}
function valueFrom(record, fields) {
  if (!record || typeof record !== 'object') return '-'
  const field = fields.find(key => record[key] !== null && record[key] !== undefined && record[key] !== '')
  return field ? display(record[field]) : '-'
}
function formatAmount(value) {
  const number = Number(value)
  return value === null || value === undefined || value === '' || !Number.isFinite(number)
    ? '-'
    : number.toLocaleString('zh-CN', { maximumFractionDigits: 3 })
}
function formatPrice(value) {
  const number = Number(value)
  return value === null || value === undefined || value === '' || !Number.isFinite(number)
    ? '-'
    : number.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}
function warehouseNames(item) { return (item?.warehouses || []).map(group => group.warehouse).filter(Boolean).join(' / ') || '-' }
function normalizedWarehouses(item) { return Array.isArray(item?.warehouses) && item.warehouses.length ? item.warehouses.map(normalizeGroup) : [normalizeGroup({})] }
function normalizeGroup(group) {
  const replenishmentRecords = getReplenishmentRecordsForDisplay(group?.replenish)
  return {
    ...group,
    profile: group?.profile && typeof group.profile === 'object' ? group.profile : {},
    profiles: Array.isArray(group?.profiles) ? group.profiles : [],
    containers: Array.isArray(group?.containers) ? group.containers : [],
    replenish: Array.isArray(group?.replenish) ? group.replenish : [],
    replenishRecords: replenishmentRecords,
    shipments: Array.isArray(group?.shipments) ? group.shipments : [],
  }
}
function containerKey(container) { return [valueFrom(container, ['container_no', 'container_code', 'container']), valueFrom(container, ['load_time']), valueFrom(container, ['warehouse_desc']), valueFrom(container, ['carrier'])].join('-') }
function containerProgress(container) { return getContainerProgress(container) }
function containerStatus(container) { return getContainerStatus(container) }
function shipmentRows(rows) {
  return rows.map(row => {
    const quantity = getOceanShipmentQuantity(row)
    return {
      ...row,
      record_type_label: getOceanShipmentStatus(row),
      quantity_detail: `${quantity.label}：${display(quantity.value)}`,
      completion_label: getOceanShipmentCompletion(row),
    }
  })
}

async function search() {
  state.loading = true
  state.error = ''
  state.errorScope = ''
  state.searched = true
  try {
    const response = await searchLogistics({ q: state.query, warehouse: state.warehouse || undefined })
    state.items = Array.isArray(response?.items) ? response.items : []
  } catch (error) {
    state.error = error?.response?.data?.detail || '物流查询失败，请稍后重试'
    state.errorScope = 'search'
  } finally {
    state.loading = false
  }
}

async function loadWarehouses() {
  state.error = ''
  state.errorScope = ''
  try {
    const response = await getLogisticsWarehouses()
    state.warehouses = Array.isArray(response?.warehouses) ? response.warehouses : []
  } catch (error) {
    state.error = error?.response?.data?.detail || '仓库列表加载失败，请稍后重试'
    state.errorScope = 'warehouse'
  }
}

function retry() { return state.errorScope === 'warehouse' ? loadWarehouses() : search() }

onMounted(loadWarehouses)
</script>

<style scoped>
.logistics-page{display:flex;max-width:1500px;margin:auto;flex-direction:column;gap:16px;color:#17243f}.control-strip{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;padding:5px 2px 4px}.eyebrow{margin:0 0 7px;color:#2f7df4;font-size:9px;font-weight:750;letter-spacing:.18em}.control-strip h2{margin:0;color:#17243f;font-size:23px;font-weight:650}.control-strip p:last-child{margin:6px 0 0;color:#7b89a1;font-size:12px}.search-form{display:flex;gap:8px;min-width:520px}.query-input{width:280px}.warehouse-select{width:190px}.option-count{float:right;margin-left:14px;color:#9aa7ba;font-size:11px}.state-panel{display:flex;min-height:180px;align-items:center;justify-content:center;gap:10px;border:1px solid #dce5f2;border-radius:8px;background:#fff;color:#7b89a1}.state-panel strong{color:#35445f}.state-panel span{font-size:12px}.error-panel{border-color:#f1d4d1;color:#c44c48}.error-panel strong{color:#bd4541}.error-banner{display:flex;align-items:center;gap:10px;padding:10px 13px;border:1px solid #f1d4d1;border-radius:6px;color:#c44c48;background:#fff8f7;font-size:12px}.error-banner strong{color:#bd4541}.error-banner span{flex:1}.result-bar{display:flex;align-items:center;gap:18px;padding:10px 13px;border:1px solid #dce5f2;border-radius:6px;color:#75839b;background:#f8fbff;font-size:12px}.result-bar strong{color:#1767df}.result-bar span:last-child{margin-left:auto;color:#536887}.sku-block{border:1px solid #d7e3f1;border-radius:8px;background:#fff;overflow:hidden}.sku-header{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 18px;border-bottom:1px solid #e7edf5;background:#fbfdff}.sku-title{display:flex;min-width:0;align-items:center;gap:10px}.sku-code{color:#1767df;font-weight:700}.custom-code{padding:3px 7px;border:1px solid #dce8f7;border-radius:4px;color:#6a7d9c;background:#f4f8fe;font-size:11px}.sku-title h3{min-width:0;margin:0;color:#233554;font-size:15px;font-weight:650;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.warehouse-count{color:#8290a6;font-size:11px}.warehouse-group{padding:17px 18px;border-bottom:1px solid #e6edf6}.warehouse-group:last-child{border-bottom:0}.group-heading,.section-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.group-heading{margin-bottom:11px}.group-heading h4{margin:0;font-size:14px}.warehouse-tag{padding:3px 8px;border:1px solid #cfe0f7;border-radius:4px;color:#2f7df4;background:#f1f7ff;font-size:10px}.profile-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid #e0e8f2;border-radius:6px;overflow:hidden}.profile-cell{min-height:68px;padding:11px 13px;border-right:1px solid #e0e8f2;background:#fff}.profile-cell:last-child{border-right:0}.profile-cell span{display:block;color:#8b99af;font-size:10px}.profile-cell strong{display:block;margin-top:7px;color:#283c5b;font-size:16px;font-weight:650}.profile-cell.profile-text strong{font-size:13px}.detail-section{margin-top:15px}.section-title{margin-bottom:8px}.section-title h5{margin:0;color:#3d5272;font-size:12px;font-weight:700}.section-title span{color:#98a6b9;font-size:10px}.container-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.container-row{display:grid;grid-template-columns:minmax(130px,1fr) auto auto;align-items:center;gap:8px;padding:10px 11px;border:1px solid #e1e9f3;border-radius:5px;background:#fbfdff}.container-row>div:first-child{display:flex;min-width:0;flex-direction:column;gap:3px}.container-row strong{overflow:hidden;color:#334a6e;font-size:12px;text-overflow:ellipsis;white-space:nowrap}.container-row span{color:#8795aa;font-size:10px}.stage-seq{white-space:nowrap}.status-tag{padding:3px 7px;border-radius:4px;color:#287a60!important;background:#e9f8f0}.status-tag.active{color:#2f68b1!important;background:#edf4ff}.status-tag.danger{color:#bd514a!important;background:#fff0ef}.container-progress{grid-column:1/-1;display:flex;flex-direction:column;gap:4px;margin-top:3px}.progress-track{height:5px;overflow:hidden;border-radius:5px;background:#e7eef7}.progress-track i{display:block;height:100%;border-radius:inherit;background:#2f7df4;transition:width .2s ease}.progress-nodes{display:grid;grid-template-columns:repeat(5,1fr);gap:4px}.progress-nodes span{display:flex;align-items:center;gap:4px;min-width:0;color:#a2adbd;font-size:9px}.progress-nodes b{display:grid;width:17px;height:17px;flex:0 0 17px;place-items:center;border:1px solid #d7e1ee;border-radius:50%;background:#fff;font-size:9px;font-weight:650}.progress-nodes span.active{color:#4b6f9e}.progress-nodes span.active b{border-color:#8fb8ee;color:#1767df;background:#edf5ff}.progress-nodes span.current{color:#1767df;font-weight:650}.progress-nodes small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.container-dates{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:6px 16px;padding-top:7px;border-top:1px dashed #e1e8f1}.tracking-details{margin-top:10px;border:1px solid #e0e8f2;border-radius:5px;background:#fbfdff}.tracking-details summary{padding:9px 11px;color:#567193;font-size:11px;cursor:pointer}.tracking-list{padding:0 11px 8px}.tracking-row{display:grid;grid-template-columns:170px 1fr 150px;gap:10px;padding:8px 0;border-top:1px solid #edf1f6;font-size:11px}.tracking-row span{color:#8998ad}.tracking-row strong{font-weight:600}.data-section{margin-top:15px}.table-wrap{overflow:auto;border:1px solid #e0e8f2;border-radius:5px}.table-wrap table{width:100%;border-collapse:collapse;min-width:520px;font-size:11px}.table-wrap th{padding:8px 10px;color:#7c8ca5;background:#f7f9fc;font-size:10px;font-weight:650;text-align:left;white-space:nowrap}.table-wrap td{padding:8px 10px;border-top:1px solid #edf1f6;color:#4d607e;white-space:nowrap}.sub-empty{padding:9px 11px;border:1px dashed #dce5f2;color:#9aa7b8;font-size:11px}
@media(max-width:1000px){.control-strip{align-items:stretch;flex-direction:column}.search-form{min-width:0}.profile-grid{grid-template-columns:repeat(2,1fr)}.profile-cell:nth-child(2){border-right:0}.profile-cell:nth-child(-n+2){border-bottom:1px solid #e0e8f2}.container-grid{grid-template-columns:1fr}}
@media(max-width:620px){.search-form{display:grid;grid-template-columns:1fr}.query-input,.warehouse-select{width:100%}.result-bar{align-items:flex-start;flex-direction:column;gap:5px}.result-bar span:last-child{margin-left:0}.sku-title{align-items:flex-start;flex-wrap:wrap}.sku-title h3{width:100%;order:3}.sku-header{align-items:flex-start;flex-direction:column}.profile-grid{grid-template-columns:1fr}.profile-cell{border-right:0!important;border-bottom:1px solid #e0e8f2}.profile-cell:last-child{border-bottom:0}.tracking-row{grid-template-columns:1fr;gap:3px}.container-row{grid-template-columns:1fr auto}.container-dates{grid-column:1/-1}}
.container-card{margin-bottom:10px;padding:14px;border:1px solid #e0e8f2;border-radius:7px;background:#fcfdff}.container-card:last-child{margin-bottom:0}.container-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}.container-heading-main{display:flex;align-items:center;gap:9px}.container-index{color:#304765;font-size:12px;font-weight:700}.container-destination{max-width:55%;overflow:hidden;color:#71829b;font-size:11px;text-overflow:ellipsis;white-space:nowrap}.status-tag.transit{color:#8c6a18!important;background:#fff6db}.status-tag.signed{color:#247750!important;background:#e8f6ee}.status-tag.danger{color:#b64c48!important;background:#fff0ef}.container-meta{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px 14px;margin-top:11px;padding:10px 11px;border:1px solid #e7edf5;border-radius:5px;background:#fff}.container-meta div{display:flex;min-width:0;flex-direction:column;gap:4px}.container-meta span{color:#8795aa;font-size:10px}.container-meta strong{overflow:hidden;color:#405673;font-size:11px;font-weight:600;text-overflow:ellipsis;white-space:nowrap}.container-progress{display:block;margin-top:12px;padding:11px 12px;border:1px solid #e6ecf4;border-radius:6px;background:#fff}.progress-head{display:flex;align-items:baseline;gap:9px;margin-bottom:10px;color:#6e7e95;font-size:10px}.progress-head strong{color:#405673;font-size:11px}.progress-head span:nth-child(2){margin-left:auto;color:#2471d5;font-size:14px;font-weight:700}.progress-track{height:8px;margin:0 8px;overflow:hidden;border-radius:5px;background:#e7edf5}.progress-track i{background:linear-gradient(90deg,#e74c3c,#e67e22,#f1c40f,#7fb84e,#27ae60)}.progress-nodes{margin-top:8px}.progress-nodes span{flex-direction:column;justify-content:flex-start;gap:4px;text-align:center}.progress-nodes b{color:#99a5b5}.progress-nodes span.done b{border-color:var(--stage-color);color:#fff;background:var(--stage-color)}.progress-nodes span.done small{color:#536783}.progress-nodes span.current small{color:#243e61;font-weight:700}.progress-nodes small{width:100%;font-size:10px}.progress-caption{margin:8px 0 0;color:#8997aa;font-size:10px}.tracking-details{margin-top:10px}.tracking-details summary{transition:color .15s ease}.tracking-details summary:hover{color:#1767df}.tracking-details pre{margin:0;padding:10px 12px;border-top:1px solid #e8edf4;color:#445975;background:#fff;font-family:inherit;font-size:11px;line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere}.tracking-empty{margin-top:9px;color:#9aa7b8;font-size:10px}.profile-note{margin-top:8px;color:#8997aa;font-size:11px}.data-section .section-title h5{color:#3d5272}.table-wrap table{min-width:760px}.table-wrap td{vertical-align:top}.table-wrap tbody tr:hover td{background:#f8fbff}
@media(max-width:800px){.container-meta{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:620px){.container-heading{align-items:flex-start;flex-direction:column}.container-destination{max-width:100%}.container-meta{grid-template-columns:1fr 1fr}.progress-head{flex-wrap:wrap}.progress-head span:last-child{width:100%;margin-left:0}.progress-nodes{gap:1px}.progress-nodes small{font-size:9px}.container-card{padding:10px}}

.container-heading {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  align-items: center;
}
.container-heading-meta {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}
.container-heading-meta > div {
  display: flex;
  min-width: 0;
  align-items: baseline;
  gap: 5px;
  white-space: nowrap;
}
.container-heading-meta > div > span {
  color: #8795aa;
  font-size: 10px;
}
.container-heading-meta strong {
  max-width: 240px;
  overflow: hidden;
  color: #405673;
  font-size: 11px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.container-heading-meta .meta-divider {
  color: #c3ccd8;
  font-size: 11px;
}
.container-quantity {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
  padding: 8px 11px;
  border: 1px solid #e7edf5;
  border-radius: 5px;
  background: #fff;
}
.container-quantity span {
  color: #8795aa;
  font-size: 10px;
}
.container-quantity strong {
  color: #405673;
  font-size: 14px;
  font-weight: 650;
}
.container-meta {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
.logistics-page :deep(.data-section) {
  min-width: 0;
  margin-top: 15px;
}
.logistics-page :deep(.data-section .section-title) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}
.logistics-page :deep(.data-section .section-title h5) {
  margin: 0;
  color: #3d5272;
  font-size: 12px;
  font-weight: 700;
}
.logistics-page :deep(.data-section .section-title span) {
  color: #98a6b9;
  font-size: 10px;
}
.logistics-page :deep(.data-section .table-wrap) {
  max-width: 100%;
  overflow-x: auto;
  border: 1px solid #e0e8f2;
  border-radius: 5px;
  scrollbar-gutter: stable;
}
.logistics-page :deep(.data-section .table-wrap table) {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
  font-size: 11px;
  table-layout: auto;
}
.logistics-page :deep(.data-section .table-wrap .wide-table) {
  min-width: 980px;
}
.logistics-page :deep(.data-section .table-wrap th),
.logistics-page :deep(.data-section .table-wrap td) {
  padding: 8px 10px;
  line-height: 1.45;
  text-align: left;
  vertical-align: middle;
  white-space: nowrap;
}
.logistics-page :deep(.data-section .table-wrap th) {
  border-bottom: 1px solid #e6edf5;
  color: #7c8ca5;
  background: #f7f9fc;
  font-size: 10px;
  font-weight: 650;
}
.logistics-page :deep(.data-section .table-wrap td) {
  border-top: 1px solid #edf1f6;
  color: #4d607e;
}
.logistics-page :deep(.data-section .table-wrap th:nth-child(3)),
.logistics-page :deep(.data-section .table-wrap td:nth-child(3)),
.logistics-page :deep(.data-section .table-wrap th:nth-child(5)),
.logistics-page :deep(.data-section .table-wrap td:nth-child(5)) {
  text-align: right;
}
.logistics-page :deep(.data-section .table-wrap tbody tr:hover td) {
  background: #f8fbff;
}
.logistics-page :deep(.data-section .sub-empty) {
  padding: 9px 11px;
  border: 1px dashed #dce5f2;
  color: #9aa7b8;
  font-size: 11px;
}

@media (max-width: 800px) {
  .container-heading-meta {
    gap: 6px;
  }
  .container-heading-meta strong {
    max-width: 170px;
  }
}
@media (max-width: 620px) {
  .container-heading {
    grid-template-columns: minmax(0, 1fr);
    align-items: start;
    gap: 8px;
  }
  .container-heading-meta {
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: 5px 8px;
  }
  .container-heading-meta .meta-divider {
    display: none;
  }
  .container-heading-meta strong {
    max-width: 150px;
  }
}

.profile-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

@media (max-width: 1000px) {
  .profile-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .profile-cell:nth-child(odd) {
    border-right: 1px solid #e0e8f2;
  }

  .profile-cell:nth-child(even) {
    border-right: 0;
  }

  .profile-cell:nth-child(-n + 2) {
    border-bottom: 1px solid #e0e8f2;
  }
}

@media (max-width: 620px) {
  .profile-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .profile-cell {
    border-right: 0 !important;
    border-bottom: 1px solid #e0e8f2;
  }

  .profile-cell:last-child {
    border-bottom: 0;
  }
}
</style>
