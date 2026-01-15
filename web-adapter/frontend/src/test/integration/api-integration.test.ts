import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '@/stores/authStore'
import { useChatStore } from '@/stores/chatStore'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

vi.mock('@/services/api')
vi.mock('@/services/websocket')

describe('API Integration Flows', () => {
  beforeEach(() => {
    useAuthStore.setState({ user: null, token: null, isLoading: false, error: null })
    useChatStore.setState({
      conversations: [],
      currentConversationId: null,
      isConnected: false,
      isSending: false,
      error: null
    })
    
    vi.clearAllMocks()
    vi.mocked(localStorage.getItem).mockReturnValue(null)
    vi.mocked(localStorage.setItem).mockImplementation(() => {})
  })
  
  it('should complete full login flow', async () => {
    // Step 1: Login
    vi.mocked(api.login).mockResolvedValue({
      token: 'new-token',
      user: { email: 'user@example.com', role: 'user', require_password_change: false }
    })
    vi.mocked(websocket.connect).mockImplementation(() => {})
    
    await useAuthStore.getState().login('user@example.com', 'pass123')
    
    // Verify auth state
    expect(useAuthStore.getState().token).toBe('new-token')
    expect(localStorage.setItem).toHaveBeenCalledWith('jwt_token', 'new-token')
    expect(websocket.connect).toHaveBeenCalled()
  })
  
  it('should complete full chat flow with conversations', async () => {
    // Setup: logged in
    useAuthStore.setState({ token: 'valid-token' })
    vi.mocked(localStorage.getItem).mockReturnValue('valid-token')
    
    // Step 1: Load conversations
    vi.mocked(api.getConversations).mockResolvedValue({
      conversations: {
        pinned: [],
        recent: [{
          conversation_id: 'conv-1',
          title: 'Existing Chat',
          last_message_time: '2026-01-12T00:00:00Z',
          message_count: 0,
          is_pinned: false,
          created_at: '2026-01-12T00:00:00Z'
        }]
      },
      count: 1
    })
    
    await useChatStore.getState().loadConversations()
    
    // Verify conversation loaded
    expect(useChatStore.getState().conversations).toHaveLength(1)
    
    // Step 2: Send message
    useChatStore.setState({ currentConversationId: 'conv-1', isConnected: true })
    vi.mocked(websocket.isConnected).mockReturnValue(true)
    vi.mocked(websocket.sendMessage).mockImplementation(() => {})
    
    await useChatStore.getState().sendMessage('Hello!', [])
    
    // Verify message sent
    expect(websocket.sendMessage).toHaveBeenCalledWith('Hello!', 'conv-1', [])
    
    // Verify optimistic update
    const messages = useChatStore.getState().conversations[0].messages
    expect(messages).toHaveLength(1)
    expect(messages[0].content).toBe('Hello!')
  })
  
  it('should complete conversation management flow', async () => {
    // Setup: logged in
    vi.mocked(localStorage.getItem).mockReturnValue('valid-token')
    
    // Step 1: Create conversation
    vi.mocked(api.createConversation).mockResolvedValue({
      conversation_id: 'new-conv',
      title: 'New Chat',
      created_at: '2026-01-12T00:00:00Z',
      message: 'Created'
    })
    
    const newId = await useChatStore.getState().createNewConversation('New Chat')
    
    expect(newId).toBe('new-conv')
    expect(useChatStore.getState().conversations).toHaveLength(1)
    expect(useChatStore.getState().currentConversationId).toBe('new-conv')
    
    // Step 2: Rename conversation
    vi.mocked(api.updateConversation).mockResolvedValue({ message: 'Updated' })
    
    await useChatStore.getState().renameConversation('new-conv', 'Renamed Chat')
    
    expect(api.updateConversation).toHaveBeenCalledWith('new-conv', { title: 'Renamed Chat' })
    expect(useChatStore.getState().conversations[0].title).toBe('Renamed Chat')
    
    // Step 3: Delete conversation
    vi.mocked(api.deleteConversation).mockResolvedValue({ message: 'Deleted' })
    
    await useChatStore.getState().deleteConversation('new-conv')
    
    expect(useChatStore.getState().conversations).toHaveLength(0)
    expect(useChatStore.getState().currentConversationId).toBeNull()
  })
})
