<template>
  <a-card>
    <a-space wrap style="margin-bottom: 16px">
      <a-input v-model:value="searchName" placeholder="搜索 姓名 (Name)" allow-clear style="width: 200px" />
      <a-select v-model:value="searchApt" style="width: 180px" placeholder="筛选 部门 (Apt)" allow-clear>
        <a-select-option v-for="s in aptList" :key="s" :value="s">{{ s }}</a-select-option>
      </a-select>
      <a-select v-model:value="searchRoles" style="width: 200px" placeholder="筛选 角色 (Roles)" allow-clear>
        <a-select-option v-for="s in rolesList" :key="s" :value="s">{{ s }}</a-select-option>
      </a-select>
      <a-button @click="resetFilter">重置</a-button>
    </a-space>

    <a-card :loading="loading">
      <a-empty v-if="filteredData.length === 0" description="没有找到符合查询条件的人员数据" />
      <template v-else>
        <a-typography-text type="success">查询成功，符合条件的共计 {{ filteredData.length }} 条。</a-typography-text>
        <a-table :data-source="filteredData" :columns="columns" :pagination="{ pageSize: 20 }" size="middle" row-key="name" />
      </template>
    </a-card>
  </a-card>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { getManagement } from '@/services/api'

const loading = ref(true)
const rawData = ref([])
const searchName = ref('')
const searchApt = ref(null)
const searchRoles = ref(null)

const aptList = computed(() => [...new Set(rawData.value.map((d) => String(d.apt)).filter(Boolean))])
const rolesList = computed(() => [...new Set(rawData.value.map((d) => String(d.roles)).filter(Boolean))])

const columns = [
  { title: '姓名 (Name)', dataIndex: 'name', key: 'name' },
  { title: '角色 (Roles)', dataIndex: 'roles', key: 'roles' },
  { title: '部门 (Apt)', dataIndex: 'apt', key: 'apt' },
]

const filteredData = computed(() => {
  return rawData.value.filter((d) => {
    const matchName = !searchName.value || String(d.name).toLowerCase().includes(searchName.value.toLowerCase())
    const matchApt = !searchApt.value || String(d.apt) === searchApt.value
    const matchRoles = !searchRoles.value || String(d.roles) === searchRoles.value
    return matchName && matchApt && matchRoles
  })
})

function resetFilter() {
  searchName.value = ''
  searchApt.value = null
  searchRoles.value = null
}

onMounted(async () => {
  try {
    rawData.value = await getManagement()
  } finally {
    loading.value = false
  }
})
</script>
