import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { useChatStore } from '@/stores/chatStore'
import ChatWindow from '@/components/Chat/ChatWindow'
import Sidebar from '@/components/Chat/Sidebar'
import { Menu } from 'lucide-react'

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { user } = useAuthStore()
  const { isConnected } = useChatStore()
  
  // Note: WebSocket initialization is handled in App.tsx
  // No need to initialize again here
  
  return (
    <div className="h-screen flex overflow-hidden bg-dark-bg">
      {/* Sidebar - Desktop: always visible, Mobile: toggle */}
      <div className={`
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        fixed lg:relative lg:translate-x-0
        w-64 h-full
        transition-transform duration-300 ease-in-out
        z-30
      `}>
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>
      
      {/* Main chat area */}
      <div className="flex-1 flex flex-col h-full">
        {/* Header */}
        <header className="bg-dark-surface border-b border-dark-border px-4 py-3 flex items-center gap-3">
          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden p-2 hover:bg-dark-surface-hover rounded-lg transition-colors"
          >
            <Menu className="w-5 h-5" />
          </button>
          
          {/* Title */}
          <div className="flex-1">
            <h1 className="text-lg font-semibold">AgentCore Chat</h1>
            <p className="text-xs text-dark-text-secondary">
              {user?.email}
            </p>
          </div>
          
          {/* Connection status */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-success' : 'bg-error'
            }`} />
            <span className="text-xs text-dark-text-secondary">
              {isConnected ? '已連接' : '未連接'}
            </span>
          </div>
        </header>
        
        {/* Chat window */}
        <ChatWindow />
      </div>
      
      {/* Overlay for mobile sidebar */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-20"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  )
}