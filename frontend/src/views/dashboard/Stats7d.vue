<template>
  <a-card :loading="loading">
    <a-tabs>
      <a-tab-pane key="regional" tab="各地区近 7 天统计">
        <EChart :option="regionalOption" :height="480" />
        <a-divider />
        <a-typography-title :level="5">各区域数据明细</a-typography-title>
        <a-table :data-source="regionalData" :columns="regionalColumns" :pagination="false" size="middle" :scroll="{ x: true }" />
      </a-tab-pane>

      <a-tab-pane key="platform" tab="各平台近 7 天统计">
        <EChart :option="platformOption" :height="480" />
        <a-divider />
        <a-typography-title :level="5">各平台数据明细</a-typography-title>
        <a-table :data-source="platformData" :columns="platformColumns" :pagination="false" size="middle" :scroll="{ x: true }" />
      </a-tab-pane>
    </a-tabs>
  </a-card>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import EChart from '@/components/EChart.vue'
import { getRegionalStats, getPlatformStats } from '@/services/api'

const loading = ref(true)
const regionalData = ref([])
const platformData = ref([])

// ---------- 地区图表 ----------
const regionalOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0 },
  grid: { left: 60, right: 60, bottom: 50, top: 60 },
  title: { text: '各区域近7天销售额以及订单数据统计', left: 'center' },
  xAxis: { type: 'category', data: regionalData.value.map((d) => d.rq) },
  yAxis: [{ type: 'value', name: '订单量' }, { type: 'value', name: '销售额' }],
  series: [
    { name: '南昌订单', type: 'bar', data: regionalData.value.map((d) => d['南昌部_订单量']), itemStyle: { color: '#B2E29B' } },
    { name: '武汉订单', type: 'bar', data: regionalData.value.map((d) => d['武汉部_订单量']), itemStyle: { color: '#93D2F3' } },
    { name: '深圳订单', type: 'bar', data: regionalData.value.map((d) => d['深圳部_订单量']), itemStyle: { color: '#D996D4' } },
    { name: '南昌销售额', type: 'line', yAxisIndex: 1, data: regionalData.value.map((d) => d['南昌部_销售额']), itemStyle: { color: '#4A72B0' } },
    { name: '武汉销售额', type: 'line', yAxisIndex: 1, data: regionalData.value.map((d) => d['武汉部_销售额']), itemStyle: { color: '#FF0000' } },
    { name: '深圳销售额', type: 'line', yAxisIndex: 1, data: regionalData.value.map((d) => d['深圳部_销售额']), itemStyle: { color: '#3D8415' } },
  ],
}))

// ---------- 平台图表 ----------
const platformOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  legend: { bottom: 0 },
  grid: { left: 60, right: 60, bottom: 50, top: 60 },
  title: { text: '各平台近7天销售额以及订单数据统计', left: 'center' },
  xAxis: { type: 'category', data: platformData.value.map((d) => d.rq) },
  yAxis: [{ type: 'value', name: '订单量' }, { type: 'value', name: '销售额' }],
  series: [
    { name: 'Lazada订单', type: 'bar', data: platformData.value.map((d) => d['Lazada_订单量']), itemStyle: { color: '#B2E29B' } },
    { name: 'Shopee订单', type: 'bar', data: platformData.value.map((d) => d['Shopee_订单量']), itemStyle: { color: '#93D2F3' } },
    { name: 'TK订单', type: 'bar', data: platformData.value.map((d) => d['TK_订单量']), itemStyle: { color: '#D996D4' } },
    { name: 'Lazada销售额', type: 'line', yAxisIndex: 1, data: platformData.value.map((d) => d['Lazada_销售额']), itemStyle: { color: '#4A72B0' } },
    { name: 'Shopee销售额', type: 'line', yAxisIndex: 1, data: platformData.value.map((d) => d['Shopee_销售额']), itemStyle: { color: '#FF0000' } },
    { name: 'TK销售额', type: 'line', yAxisIndex: 1, data: platformData.value.map((d) => d['TK_销售额']), itemStyle: { color: '#3D8415' } },
  ],
}))

// ---------- 明细表列：动态生成 ----------
const regionalColumns = computed(() =>
  Object.keys(regionalData.value[0] || {}).map((k) => ({ title: k, dataIndex: k, key: k }))
)
const platformColumns = computed(() =>
  Object.keys(platformData.value[0] || {}).map((k) => ({ title: k, dataIndex: k, key: k }))
)

onMounted(async () => {
  try {
    const [reg, plat] = await Promise.all([getRegionalStats(), getPlatformStats()])
    regionalData.value = reg
    platformData.value = plat
  } finally {
    loading.value = false
  }
})
</script>
