<template>
  <div>
    <a-card :loading="loading">
      <a-typography-title :level="4">{{ dateLabel }} 各区域订单销售情况表</a-typography-title>
      <a-empty v-if="regionData.length === 0" description="昨日没有区域订单数据" />
      <template v-else>
        <EChart :option="regionOption" :height="440" />
        <a-divider />
        <a-typography-title :level="5">区域分布明细</a-typography-title>
        <a-table :data-source="regionData" :columns="regionColumns" :pagination="false" size="middle" :scroll="{ x: true }" />
      </template>
    </a-card>

    <a-card :loading="loading" style="margin-top: 24px">
      <a-typography-title :level="4">{{ dateLabel }} 菲律宾各仓库订单和销售情况表</a-typography-title>
      <a-empty v-if="whData.length === 0" description="昨日没有仓库订单数据" />
      <template v-else>
        <EChart :option="whOption" :height="440" />
        <a-divider />
        <a-typography-title :level="5">仓库分布明细</a-typography-title>
        <a-table :data-source="whData" :columns="whColumns" :pagination="false" size="middle" :scroll="{ x: true }" />
      </template>
    </a-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import EChart from '@/components/EChart.vue'
import { getRegionDistribution, getWarehouseDistribution } from '@/services/api'

const loading = ref(true)
const regionData = ref([])
const whData = ref([])
const columnTitle = (key) => key.includes('销售额') ? `${key}（USD）` : key

const dateLabel = computed(() => dayjs().subtract(1, 'day').format('M月D日'))

const buildOption = (refData) => ({
  tooltip: { trigger: 'axis' },
  legend: { top: 0 },
  grid: { left: 60, right: 80, bottom: 40, top: 50 },
  xAxis: { type: 'category', data: refData.value.map(d => d['区域'] || d['仓库']) },
    yAxis: [{ type: 'value', name: '订单量' }, { type: 'value', name: '销售额（USD）' }],
  series: [
    { name: '订单量', type: 'bar', data: refData.value.map(d => d['订单量']), itemStyle: { color: '#1F618D' } },
    { name: '销售额（USD）', type: 'bar', data: refData.value.map(d => d['销售额']), itemStyle: { color: '#E67E22' }, yAxisIndex: 1 },
  ],
})

const regionOption = computed(() => buildOption(regionData))
const whOption = computed(() => buildOption(whData))

const regionColumns = computed(() => Object.keys(regionData.value[0] || {}).map((k) => ({ title: columnTitle(k), dataIndex: k, key: k })))
const whColumns = computed(() => Object.keys(whData.value[0] || {}).map((k) => ({ title: columnTitle(k), dataIndex: k, key: k })))

onMounted(async () => {
  try {
    const [reg, wh] = await Promise.all([getRegionDistribution(), getWarehouseDistribution()])
    regionData.value = reg
    whData.value = wh
  } finally {
    loading.value = false
  }
})
</script>
