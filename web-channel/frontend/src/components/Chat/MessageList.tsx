import { useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { User, Bot } from 'lucide-react'
import AttachmentItem from './AttachmentItem'

export default function MessageList() {
  const { getCurrentMessages } = useChatStore()
  const messages = getCurrentMessages()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  
  // Auto-scroll to bottom when new message arrives
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])
  
  if (messages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <div className="text-center text-dark-text-secondary">
          <p className="text-lg mb-2">💬 開始新對話</p>
          <p className="text-sm">在下方輸入框發送您的第一條消息</p>
        </div>
      </div>
    )
  }
  
  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex gap-3 ${
            message.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          {/* Avatar (for assistant) */}
          {message.role === 'assistant' && (
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
          )}
          
          {/* Message bubble */}
          <div
            className={`max-w-[70%] rounded-2xl px-4 py-3 space-y-3 ${
              message.role === 'user'
                ? 'bg-primary text-white'
                : 'bg-dark-surface border border-dark-border'
            }`}
          >
            {message.content && (
              <p className="text-sm whitespace-pre-wrap break-words">
                {message.content}
              </p>
            )}
            {!!message.attachments?.length && (
              <div className="space-y-2">
                {message.attachments.map((attachment) => (
                  <AttachmentItem key={attachment.id} attachment={attachment} />
                ))}
              </div>
            )}
            <p
              className={`text-xs mt-1 ${
                message.role === 'user' ? 'text-white/70' : 'text-dark-text-secondary'
              }`}
            >
              {new Date(message.timestamp).toLocaleTimeString('zh-TW', {
                hour: '2-digit',
                minute: '2-digit'
              })}
            </p>
          </div>
          
          {/* Avatar (for user) */}
          {message.role === 'user' && (
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <User className="w-5 h-5 text-primary" />
            </div>
          )}
        </div>
      ))}
      
      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
    </div>
  )
}
