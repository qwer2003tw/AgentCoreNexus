import { useState, useRef, useEffect } from 'react'
import { useChatStore, Attachment } from '@/stores/chatStore'
import { Send, Loader2, AlertCircle, Paperclip, X, RotateCw } from 'lucide-react'
import MessageList from './MessageList'
import { useIsMobile } from '@/hooks/useDeviceType'
import { api } from '@/services/api'
import { config } from '@/config/env'

interface UploadItem {
  id: string
  file: File
  status: 'uploading' | 'uploaded' | 'failed' | 'canceled'
  progress: number
  error?: string
  attachment?: Attachment
}

export default function ChatWindow() {
  const [input, setInput] = useState('')
  const [uploads, setUploads] = useState<UploadItem[]>([])
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadRequestsRef = useRef<Record<string, XMLHttpRequest>>({})
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

    const readyAttachments = uploads
      .filter(upload => upload.status === 'uploaded' && upload.attachment)
      .map(upload => upload.attachment as Attachment)
    const hasPendingUploads = uploads.some(upload => upload.status === 'uploading')
    const message = input.trim()

    if (
      (!message && readyAttachments.length === 0) ||
      isSending ||
      hasPendingUploads ||
      !isConnected ||
      !currentConversationId
    ) {
      return
    }

    setInput('')
    
    try {
      await sendMessage(message, readyAttachments)

      setUploads([])
      
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

  const updateUpload = (id: string, update: Partial<UploadItem>) => {
    setUploads(prev =>
      prev.map(item => (item.id === id ? { ...item, ...update } : item))
    )
  }

  const uploadFile = async (id: string, file: File) => {
    try {
      const response = await api.createAttachmentUpload({
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        size: file.size
      })

      const xhr = new XMLHttpRequest()
      uploadRequestsRef.current[id] = xhr

      xhr.upload.addEventListener('progress', event => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100)
          updateUpload(id, { progress: percent })
        }
      })

      xhr.addEventListener('load', () => {
        console.log('Upload response:', {
          status: xhr.status,
          statusText: xhr.statusText,
          responseText: xhr.responseText
        })
        
        if (xhr.status >= 200 && xhr.status < 300) {
          updateUpload(id, {
            status: 'uploaded',
            progress: 100,
            attachment: response.attachment
          })
        } else {
          const errorMsg = `上傳失敗 (${xhr.status}): ${xhr.statusText}`
          console.error('Upload failed:', errorMsg, xhr.responseText)
          updateUpload(id, { status: 'failed', error: errorMsg })
        }
      })

      xhr.addEventListener('error', (e) => {
        console.error('Upload XHR error:', e, 'status:', xhr.status)
        const errorMsg = xhr.status ? `網絡錯誤 (${xhr.status})` : '網絡錯誤'
        updateUpload(id, { status: 'failed', error: errorMsg })
      })

      xhr.addEventListener('abort', () => {
        updateUpload(id, { status: 'canceled', error: '已取消上傳' })
      })

      xhr.open('PUT', response.upload_url, true)
      xhr.setRequestHeader('Content-Type', file.type || 'application/octet-stream')
      xhr.send(file)
    } catch (error: any) {
      updateUpload(id, { status: 'failed', error: error?.error || '上傳失敗' })
    }
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || [])
    if (!files.length) return

    files.forEach(file => {
      if (file.size > config.maxAttachmentSizeBytes) {
        const failedId = `${Date.now()}-${file.name}`
        setUploads(prev => [
          ...prev,
          {
            id: failedId,
            file,
            status: 'failed',
            progress: 0,
            error: '檔案超過大小限制'
          }
        ])
        return
      }

      const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
      setUploads(prev => [
        ...prev,
        { id, file, status: 'uploading', progress: 0 }
      ])
      uploadFile(id, file)
    })

    event.target.value = ''
  }

  const handleCancelUpload = (id: string) => {
    const xhr = uploadRequestsRef.current[id]
    if (xhr) {
      xhr.abort()
    }
  }

  const handleRetryUpload = (id: string) => {
    const item = uploads.find(upload => upload.id === id)
    if (!item) return

    updateUpload(id, { status: 'uploading', progress: 0, error: undefined })
    uploadFile(id, item.file)
  }

  const handleRemoveUpload = (id: string) => {
    setUploads(prev => prev.filter(item => item.id !== id))
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
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto space-y-3">
          {uploads.length > 0 && (
            <div className="space-y-2 rounded-xl border border-dark-border bg-dark-bg/60 p-3">
              <div className="flex items-center justify-between text-xs text-dark-text-secondary">
                <span>待上傳檔案</span>
                <span>上限 {Math.round(config.maxAttachmentSizeBytes / (1024 * 1024))} MB</span>
              </div>
              <div className="space-y-2">
                {uploads.map(upload => (
                  <div
                    key={upload.id}
                    className="flex items-center gap-3 rounded-lg border border-dark-border bg-dark-surface/70 px-3 py-2"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-dark-text truncate">{upload.file.name}</p>
                      <div className="mt-1 h-1.5 rounded-full bg-dark-border">
                        <div
                          className={`h-full rounded-full ${
                            upload.status === 'failed' ? 'bg-error' : 'bg-primary'
                          }`}
                          style={{ width: `${upload.progress}%` }}
                        />
                      </div>
                      {upload.error && (
                        <p className="mt-1 text-xs text-error">{upload.error}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {upload.status === 'uploading' && (
                        <button
                          type="button"
                          className="btn-secondary px-2 py-1 text-xs"
                          onClick={() => handleCancelUpload(upload.id)}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                      {upload.status === 'failed' && (
                        <button
                          type="button"
                          className="btn-secondary px-2 py-1 text-xs"
                          onClick={() => handleRetryUpload(upload.id)}
                        >
                          <RotateCw className="h-3 w-3" />
                        </button>
                      )}
                      {upload.status !== 'uploading' && (
                        <button
                          type="button"
                          className="btn-secondary px-2 py-1 text-xs"
                          onClick={() => handleRemoveUpload(upload.id)}
                        >
                          <X className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex items-end gap-3">
            {/* Upload button */}
            <div className="flex items-center">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
              <button
                type="button"
                className="btn-secondary px-4 py-3"
                onClick={() => fileInputRef.current?.click()}
                disabled={!isConnected || isSending || !currentConversationId}
                aria-label="上傳檔案"
              >
                <Paperclip className="w-5 h-5" />
              </button>
            </div>

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
              disabled={
                (!input.trim() && uploads.every(upload => upload.status !== 'uploaded')) ||
                uploads.some(upload => upload.status === 'uploading') ||
                !isConnected ||
                isSending ||
                !currentConversationId
              }
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
          <div className="flex items-center justify-between text-xs text-dark-text-secondary">
            <span>
              {uploads.some(upload => upload.status === 'uploading') ? '檔案上傳中...' : '可附加多個檔案'}
            </span>
            <span>{input.length} / 4000</span>
          </div>
        </form>
      </div>
    </div>
  )
}