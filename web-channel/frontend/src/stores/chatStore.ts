/**
 * Chat state store with conversation management
 */

import { create } from 'zustand'
import { websocket, Message } from '@/services/websocket'
import { api } from '@/services/api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  channel?: string
}

export interface Conversation {
  id: string
  title: string
  messages: ChatMessage[]
  lastMessageTime: string
  messageCount: number
  isPinned: boolean
  createdAt: string
}

interface ChatState {
  // Conversations
  conversations: Conversation[]
  currentConversationId: string | null
  isLoadingConversations: boolean
  searchQuery: string
  
  // Connection
  isConnected: boolean
  isSending: boolean
  error: string | null
  
  // Actions - Conversations
  loadConversations: () => Promise<void>
  createNewConversation: (title?: string) => Promise<string>
  switchConversation: (id: string) => void
  deleteConversation: (id: string) => Promise<void>
  renameConversation: (id: string, title: string) => Promise<void>
  togglePinConversation: (id: string) => Promise<void>
  setSearchQuery: (query: string) => void
  getFilteredConversations: () => { pinned: Conversation[], recent: Conversation[] }
  
  // Actions - Messages
  sendMessage: (content: string) => Promise<void>
  addMessage: (message: ChatMessage) => void
  getCurrentMessages: () => ChatMessage[]
  
  // Actions - Connection
  setConnected: (connected: boolean) => void
  clearError: () => void
  
  // Initialize
  initialize: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  // Initial state
  conversations: [],
  currentConversationId: null,
  isLoadingConversations: false,
  searchQuery: '',
  isConnected: false,
  isSending: false,
  error: null,
  
  // ============================================================
  // Conversation Management
  // ============================================================
  
  loadConversations: async () => {
    set({ isLoadingConversations: true })
    
    try {
      const response = await api.getConversations()
      const { pinned = [], recent = [] } = response.conversations || {}
      
      const allConversations: Conversation[] = [
        ...pinned.map((c: any) => ({
          id: c.conversation_id,
          title: c.title,
          messages: [],  // Load on demand when switching
          lastMessageTime: c.last_message_time,
          messageCount: c.message_count,
          isPinned: c.is_pinned,
          createdAt: c.created_at
        })),
        ...recent.map((c: any) => ({
          id: c.conversation_id,
          title: c.title,
          messages: [],
          lastMessageTime: c.last_message_time,
          messageCount: c.message_count,
          isPinned: c.is_pinned,
          createdAt: c.created_at
        }))
      ]
      
      set({ 
        conversations: allConversations,
        isLoadingConversations: false
      })
      
      // Auto-create first conversation if empty, or select first if available
      if (allConversations.length === 0) {
        // No conversations exist, create one
        console.log('No conversations found, creating first conversation...')
        await get().createNewConversation('First Chat')
      } else if (!get().currentConversationId) {
        // Conversations exist but none selected, select first
        get().switchConversation(allConversations[0].id)
      }
      
    } catch (error: any) {
      console.error('Failed to load conversations:', error)
      set({ 
        error: '無法載入對話列表',
        isLoadingConversations: false
      })
    }
  },
  
  createNewConversation: async (title = '新對話') => {
    try {
      const response = await api.createConversation(title)
      const newConv: Conversation = {
        id: response.conversation_id,
        title: response.title,
        messages: [],
        lastMessageTime: response.created_at,
        messageCount: 0,
        isPinned: false,
        createdAt: response.created_at
      }
      
      set(state => ({
        conversations: [newConv, ...state.conversations],
        currentConversationId: newConv.id
      }))
      
      return newConv.id
      
    } catch (error: any) {
      console.error('Failed to create conversation:', error)
      set({ error: '無法創建新對話' })
      throw error
    }
  },
  
  switchConversation: async (id: string) => {
    const state = get()
    const conversation = state.conversations.find(c => c.id === id)
    
    if (!conversation) {
      console.error('Conversation not found:', id)
      return
    }
    
    // Load messages if not yet loaded
    if (conversation.messages.length === 0 && conversation.messageCount > 0) {
      try {
        const response = await api.getConversationMessages(id)
        const messages: ChatMessage[] = response.messages.map((m: any) => ({
          id: m.timestamp_msgid.split('#')[1],
          role: m.role,
          content: m.content.text,
          timestamp: m.timestamp_msgid.split('#')[0],
          channel: m.channel
        }))
        
        // Update conversation with messages
        set(state => ({
          conversations: state.conversations.map(c =>
            c.id === id ? { ...c, messages } : c
          ),
          currentConversationId: id
        }))
        
      } catch (error: any) {
        console.error('Failed to load messages:', error)
        set({ error: '無法載入對話消息' })
      }
    } else {
      // Messages already loaded, just switch
      set({ currentConversationId: id })
    }
  },
  
  deleteConversation: async (id: string) => {
    try {
      await api.deleteConversation(id)
      
      const state = get()
      const newConversations = state.conversations.filter(c => c.id !== id)
      
      // If deleting current conversation, switch to newest
      let newCurrentId = state.currentConversationId
      if (state.currentConversationId === id) {
        newCurrentId = newConversations.length > 0 ? newConversations[0].id : null
      }
      
      set({
        conversations: newConversations,
        currentConversationId: newCurrentId
      })
      
    } catch (error: any) {
      console.error('Failed to delete conversation:', error)
      set({ error: '無法刪除對話' })
      throw error
    }
  },
  
  renameConversation: async (id: string, title: string) => {
    try {
      await api.updateConversation(id, { title })
      
      set(state => ({
        conversations: state.conversations.map(c =>
          c.id === id ? { ...c, title } : c
        )
      }))
      
    } catch (error: any) {
      console.error('Failed to rename conversation:', error)
      set({ error: '無法重命名對話' })
      throw error
    }
  },
  
  togglePinConversation: async (id: string) => {
    const conversation = get().conversations.find(c => c.id === id)
    if (!conversation) return
    
    const newPinned = !conversation.isPinned
    
    try {
      await api.updateConversation(id, { is_pinned: newPinned })
      
      set(state => ({
        conversations: state.conversations.map(c =>
          c.id === id ? { ...c, isPinned: newPinned } : c
        )
      }))
      
    } catch (error: any) {
      console.error('Failed to toggle pin:', error)
      set({ error: '無法置頂對話' })
      throw error
    }
  },
  
  setSearchQuery: (query: string) => {
    set({ searchQuery: query })
  },
  
  getFilteredConversations: () => {
    const { conversations, searchQuery } = get()
    
    // Search filter
    let filtered = conversations
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filtered = conversations.filter(c =>
        c.title.toLowerCase().includes(query) ||
        c.messages.some(m => m.content.toLowerCase().includes(query))
      )
    }
    
    // Group: pinned + unpinned
    const pinned = filtered.filter(c => c.isPinned)
    const recent = filtered.filter(c => !c.isPinned)
    
    return { pinned, recent }
  },
  
  // ============================================================
  // Message Management
  // ============================================================
  
  sendMessage: async (content: string) => {
    if (!websocket.isConnected()) {
      set({ error: '未連接到伺服器' })
      return
    }
    
    const currentConvId = get().currentConversationId
    if (!currentConvId) {
      set({ error: '請先選擇或創建對話' })
      return
    }
    
    set({ isSending: true, error: null })
    
    try {
      // Add user message (optimistic update)
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        channel: 'web'
      }
      
      get().addMessage(userMessage)
      
      // Send to server (with conversation_id)
      websocket.sendMessage(content, currentConvId)
      
      set({ isSending: false })
      
    } catch (error: any) {
      set({
        error: error.message || '發送失敗',
        isSending: false
      })
    }
  },
  
  addMessage: (message: ChatMessage) => {
    const state = get()
    const currentConvId = state.currentConversationId
    
    if (!currentConvId) return
    
    // Add message to current conversation
    set(state => ({
      conversations: state.conversations.map(c =>
        c.id === currentConvId
          ? { 
              ...c, 
              messages: [...c.messages, message],
              lastMessageTime: message.timestamp,
              messageCount: c.messageCount + 1
            }
          : c
      )
    }))
  },
  
  getCurrentMessages: () => {
    const state = get()
    const currentConv = state.conversations.find(
      c => c.id === state.currentConversationId
    )
    return currentConv?.messages || []
  },
  
  // ============================================================
  // Connection Management
  // ============================================================
  
  setConnected: (connected: boolean) => {
    set({ isConnected: connected })
  },
  
  clearError: () => {
    set({ error: null })
  },
  
  // ============================================================
  // Initialize
  // ============================================================
  
  initialize: () => {
    // Subscribe to WebSocket messages
    const unsubscribeMessage = websocket.onMessage((message: Message) => {
      if (message.type === 'message') {
        const chatMessage: ChatMessage = {
          id: Date.now().toString(),
          role: 'assistant',
          content: message.content,
          timestamp: message.timestamp,
          channel: 'web'
        }
        get().addMessage(chatMessage)
      }
    })
    
    // Subscribe to connection changes
    const unsubscribeConnection = websocket.onConnectionChange((connected: boolean) => {
      get().setConnected(connected)
    })
    
    // Set initial connection state
    set({ isConnected: websocket.isConnected() })
    
    // Load conversations
    get().loadConversations()
    
    // Cleanup function
    return () => {
      unsubscribeMessage()
      unsubscribeConnection()
    }
  }
}))