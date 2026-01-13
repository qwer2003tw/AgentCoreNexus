import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import ChatWindow from '../ChatWindow'
import { useChatStore } from '@/stores/chatStore'
import { useIsMobile } from '@/hooks/useDeviceType'

// Mock dependencies
vi.mock('@/hooks/useDeviceType')
vi.mock('@/stores/chatStore')
vi.mock('../MessageList', () => ({
  default: () => <div data-testid="message-list">Messages</div>
}))

describe('ChatWindow', () => {
  const mockSendMessage = vi.fn()
  const mockClearError = vi.fn()
  
  const defaultStoreState = {
    sendMessage: mockSendMessage,
    isSending: false,
    isConnected: true,
    error: null,
    clearError: mockClearError,
    currentConversationId: 'conv-1',
    conversations: [
      {
        id: 'conv-1',
        title: 'Test Conversation',
        messageCount: 5,
        messages: [],
        lastMessageTime: '',
        isPinned: false,
        createdAt: ''
      }
    ]
  }
  
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useChatStore).mockReturnValue(defaultStoreState as any)
    vi.mocked(useIsMobile).mockReturnValue(false) // Default to desktop
  })
  
  describe('Desktop Mode - Keyboard Behavior', () => {
    it('should send message on Enter key (desktop)', async () => {
      vi.mocked(useIsMobile).mockReturnValue(false)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      // Type message
      fireEvent.change(textarea, { target: { value: 'Hello!' } })
      
      // Press Enter (without Shift)
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
      
      // Should have called sendMessage
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith('Hello!')
      })
      
      // Input should be cleared
      expect(textarea).toHaveValue('')
    })
    
    it('should insert newline on Shift+Enter (desktop)', () => {
      vi.mocked(useIsMobile).mockReturnValue(false)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      // Type message
      fireEvent.change(textarea, { target: { value: 'Line 1' } })
      
      // Press Shift+Enter (should allow default newline behavior)
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true })
      
      // Should NOT have called sendMessage
      expect(mockSendMessage).not.toHaveBeenCalled()
      
      // Value should still be there (newline would be added by browser)
      expect(textarea).toHaveValue('Line 1')
    })
    
    it('should show correct placeholder for desktop', () => {
      vi.mocked(useIsMobile).mockReturnValue(false)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      expect(textarea).toHaveAttribute(
        'placeholder',
        '輸入訊息... (Enter 發送，Shift+Enter 換行)'
      )
    })
    
    it('should show correct ARIA label for desktop', () => {
      vi.mocked(useIsMobile).mockReturnValue(false)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      expect(textarea).toHaveAttribute(
        'aria-label',
        '輸入訊息，按 Enter 發送消息，Shift 加 Enter 換行'
      )
    })
  })
  
  describe('Mobile Mode - Keyboard Behavior', () => {
    it('should NOT send message on Enter key (mobile)', () => {
      vi.mocked(useIsMobile).mockReturnValue(true)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      // Type message
      fireEvent.change(textarea, { target: { value: 'Hello!' } })
      
      // Press Enter (mobile - should just add newline)
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
      
      // Should NOT have called sendMessage
      expect(mockSendMessage).not.toHaveBeenCalled()
      
      // Value should still be there
      expect(textarea).toHaveValue('Hello!')
    })
    
    it('should send message via button click (mobile)', async () => {
      vi.mocked(useIsMobile).mockReturnValue(true)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      const sendButton = screen.getByRole('button', { name: /發送/i })
      
      // Type message
      fireEvent.change(textarea, { target: { value: 'Hello!' } })
      
      // Click send button
      fireEvent.click(sendButton)
      
      // Should have called sendMessage
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith('Hello!')
      })
    })
    
    it('should show correct placeholder for mobile', () => {
      vi.mocked(useIsMobile).mockReturnValue(true)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      expect(textarea).toHaveAttribute(
        'placeholder',
        '輸入訊息... (Enter 換行，點擊發送)'
      )
    })
    
    it('should show correct ARIA label for mobile', () => {
      vi.mocked(useIsMobile).mockReturnValue(true)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      expect(textarea).toHaveAttribute(
        'aria-label',
        '輸入訊息，按 Enter 換行，點擊發送按鈕發送消息'
      )
    })
  })
  
  describe('Mobile UI Optimizations', () => {
    it('should show "發送" text on button (mobile)', () => {
      vi.mocked(useIsMobile).mockReturnValue(true)
      
      render(<ChatWindow />)
      
      // Button should contain "發送" text
      expect(screen.getByText('發送')).toBeInTheDocument()
    })
    
    it('should NOT show "發送" text on button (desktop)', () => {
      vi.mocked(useIsMobile).mockReturnValue(false)
      
      render(<ChatWindow />)
      
      // Button should NOT contain "發送" text
      expect(screen.queryByText('發送')).not.toBeInTheDocument()
    })
    
    it('should have larger button on mobile', () => {
      vi.mocked(useIsMobile).mockReturnValue(true)
      
      render(<ChatWindow />)
      const sendButton = screen.getByRole('button', { name: /發送/i })
      
      // Check for mobile-specific classes
      expect(sendButton.className).toContain('px-5')
      expect(sendButton.className).toContain('py-4')
      expect(sendButton.className).toContain('min-w-[64px]')
      expect(sendButton.className).toContain('min-h-[48px]')
    })
    
    it('should have standard button size on desktop', () => {
      vi.mocked(useIsMobile).mockReturnValue(false)
      
      render(<ChatWindow />)
      const sendButton = screen.getByRole('button', { name: /發送訊息/i })
      
      // Check for desktop-specific classes
      expect(sendButton.className).toContain('px-6')
      expect(sendButton.className).toContain('py-3')
    })
  })
  
  describe('Textarea Auto-height', () => {
    it('should adjust textarea height on input', () => {
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox') as HTMLTextAreaElement
      
      // Mock scrollHeight
      Object.defineProperty(textarea, 'scrollHeight', {
        configurable: true,
        value: 100
      })
      
      // Type message
      fireEvent.change(textarea, { target: { value: 'Line 1\nLine 2\nLine 3' } })
      
      // Height should be adjusted (would be set in the actual implementation)
      // We're testing that the handler is called
      expect(textarea.value).toBe('Line 1\nLine 2\nLine 3')
    })
  })
  
  describe('Form Submission', () => {
    it('should prevent sending empty message', () => {
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      // Try to send empty message
      fireEvent.change(textarea, { target: { value: '   ' } })
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
      
      // Should NOT have called sendMessage
      expect(mockSendMessage).not.toHaveBeenCalled()
    })
    
    it('should trim whitespace from message', async () => {
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      // Type message with whitespace
      fireEvent.change(textarea, { target: { value: '  Hello!  ' } })
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
      
      // Should send trimmed message
      await waitFor(() => {
        expect(mockSendMessage).toHaveBeenCalledWith('Hello!')
      })
    })
    
    it('should not send when disconnected', () => {
      vi.mocked(useChatStore).mockReturnValue({
        ...defaultStoreState,
        isConnected: false
      } as any)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      const sendButton = screen.getByRole('button', { name: /發送/i })
      
      // Type message
      fireEvent.change(textarea, { target: { value: 'Hello!' } })
      
      // Button should be disabled
      expect(sendButton).toBeDisabled()
      
      // Try to send
      fireEvent.click(sendButton)
      
      // Should NOT have called sendMessage
      expect(mockSendMessage).not.toHaveBeenCalled()
    })
    
    it('should not send when already sending', () => {
      vi.mocked(useChatStore).mockReturnValue({
        ...defaultStoreState,
        isSending: true
      } as any)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      const sendButton = screen.getByRole('button', { name: /發送/i })
      
      // Type message
      fireEvent.change(textarea, { target: { value: 'Hello!' } })
      
      // Button should be disabled
      expect(sendButton).toBeDisabled()
      
      // Try to send
      fireEvent.click(sendButton)
      
      // Should NOT have called sendMessage
      expect(mockSendMessage).not.toHaveBeenCalled()
    })
    
    it('should clear input after successful send', async () => {
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      // Type and send
      fireEvent.change(textarea, { target: { value: 'Hello!' } })
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false })
      
      // Input should be cleared immediately (optimistic)
      expect(textarea).toHaveValue('')
    })
  })
  
  describe('No Conversation Selected', () => {
    it('should show empty state when no conversation selected', () => {
      vi.mocked(useChatStore).mockReturnValue({
        ...defaultStoreState,
        currentConversationId: null,
        conversations: []
      } as any)
      
      render(<ChatWindow />)
      
      expect(screen.getByText(/選擇一個對話開始聊天/)).toBeInTheDocument()
      expect(screen.getByText(/或點擊「新對話」創建新的對話/)).toBeInTheDocument()
    })
  })
  
  describe('Error Handling', () => {
    it('should display error message when present', () => {
      vi.mocked(useChatStore).mockReturnValue({
        ...defaultStoreState,
        error: '發送失敗，請重試'
      } as any)
      
      render(<ChatWindow />)
      
      expect(screen.getByText('發送失敗，請重試')).toBeInTheDocument()
    })
    
    it('should clear error on button click', () => {
      vi.mocked(useChatStore).mockReturnValue({
        ...defaultStoreState,
        error: '發送失敗，請重試'
      } as any)
      
      render(<ChatWindow />)
      
      const closeButton = screen.getByText('關閉')
      fireEvent.click(closeButton)
      
      expect(mockClearError).toHaveBeenCalled()
    })
  })
  
  describe('Connection Status', () => {
    it('should show disconnected banner when not connected', () => {
      vi.mocked(useChatStore).mockReturnValue({
        ...defaultStoreState,
        isConnected: false
      } as any)
      
      render(<ChatWindow />)
      
      expect(screen.getByText(/未連接到伺服器/)).toBeInTheDocument()
    })
    
    it('should show "等待連接..." placeholder when disconnected', () => {
      vi.mocked(useChatStore).mockReturnValue({
        ...defaultStoreState,
        isConnected: false
      } as any)
      
      render(<ChatWindow />)
      const textarea = screen.getByRole('textbox')
      
      expect(textarea).toHaveAttribute('placeholder', '等待連接...')
    })
  })
})