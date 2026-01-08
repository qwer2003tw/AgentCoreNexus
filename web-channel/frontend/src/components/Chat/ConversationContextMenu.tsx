import { useEffect, useRef } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Edit2, Pin, PinOff, Trash2, Download } from 'lucide-react'

interface ConversationContextMenuProps {
  conversationId: string
  x: number
  y: number
  onClose: () => void
  onRename: (id: string) => void
  onDelete: (id: string) => void
}

export default function ConversationContextMenu({
  conversationId,
  x,
  y,
  onClose,
  onRename,
  onDelete
}: ConversationContextMenuProps) {
  const menuRef = useRef<HTMLDivElement>(null)
  const { conversations, togglePinConversation } = useChatStore()
  
  const conversation = conversations.find(c => c.id === conversationId)
  if (!conversation) return null
  
  const isPinned = conversation.isPinned
  
  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose()
      }
    }
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [onClose])
  
  const handlePin = async () => {
    try {
      await togglePinConversation(conversationId)
      onClose()
    } catch (error) {
      console.error('Failed to toggle pin:', error)
    }
  }
  
  return (
    <div
      ref={menuRef}
      className="fixed bg-dark-surface border border-dark-border rounded-lg shadow-xl py-1 min-w-[180px] z-50"
      style={{
        top: `${y}px`,
        left: `${x}px`
      }}
    >
      {/* Rename */}
      <button
        onClick={() => onRename(conversationId)}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3"
      >
        <Edit2 className="w-4 h-4" />
        <span>重命名對話</span>
      </button>
      
      {/* Pin/Unpin */}
      <button
        onClick={handlePin}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3"
      >
        {isPinned ? (
          <>
            <PinOff className="w-4 h-4" />
            <span>取消置頂</span>
          </>
        ) : (
          <>
            <Pin className="w-4 h-4" />
            <span>置頂對話</span>
          </>
        )}
      </button>
      
      {/* Divider */}
      <div className="my-1 border-t border-dark-border" />
      
      {/* Export */}
      <button
        onClick={() => {
          console.log('Export conversation:', conversationId)
          onClose()
        }}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3"
      >
        <Download className="w-4 h-4" />
        <span>導出對話</span>
      </button>
      
      {/* Delete */}
      <button
        onClick={() => onDelete(conversationId)}
        className="w-full px-4 py-2 text-left text-sm hover:bg-dark-surface-hover transition-colors flex items-center gap-3 text-error"
      >
        <Trash2 className="w-4 h-4" />
        <span>刪除對話</span>
      </button>
    </div>
  )
}