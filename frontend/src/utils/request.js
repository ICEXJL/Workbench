import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '@/router'

// 统一请求封装：自动带 token、统一错误提示、401 跳登录
const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const isNetworkError = !error.response
    const detail = error.response?.data?.detail || (isNetworkError ? '数据服务未启动，请联系管理员或启动后端服务' : '请求失败，请稍后重试')

    if (status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      localStorage.removeItem('real_name')
      localStorage.removeItem('role')
      localStorage.removeItem('department')
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
      message.error(typeof detail === 'string' ? detail : '登录已过期，请重新登录')
    } else if (status === 403) {
      message.error(typeof detail === 'string' ? detail : '无权限访问该功能')
    } else if (isNetworkError) {
      message.error(detail)
    } else {
      message.error(typeof detail === 'string' ? detail : '请求失败')
    }
    return Promise.reject(error)
  }
)

export default request
