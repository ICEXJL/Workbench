import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'login', component: () => import('@/views/Login.vue') },
  {
    path: '/',
    component: () => import('@/layout/MainLayout.vue'),
    children: [
      { path: '', redirect: '/daily' },
      { path: 'logistics/search', name: 'logistics-search', component: () => import('@/views/logistics/LogisticsSearch.vue'), meta: { title: '物流查询' } },
      { path: 'daily', name: 'daily', component: () => import('@/views/dashboard/DailySales.vue'), meta: { title: '经营总览' } },
      { path: 'personnel', name: 'personnel', component: () => import('@/views/dashboard/PersonnelSales.vue'), meta: { title: '人员销售' } },
      { path: 'report/submit', name: 'report-submit', component: () => import('@/views/report/DailyReportForm.vue'), meta: { title: '提交运营日报', roles: ['operator', 'leader', 'manager'] } },
      { path: 'report/list', name: 'report-list', component: () => import('@/views/report/DailyReportList.vue'), meta: { title: '运营日报进度' } },
      { path: 'report/targets', name: 'report-targets', component: () => import('@/views/report/MonthlyTarget.vue'), meta: { title: '月度目标配置', roles: ['admin'] } },
      { path: 'stats7d', name: 'stats7d', component: () => import('@/views/dashboard/Stats7d.vue'), meta: { title: '趋势分析', roles: ['admin'] } },
      { path: 'statsdaily', name: 'statsdaily', component: () => import('@/views/dashboard/StatsDaily.vue'), meta: { title: '分布洞察', roles: ['admin'] } },
      { path: 'manage', name: 'manage', component: () => import('@/views/dashboard/Manage.vue'), meta: { title: '人员目录', roles: ['admin'] } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 登录守卫：未登录一律跳登录页
router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  const role = localStorage.getItem('role')
  if (to.path !== '/login' && !token) {
    return '/login'
  }
  if (to.path === '/login' && token) {
    return '/daily'
  }
  if (to.meta.roles && !to.meta.roles.includes(role)) {
    return '/daily'
  }
  return true
})

router.afterEach((to) => {
  document.title = `${to.meta.title || '登录'} - EnjoyOurs 运营平台`
})

export default router
