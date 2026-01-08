import { Conversation } from '@/stores/chatStore'
import { Pin } from 'lucide-react'

interface ConversationItemProps {
  conversation: Conversation
  isActive: boolean
  onClick: () => void
  onContextMenu: (e: React.MouseEvent) => void
}

export default function ConversationItem({
  conversation,
  isActive,
  onClick,
  onContextMenu
}: ConversationItemProps) {
  // Format time (simple relative time without date-fns for now)
  const getTimeAgo = (timestamp: string) => {
    const now = new Date()
    const time = new Date(timestamp)
    const diffMs = now.getTime() - time.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)
    
    if (diffMins < 1) return '剛剛'
    if (diffMins < 60) return `${diffMins}分鐘前`
    if (diffHours < 24) return `${diffHours}小時前`
    if (diffDays === 1) return '昨天'
    if (diffDays < 7) return `${diffDays}天前`
    return time.toLocaleDateString('zh-TW')
  }
  
  const timeAgo = getTimeAgo(conversation.lastMessageTime)
  
  // Get last message preview
  const lastMessage = conversation.messages[conversation.messages.length - 1]
  const preview = lastMessage?.content.slice(0, 50) || '開始對話...'
  
  return (
    <button
      onClick={onClick}
      onContextMenu={onContextMenu}
      className={`
        w-full text-left px-3 py-3 rounded-lg transition-colors mb-1
        ${isActive 
          ? 'bg-dark-surface-hover border border-primary' 
          : 'hover:bg-dark-bg border border-transparent'
        }
      `}
    >
      <div className="flex items-start gap-2 mb-1">
        {/* Pin icon */}
        {conversation.isPinned && (
          <Pin className="w-3 h-3 text-primary flex-shrink-0 mt-1" />
        )}
        
        {/* Title */}
        <h3 className="flex-1 text-sm font-medium truncate">
          {conversation.title}
        </h3>
        
        {/* Message count */}
        {conversation.messageCount > 0 && (
          <span className="text-xs text-dark-text-secondary">
            {conversation.messageCount}
          </span>
        )}
      </div>
      
      {/* Preview and time */}
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs text-dark-text-secondary truncate flex-1">
          {preview}
        </p>
        <span className="text-xs text-dark-text-secondary whitespace-nowrap">
          {timeAgo}
        </span>
      </div>
    </button>
  )
}