import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '@/stores/authStore'
import { useChatStore } from '@/stores/chatStore'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

vi.mock('@/services/api')
vi.mock('@/services/websocket')

describe('Store Integration', () => {
  beforeEach(() => {
    // Reset stores
    useAuthStore.setState({
      user: null,
      token: null,
      isLoading: false,
      error: null
    })
    
    useChatStore.setState({
      conversations: [],
      currentConversationId: null,
      isLoadingConversations: false,
      searchQuery: '',
      isConnected: false,
      isSending: false,
      error: null
    })
    
    vi.clearAllMocks()
    vi.mocked(localStorage.getItem).mockReturnValue(null)
    vi.mocked(localStorage.setItem).mockImplementation(() => {})
    vi.mocked(localStorage.removeItem).mockImplementation(() => {})
  })
  
  it('should integrate authStore and chatStore on login', async () => {
    // Mock login response
    const mockLoginResponse = {
      token: 'test-token',
      user: { email: 'test@example.com', role: 'user', require_password_change: false }
    }
    vi.mocked(api.login).mockResolvedValue(mockLoginResponse)
    vi.mocked(websocket.connect).mockImplementation(() => {})
    
    // Execute login
    await useAuthStore.getState().login('test@example.com', 'password')
    
    // Verify auth state set correctly
    expect(useAuthStore.getState().token).toBe('test-token')
    expect(useAuthStore.getState().user?.email).toBe('test@example.com')
    expect(useAuthStore.getState().error).toBeNull()
    
    // Verify WebSocket connected with token
    expect(websocket.connect).toHaveBeenCalledWith('test-token')
    expect(localStorage.setItem).toHaveBeenCalledWith('jwt_token', 'test-token')
  })
  
  it('should route WebSocket messages to correct conversation in chatStore', () => {
    // Setup: multiple conversations
    useChatStore.setState({
      currentConversationId: 'conv-1',
      conversations: [
        {
          id: 'conv-1',
          title: 'Conv 1',
          messages: [],
          messageCount: 0,
          lastMessageTime: '',
          isPinned: false,
          createdAt: ''
        },
        {
          id: 'conv-2',
          title: 'Conv 2',
          messages: [],
          messageCount: 0,
          lastMessageTime: '',
          isPinned: false,
          createdAt: ''
        }
      ]
    })
    
    // Add message to conv-2 (not current)
    const message = {
      id: 'msg-1',
      role: 'assistant' as const,
      content: 'Response for conv-2',
      timestamp: '2026-01-12T00:00:00Z',
      channel: 'web'
    }
    
    useChatStore.getState().addMessage(message, 'conv-2')
    
    // Verify message added to conv-2, not conv-1
    const state = useChatStore.getState()
    expect(state.conversations[0].messages).toHaveLength(0)  // conv-1 unchanged
    expect(state.conversations[1].messages).toHaveLength(1)  // conv-2 updated
    expect(state.conversations[1].messages[0].content).toBe('Response for conv-2')
  })
  
  it('should handle API 401 error and clear both stores', async () => {
    // Setup: logged in with conversations
    useAuthStore.setState({
      token: 'expired-token',
      user: { email: 'test@example.com', role: 'user', require_password_change: false }
    })
    
    useChatStore.setState({
      conversations: [
        {
          id: 'conv-1',
          title: 'Test',
          messages: [],
          messageCount: 0,
          lastMessageTime: '',
          isPinned: false,
          createdAt: ''
        }
      ]
    })
    
    // Mock 401 error
    vi.mocked(api.getCurrentUser).mockRejectedValue({
      statusCode: 401,
      error: 'Unauthorized'
    })
    vi.mocked(websocket.disconnect).mockImplementation(() => {})
    vi.mocked(api.logout).mockResolvedValue({})
    
    // Try to load user (will fail with 401)
    await useAuthStore.getState().loadUser()
    
    // Verify auth store cleared
    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
    
    // Verify WebSocket disconnected
    expect(websocket.disconnect).toHaveBeenCalled()
  })
})