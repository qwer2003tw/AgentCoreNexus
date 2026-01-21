import { useEffect } from 'react'
import { AlertCircle, MessageSquare, X } from 'lucide-react'

interface NewChatDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  isDisabled?: boolean
}

export default function NewChatDialog({ 
  isOpen, 
  onClose, 
  onConfirm,
  isDisabled = false 
}: NewChatDialogProps) {
  // ESC 鍵支持
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isDisabled) {
        onClose()
      }
    }
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen, onClose, isDisabled])
  
  if (!isOpen) return null
  
  const handleConfirm = () => {
    onConfirm()
    onClose()
  }
  
  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="new-chat-dialog-title"
    >
      <div className="bg-dark-surface rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <h2 
            id="new-chat-dialog-title"
            className="text-xl font-semibold flex items-center gap-2"
          >
            <MessageSquare className="w-5 h-5" />
            開始新對話
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-dark-surface-hover rounded transition-colors"
            aria-label="關閉對話框"
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
                確定要開始新對話嗎？
              </p>
              <p className="text-sm text-dark-text-secondary">
                當前對話將會清空且<strong className="text-error">無法恢復</strong>。
              </p>
            </div>
          </div>
          
          {isDisabled && (
            <div 
              className="bg-error/10 border border-error/20 rounded-lg p-3 flex items-start gap-2 text-error"
              role="alert"
            >
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              <span className="text-sm">
                請等待當前消息發送完成
              </span>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-6 border-t border-dark-border flex justify-end gap-3">
          <button
            onClick={onClose}
            className="btn-secondary"
            aria-label="取消"
          >
            取消
          </button>
          <button
            onClick={handleConfirm}
            disabled={isDisabled}
            className="btn-primary"
            aria-label="確定開始新對話"
          >
            確定
          </button>
        </div>
      </div>
    </div>
  )
}