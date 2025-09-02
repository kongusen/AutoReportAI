'use client'

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User, LoginForm, RegisterForm, ApiResponse } from '@/types'
import { AuthService } from '@/services/apiService'
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
  fetchCurrentUser: () => Promise<User>
  updateUser: (userData: Partial<User>) => void
  updateProfile: (userData: User) => void
  
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
          
          // 使用新的AuthService
          const loginResponse = await AuthService.login({
            username: credentials.username,
            password: credentials.password
          })
          
          // 更新状态
          set({
            user: loginResponse.user,
            token: loginResponse.access_token,
            isAuthenticated: true,
            isLoading: false,
          })

          // 存储到localStorage（AuthService已处理）
          localStorage.setItem('authToken', loginResponse.access_token)
          localStorage.setItem('user', JSON.stringify(loginResponse.user))

          toast.success('登录成功')
        } catch (error: any) {
          console.error('Login failed:', error)
          set({ isLoading: false })
          
          // 错误处理已在AuthService中完成
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
          
          // 使用新的AuthService
          const user = await AuthService.register(registerData)

          set({ isLoading: false })
          toast.success('注册成功，请登录')
        } catch (error: any) {
          console.error('Registration failed:', error)
          set({ isLoading: false })
          throw error
        }
      },

      // 登出
      logout: async () => {
        try {
          // 使用新的AuthService
          await AuthService.logout()
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
          const refreshResponse = await AuthService.refreshToken()

          set({ token: refreshResponse.access_token })
          localStorage.setItem('authToken', refreshResponse.access_token)
        } catch (error) {
          console.error('Token refresh failed:', error)
          // 刷新失败，执行登出
          await get().logout()
          throw error
        }
      },

      // 获取当前用户信息
      fetchCurrentUser: async () => {
        try {
          const user = await AuthService.getCurrentUser()
          set({ user })
          localStorage.setItem('user', JSON.stringify(user))
          return user
        } catch (error) {
          console.error('Failed to fetch current user:', error)
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

      // 更新完整用户资料（包括profile）
      updateProfile: (userData: User) => {
        set({ user: userData })
        localStorage.setItem('user', JSON.stringify(userData))
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