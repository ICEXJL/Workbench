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
          <div class="sku-title"><span class="sku-code">{{ display(item.sku) }}</span><span class="custom-code">{{ display(item.custom_sku) }}</span><h3>{{ display(item.product_name) }}</h3></div>
          <span class="warehouse-count">{{ formatNumber(item.warehouses?.length) }} 个仓库</span>
        </header>

        <div v-for="group in normalizedWarehouses(item)" :key="group.warehouse || 'all'" class="warehouse-group">
          <div class="group-heading"><div><span class="eyebrow">WAREHOUSE PROFILE</span><h4>{{ display(group.warehouse) }}</h4></div><span class="warehouse-tag">{{ group.warehouse ? '单仓资料' : '跨仓汇总' }}</span></div>
          <div class="profile-grid">
            <div class="profile-cell"><span>库存</span><strong>{{ numberFrom(group.profile, ['available_qty', 'inventory', 'stock', 'stock_qty', 'quantity']) }}</strong></div>
            <div class="profile-cell"><span>采购中</span><strong>{{ numberFrom(group.profile, ['purchasing', 'purchasing_qty', 'purchase_qty', 'in_purchase']) }}</strong></div>
            <div class="profile-cell"><span>采购价</span><strong>{{ moneyFrom(group.profile, ['price', 'purchase_price', 'cost_price', '采购价']) }}</strong></div>
            <div class="profile-cell profile-text"><span>档案状态</span><strong>{{ valueFrom(group.profile, ['product_status', 'status', 'profile_status', 'state']) }}</strong></div>
          </div>

          <section class="detail-section" v-if="group.containers.length">
            <div class="section-title"><h5>货柜进度</h5><span>{{ group.containers.length }} 条记录</span></div>
            <div class="container-grid">
              <article v-for="container in group.containers" :key="containerKey(container)" class="container-row">
                <div><strong>{{ valueFrom(container, ['container_no', 'container_code', 'container']) }}</strong><span>{{ valueFrom(container, ['stage_name', 'stage']) }}</span></div>
                <span class="stage-seq">阶段 {{ valueFrom(container, ['stage_seq']) }}</span>
                <span class="status-tag" :class="statusClass(container.status)">{{ valueFrom(container, ['status']) }}</span>
                <div class="container-progress" aria-label="货柜阶段进度">
                  <div class="progress-track"><i :style="{ width: stageProgress(container) }"></i></div>
                  <div class="progress-nodes"><span v-for="step in 5" :key="step" :class="{ active: step <= stageNumber(container), current: step === stageNumber(container) }"><b>{{ step }}</b><small>{{ step === stageNumber(container) ? display(container.stage_name) : `阶段 ${step}` }}</small></span></div>
                </div>
                <div class="container-dates"><span>装柜 {{ valueFrom(container, ['load_time']) }}</span><span>仓库 {{ valueFrom(container, ['warehouse_desc']) }}</span><span>承运 {{ valueFrom(container, ['carrier']) }}</span><span>预计 {{ valueFrom(container, ['eta', 'estimated_arrival']) }}</span><span>实际 {{ valueFrom(container, ['actual_in', 'actual_arrival']) }}</span></div>
              </article>
            </div>
          </section>
          <div v-else class="sub-empty">暂无货柜进度</div>

          <details v-if="trackingRows(group).length" class="tracking-details">
            <summary>查看物流轨迹（{{ trackingRows(group).length }} 条）</summary>
            <div class="tracking-list"><div v-for="(track, index) in trackingRows(group)" :key="trackKey(track, index)" class="tracking-row"><span>{{ valueFrom(track, ['time', 'event_time', 'created_at', 'date']) }}</span><strong>{{ valueFrom(track, ['status', 'event', 'description', 'remark']) }}</strong><span>{{ valueFrom(track, ['location', 'place', 'warehouse']) }}</span></div></div>
          </details>

          <DataTable title="补货表" :rows="group.replenish" :columns="replenishColumns" />
          <DataTable title="未发货" :rows="pendingShipments(group.shipments)" :columns="shipmentColumns" />
          <DataTable title="已发货" :rows="emittedShipments(group.shipments)" :columns="shipmentColumns" />
          <DataTable title="批次-货柜映射" :rows="allContainerMaps(group)" :columns="mappingColumns" />
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { defineComponent, h, onMounted, reactive } from 'vue'
import { getLogisticsWarehouses, searchLogistics } from '@/services/api'

const state = reactive({ query: '', warehouse: '', warehouses: [], items: [], searched: false, loading: false, error: '', errorScope: '' })
const replenishColumns = [
  { key: 'date', label: '登记日期', fields: ['reg_date', 'eta', 'expected_date', 'created_at'] },
  { key: 'air', label: '空运数量', fields: ['air_qty', 'air_quantity'] },
  { key: 'sea', label: '海运数量', fields: ['sea_qty', 'sea_quantity'] },
  { key: 'operator', label: '负责人', fields: ['operator_name', 'operator'] },
]
const shipmentColumns = [
  { key: 'type', label: '记录类型', fields: ['record_type', 'batch_no', 'batch', 'shipment_no'] },
  { key: 'date', label: '登记日期', fields: ['reg_date', 'ship_date', 'shipped_at', 'created_at'] },
  { key: 'orderQty', label: '订单数量', fields: ['order_qty', 'quantity', 'qty', 'shipment_qty'] },
  { key: 'qty2', label: '数量 2', fields: ['qty2'] },
  { key: 'badge', label: '提单号', fields: ['badge_no'] },
  { key: 'done', label: '完成', fields: ['is_done'] },
  { key: 'statusRaw', label: '原始状态', fields: ['status_raw', 'status'] },
  { key: 'handover', label: '交接', fields: ['handover'] },
  { key: 'carrier', label: '承运商', fields: ['carrier'] },
]
const mappingColumns = [
  { key: 'badge', label: '提单号', fields: ['badge_no', 'batch_no', 'batch'] },
  { key: 'handover', label: '交接', fields: ['handover'] },
  { key: 'carrier', label: '承运商', fields: ['carrier'] },
  { key: 'container', label: '货柜', fields: ['container_key', 'container_no', 'container_code', 'container'] },
  { key: 'status', label: '映射状态', fields: ['link_status', 'status', 'state'] },
]

const DataTable = defineComponent({
  props: { title: String, rows: { type: Array, default: () => [] }, columns: { type: Array, default: () => [] } },
  setup(props) {
    return () => h('section', { class: 'detail-section data-section' }, [
      h('div', { class: 'section-title' }, [h('h5', props.title), h('span', `${props.rows.length} 条记录`)]),
      props.rows.length ? h('div', { class: 'table-wrap' }, [h('table', [
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
function numberFrom(record, fields) { const value = valueFrom(record, fields); return value === '-' ? '-' : formatNumber(value) }
function moneyFrom(record, fields) {
  const value = valueFrom(record, fields)
  const number = Number(value)
  return value === '-' || !Number.isFinite(number) ? '-' : `¥ ${number.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}
function normalizedWarehouses(item) { return Array.isArray(item?.warehouses) && item.warehouses.length ? item.warehouses.map(normalizeGroup) : [normalizeGroup({})] }
function normalizeGroup(group) {
  return {
    ...group,
    profile: group?.profile && typeof group.profile === 'object' ? group.profile : {},
    containers: Array.isArray(group?.containers) ? group.containers : [],
    replenish: Array.isArray(group?.replenish) ? group.replenish : [],
    shipments: Array.isArray(group?.shipments) ? group.shipments : [],
    containerMaps: Array.isArray(group?.container_maps) ? group.container_maps : [],
  }
}
function containerKey(container) { return [valueFrom(container, ['container_no', 'container_code', 'container']), valueFrom(container, ['load_time']), valueFrom(container, ['warehouse_desc']), valueFrom(container, ['carrier'])].join('-') }
function trackKey(track, index) { return `${valueFrom(track, ['time', 'event_time', 'created_at'])}-${index}` }
function trackingValue(value) {
  if (Array.isArray(value)) return value.flatMap(item => typeof item === 'string' ? [{ description: item }] : item && typeof item === 'object' ? [item] : [])
  if (typeof value === 'string' && value.trim()) return [{ description: value }]
  return []
}
function trackingRows(group) {
  return [
    ...group.containers.flatMap(container => trackingValue(container.tracking).concat(trackingValue(container.tracks))),
    ...group.shipments.flatMap(shipment => Array.isArray(shipment.container_maps) ? shipment.container_maps : []),
  ]
}
function allContainerMaps(group) {
  return [
    ...group.containerMaps,
    ...group.shipments.flatMap(shipment => Array.isArray(shipment.container_maps) ? shipment.container_maps : []),
  ]
}
function shipmentIsEmitted(row) {
  const type = String(row?.record_type || '').trim().toUpperCase()
  if (['EMITTED', 'SHIPPED', '已发货', '已出货'].includes(type)) return true
  if (['PENDING', '未发货'].includes(type)) return false
  if (row?.is_done === true || row?.is_done === 1 || String(row?.is_done).toLowerCase() === 'true' || String(row?.is_done) === '1') return true
  const status = String(row?.status_raw || row?.status || '').trim().toLowerCase()
  return ['emitted', 'shipped', '已发货', '已出货', 'done', 'completed', '完成'].includes(status)
}
function pendingShipments(rows) { return rows.filter(row => !shipmentIsEmitted(row)) }
function emittedShipments(rows) { return rows.filter(shipmentIsEmitted) }
function stageNumber(container) {
  const sequence = Number(container?.stage_seq)
  return Number.isFinite(sequence) ? Math.min(5, Math.max(1, sequence)) : 0
}
function stageProgress(container) {
  const status = String(container?.status || '').toLowerCase()
  if (['已完成', '完成', 'done', 'completed'].includes(status)) return '100%'
  const sequence = stageNumber(container)
  return sequence ? `${((sequence - 1) / 4) * 100}%` : '0%'
}
function statusClass(status) {
  const text = String(status || '').toLowerCase()
  return ['已完成', '完成', 'done', 'completed'].includes(text) ? 'done' : ['异常', '延误', 'failed', 'exception'].includes(text) ? 'danger' : 'active'
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
</style>
