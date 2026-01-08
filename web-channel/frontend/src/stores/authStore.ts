/**
 * Authentication state store
 */

import { create } from 'zustand'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

export interface User {
  email: string
  role: 'user' | 'admin'
  require_password_change: boolean
}

interface AuthState {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  
  // Actions
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  changePassword: (oldPassword: string, newPassword: string) => Promise<void>
  loadUser: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('jwt_token'),
  isLoading: false,
  error: null,
  
  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null })
    
    try {
      const response = await api.login({ email, password })
      
      // Save token
      localStorage.setItem('jwt_token', response.token)
      
      set({
        token: response.token,
        user: response.user as User,
        isLoading: false
      })
      
      // Connect WebSocket
      websocket.connect(response.token)
      
    } catch (error: any) {
      set({
        error: error.error || '登入失敗',
        isLoading: false
      })
      throw error
    }
  },
  
  logout: () => {
    // Clear token
    localStorage.removeItem('jwt_token')
    
    // Disconnect WebSocket
    websocket.disconnect()
    
    // Clear state
    set({
      user: null,
      token: null,
      error: null
    })
    
    // Call logout API (optional, non-blocking)
    api.logout().catch(console.error)
  },
  
  changePassword: async (oldPassword: string, newPassword: string) => {
    set({ isLoading: true, error: null })
    
    try {
      await api.changePassword({
        old_password: oldPassword,
        new_password: newPassword
      })
      
      // Update require_password_change flag
      const user = get().user
      if (user) {
        set({
          user: { ...user, require_password_change: false },
          isLoading: false
        })
      }
      
    } catch (error: any) {
      set({
        error: error.error || '修改密碼失敗',
        isLoading: false
      })
      throw error
    }
  },
  
  loadUser: async () => {
    const token = get().token
    if (!token) return
    
    set({ isLoading: true, error: null })
    
    try {
      const user = await api.getCurrentUser()
      set({ user: user as User, isLoading: false })
      
      // Connect WebSocket if not already connected
      if (!websocket.isConnected()) {
        websocket.connect(token)
      }
      
    } catch (error: any) {
      // Token might be expired
      if (error.statusCode === 401) {
        get().logout()
      }
      set({
        error: error.error || '載入用戶資訊失敗',
        isLoading: false
      })
    }
  },
  
  clearError: () => {
    set({ error: null })
  }
}))