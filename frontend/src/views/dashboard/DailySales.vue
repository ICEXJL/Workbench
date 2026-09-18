<template>
  <div class="overview-page">
    <section class="control-strip">
      <div><p class="eyebrow">DAILY PERFORMANCE</p><h2>{{ dateTitle }} 经营概览</h2><p>聚合东南亚店铺订单、销售额与仓库履约表现</p></div>
      <div class="filters">
        <a-date-picker v-model:value="selectedDate" value-format="YYYY-MM-DD" :allow-clear="false" @change="dateChanged" />
        <a-select v-model:value="selectedStore" class="store-select" placeholder="全部店铺" allow-clear @change="filtersChanged">
          <a-select-option v-for="store in storeList" :key="store" :value="store">{{ store }}</a-select-option>
        </a-select>
      </div>
    </section>

    <section class="metric-grid" aria-label="核心指标">
      <article class="metric primary"><span class="metric-icon"><svg viewBox="0 0 24 24"><path d="M4 7h16l-1 13H5L4 7ZM8 7a4 4 0 0 1 8 0" /></svg></span><div><p>订单总量</p><strong>{{ formatInteger(summary.orders) }}</strong><small>当前筛选范围</small></div></article>
      <article class="metric"><span class="metric-icon"><svg viewBox="0 0 24 24"><path d="M4 19h16M6 16l4-5 3 3 5-8" /></svg></span><div><p>销售额</p><strong>¥ {{ formatMoney(summary.sales) }}</strong><small>人民币口径</small></div></article>
      <article class="metric"><span class="metric-icon"><svg viewBox="0 0 24 24"><path d="M4 10h16v10H4V10ZM7 10V6h10v4M8 15h8" /></svg></span><div><p>活跃店铺</p><strong>{{ summary.stores }}</strong><small>有销售记录店铺</small></div></article>
      <article class="metric"><span class="metric-icon"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="8"/><path d="M12 8v5l3 2" /></svg></span><div><p>平均客单</p><strong>¥ {{ formatMoney(summary.aov) }}</strong><small>销售额 / 订单量</small></div></article>
    </section>

    <section class="data-panel">
      <div class="panel-head"><div><h3>店铺经营明细</h3><p>{{ total }} 条记录 · 翻页加载</p></div><span class="live-tag"><i></i>LIVE DATA</span></div>
      <a-empty v-if="!loading && rows.length === 0" description="当前日期和店铺范围暂无数据" />
      <a-table v-else :loading="loading" :data-source="rows" :columns="columns" :pagination="pagination" :scroll="{ x: 760 }" :row-key="rowKey" size="middle" @change="tableChanged">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'dpbh'"><span class="store-cell"><i :class="platformClass(record.dpbh)"></i>{{ record.dpbh }}</span></template>
          <template v-else-if="column.key === 'dds'"><strong class="number-cell">{{ formatInteger(record.dds) }}</strong></template>
          <template v-else-if="column.key === 'xse'"><strong class="sales-cell">¥ {{ formatMoney(record.xse) }}</strong></template>
          <template v-else-if="column.key === 'ckh'"><span class="warehouse-tag">{{ record.ckh || '未配置' }}</span></template>
        </template>
      </a-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { getDailySales } from '@/services/api'
const loading=ref(false), rows=ref([]), selectedDate=ref(dayjs().subtract(1,'day').format('YYYY-MM-DD')), selectedStore=ref(), storeList=ref([]), total=ref(0), page=ref(1), pageSize=ref(20)
const pageCache=new Map(), pending=new Map()
let requestVersion=0
const dateTitle=computed(()=>dayjs(selectedDate.value).format('M月D日'))
const summary=ref({orders:0,sales:0,stores:0,aov:0})
const pagination=computed(()=>({current:page.value,pageSize:pageSize.value,total:total.value,showSizeChanger:true,pageSizeOptions:['10','20','50'],showTotal:n=>`共 ${n} 条`}))
const columns=[
  {title:'店铺代号',dataIndex:'dpbh',key:'dpbh',width:260},
  {title:'订单量',dataIndex:'dds',key:'dds',width:120},
  {title:'销售额',dataIndex:'xse',key:'xse',width:150},
  {title:'仓库',dataIndex:'ckh',key:'ckh',width:120},{title:'日期',dataIndex:'rq',key:'rq',width:130},
]
const formatInteger=(value)=>new Intl.NumberFormat('zh-CN',{maximumFractionDigits:0}).format(Number(value||0))
const formatMoney=(value)=>new Intl.NumberFormat('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(value||0))
const platformClass=(store='')=>{const value=String(store).toLowerCase();return value.includes('shopee')?'shopee':value.includes('lazada')?'lazada':value.includes('tiktok')?'tiktok':'other'}
const rowKey=(record,index)=>`${record.dpbh}-${record.rq}-${index}`
const cacheKey=(targetPage,targetSize=pageSize.value)=>[selectedDate.value,selectedStore.value||'',targetPage,targetSize].join('|')
function fetchPage(targetPage,targetSize=pageSize.value){const key=cacheKey(targetPage,targetSize);if(pageCache.has(key))return Promise.resolve(pageCache.get(key));if(pending.has(key))return pending.get(key);const task=getDailySales({target_date:selectedDate.value,store:selectedStore.value,page:targetPage,page_size:targetSize}).then(data=>{pageCache.set(key,data);return data}).finally(()=>pending.delete(key));pending.set(key,task);return task}
async function showPage(targetPage=1,targetSize=pageSize.value){const version=++requestVersion;loading.value=true;try{const data=await fetchPage(targetPage,targetSize);if(version!==requestVersion)return;page.value=targetPage;pageSize.value=targetSize;rows.value=data.items;total.value=data.total;summary.value=data.summary;storeList.value=data.stores;prefetch(targetPage,targetSize,data.total)}finally{if(version===requestVersion)loading.value=false}}
function prefetch(current,size,count){const last=Math.ceil(count/size);[current+1,current+2].filter(p=>p<=last).forEach(p=>fetchPage(p,size).catch(()=>{}))}
function filtersChanged(){pageCache.clear();showPage(1)}
function dateChanged(){selectedStore.value=undefined;filtersChanged()}
function tableChanged(p){if(p.pageSize!==pageSize.value)pageCache.clear();showPage(p.current,p.pageSize)}
onMounted(()=>showPage(1))
</script>

<style scoped>
.overview-page{display:flex;flex-direction:column;gap:18px}.control-strip{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;padding:5px 2px 7px}.eyebrow{margin:0 0 7px;color:#2f7df4;font-size:9px;font-weight:750;letter-spacing:.18em}.control-strip h2{margin:0;color:#17243f;font-size:23px;font-weight:650}.control-strip p:last-child{margin:6px 0 0;color:#7b89a1;font-size:12px}.filters{display:flex;gap:10px}.store-select{width:240px}
.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid #dce5f2;border-radius:8px;background:#fff;overflow:hidden}.metric{display:flex;align-items:center;gap:15px;min-height:124px;padding:22px;border-right:1px solid #e4ebf4}.metric:last-child{border-right:0}.metric-icon{display:grid;width:40px;height:40px;flex:0 0 40px;place-items:center;border-radius:7px;color:#2f7df4;background:#edf5ff}.metric-icon svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-linecap:round;stroke-linejoin:round;stroke-width:1.7}.metric div{display:flex;min-width:0;flex-direction:column}.metric p{margin:0 0 3px;color:#71809d;font-size:11px}.metric strong{overflow:hidden;color:#17243f;font-size:24px;font-weight:650;letter-spacing:0;text-overflow:ellipsis;white-space:nowrap;font-variant-numeric:tabular-nums}.metric small{margin-top:4px;color:#a1adc0;font-size:9px}.metric.primary{background:#f7faff}.metric.primary strong{color:#1767df}
.data-panel{border:1px solid #dce5f2;border-radius:8px;background:#fff;overflow:hidden}.panel-head{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 22px;border-bottom:1px solid #e5ebf4}.panel-head h3{margin:0;color:#17243f;font-size:15px}.panel-head p{margin:4px 0 0;color:#8b98ae;font-size:10px}.live-tag{display:flex;align-items:center;gap:7px;color:#68809f;font-size:9px;font-weight:700;letter-spacing:.1em}.live-tag i{width:7px;height:7px;border-radius:50%;background:#28b47a}.store-cell{display:flex;align-items:center;gap:9px;color:#35445f;font-weight:550}.store-cell i{width:7px;height:7px;border-radius:2px}.store-cell i.shopee{background:#ee6b4d}.store-cell i.lazada{background:#7457d5}.store-cell i.tiktok{background:#2c313f}.store-cell i.other{background:#7f91aa}.number-cell{color:#34435d;font-variant-numeric:tabular-nums}.sales-cell{color:#1767df;font-variant-numeric:tabular-nums}.warehouse-tag{display:inline-flex;padding:2px 8px;border-radius:4px;color:#59708f;background:#eef3f9;font-size:11px}
:deep(.ant-table-wrapper .ant-table){color:#52617a;font-size:12px}:deep(.ant-table-wrapper .ant-table-thead>tr>th){color:#7f8ca2;background:#f7f9fc;font-size:10px;font-weight:650}:deep(.ant-table-wrapper .ant-table-tbody>tr>td){border-bottom-color:#edf1f6}:deep(.ant-pagination .ant-pagination-item-active){border-color:#2f7df4}:deep(.ant-pagination .ant-pagination-item-active a){color:#2f7df4}
@media(max-width:1100px){.metric-grid{grid-template-columns:repeat(2,1fr)}.metric:nth-child(2){border-right:0}.metric:nth-child(-n+2){border-bottom:1px solid #e4ebf4}}
@media(max-width:700px){.control-strip{align-items:stretch;flex-direction:column}.filters{display:grid;grid-template-columns:1fr}.store-select{width:100%}.metric-grid{grid-template-columns:1fr 1fr}.metric{min-height:110px;padding:16px;align-items:flex-start}.metric-icon{width:34px;height:34px;flex-basis:34px}.metric strong{font-size:19px}}
@media(max-width:460px){.metric-grid{grid-template-columns:1fr}.metric{border-right:0!important;border-bottom:1px solid #e4ebf4}.metric:last-child{border-bottom:0}.panel-head{align-items:flex-start;flex-direction:column}}
</style>
