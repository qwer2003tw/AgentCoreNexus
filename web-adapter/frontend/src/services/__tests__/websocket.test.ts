import { describe, it, expect, beforeEach, vi } from 'vitest'

describe('WebSocket Service', () => {
  let mockWebSocket: any
  
  beforeEach(() => {
    // Reset modules to get fresh instance
    vi.resetModules()
    
    // Mock WebSocket constructor
    mockWebSocket = {
      send: vi.fn(),
      close: vi.fn(),
      readyState: WebSocket.OPEN,
      onopen: null,
      onclose: null,
      onmessage: null,
      onerror: null,
    }
    
    global.WebSocket = vi.fn(() => mockWebSocket) as any
    vi.mocked(localStorage.getItem).mockReturnValue(null)
  })
  
  it('should create WebSocket instance with token', async () => {
    const { websocket } = await import('../websocket')
    
    websocket.connect('test-token-123')
    
    // Check WebSocket created with correct URL
    expect(WebSocket).toHaveBeenCalledWith(
      expect.stringContaining('test-token-123')
    )
  })
  
  it('should send message with conversation_id', async () => {
    const { websocket } = await import('../websocket')
    
    websocket.connect('test-token')
    mockWebSocket.readyState = WebSocket.OPEN
    
    websocket.sendMessage('Hello', 'conv-123', [])
    
    // Check message sent
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining('"message":"Hello"')
    )
    expect(mockWebSocket.send).toHaveBeenCalledWith(
      expect.stringContaining('"conversation_id":"conv-123"')
    )
  })
  
  it('should throw error when not connected', async () => {
    const { websocket } = await import('../websocket')
    
    mockWebSocket.readyState = WebSocket.CLOSED
    
    expect(() => websocket.sendMessage('Hello', undefined, [])).toThrow('WebSocket not connected')
  })
  
  it('should notify message handlers', async () => {
    const { websocket } = await import('../websocket')
    const handler = vi.fn()
    
    websocket.connect('test-token')
    websocket.onMessage(handler)
    
    // Simulate message received
    const mockMessage = {
      type: 'message',
      content: 'Hello',
      timestamp: '2026-01-12T00:00:00Z'
    }
    
    if (mockWebSocket.onmessage) {
      mockWebSocket.onmessage({
        data: JSON.stringify(mockMessage)
      })
    }
    
    expect(handler).toHaveBeenCalledWith(mockMessage)
  })
  
  it('should return isConnected status', async () => {
    const { websocket } = await import('../websocket')
    
    // Before connection
    expect(websocket.isConnected()).toBe(false)
    
    // After connection with OPEN state
    websocket.connect('test-token')
    mockWebSocket.readyState = WebSocket.OPEN
    
    // Should be connected
    expect(websocket.isConnected()).toBe(true)
  })
  
  it('should cleanup on disconnect', async () => {
    const { websocket } = await import('../websocket')
    
    websocket.connect('test-token')
    websocket.disconnect()
    
    expect(mockWebSocket.close).toHaveBeenCalled()
  })
})
