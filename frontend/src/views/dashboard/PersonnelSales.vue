<template>
  <div>
    <a-card :loading="loading">
      <a-space wrap>
        <a-date-picker v-model:value="cxrq" value-format="YYYY-MM-DD" @change="load" />
        <a-select v-model:value="jc" style="width: 140px" placeholder="部门简称" @change="onJcChange">
          <a-select-option value="全部">全部</a-select-option>
          <a-select-option v-for="s in jcList" :key="s" :value="s">{{ s }}</a-select-option>
        </a-select>
        <a-select v-model:value="zm" style="width: 140px" placeholder="组别" @change="onZmChange">
          <a-select-option value="全部">全部</a-select-option>
          <a-select-option v-for="s in zmList" :key="s" :value="s">{{ s }}</a-select-option>
        </a-select>
        <a-select v-model:value="yy" style="width: 140px" placeholder="运营" @change="filtersChanged">
          <a-select-option value="全部">全部</a-select-option>
          <a-select-option v-for="s in yyList" :key="s" :value="s">{{ s }}</a-select-option>
        </a-select>
      </a-space>
      <a-divider />
      <a-empty v-if="!loading && rows.length === 0" :description="`基准日期 ${cxrq} 无销售业绩数据`" />
      <a-table
        v-else
        :data-source="rows"
        :columns="columns"
        :pagination="pagination"
        :scroll="{ x: 1500 }"
        size="middle"
        bordered
        @change="tableChanged"
      />
    </a-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { getPersonnelSales } from '@/services/api'

const loading = ref(false)
const cxrq = ref(dayjs().subtract(1, 'day').format('YYYY-MM-DD'))
const rows = ref([])
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
  for (let i = 7; i >= 1; i--) {
    const d = dayjs(cxrq.value).subtract(i, 'day')
    headers.push(`${d.month() + 1}月${d.date()}日`)
  }
  return headers
})

const columns = computed(() => {
  const base = [
    { title: '部门简称', dataIndex: 'jc', key: 'jc', fixed: 'left', width: 90 },
    { title: '组别', dataIndex: 'zm', key: 'zm', fixed: 'left', width: 90 },
    { title: '运营', dataIndex: 'yy', key: 'yy', fixed: 'left', width: 90 },
    { title: '入职时间', dataIndex: 'rzsj', key: 'rzsj', fixed: 'left', width: 110 },
    { title: '店铺编号', dataIndex: 'dpbh', key: 'dpbh', fixed: 'left', width: 160 },
    { title: '平台', dataIndex: 'fl', key: 'fl', width: 100 },
  ]
  const dayCols = []
  dayHeaders.value.forEach((h, idx) => {
    const n = idx + 1
    dayCols.push({
      title: h,
      children: [
        { title: '订单数', dataIndex: `dd${n}`, key: `dd${n}`, width: 90 },
        { title: '销售额（USD）', dataIndex: `xs${n}`, key: `xs${n}`, width: 110 },
      ],
    })
  })
  return [...base, ...dayCols]
})

const pagination = computed(() => ({ current: page.value, pageSize: pageSize.value, total: total.value, showSizeChanger: true, pageSizeOptions: ['10','20','50'], showTotal: (n) => `共 ${n} 条` }))
const cacheKey = (targetPage, targetSize=pageSize.value) => [cxrq.value,jc.value,zm.value,yy.value,targetPage,targetSize].join('|')
function fetchPage(targetPage,targetSize=pageSize.value){const key=cacheKey(targetPage,targetSize);if(pageCache.has(key))return Promise.resolve(pageCache.get(key));if(pending.has(key))return pending.get(key);const task=getPersonnelSales({cxrq:cxrq.value,department:jc.value==='全部'?undefined:jc.value,group:zm.value==='全部'?undefined:zm.value,operator:yy.value==='全部'?undefined:yy.value,page:targetPage,page_size:targetSize}).then(data=>{pageCache.set(key,data);return data}).finally(()=>pending.delete(key));pending.set(key,task);return task}
async function showPage(targetPage=1,targetSize=pageSize.value){const version=++requestVersion;loading.value=true;try{const data=await fetchPage(targetPage,targetSize);if(version!==requestVersion)return;page.value=targetPage;pageSize.value=targetSize;rows.value=data.items;total.value=data.total;options.value=data.options;prefetch(targetPage,targetSize,data.total)}finally{if(version===requestVersion)loading.value=false}}
function prefetch(current,size,count){const last=Math.ceil(count/size);[current+1,current+2].filter(p=>p<=last).forEach(p=>fetchPage(p,size).catch(()=>{}))}
function filtersChanged(){pageCache.clear();showPage(1)}
function onJcChange(){zm.value='全部';yy.value='全部';filtersChanged()}
function onZmChange(){yy.value='全部';filtersChanged()}
function tableChanged(p){if(p.pageSize!==pageSize.value)pageCache.clear();showPage(p.current,p.pageSize)}
function load(){pageCache.clear();showPage(1)}

onMounted(load)
</script>
