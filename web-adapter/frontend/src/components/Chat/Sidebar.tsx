import { useAuthStore } from '@/stores/authStore'
import { LogOut, X, User, Shield } from 'lucide-react'
import ConversationList from './ConversationList'

interface SidebarProps {
  onClose: () => void
}

export default function Sidebar({ onClose }: SidebarProps) {
  const { user, logout } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  
  return (
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
      
      {/* Conversation List */}
      <ConversationList />
      
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
  )
}