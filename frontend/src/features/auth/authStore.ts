'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, LoginForm, RegisterForm, ApiResponse } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface AuthState {
  // 状态
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean

  // 操作
  login: (credentials: LoginForm) => Promise<void>
  register: (userData: RegisterForm) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
  updateUser: (userData: Partial<User>) => void
  
  // 内部方法
  setLoading: (loading: boolean) => void
  setUser: (user: User | null) => void
  setToken: (token: string | null) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false,

      // 登录
      login: async (credentials: LoginForm) => {
        try {
          set({ isLoading: true })
          
          // 准备表单数据
          const formData = new FormData()
          formData.append('username', credentials.username)
          formData.append('password', credentials.password)

          const response = await api.post('/auth/login', formData, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
          })

          // 处理后端API响应格式
          const responseData = response.data || response
          const { access_token, user } = responseData
          
          // 更新状态
          set({
            user,
            token: access_token,
            isAuthenticated: true,
            isLoading: false,
          })

          // 存储到localStorage
          localStorage.setItem('authToken', access_token)
          localStorage.setItem('user', JSON.stringify(user))

          toast.success('登录成功')
        } catch (error: any) {
          console.error('Login failed:', error)
          set({ isLoading: false })
          
          // 错误消息已由API拦截器处理
          throw error
        }
      },

      // 注册
      register: async (userData: RegisterForm) => {
        try {
          set({ isLoading: true })
          
          if (userData.password !== userData.confirmPassword) {
            throw new Error('两次输入的密码不一致')
          }

          const { confirmPassword, ...registerData } = userData
          const response = await api.post('/auth/register', registerData)

          set({ isLoading: false })
          // 处理后端API响应格式
          const responseData = response.data || response
          toast.success(responseData.message || response.message || '注册成功，请登录')
        } catch (error: any) {
          console.error('Registration failed:', error)
          set({ isLoading: false })
          throw error
        }
      },

      // 登出
      logout: () => {
        try {
          // 调用后端登出接口
          api.post('/auth/logout').catch(console.error)
        } catch (error) {
          console.error('Logout API call failed:', error)
        } finally {
          // 无论API调用是否成功，都清除本地状态
          set({
            user: null,
            token: null,
            isAuthenticated: false,
            isLoading: false,
          })

          // 清除localStorage
          localStorage.removeItem('authToken')
          localStorage.removeItem('user')

          toast.success('已退出登录')
        }
      },

      // 刷新令牌
      refreshToken: async () => {
        try {
          const response = await api.post('/auth/refresh')
          const { access_token } = response.data

          set({ token: access_token })
          localStorage.setItem('authToken', access_token)
        } catch (error) {
          console.error('Token refresh failed:', error)
          // 刷新失败，执行登出
          get().logout()
          throw error
        }
      },

      // 更新用户信息
      updateUser: (userData: Partial<User>) => {
        const currentUser = get().user
        if (currentUser) {
          const updatedUser = { ...currentUser, ...userData }
          set({ user: updatedUser })
          localStorage.setItem('user', JSON.stringify(updatedUser))
        }
      },

      // 设置加载状态
      setLoading: (loading: boolean) => set({ isLoading: loading }),

      // 设置用户
      setUser: (user: User | null) => set({ user, isAuthenticated: !!user }),

      // 设置令牌
      setToken: (token: string | null) => set({ token }),
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // 从localStorage恢复状态后，验证token是否仍然有效
        if (state?.token) {
          // 可以在这里添加token验证逻辑
          console.log('Auth state rehydrated')
        }
      },
    }
  )
)