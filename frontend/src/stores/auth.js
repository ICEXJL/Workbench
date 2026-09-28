import { defineStore } from 'pinia'
import { login as apiLogin } from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    username: localStorage.getItem('username') || '',
    realName: localStorage.getItem('real_name') || '',
    role: localStorage.getItem('role') || '',
    department: localStorage.getItem('department') || '',
    mustChangePassword: localStorage.getItem('must_change_password') === '1',
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const data = await apiLogin({ username, password })
      this.token = data.access_token
      this.username = data.username
      this.realName = data.realName
      this.role = data.role
      this.department = data.department || ''
      this.mustChangePassword = Boolean(data.mustChangePassword)
      localStorage.setItem('access_token', this.token)
      localStorage.setItem('username', this.username)
      localStorage.setItem('real_name', this.realName)
      localStorage.setItem('role', this.role)
      localStorage.setItem('department', this.department)
      localStorage.setItem('must_change_password', this.mustChangePassword ? '1' : '0')
    },
    completePasswordChange(token) {
      if (token) {
        this.token = token
        localStorage.setItem('access_token', token)
      }
      this.mustChangePassword = false
      localStorage.setItem('must_change_password', '0')
    },
    logout() {
      this.token = ''
      this.username = ''
      this.realName = ''
      this.role = ''
      this.department = ''
      this.mustChangePassword = false
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      localStorage.removeItem('real_name')
      localStorage.removeItem('role')
      localStorage.removeItem('department')
      localStorage.removeItem('must_change_password')
    },
  },
})
