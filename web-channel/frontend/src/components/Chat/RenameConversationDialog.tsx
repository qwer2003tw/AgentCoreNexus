import { useState, useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Edit2, X, Loader2 } from 'lucide-react'

interface RenameConversationDialogProps {
  conversationId: string
  onClose: () => void
}

export default function RenameConversationDialog({
  conversationId,
  onClose
}: RenameConversationDialogProps) {
  const { conversations, renameConversation } = useChatStore()
  const conversation = conversations.find(c => c.id === conversationId)
  
  const [title, setTitle] = useState(conversation?.title || '')
  const [isRenaming, setIsRenaming] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  
  useEffect(() => {
    // Auto-select input
    inputRef.current?.select()
    
    // ESC to close
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isRenaming) {
        onClose()
      }
    }
    
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [onClose, isRenaming])
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    const newTitle = title.trim()
    if (!newTitle) {
      setError('標題不能為空')
      return
    }
    
    if (newTitle === conversation?.title) {
      onClose()
      return
    }
    
    setIsRenaming(true)
    setError('')
    
    try {
      await renameConversation(conversationId, newTitle)
      onClose()
    } catch (error: any) {
      setError(error.message || '重命名失敗')
      setIsRenaming(false)
    }
  }
  
  if (!conversation) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Edit2 className="w-5 h-5" />
            重命名對話
          </h2>
          <button
            onClick={onClose}
            disabled={isRenaming}
            className="p-1 hover:bg-dark-surface-hover rounded transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <form onSubmit={handleSubmit} className="p-6">
          <div className="mb-4">
            <label htmlFor="title" className="block text-sm font-medium mb-2">
              對話標題
            </label>
            <input
              ref={inputRef}
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              disabled={isRenaming}
              className="w-full px-4 py-2 rounded-lg input-field"
              maxLength={50}
              autoComplete="off"
            />
            <p className="text-xs text-dark-text-secondary mt-1">
              {title.length}/50
            </p>
          </div>
          
          {/* Error */}
          {error && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm">
              {error}
            </div>
          )}
          
          {/* Buttons */}
          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isRenaming}
              className="btn-secondary"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isRenaming || !title.trim()}
              className="btn-primary flex items-center gap-2"
            >
              {isRenaming ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  重命名中...
                </>
              ) : (
                '確定'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}