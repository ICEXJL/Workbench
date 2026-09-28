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
    const rawDetail = error.response?.data?.detail
    const detail = Array.isArray(rawDetail)
      ? rawDetail.map((item) => {
          const location = Array.isArray(item.loc) ? item.loc.filter((part) => part !== 'body').join('.') : ''
          return location ? `${location}：${item.msg}` : item.msg
        }).join('；')
      : rawDetail || (isNetworkError ? '数据服务未启动，请联系管理员或启动后端服务' : '请求失败，请稍后重试')

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
      const detailCode = typeof detail === 'object' ? detail.code : ''
      if (detailCode === 'PASSWORD_CHANGE_REQUIRED') {
        const alreadyMarked = localStorage.getItem('must_change_password') === '1'
        if (alreadyMarked) {
          // The shell owns the blocking modal; keep the token so the user can submit the password change.
        } else {
          localStorage.setItem('must_change_password', '1')
          localStorage.removeItem('access_token')
          message.warning('请重新登录并完成首次密码修改')
          if (router.currentRoute.value.path !== '/login') router.push('/login')
        }
      } else {
        message.error(typeof detail === 'string' ? detail : '无权限访问该功能')
      }
    } else if (isNetworkError) {
      message.error(detail)
    } else {
      message.error(typeof detail === 'string' ? detail : '请求失败')
    }
    return Promise.reject(error)
  }
)

export default request
