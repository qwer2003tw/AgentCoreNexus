import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useChatStore } from '../chatStore'
import { api } from '@/services/api'
import { websocket } from '@/services/websocket'

// Mock services
vi.mock('@/services/api')
vi.mock('@/services/websocket')

describe('chatStore', () => {
  beforeEach(() => {
    // Reset store
    useChatStore.setState({
      conversations: [],
      currentConversationId: null,
      isLoadingConversations: false,
      searchQuery: '',
      isConnected: false,
      isSending: false,
      error: null
    })
    
    // Clear mocks
    vi.clearAllMocks()
    
    // Mock localStorage
    vi.mocked(localStorage.getItem).mockReturnValue('test-token')
  })
  
  describe('loadConversations', () => {
    it('should load conversations from API', async () => {
      const mockConversations = {
        conversations: {
          pinned: [],
          recent: [
            {
              conversation_id: 'conv-1',
              title: 'Test Chat',
              last_message_time: '2026-01-12T00:00:00Z',
              message_count: 5,
              is_pinned: false,
              created_at: '2026-01-12T00:00:00Z'
            }
          ]
        }
      }
      
      vi.mocked(api.getConversations).mockResolvedValue(mockConversations)
      
      const store = useChatStore.getState()
      await store.loadConversations()
      
      // Check state
      const state = useChatStore.getState()
      expect(state.conversations).toHaveLength(1)
      expect(state.conversations[0].title).toBe('Test Chat')
      expect(state.isLoadingConversations).toBe(false)
    })
    
    it('should create first conversation if empty', async () => {
      vi.mocked(api.getConversations).mockResolvedValue({ conversations: { pinned: [], recent: [] } })
      vi.mocked(api.createConversation).mockResolvedValue({
        conversation_id: 'conv-new',
        title: 'First Chat',
        created_at: '2026-01-12T00:00:00Z'
      })
      
      const store = useChatStore.getState()
      await store.loadConversations()
      
      // Should have called createConversation
      expect(api.createConversation).toHaveBeenCalledWith('First Chat')
    })
  })
  
  describe('createNewConversation', () => {
    it('should create new conversation', async () => {
      const mockResponse = {
        conversation_id: 'conv-new',
        title: '新對話',
        created_at: '2026-01-12T00:00:00Z'
      }
      
      vi.mocked(api.createConversation).mockResolvedValue(mockResponse)
      
      const store = useChatStore.getState()
      const newId = await store.createNewConversation()
      
      // Check state
      const state = useChatStore.getState()
      expect(state.conversations).toHaveLength(1)
      expect(state.conversations[0].id).toBe('conv-new')
      expect(state.currentConversationId).toBe('conv-new')
      expect(newId).toBe('conv-new')
    })
  })
  
  describe('switchConversation', () => {
    it('should switch to conversation and load messages', async () => {
      // Setup: conversation exists but messages not loaded
      useChatStore.setState({
        conversations: [
          {
            id: 'conv-1',
            title: 'Test',
            messages: [],
            messageCount: 2,
            lastMessageTime: '2026-01-12T00:00:00Z',
            isPinned: false,
            createdAt: '2026-01-12T00:00:00Z'
          }
        ]
      })
      
      const mockMessages = {
        messages: [
          {
            timestamp_msgid: '2026-01-12T00:00:00Z#msg-1',
            role: 'user',
            content: { text: 'Hello' },
            channel: 'web'
          }
        ]
      }
      
      vi.mocked(api.getConversationMessages).mockResolvedValue(mockMessages)
      
      const store = useChatStore.getState()
      await store.switchConversation('conv-1')
      
      // Check state
      const state = useChatStore.getState()
      expect(state.currentConversationId).toBe('conv-1')
      expect(state.conversations[0].messages).toHaveLength(1)
      expect(state.conversations[0].messages[0].content).toBe('Hello')
    })
    
    it('should switch without loading if messages already loaded', async () => {
      useChatStore.setState({
        conversations: [
          {
            id: 'conv-1',
            title: 'Test',
            messages: [{ id: 'msg-1', role: 'user', content: 'Existing', timestamp: '', channel: 'web' }],
            messageCount: 1,
            lastMessageTime: '2026-01-12T00:00:00Z',
            isPinned: false,
            createdAt: '2026-01-12T00:00:00Z'
          }
        ]
      })
      
      const store = useChatStore.getState()
      await store.switchConversation('conv-1')
      
      // Should NOT have called API
      expect(api.getConversationMessages).not.toHaveBeenCalled()
      
      // Should have switched
      expect(useChatStore.getState().currentConversationId).toBe('conv-1')
    })
  })
  
  describe('sendMessage', () => {
    it('should send message via WebSocket', async () => {
      useChatStore.setState({
        currentConversationId: 'conv-1',
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
      
      vi.mocked(websocket.isConnected).mockReturnValue(true)
      vi.mocked(websocket.sendMessage).mockImplementation(() => {})
      
      const store = useChatStore.getState()
      await store.sendMessage('Hello!', [])
      
      // Check WebSocket called
      expect(websocket.sendMessage).toHaveBeenCalledWith('Hello!', 'conv-1', [])
      
      // Check optimistic update
      const state = useChatStore.getState()
      const messages = state.conversations[0].messages
      expect(messages).toHaveLength(1)
      expect(messages[0].content).toBe('Hello!')
      expect(messages[0].role).toBe('user')
    })
    
    it('should handle not connected error', async () => {
      useChatStore.setState({ currentConversationId: 'conv-1' })
      
      vi.mocked(websocket.isConnected).mockReturnValue(false)
      
      const store = useChatStore.getState()
      await store.sendMessage('Hello', [])
      
      // Should set error
      const state = useChatStore.getState()
      expect(state.error).toBe('未連接到伺服器')
    })
  })
  
  describe('addMessage', () => {
    it('should add message to correct conversation', () => {
      useChatStore.setState({
        currentConversationId: 'conv-1',
        conversations: [
          {
            id: 'conv-1',
            title: 'Test 1',
            messages: [],
            messageCount: 0,
            lastMessageTime: '',
            isPinned: false,
            createdAt: ''
          },
          {
            id: 'conv-2',
            title: 'Test 2',
            messages: [],
            messageCount: 0,
            lastMessageTime: '',
            isPinned: false,
            createdAt: ''
          }
        ]
      })
      
      const store = useChatStore.getState()
      const message = {
        id: 'msg-1',
        role: 'assistant' as const,
        content: 'Response',
        timestamp: '2026-01-12T00:00:00Z',
        channel: 'web'
      }
      
      // Add to conv-2 (not current conversation)
      store.addMessage(message, 'conv-2')
      
      // Check message added to correct conversation
      const state = useChatStore.getState()
      expect(state.conversations[0].messages).toHaveLength(0) // conv-1 unchanged
      expect(state.conversations[1].messages).toHaveLength(1) // conv-2 updated
      expect(state.conversations[1].messages[0].content).toBe('Response')
    })
  })
  
  describe('updateConversationTitle', () => {
    it('should update conversation title', () => {
      useChatStore.setState({
        conversations: [
          {
            id: 'conv-1',
            title: 'Old Title',
            messages: [],
            messageCount: 0,
            lastMessageTime: '',
            isPinned: false,
            createdAt: ''
          }
        ]
      })
      
      const store = useChatStore.getState()
      store.updateConversationTitle('conv-1', 'New Title')
      
      // Check title updated
      const state = useChatStore.getState()
      expect(state.conversations[0].title).toBe('New Title')
    })
  })
  
  describe('getFilteredConversations', () => {
    it('should filter conversations by search query', () => {
      useChatStore.setState({
        conversations: [
          {
            id: 'conv-1',
            title: 'Apple Chat',
            messages: [{ id: 'msg-1', role: 'user', content: 'About apples', timestamp: '', channel: 'web' }],
            messageCount: 1,
            lastMessageTime: '',
            isPinned: false,
            createdAt: ''
          },
          {
            id: 'conv-2',
            title: 'Banana Chat',
            messages: [],
            messageCount: 0,
            lastMessageTime: '',
            isPinned: false,
            createdAt: ''
          }
        ],
        searchQuery: 'apple'
      })
      
      const store = useChatStore.getState()
      const result = store.getFilteredConversations()
      
      // Should only return apple conversation
      expect(result.recent).toHaveLength(1)
      expect(result.recent[0].title).toBe('Apple Chat')
    })

    it('should match attachments in search query', () => {
      useChatStore.setState({
        conversations: [
          {
            id: 'conv-1',
            title: 'Files',
            messages: [
              {
                id: 'msg-1',
                role: 'user',
                content: '',
                timestamp: '',
                channel: 'web',
                attachments: [
                  {
                    id: 'att-1',
                    name: 'invoice.pdf',
                    size: 100,
                    content_type: 'application/pdf',
                    key: 'attachments/user/att-1/invoice.pdf'
                  }
                ]
              }
            ],
            messageCount: 1,
            lastMessageTime: '',
            isPinned: false,
            createdAt: ''
          }
        ],
        searchQuery: 'invoice'
      })

      const store = useChatStore.getState()
      const result = store.getFilteredConversations()

      expect(result.recent).toHaveLength(1)
      expect(result.recent[0].title).toBe('Files')
    })
    
    it('should group pinned and recent conversations', () => {
      useChatStore.setState({
        conversations: [
          {
            id: 'conv-1',
            title: 'Pinned',
            messages: [],
            messageCount: 0,
            lastMessageTime: '',
            isPinned: true,
            createdAt: ''
          },
          {
            id: 'conv-2',
            title: 'Recent',
            messages: [],
            messageCount: 0,
            lastMessageTime: '',
            isPinned: false,
            createdAt: ''
          }
        ],
        searchQuery: ''
      })
      
      const store = useChatStore.getState()
      const result = store.getFilteredConversations()
      
      expect(result.pinned).toHaveLength(1)
      expect(result.recent).toHaveLength(1)
      expect(result.pinned[0].title).toBe('Pinned')
    })
  })
})
