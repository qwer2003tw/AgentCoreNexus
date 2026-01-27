/**
 * ConversationDetailPage - 對話詳情頁面
 * 
 * 顯示完整的對話內容、附件、統計資訊
 */

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '@/services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
  attachments?: Array<{
    type: string
    url?: string
    file_name?: string
    content_type?: string
  }>
}

interface ConversationDetail {
  conversation_id: string
  user_id: string
  channel: string
  messages: Message[]
  created_at?: string
  updated_at?: string
  statistics?: {
    message_count: number
    attachments: {
      images: number
      files: number
      total: number
    }
  }
}

export function ConversationDetailPage() {
  const { conversation_id } = useParams<{ conversation_id: string }>()
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [generatingSummary, setGeneratingSummary] = useState(false)
  
  useEffect(() => {
    if (conversation_id) {
      loadConversation()
    }
  }, [conversation_id])
  
  const loadConversation = async () => {
    setLoading(true)
    setError(null)
    
    try {
      const data = await api.getConversationDetail(conversation_id!)
      setConversation(data)
    } catch (err: any) {
      setError(err.error || 'Failed to load conversation')
      console.error('Error loading conversation:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const handleGenerateSummary = async () => {
    if (!conversation_id) return
    
    setGeneratingSummary(true)
    try {
      const data = await api.generateConversationSummary(conversation_id)
      alert(`摘要已生成：\n\n${data.summary}`)
    } catch (err: any) {
      alert('生成摘要失敗：' + (err.error || 'Unknown error'))
    } finally {
      setGeneratingSummary(false)
    }
  }
  
  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return '-'
    try {
      return new Date(timestamp).toLocaleString('zh-TW')
    } catch {
      return timestamp
    }
  }
  
  if (loading) {
    return <div className="loading">載入中...</div>
  }
  
  if (error) {
    return (
      <div className="error-page">
        <div className="error-message">❌ {error}</div>
        <Link to="/admin" className="btn-primary">返回列表</Link>
      </div>
    )
  }
  
  if (!conversation) {
    return (
      <div className="error-page">
        <div className="error-message">對話不存在</div>
        <Link to="/admin" className="btn-primary">返回列表</Link>
      </div>
    )
  }
  
  return (
    <div className="conversation-detail-page">
      {/* 頂部操作欄 */}
      <div className="detail-header">
        <div className="header-left">
          <Link to="/admin" className="btn-back">← 返回列表</Link>
          <h2>對話詳情</h2>
        </div>
        <div className="header-right">
          <button 
            onClick={handleGenerateSummary}
            disabled={generatingSummary}
            className="btn-primary"
          >
            {generatingSummary ? '生成中...' : '🤖 生成 AI 摘要'}
          </button>
          <button className="btn-secondary">⬇️ 匯出</button>
        </div>
      </div>
      
      {/* 元數據卡片 */}
      <div className="metadata-card">
        <div className="metadata-row">
          <div className="metadata-item">
            <span className="label">對話 ID：</span>
            <span className="value monospace">{conversation.conversation_id}</span>
          </div>
          <div className="metadata-item">
            <span className="label">用戶 ID：</span>
            <span className="value">{conversation.user_id}</span>
          </div>
          <div className="metadata-item">
            <span className="label">通道：</span>
            <span className={`channel-badge ${conversation.channel}`}>
              {conversation.channel === 'telegram' ? '📱' : '🌐'} {conversation.channel}
            </span>
          </div>
        </div>
        
        {conversation.statistics && (
          <div className="statistics">
            <div className="stat-item">
              <span className="stat-label">總消息數：</span>
              <span className="stat-value">{conversation.statistics.message_count}</span>
            </div>
            <div className="stat-item">
              <span className="stat-label">附件：</span>
              <span className="stat-value">
                {conversation.statistics.attachments.images} 張圖片，
                {conversation.statistics.attachments.files} 個文件
              </span>
            </div>
          </div>
        )}
      </div>
      
      {/* 消息時間線 */}
      <div className="messages-timeline">
        <h3>對話內容</h3>
        <div className="messages-list">
          {conversation.messages.map((msg, index) => (
            <div key={index} className={`message-item ${msg.role}`}>
              <div className="message-header">
                <span className="message-role">
                  {msg.role === 'user' ? '👤 用戶' : '🤖 AI'}
                </span>
                {msg.timestamp && (
                  <span className="message-time">{formatTimestamp(msg.timestamp)}</span>
                )}
              </div>
              <div className="message-content">
                {msg.content}
              </div>
              {msg.attachments && msg.attachments.length > 0 && (
                <div className="message-attachments">
                  {msg.attachments.map((att, attIndex) => (
                    <div key={attIndex} className="attachment-item">
                      <span className="attachment-icon">
                        {att.type === 'photo' ? '🖼️' : '📄'}
                      </span>
                      <span className="attachment-name">
                        {att.file_name || 'Unnamed'}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
      
      <style>{`
        .conversation-detail-page {
          max-width: 1000px;
          margin: 0 auto;
        }
        
        .detail-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }
        
        .header-left {
          display: flex;
          align-items: center;
          gap: 1rem;
        }
        
        .header-left h2 {
          margin: 0;
          color: #ffffff;
        }
        
        .header-right {
          display: flex;
          gap: 0.75rem;
        }
        
        .btn-back {
          padding: 0.5rem 1rem;
          background-color: #6c757d;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          text-decoration: none;
          font-size: 0.9rem;
        }
        
        .btn-back:hover {
          background-color: #5a6268;
        }
        
        .btn-primary {
          padding: 0.75rem 1.5rem;
          background-color: #1976d2;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9rem;
        }
        
        .btn-primary:hover:not(:disabled) {
          background-color: #1565c0;
        }
        
        .btn-primary:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        
        .btn-secondary {
          padding: 0.75rem 1.5rem;
          background-color: #6c757d;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          font-size: 0.9rem;
        }
        
        .btn-secondary:hover {
          background-color: #5a6268;
        }
        
        .metadata-card {
          background: #2d2d2d;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .metadata-row {
          display: flex;
          gap: 2rem;
          margin-bottom: 1rem;
          flex-wrap: wrap;
        }
        
        .metadata-item {
          display: flex;
          gap: 0.5rem;
        }
        
        .metadata-item .label {
          font-weight: 600;
          color: #a0a0a0;
        }
        
        .metadata-item .value {
          color: #ffffff;
        }
        
        .monospace {
          font-family: monospace;
          font-size: 0.9rem;
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
        
        .statistics {
          display: flex;
          gap: 2rem;
          padding-top: 1rem;
          border-top: 1px solid #404040;
        }
        
        .stat-item {
          display: flex;
          gap: 0.5rem;
        }
        
        .stat-label {
          color: #a0a0a0;
        }
        
        .stat-value {
          font-weight: 600;
          color: #ffffff;
        }
        
        .messages-timeline {
          background: #2d2d2d;
          padding: 1.5rem;
          border-radius: 8px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .messages-timeline h3 {
          margin-top: 0;
          margin-bottom: 1.5rem;
          color: #ffffff;
        }
        
        .messages-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }
        
        .message-item {
          padding: 1rem;
          border-radius: 8px;
          border-left: 4px solid #404040;
        }
        
        .message-item.user {
          background-color: #1e3a5f;
          border-left-color: #3b82f6;
        }
        
        .message-item.assistant {
          background-color: #3a3a3a;
          border-left-color: #10b981;
        }
        
        .message-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 0.5rem;
        }
        
        .message-role {
          font-weight: 600;
          font-size: 0.9rem;
        }
        
        .message-time {
          font-size: 0.85rem;
          color: #a0a0a0;
        }
        
        .message-content {
          white-space: pre-wrap;
          line-height: 1.6;
          color: #ffffff;
        }
        
        .message-attachments {
          margin-top: 0.75rem;
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }
        
        .attachment-item {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem;
          background-color: rgba(255,255,255,0.5);
          border-radius: 4px;
        }
        
        .attachment-icon {
          font-size: 1.2rem;
        }
        
        .attachment-name {
          font-size: 0.9rem;
          color: #a0a0a0;
        }
        
        .loading, .error-page {
          text-align: center;
          padding: 3rem;
          color: #a0a0a0;
        }
        
        .error-message {
          padding: 1rem;
          background-color: #4a1f1f;
          color: #ffb3b3;
          border: 1px solid #6a2c2c;
          border-radius: 4px;
          margin-bottom: 1rem;
        }
        
        @media (max-width: 768px) {
          .detail-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
          }
          
          .header-right {
            width: 100%;
            justify-content: flex-end;
          }
          
          .metadata-row {
            flex-direction: column;
            gap: 0.75rem;
          }
        }
      `}</style>
    </div>
  )
}

export default ConversationDetailPage
