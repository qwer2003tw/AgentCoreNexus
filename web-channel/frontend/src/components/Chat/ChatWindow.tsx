import { useState, useRef, useEffect } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Send, Loader2, AlertCircle } from 'lucide-react'
import MessageList from './MessageList'
import { useIsMobile } from '@/hooks/useDeviceType'

export default function ChatWindow() {
  const [input, setInput] = useState('')
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const isMobile = useIsMobile() // 檢測移動設備
  
  const { 
    sendMessage, 
    isSending, 
    isConnected, 
    error, 
    clearError,
    currentConversationId,
    conversations
  } = useChatStore()
  
  const currentConversation = conversations.find(c => c.id === currentConversationId)
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!input.trim() || isSending || !isConnected || !currentConversationId) {
      return
    }
    
    const message = input.trim()
    setInput('')
    
    try {
      await sendMessage(message)
      
      // Focus back on input
      inputRef.current?.focus()
    } catch (err) {
      // Error handled by store
    }
  }
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    // 根據設備類型改變 Enter 行為
    if (e.key === 'Enter') {
      if (isMobile) {
        // 📱 移動設備：Enter = 換行（不阻止預設行為）
        // 讓 textarea 自然換行
        return
      } else {
        // 💻 桌面設備：Enter = 發送（除非按住 Shift）
        if (!e.shiftKey) {
          e.preventDefault()
          handleSubmit(e)
        }
        // Shift+Enter 時不 preventDefault，允許換行
      }
    }
  }
  
  // 自動調整 textarea 高度
  const adjustTextareaHeight = () => {
    const textarea = inputRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }
  
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    adjustTextareaHeight()
  }
  
  useEffect(() => {
    // Auto-focus input on mount
    inputRef.current?.focus()
  }, [])
  
  // 當輸入改變時調整高度
  useEffect(() => {
    adjustTextareaHeight()
  }, [input])
  
  // Empty state (no conversation selected)
  if (!currentConversationId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-dark-bg">
        <div className="text-center text-dark-text-secondary">
          <p className="text-lg mb-2">👈 選擇一個對話開始聊天</p>
          <p className="text-sm">或點擊「新對話」創建新的對話</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Connection error banner */}
      {!isConnected && (
        <div className="bg-error/10 border-b border-error/20 px-4 py-2 flex items-center gap-2 text-error">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">未連接到伺服器，正在重新連接...</span>
        </div>
      )}
      
      {/* Error message */}
      {error && (
        <div className="bg-error/10 border-b border-error/20 px-4 py-2 flex items-center justify-between text-error">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            <span className="text-sm">{error}</span>
          </div>
          <button
            onClick={clearError}
            className="text-xs hover:underline"
          >
            關閉
          </button>
        </div>
      )}
      
      {/* Conversation title */}
      {currentConversation && (
        <div className="px-4 py-2 border-b border-dark-border bg-dark-surface">
          <h3 className="text-sm font-medium truncate">
            {currentConversation.title}
          </h3>
          <p className="text-xs text-dark-text-secondary">
            {currentConversation.messageCount} 條消息
          </p>
        </div>
      )}
      
      {/* Messages */}
      <div className="flex-1 overflow-hidden">
        <MessageList />
      </div>
      
      {/* Input area */}
      <div className="border-t border-dark-border bg-dark-surface p-4">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3">
            {/* Text input */}
            <div className="flex-1 relative">
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder={
                  isConnected 
                    ? isMobile
                      ? "輸入訊息... (Enter 換行，點擊發送)" // 📱 移動設備提示
                      : "輸入訊息... (Enter 發送，Shift+Enter 換行)" // 💻 桌面提示
                    : "等待連接..."
                }
                aria-label={
                  isMobile 
                    ? "輸入訊息，按 Enter 換行，點擊發送按鈕發送消息" 
                    : "輸入訊息，按 Enter 發送消息，Shift 加 Enter 換行"
                }
                className="w-full px-4 py-3 rounded-xl input-field resize-none"
                rows={1}
                style={{
                  minHeight: '48px',
                  maxHeight: '200px',
                  height: 'auto'
                }}
                disabled={!isConnected || isSending || !currentConversationId}
              />
            </div>
            
            {/* Send button */}
            <button
              type="submit"
              disabled={!input.trim() || !isConnected || isSending || !currentConversationId}
              className={`btn-primary flex items-center gap-2 ${
                isMobile ? 'px-5 py-4 min-w-[64px] min-h-[48px]' : 'px-6 py-3'
              }`}
              aria-label="發送訊息"
            >
              {isSending ? (
                <Loader2 className={isMobile ? "w-6 h-6 animate-spin" : "w-5 h-5 animate-spin"} />
              ) : (
                <Send className={isMobile ? "w-6 h-6" : "w-5 h-5"} />
              )}
              {/* 移動設備顯示「發送」文字提示 */}
              {isMobile && !isSending && (
                <span className="text-sm font-medium">發送</span>
              )}
            </button>
          </div>
          
          {/* Character count */}
          <div className="mt-2 text-xs text-dark-text-secondary text-right">
            {input.length} / 4000
          </div>
        </form>
      </div>
    </div>
  )
}