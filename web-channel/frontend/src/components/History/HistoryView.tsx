import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Calendar, Filter, Download, Loader2 } from 'lucide-react'

interface GroupedMessages {
  today: any[]
  yesterday: any[]
  this_week: any[]
  earlier: any[]
}

export default function HistoryView() {
  const [channelFilter, setChannelFilter] = useState<'all' | 'web' | 'telegram'>('all')
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['history', channelFilter],
    queryFn: async () => {
      return api.getHistory({
        limit: 100,
        channel: channelFilter === 'all' ? undefined : channelFilter
      })
    }
  })
  
  const conversations = data?.conversations as GroupedMessages | undefined
  
  return (
    <div className="h-full flex flex-col bg-dark-bg">
      {/* Header */}
      <div className="p-4 border-b border-dark-border bg-dark-surface">
        <h2 className="text-xl font-semibold mb-4">對話歷史</h2>
        
        {/* Filters */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-dark-text-secondary" />
            <span className="text-sm text-dark-text-secondary">篩選:</span>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => setChannelFilter('all')}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                channelFilter === 'all'
                  ? 'bg-primary text-white'
                  : 'bg-dark-bg text-dark-text-secondary hover:bg-dark-surface-hover'
              }`}
            >
              全部
            </button>
            <button
              onClick={() => setChannelFilter('web')}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                channelFilter === 'web'
                  ? 'bg-primary text-white'
                  : 'bg-dark-bg text-dark-text-secondary hover:bg-dark-surface-hover'
              }`}
            >
              Web
            </button>
            <button
              onClick={() => setChannelFilter('telegram')}
              className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                channelFilter === 'telegram'
                  ? 'bg-primary text-white'
                  : 'bg-dark-bg text-dark-text-secondary hover:bg-dark-surface-hover'
              }`}
            >
              Telegram
            </button>
          </div>
        </div>
      </div>
      
      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="w-8 h-8 animate-spin text-primary" />
          </div>
        )}
        
        {error && (
          <div className="text-center text-error">
            <p>載入歷史記錄失敗</p>
            <p className="text-sm mt-2">{(error as any).error || '請稍後再試'}</p>
          </div>
        )}
        
        {conversations && (
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Today */}
            {conversations.today && conversations.today.length > 0 && (
              <TimeGroup title="今天" messages={conversations.today} />
            )}
            
            {/* Yesterday */}
            {conversations.yesterday && conversations.yesterday.length > 0 && (
              <TimeGroup title="昨天" messages={conversations.yesterday} />
            )}
            
            {/* This Week */}
            {conversations.this_week && conversations.this_week.length > 0 && (
              <TimeGroup title="本週" messages={conversations.this_week} />
            )}
            
            {/* Earlier */}
            {conversations.earlier && conversations.earlier.length > 0 && (
              <TimeGroup title="更早" messages={conversations.earlier} />
            )}
            
            {/* No messages */}
            {!conversations.today?.length && 
             !conversations.yesterday?.length && 
             !conversations.this_week?.length && 
             !conversations.earlier?.length && (
              <div className="text-center text-dark-text-secondary py-12">
                <Calendar className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p>尚無對話歷史</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

interface TimeGroupProps {
  title: string
  messages: any[]
}

function TimeGroup({ title, messages }: TimeGroupProps) {
  return (
    <div>
      <h3 className="text-sm font-medium text-dark-text-secondary mb-3 flex items-center gap-2">
        <Calendar className="w-4 h-4" />
        {title}
      </h3>
      
      <div className="space-y-2">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className="card hover:bg-dark-surface-hover transition-colors cursor-pointer"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <p className={`text-sm font-medium ${
                  msg.role === 'user' ? 'text-primary' : 'text-dark-text'
                }`}>
                  {msg.role === 'user' ? '你' : 'AI 助理'}
                </p>
                <p className="text-sm text-dark-text mt-1 line-clamp-2">
                  {msg.content?.text || ''}
                </p>
              </div>
              
              <div className="flex flex-col items-end gap-1">
                <span className="text-xs text-dark-text-secondary">
                  {formatTime(msg.timestamp_msgid)}
                </span>
                {msg.channel && (
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    msg.channel === 'web'
                      ? 'bg-primary/20 text-primary'
                      : 'bg-success/20 text-success'
                  }`}>
                    {msg.channel === 'web' ? 'Web' : 'Telegram'}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatTime(timestamp_msgid: string): string {
  try {
    const timestamp = timestamp_msgid.split('#')[0]
    const date = new Date(timestamp)
    return date.toLocaleString('zh-TW', {
      month: 'numeric',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return ''
  }
}