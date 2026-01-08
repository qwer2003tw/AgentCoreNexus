/**
 * WebSocket client service
 * Manages WebSocket connection with auto-reconnect
 */

import { config } from '@/config/env'

export interface Message {
  type: 'message' | 'error' | 'connected' | 'disconnected'
  content: string
  timestamp: string
}

type MessageHandler = (message: Message) => void
type ConnectionHandler = (connected: boolean) => void

class WebSocketClient {
  private ws: WebSocket | null = null
  private token: string | null = null
  private reconnectAttempts = 0
  private reconnectTimeout: NodeJS.Timeout | null = null
  private messageHandlers: Set<MessageHandler> = new Set()
  private connectionHandlers: Set<ConnectionHandler> = new Set()
  private intentionalClose = false
  
  constructor() {
    // Auto-connect if token exists
    const token = localStorage.getItem('jwt_token')
    if (token) {
      this.connect(token)
    }
  }
  
  connect(token: string): void {
    this.token = token
    this.intentionalClose = false
    this.reconnectAttempts = 0
    
    const url = `${config.wsEndpoint}?token=${encodeURIComponent(token)}`
    
    console.log('Connecting to WebSocket...')
    
    this.ws = new WebSocket(url)
    
    this.ws.onopen = () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
      this.notifyConnectionHandlers(true)
    }
    
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data) as Message
        console.log('WebSocket message received:', message)
        this.notifyMessageHandlers(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
    
    this.ws.onclose = () => {
      console.log('WebSocket disconnected')
      this.notifyConnectionHandlers(false)
      
      // Auto-reconnect if not intentional close
      if (!this.intentionalClose && this.token) {
        this.scheduleReconnect()
      }
    }
  }
  
  disconnect(): void {
    this.intentionalClose = true
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
      this.reconnectTimeout = null
    }
    
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    
    this.notifyConnectionHandlers(false)
  }
  
  sendMessage(message: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not connected')
    }
    
    const payload = {
      action: 'sendMessage',
      message
    }
    
    console.log('Sending message:', payload)
    this.ws.send(JSON.stringify(payload))
  }
  
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
  
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler)
    // Return unsubscribe function
    return () => {
      this.messageHandlers.delete(handler)
    }
  }
  
  onConnectionChange(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler)
    // Return unsubscribe function
    return () => {
      this.connectionHandlers.delete(handler)
    }
  }
  
  private notifyMessageHandlers(message: Message): void {
    this.messageHandlers.forEach(handler => {
      try {
        handler(message)
      } catch (error) {
        console.error('Message handler error:', error)
      }
    })
  }
  
  private notifyConnectionHandlers(connected: boolean): void {
    this.connectionHandlers.forEach(handler => {
      try {
        handler(connected)
      } catch (error) {
        console.error('Connection handler error:', error)
      }
    })
  }
  
  private scheduleReconnect(): void {
    // Cancel any pending reconnect
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout)
    }
    
    // Calculate backoff delay
    const baseDelay = config.wsReconnectInterval
    const maxDelay = config.wsMaxReconnectInterval
    const multiplier = config.wsReconnectMultiplier
    
    const delay = Math.min(
      baseDelay * Math.pow(multiplier, this.reconnectAttempts),
      maxDelay
    )
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`)
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++
      if (this.token) {
        this.connect(this.token)
      }
    }, delay)
  }
}

// Singleton instance
export const websocket = new WebSocketClient()