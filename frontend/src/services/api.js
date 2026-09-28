import request from '@/utils/request'

// ---- 认证 ----
export function login(data) {
  return request.post('/auth/login', data)
}

export function changePassword(data) {
  return request.post('/auth/change-password', data)
}

// ---- 每日销售 ----
export function getDailySales(params) {
  return request.get('/sales/daily', { params })
}

// ---- 人员销售表 ----
export function getPersonnelSales(params) {
  return request.get('/sales/personnel', { params })
}

// ---- 7天统计 ----
export function getRegionalStats() {
  return request.get('/sales/stats/regional')
}

export function getPlatformStats() {
  return request.get('/sales/stats/platform')
}

// ---- 每日分布 ----
export function getRegionDistribution() {
  return request.get('/sales/distribution/region')
}

export function getWarehouseDistribution() {
  return request.get('/sales/distribution/warehouse')
}

// ---- 人员管理 ----
export function getManagement() {
  return request.get('/sales/management')
}

// ---- 运营日报 ----
export function getMyDailyReport(reportDate) {
  return request.get('/report/daily/mine', { params: { report_date: reportDate } })
}

export function submitDailyReport(data) {
  return request.post('/report/daily', data)
}

export function getDailyReports(params) {
  return request.get('/report/daily', { params })
}

export function getReportPeople() {
  return request.get('/report/people')
}

export function getComplianceOverview(params) {
  return request.get('/report/compliance', { params })
}

export function saveMonthlyTarget(data) {
  return request.post('/report/target', data)
}
