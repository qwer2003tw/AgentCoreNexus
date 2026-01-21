import { useState } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Trash2, X, Loader2, AlertCircle } from 'lucide-react'

interface DeleteConfirmDialogProps {
  conversationId: string
  onClose: () => void
}

export default function DeleteConfirmDialog({
  conversationId,
  onClose
}: DeleteConfirmDialogProps) {
  const { conversations, deleteConversation } = useChatStore()
  const conversation = conversations.find(c => c.id === conversationId)
  
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState('')
  
  const handleDelete = async () => {
    setIsDeleting(true)
    setError('')
    
    try {
      await deleteConversation(conversationId)
      onClose()
    } catch (error: any) {
      setError(error.message || '刪除失敗')
      setIsDeleting(false)
    }
  }
  
  if (!conversation) return null
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Trash2 className="w-5 h-5 text-error" />
            刪除對話
          </h2>
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="p-1 hover:bg-dark-surface-hover rounded transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          <div className="flex items-start gap-3 mb-4">
            <AlertCircle className="w-5 h-5 text-error flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-dark-text mb-2">
                確定要刪除這個對話嗎？
              </p>
              <p className="text-sm text-dark-text-secondary">
                對話標題：<strong>{conversation.title}</strong>
              </p>
              <p className="text-sm text-dark-text-secondary">
                包含 <strong>{conversation.messageCount}</strong> 條消息
              </p>
              <p className="text-sm text-error mt-2">
                ⚠️ 刪除後無法恢復
              </p>
            </div>
          </div>
          
          {/* Error */}
          {error && (
            <div className="p-3 bg-error/10 border border-error/20 rounded-lg text-error text-sm">
              {error}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-6 border-t border-dark-border flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={isDeleting}
            className="btn-secondary"
          >
            取消
          </button>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="bg-error hover:bg-error/90 text-white px-4 py-2 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {isDeleting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                刪除中...
              </>
            ) : (
              <>
                <Trash2 className="w-4 h-4" />
                刪除
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}