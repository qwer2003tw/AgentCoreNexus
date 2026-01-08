import { useState } from 'react'
import { useChatStore } from '@/stores/chatStore'
import { Search, Plus } from 'lucide-react'
import ConversationItem from './ConversationItem'
import ConversationContextMenu from './ConversationContextMenu'
import RenameConversationDialog from './RenameConversationDialog'
import DeleteConfirmDialog from './DeleteConfirmDialog'

interface ContextMenuState {
  conversationId: string | null
  x: number
  y: number
}

export default function ConversationList() {
  const {
    isLoadingConversations,
    searchQuery,
    setSearchQuery,
    getFilteredConversations,
    createNewConversation,
    currentConversationId,
    switchConversation
  } = useChatStore()
  
  const [contextMenu, setContextMenu] = useState<ContextMenuState>({
    conversationId: null,
    x: 0,
    y: 0
  })
  const [renameDialog, setRenameDialog] = useState<string | null>(null)
  const [deleteDialog, setDeleteDialog] = useState<string | null>(null)
  
  const { pinned, recent } = getFilteredConversations()
  
  const handleContextMenu = (e: React.MouseEvent, conversationId: string) => {
    e.preventDefault()
    setContextMenu({
      conversationId,
      x: e.clientX,
      y: e.clientY
    })
  }
  
  const closeContextMenu = () => {
    setContextMenu({ conversationId: null, x: 0, y: 0 })
  }
  
  const handleNewConversation = async () => {
    try {
      await createNewConversation()
    } catch (error) {
      console.error('Failed to create conversation:', error)
    }
  }
  
  if (isLoadingConversations) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-dark-text-secondary">載入中...</div>
      </div>
    )
  }
  
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Search box */}
      <div className="p-3 border-b border-dark-border">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-dark-text-secondary" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索對話..."
            className="w-full pl-10 pr-4 py-2 rounded-lg input-field text-sm"
          />
        </div>
      </div>
      
      {/* New conversation button */}
      <div className="p-2 border-b border-dark-border">
        <button
          onClick={handleNewConversation}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-dark-surface-hover transition-colors text-sm"
        >
          <Plus className="w-4 h-4" />
          <span>新對話</span>
        </button>
      </div>
      
      {/* Conversation list */}
      <div className="flex-1 overflow-y-auto">
        {/* Pinned conversations */}
        {pinned.length > 0 && (
          <div className="p-2">
            <div className="text-xs text-dark-text-secondary px-3 py-1 mb-1">
              📌 置頂
            </div>
            {pinned.map(conv => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === currentConversationId}
                onClick={() => switchConversation(conv.id)}
                onContextMenu={(e) => handleContextMenu(e, conv.id)}
              />
            ))}
          </div>
        )}
        
        {/* Recent conversations */}
        {recent.length > 0 && (
          <div className="p-2">
            {pinned.length > 0 && (
              <div className="text-xs text-dark-text-secondary px-3 py-1 mb-1 border-t border-dark-border pt-2">
                最近對話
              </div>
            )}
            {recent.map(conv => (
              <ConversationItem
                key={conv.id}
                conversation={conv}
                isActive={conv.id === currentConversationId}
                onClick={() => switchConversation(conv.id)}
                onContextMenu={(e) => handleContextMenu(e, conv.id)}
              />
            ))}
          </div>
        )}
        
        {/* Empty state */}
        {pinned.length === 0 && recent.length === 0 && !searchQuery && (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="text-center text-dark-text-secondary text-sm">
              <p>還沒有對話</p>
              <p className="mt-2">點擊上方「新對話」開始</p>
            </div>
          </div>
        )}
        
        {/* No search results */}
        {pinned.length === 0 && recent.length === 0 && searchQuery && (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="text-center text-dark-text-secondary text-sm">
              <p>沒有找到匹配的對話</p>
              <p className="mt-2">「{searchQuery}」</p>
            </div>
          </div>
        )}
      </div>
      
      {/* Context menu */}
      {contextMenu.conversationId && (
        <ConversationContextMenu
          conversationId={contextMenu.conversationId}
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={closeContextMenu}
          onRename={(id) => {
            setRenameDialog(id)
            closeContextMenu()
          }}
          onDelete={(id) => {
            setDeleteDialog(id)
            closeContextMenu()
          }}
        />
      )}
      
      {/* Rename dialog */}
      {renameDialog && (
        <RenameConversationDialog
          conversationId={renameDialog}
          onClose={() => setRenameDialog(null)}
        />
      )}
      
      {/* Delete confirmation dialog */}
      {deleteDialog && (
        <DeleteConfirmDialog
          conversationId={deleteDialog}
          onClose={() => setDeleteDialog(null)}
        />
      )}
    </div>
  )
}