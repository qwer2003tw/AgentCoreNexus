/**
 * ConversationListPage - 對話列表管理頁面
 * 
 * 顯示所有對話，支持篩選、分頁、查看詳情
 */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '@/services/api'

interface Conversation {
  conversation_id: string
  user_id: string
  channel: string
  timestamp: string
  message_count?: number
  last_message?: string
}

interface FilterState {
  channel: string
  startTime: string
  endTime: string
  searchQuery: string
}

export function ConversationListPage() {
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nextToken, setNextToken] = useState<string | null>(null)
  
  const [filters, setFilters] = useState<FilterState>({
    channel: '',
    startTime: '',
    endTime: '',
    searchQuery: ''
  })
  
  useEffect(() => {
    loadConversations()
  }, [filters.channel, filters.startTime, filters.endTime])
  
  const loadConversations = async (token?: string) => {
    setLoading(true)
    setError(null)
    
    try {
      // 使用 API client
      const data = await api.listAllConversations({
        limit: 50,
        next_token: token,
        channel: filters.channel || undefined,
        start_time: filters.startTime || undefined,
        end_time: filters.endTime || undefined
      })
      
      if (token) {
        // 追加數據（加載更多）
        setConversations(prev => [...prev, ...data.conversations])
      } else {
        // 新查詢（替換數據）
        setConversations(data.conversations)
      }
      
      setNextToken(data.next_token || null)
    } catch (err: any) {
      setError(err.error || 'Failed to load conversations')
      console.error('Error loading conversations:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const handleLoadMore = () => {
    if (nextToken && !loading) {
      loadConversations(nextToken)
    }
  }
  
  const handleFilterChange = (key: keyof FilterState, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setNextToken(null) // 重置分頁
  }
  
  const formatTimestamp = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleString('zh-TW')
    } catch {
      return timestamp
    }
  }
  
  return (
    <div className="conversation-list-page">
      <h2>對話管理</h2>
      
      {/* 篩選器 */}
      <div className="filter-panel">
        <div className="filter-row">
          <div className="filter-item">
            <label htmlFor="channel-filter">通道：</label>
            <select
              id="channel-filter"
              value={filters.channel}
              onChange={(e) => handleFilterChange('channel', e.target.value)}
            >
              <option value="">全部</option>
              <option value="telegram">Telegram</option>
              <option value="web">Web</option>
            </select>
          </div>
          
          <div className="filter-item">
            <label htmlFor="start-time">開始時間：</label>
            <input
              id="start-time"
              type="datetime-local"
              value={filters.startTime}
              onChange={(e) => handleFilterChange('startTime', e.target.value)}
            />
          </div>
          
          <div className="filter-item">
            <label htmlFor="end-time">結束時間：</label>
            <input
              id="end-time"
              type="datetime-local"
              value={filters.endTime}
              onChange={(e) => handleFilterChange('endTime', e.target.value)}
            />
          </div>
          
          <button 
            onClick={() => setFilters({ channel: '', startTime: '', endTime: '', searchQuery: '' })}
            className="btn-secondary"
          >
            清除篩選
          </button>
        </div>
      </div>
      
      {/* 對話列表 */}
      {error && (
        <div className="error-message">
          ❌ {error}
        </div>
      )}
      
      {loading && conversations.length === 0 ? (
        <div className="loading">載入中...</div>
      ) : (
        <>
          <div className="conversations-table">
            <table>
              <thead>
                <tr>
                  <th>對話 ID</th>
                  <th>用戶 ID</th>
                  <th>通道</th>
                  <th>時間</th>
                  <th>消息數</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {conversations.map(conv => (
                  <tr key={conv.conversation_id}>
                    <td className="conv-id">{conv.conversation_id}</td>
                    <td>{conv.user_id}</td>
                    <td>
                      <span className={`channel-badge ${conv.channel}`}>
                        {conv.channel === 'telegram' ? '📱' : '🌐'} {conv.channel}
                      </span>
                    </td>
                    <td>{formatTimestamp(conv.timestamp)}</td>
                    <td>{conv.message_count || '-'}</td>
                    <td>
                      <Link 
                        to={`/admin/conversations/${conv.conversation_id}`}
                        className="btn-primary-small"
                      >
                        查看
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            
            {conversations.length === 0 && !loading && (
              <div className="empty-state">
                沒有找到對話記錄
              </div>
            )}
          </div>
          
          {/* 加載更多 */}
          {nextToken && (
            <div className="load-more">
              <button 
                onClick={handleLoadMore}
                disabled={loading}
                className="btn-primary"
              >
                {loading ? '載入中...' : '加載更多'}
              </button>
            </div>
          )}
        </>
      )}
      
      <style>{`
        .conversation-list-page {
          max-width: 1400px;
          margin: 0 auto;
        }
        
        .conversation-list-page h2 {
          margin-bottom: 1.5rem;
          color: #2c3e50;
        }
        
        .filter-panel {
          background: white;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .filter-row {
          display: flex;
          gap: 1rem;
          align-items: flex-end;
          flex-wrap: wrap;
        }
        
        .filter-item {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        
        .filter-item label {
          font-size: 0.9rem;
          color: #666;
          font-weight: 500;
        }
        
        .filter-item select,
        .filter-item input {
          padding: 0.5rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 0.9rem;
        }
        
        .conversations-table {
          background: white;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .conversations-table table {
          width: 100%;
          border-collapse: collapse;
        }
        
        .conversations-table thead {
          background-color: #f8f9fa;
        }
        
        .conversations-table th {
          padding: 1rem;
          text-align: left;
          font-weight: 600;
          color: #495057;
          border-bottom: 2px solid #dee2e6;
        }
        
        .conversations-table td {
          padding: 0.75rem 1rem;
          border-bottom: 1px solid #dee2e6;
        }
        
        .conversations-table tbody tr:hover {
          background-color: #f8f9fa;
        }
        
        .conv-id {
          font-family: monospace;
          font-size: 0.85rem;
          color: #6c757d;
        }
        
        .channel-badge {
          display: inline-block;
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.85rem;
          font-weight: 500;
        }
        
        .channel-badge.telegram {
          background-color: #e3f2fd;
          color: #1976d2;
        }
        
        .channel-badge.web {
          background-color: #f3e5f5;
          color: #7b1fa2;
        }
        
        .btn-primary-small {
          padding: 0.25rem 0.75rem;
          background-color: #1976d2;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          text-decoration: none;
          font-size: 0.85rem;
        }
        
        .btn-primary-small:hover {
          background-color: #1565c0;
        }
        
        .btn-primary {
          padding: 0.75rem 2rem;
          background-color: #1976d2;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 1rem;
        }
        
        .btn-primary:hover:not(:disabled) {
          background-color: #1565c0;
        }
        
        .btn-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .btn-secondary {
          padding: 0.5rem 1rem;
          background-color: #6c757d;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          text-decoration: none;
          font-size: 0.9rem;
        }
        
        .btn-secondary:hover {
          background-color: #5a6268;
        }
        
        .load-more {
          text-align: center;
          margin-top: 1.5rem;
        }
        
        .loading, .empty-state {
          text-align: center;
          padding: 3rem;
          color: #6c757d;
          background: white;
          border-radius: 8px;
        }
        
        .error-message {
          padding: 1rem;
          background-color: #f8d7da;
          color: #721c24;
          border: 1px solid #f5c6cb;
          border-radius: 4px;
          margin-bottom: 1rem;
        }
        
        @media (max-width: 768px) {
          .filter-row {
            flex-direction: column;
          }
          
          .filter-item {
            width: 100%;
          }
          
          .conversations-table {
            overflow-x: auto;
          }
          
          .conversations-table table {
            min-width: 800px;
          }
        }
      `}</style>
    </div>
  )
}

export default ConversationListPage