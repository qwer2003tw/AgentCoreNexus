import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '../authStore'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

// Mock services
vi.mock('@/services/api')
vi.mock('@/services/websocket')

describe('authStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useAuthStore.setState({
      user: null,
      token: null,
      isLoading: false,
      error: null
    })
    
    // Clear mocks
    vi.clearAllMocks()
    
    // Reset localStorage mock
    vi.mocked(localStorage.getItem).mockReturnValue(null)
    vi.mocked(localStorage.setItem).mockImplementation(() => {})
    vi.mocked(localStorage.removeItem).mockImplementation(() => {})
  })
  
  describe('login', () => {
    it('should login successfully and set token', async () => {
      const mockResponse = {
        token: 'test-jwt-token',
        user: { email: 'test@example.com', role: 'user', require_password_change: false }
      }
      
      vi.mocked(api.login).mockResolvedValue(mockResponse)
      vi.mocked(websocket.connect).mockImplementation(() => {})
      
      const store = useAuthStore.getState()
      await store.login('test@example.com', 'password123')
      
      // Check state
      const state = useAuthStore.getState()
      expect(state.token).toBe('test-jwt-token')
      expect(state.user).toEqual(mockResponse.user)
      expect(state.isLoading).toBe(false)
      expect(state.error).toBeNull()
      
      // Check localStorage
      expect(localStorage.setItem).toHaveBeenCalledWith('jwt_token', 'test-jwt-token')
      
      // Check WebSocket connection
      expect(websocket.connect).toHaveBeenCalledWith('test-jwt-token')
    })
    
    it('should handle login failure', async () => {
      const mockError = { error: '登入失敗' }
      vi.mocked(api.login).mockRejectedValue(mockError)
      
      const store = useAuthStore.getState()
      
      await expect(store.login('test@example.com', 'wrong')).rejects.toEqual(mockError)
      
      // Check state
      const state = useAuthStore.getState()
      expect(state.token).toBeNull()
      expect(state.user).toBeNull()
      expect(state.error).toBe('登入失敗')
      expect(state.isLoading).toBe(false)
    })
  })
  
  describe('logout', () => {
    it('should clear token and disconnect WebSocket', () => {
      // Setup: logged in state
      useAuthStore.setState({
        user: { email: 'test@example.com', role: 'user', require_password_change: false },
        token: 'test-token'
      })
      
      vi.mocked(websocket.disconnect).mockImplementation(() => {})
      vi.mocked(api.logout).mockResolvedValue({})
      
      const store = useAuthStore.getState()
      store.logout()
      
      // Check state
      const state = useAuthStore.getState()
      expect(state.user).toBeNull()
      expect(state.token).toBeNull()
      expect(state.error).toBeNull()
      
      // Check localStorage
      expect(localStorage.removeItem).toHaveBeenCalledWith('jwt_token')
      
      // Check WebSocket disconnection
      expect(websocket.disconnect).toHaveBeenCalled()
    })
  })
  
  describe('loadUser', () => {
    it('should load user info with valid token', async () => {
      useAuthStore.setState({ token: 'valid-token' })
      
      const mockUser = {
        email: 'test@example.com',
        role: 'user',
        require_password_change: false
      }
      
      vi.mocked(api.getCurrentUser).mockResolvedValue(mockUser)
      vi.mocked(websocket.isConnected).mockReturnValue(false)
      vi.mocked(websocket.connect).mockImplementation(() => {})
      
      const store = useAuthStore.getState()
      await store.loadUser()
      
      // Check state
      const state = useAuthStore.getState()
      expect(state.user).toEqual(mockUser)
      expect(state.isLoading).toBe(false)
      
      // Should connect WebSocket if not connected
      expect(websocket.connect).toHaveBeenCalledWith('valid-token')
    })
    
    it('should logout on 401 error', async () => {
      useAuthStore.setState({ token: 'expired-token' })
      
      vi.mocked(api.getCurrentUser).mockRejectedValue({ statusCode: 401, error: 'Unauthorized' })
      
      const store = useAuthStore.getState()
      await store.loadUser()
      
      // Should have logged out
      const state = useAuthStore.getState()
      expect(state.token).toBeNull()
      expect(state.user).toBeNull()
    })
  })
  
  describe('changePassword', () => {
    it('should change password and update user state', async () => {
      useAuthStore.setState({
        user: { email: 'test@example.com', role: 'user', require_password_change: true }
      })
      
      vi.mocked(api.changePassword).mockResolvedValue({ message: 'Success' })
      
      const store = useAuthStore.getState()
      await store.changePassword('oldpass', 'newpass')
      
      // Check user flag updated
      const state = useAuthStore.getState()
      expect(state.user?.require_password_change).toBe(false)
      expect(state.isLoading).toBe(false)
    })
    
    it('should handle password change error', async () => {
      useAuthStore.setState({
        user: { email: 'test@example.com', role: 'user', require_password_change: false }
      })
      
      const mockError = { error: '密碼錯誤' }
      vi.mocked(api.changePassword).mockRejectedValue(mockError)
      
      const store = useAuthStore.getState()
      
      await expect(store.changePassword('old', 'new')).rejects.toEqual(mockError)
      
      const state = useAuthStore.getState()
      expect(state.error).toBe('密碼錯誤')
    })
  })
})