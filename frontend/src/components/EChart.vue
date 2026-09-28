<template>
  <div ref="chartRef" :style="{ width: '100%', height: height + 'px' }"></div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: Number, default: 480 },
})
const emit = defineEmits(['chart-click'])

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
    chart.on('click', params => emit('chart-click', params))
  }
  chart.setOption(props.option, true)
}

function handleResize() {
  chart && chart.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.off('click')
    chart.dispose()
  }
})

watch(() => props.option, render, { deep: true })
</script>
