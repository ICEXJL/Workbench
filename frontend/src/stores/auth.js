import { defineStore } from 'pinia'
import { login as apiLogin } from '@/services/api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('access_token') || '',
    username: localStorage.getItem('username') || '',
    realName: localStorage.getItem('real_name') || '',
    role: localStorage.getItem('role') || '',
    department: localStorage.getItem('department') || '',
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
      localStorage.setItem('access_token', this.token)
      localStorage.setItem('username', this.username)
      localStorage.setItem('real_name', this.realName)
      localStorage.setItem('role', this.role)
      localStorage.setItem('department', this.department)
    },
    logout() {
      this.token = ''
      this.username = ''
      this.realName = ''
      this.role = ''
      this.department = ''
      localStorage.removeItem('access_token')
      localStorage.removeItem('username')
      localStorage.removeItem('real_name')
      localStorage.removeItem('role')
      localStorage.removeItem('department')
    },
  },
})
