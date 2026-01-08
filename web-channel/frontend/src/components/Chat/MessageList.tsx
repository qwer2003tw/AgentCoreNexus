import { useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Bot, User } from 'lucide-react'

export default function MessageList() {
  const { messages } = useChatStore()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  if (messages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-dark-text-secondary max-w-md px-4">
          <Bot className="w-16 h-16 mx-auto mb-4 opacity-50" />
          <h2 className="text-xl font-semibold mb-2">開始新對話</h2>
          <p className="text-sm">
            歡迎使用 AgentCore Chat！
            <br />
            您可以問我任何問題，我會盡力幫助您。
          </p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="h-full overflow-y-auto px-4 py-6">
      <div className="max-w-3xl mx-auto space-y-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex gap-3 ${
              message.role === 'user' ? 'flex-row-reverse' : 'flex-row'
            }`}
          >
            {/* Avatar */}
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              message.role === 'user' 
                ? 'bg-primary' 
                : 'bg-dark-surface border border-dark-border'
            }`}>
              {message.role === 'user' ? (
                <User className="w-5 h-5 text-white" />
              ) : (
                <Bot className="w-5 h-5 text-dark-text" />
              )}
            </div>
            
            {/* Message content */}
            <div className={`flex-1 max-w-[80%] ${
              message.role === 'user' ? 'text-right' : 'text-left'
            }`}>
              <div className={`inline-block ${
                message.role === 'user' 
                  ? 'message-user' 
                  : 'message-assistant'
              }`}>
                <p className="whitespace-pre-wrap break-words">
                  {message.content}
                </p>
                
                {/* Channel indicator */}
                {message.channel && message.channel !== 'web' && (
                  <div className="mt-2 pt-2 border-t border-white/10 text-xs opacity-60">
                    來自 {message.channel === 'telegram' ? 'Telegram' : message.channel}
                  </div>
                )}
              </div>
              
              {/* Timestamp */}
              <div className="mt-1 text-xs text-dark-text-secondary">
                {formatTimestamp(message.timestamp)}
              </div>
            </div>
          </div>
        ))}
        
        {/* Auto-scroll anchor */}
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}

function formatTimestamp(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    
    // Less than 1 minute
    if (diff < 60000) {
      return '剛剛'
    }
    
    // Less than 1 hour
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000)
      return `${minutes} 分鐘前`
    }
    
    // Less than 24 hours
    if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000)
      return `${hours} 小時前`
    }
    
    // More than 24 hours
    const sameYear = date.getFullYear() === now.getFullYear()
    if (sameYear) {
      return date.toLocaleDateString('zh-TW', {
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    } else {
      return date.toLocaleDateString('zh-TW', {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric'
      })
    }
  } catch {
    return timestamp
  }
}