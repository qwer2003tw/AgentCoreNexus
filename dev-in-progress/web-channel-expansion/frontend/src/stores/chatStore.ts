/**
 * Chat state store
 */

import { create } from 'zustand'
import { websocket, Message } from '@/services/websocket'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  channel?: string
}

interface ChatState {
  messages: ChatMessage[]
  isConnected: boolean
  isSending: boolean
  error: string | null
  
  // Actions
  sendMessage: (content: string) => Promise<void>
  addMessage: (message: ChatMessage) => void
  clearMessages: () => void
  setConnected: (connected: boolean) => void
  clearError: () => void
  
  // Initialize
  initialize: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isConnected: false,
  isSending: false,
  error: null,
  
  sendMessage: async (content: string) => {
    if (!websocket.isConnected()) {
      set({ error: '未連接到伺服器' })
      return
    }
    
    set({ isSending: true, error: null })
    
    try {
      // Add user message immediately (optimistic update)
      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
        channel: 'web'
      }
      
      get().addMessage(userMessage)
      
      // Send to server
      websocket.sendMessage(content)
      
      set({ isSending: false })
      
    } catch (error: any) {
      set({
        error: error.message || '發送失敗',
        isSending: false
      })
    }
  },
  
  addMessage: (message: ChatMessage) => {
    set(state => ({
      messages: [...state.messages, message]
    }))
  },
  
  clearMessages: () => {
    set({ messages: [] })
  },
  
  setConnected: (connected: boolean) => {
    set({ isConnected: connected })
  },
  
  clearError: () => {
    set({ error: null })
  },
  
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
    
    // Cleanup on unmount (would need to be called manually or in a React effect)
    return () => {
      unsubscribeMessage()
      unsubscribeConnection()
    }
  }
}))