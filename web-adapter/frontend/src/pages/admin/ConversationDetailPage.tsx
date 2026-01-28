/**
 * ConversationDetailPage - 對話詳情頁面
 * 
 * 顯示完整的對話內容、附件、統計資訊、AI 摘要
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

interface ConversationSummary {
  conversation_id: string
  summary?: string
  summary_text?: string
  attachment_stats: {
    images: number
    documents: number
    total: number
  }
  generated_at: number
  model_used: string
  cached: boolean
}

export function ConversationDetailPage() {
  const { conversation_id } = useParams<{ conversation_id: string }>()
  const [conversation, setConversation] = useState<ConversationDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // AI 摘要相關 state
  const [summary, setSummary] = useState<ConversationSummary | null>(null)
  const [summaryLoading, setSummaryLoading] = useState(false)
  const [summaryGenerating, setSummaryGenerating] = useState(false)
  const [summaryError, setSummaryError] = useState<string | null>(null)
  
  useEffect(() => {
    if (conversation_id) {
      loadConversation()
      loadSummaryIfExists()  // ⭐ 自動載入摘要
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
  
  const loadSummaryIfExists = async () => {
    if (!conversation_id) return
    
    setSummaryLoading(true)
    setSummaryError(null)
    
    try {
      // 嘗試載入摘要（如果有緩存會立即返回）
      const data = await api.generateConversationSummary(conversation_id)
      
      // 如果是緩存，直接顯示
      if (data.cached) {
        setSummary(data)
      } else {
        // 新生成的摘要（不太可能，但處理一下）
        setSummary(data)
      }
    } catch (err: any) {
      // 沒有摘要（正常情況，不是錯誤）
      if (err.statusCode === 404) {
        setSummary(null)
      } else {
        console.error('Error loading summary:', err)
        setSummary(null)
      }
    } finally {
      setSummaryLoading(false)
    }
  }
  
  const handleGenerateSummary = async () => {
    if (!conversation_id) return
    
    setSummaryGenerating(true)
    setSummaryError(null)
    
    try {
      const data = await api.generateConversationSummary(conversation_id)
      setSummary(data)
    } catch (err: any) {
      setSummaryError(err.error || 'Unknown error')
      console.error('Error generating summary:', err)
    } finally {
      setSummaryGenerating(false)
    }
  }
  
  const formatTimestamp = (timestamp?: string | number) => {
    if (!timestamp) return '-'
    try {
      const date = typeof timestamp === 'number' 
        ? new Date(timestamp) 
        : new Date(timestamp)
      return date.toLocaleString('zh-TW')
    } catch {
      return String(timestamp)
    }
  }
  
  const getTimeAgo = (timestamp: number) => {
    const now = Date.now()
    const diff = now - timestamp
    const hours = Math.floor(diff / 3600000)
    
    if (hours < 1) return '不到 1 小時前'
    if (hours === 1) return '1 小時前'
    if (hours < 24) return `${hours} 小時前`
    
    const days = Math.floor(hours / 24)
    return `${days} 天前`
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
      
      {/* ⭐ AI 摘要卡片 */}
      <div className="summary-card">
        <div className="summary-header">
          <h3>📊 AI 對話摘要</h3>
          {summary && !summaryGenerating && (
            <button 
              onClick={handleGenerateSummary}
              className="btn-secondary btn-small"
            >
              🔄 重新生成
            </button>
          )}
        </div>
        
        {summaryLoading && (
          <div className="summary-state">
            <div className="spinner"></div>
            <p>載入摘要中...</p>
          </div>
        )}
        
        {!summaryLoading && !summary && !summaryGenerating && (
          <div className="summary-empty">
            <p className="empty-text">暫無 AI 摘要，點擊下方按鈕生成</p>
            <button 
              onClick={handleGenerateSummary}
              className="btn-primary"
            >
              🤖 生成 AI 摘要
            </button>
          </div>
        )}
        
        {summaryGenerating && (
          <div className="summary-state">
            <div className="spinner"></div>
            <p className="generating-title">🔄 AI 正在分析對話...</p>
            <p className="generating-subtitle">預計需要 5-10 秒</p>
          </div>
        )}
        
        {!summaryLoading && !summaryGenerating && summary && (
          <div className="summary-content">
            <div className="summary-text">
              {summary.summary || summary.summary_text || '摘要內容載入失敗'}
            </div>
            <div className="summary-meta">
              <span className="summary-meta-item">
                {summary.cached ? (
                  <>💾 使用緩存（{getTimeAgo(summary.generated_at)}）</>
                ) : (
                  <>✨ 新生成</>
                )}
              </span>
              <span className="summary-meta-item">
                📅 {formatTimestamp(summary.generated_at)}
              </span>
              {summary.model_used && (
                <span className="summary-meta-item">
                  🤖 {summary.model_used.includes('haiku') ? 'Claude 3 Haiku' : 'Claude'}
                </span>
              )}
            </div>
          </div>
        )}
        
        {summaryError && (
          <div className="summary-error">
            ❌ {summaryError}
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
        
        .btn-small {
          padding: 0.5rem 1rem;
          font-size: 0.85rem;
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
        
        /* ⭐ AI 摘要卡片樣式 */
        .summary-card {
          background: #2d2d2d;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .summary-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1rem;
        }
        
        .summary-header h3 {
          margin: 0;
          color: #ffffff;
          font-size: 1.1rem;
        }
        
        .summary-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          text-align: center;
          color: #a0a0a0;
        }
        
        .summary-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 2rem;
          text-align: center;
        }
        
        .empty-text {
          color: #a0a0a0;
          margin-bottom: 1rem;
        }
        
        .summary-content {
          animation: fadeIn 0.3s ease-in;
        }
        
        .summary-text {
          white-space: pre-wrap;
          line-height: 1.8;
          color: #ffffff;
          padding: 1rem;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 6px;
          margin-bottom: 1rem;
        }
        
        .summary-meta {
          display: flex;
          gap: 1.5rem;
          flex-wrap: wrap;
          font-size: 0.85rem;
          padding-top: 0.75rem;
          border-top: 1px solid #404040;
        }
        
        .summary-meta-item {
          color: #a0a0a0;
          display: flex;
          align-items: center;
          gap: 0.25rem;
        }
        
        .summary-error {
          padding: 1rem;
          background-color: #4a1f1f;
          color: #ffb3b3;
          border: 1px solid #6a2c2c;
          border-radius: 4px;
          text-align: center;
        }
        
        .generating-title {
          font-size: 1rem;
          color: #ffffff;
          margin-bottom: 0.5rem;
        }
        
        .generating-subtitle {
          font-size: 0.85rem;
          color: #a0a0a0;
        }
        
        /* Spinner 動畫 */
        .spinner {
          width: 40px;
          height: 40px;
          border: 4px solid #404040;
          border-top-color: #1976d2;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 1rem;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
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
          background-color: rgba(255,255,255,0.05);
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
          
          .summary-meta {
            flex-direction: column;
            gap: 0.5rem;
          }
        }
      `}</style>
    </div>
  )
}

export default ConversationDetailPage