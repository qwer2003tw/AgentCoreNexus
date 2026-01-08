import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useChatStore } from '@/stores/chatStore'
import NewChatDialog from './NewChatDialog'
import { 
  MessageSquare, 
  Settings, 
  LogOut, 
  Link2,
  Download,
  X,
  User,
  Shield
} from 'lucide-react'

interface SidebarProps {
  onClose: () => void
}

export default function Sidebar({ onClose }: SidebarProps) {
  const { user, logout } = useAuthStore()
  const { clearMessages, isSending } = useChatStore()
  const [activeTab, setActiveTab] = useState<'chat' | 'history' | 'settings'>('chat')
  const [showNewChatDialog, setShowNewChatDialog] = useState(false)
  
  const isAdmin = user?.role === 'admin'
  
  // 處理新對話確認
  const handleNewChat = () => {
    clearMessages()
    setActiveTab('chat')
  }
  
  return (
    <>
      <div className="h-full bg-dark-surface border-r border-dark-border flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-dark-border flex items-center justify-between">
        <h2 className="font-semibold text-lg">AgentCore</h2>
        <button
          onClick={onClose}
          className="lg:hidden p-1 hover:bg-dark-surface-hover rounded transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
      
      {/* User info */}
      <div className="p-4 border-b border-dark-border">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
            {isAdmin ? (
              <Shield className="w-5 h-5 text-white" />
            ) : (
              <User className="w-5 h-5 text-white" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{user?.email}</p>
            <p className="text-xs text-dark-text-secondary">
              {isAdmin ? '管理員' : '用戶'}
            </p>
          </div>
        </div>
      </div>
      
      {/* Navigation tabs */}
      <div className="flex-1 overflow-y-auto p-2">
        <nav className="space-y-1">
          <button
            onClick={() => setShowNewChatDialog(true)}
            disabled={isSending}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              activeTab === 'chat'
                ? 'bg-dark-surface-hover text-dark-text'
                : 'text-dark-text-secondary hover:bg-dark-bg hover:text-dark-text'
            } ${isSending ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            <MessageSquare className="w-5 h-5" />
            <span>新對話</span>
          </button>
          
          <button
            onClick={() => setActiveTab('history')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              activeTab === 'history'
                ? 'bg-dark-surface-hover text-dark-text'
                : 'text-dark-text-secondary hover:bg-dark-bg hover:text-dark-text'
            }`}
          >
            <Download className="w-5 h-5" />
            <span>歷史記錄</span>
          </button>
          
          <button
            onClick={() => setActiveTab('settings')}
            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
              activeTab === 'settings'
                ? 'bg-dark-surface-hover text-dark-text'
                : 'text-dark-text-secondary hover:bg-dark-bg hover:text-dark-text'
            }`}
          >
            <Settings className="w-5 h-5" />
            <span>設定</span>
          </button>
        </nav>
        
        {/* Tab content */}
        <div className="mt-4">
          {activeTab === 'chat' && (
            <div className="text-sm text-dark-text-secondary p-3">
              <p>在右側輸入框開始新對話</p>
            </div>
          )}
          
          {activeTab === 'history' && (
            <div className="text-sm text-dark-text-secondary p-3">
              <p>查看和導出對話歷史</p>
              <button className="mt-2 text-primary hover:underline">
                查看完整歷史 →
              </button>
            </div>
          )}
          
          {activeTab === 'settings' && (
            <div className="space-y-2 p-3">
              <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-dark-bg transition-colors text-sm">
                <div className="flex items-center gap-2">
                  <Link2 className="w-4 h-4" />
                  <span>綁定 Telegram</span>
                </div>
              </button>
              
              <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-dark-bg transition-colors text-sm">
                <div className="flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  <span>導出對話</span>
                </div>
              </button>
            </div>
          )}
        </div>
      </div>
      
      {/* Footer with logout */}
      <div className="p-4 border-t border-dark-border">
        <button
          onClick={() => {
            if (confirm('確定要登出嗎？')) {
              logout()
            }
          }}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-dark-text-secondary hover:bg-dark-bg hover:text-error transition-colors"
        >
          <LogOut className="w-5 h-5" />
          <span>登出</span>
        </button>
      </div>
    </div>
      
    {/* 新對話確認對話框 */}
    <NewChatDialog
      isOpen={showNewChatDialog}
      onClose={() => setShowNewChatDialog(false)}
      onConfirm={handleNewChat}
      isDisabled={isSending}
    />
  </>
  )
}
