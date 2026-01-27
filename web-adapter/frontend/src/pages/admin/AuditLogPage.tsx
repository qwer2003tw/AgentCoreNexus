/**
 * AuditLogPage - 審計日誌頁面
 * 
 * 顯示所有管理員操作記錄
 */

import { useState, useEffect } from 'react'
import { api } from '@/services/api'

interface AuditLog {
  log_id: string
  admin_email: string
  admin_id: string
  admin_role: string
  action: string
  resource_type: string
  resource_id: string
  timestamp: number
  status: string
  error_message?: string
  ip_address?: string
  user_agent?: string
  request_id?: string
  request_duration_ms?: number
  details?: any
}

export function AuditLogPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [nextToken, setNextToken] = useState<string | null>(null)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)
  
  const [filters, setFilters] = useState({
    admin_email: '',
    action: ''
  })
  
  useEffect(() => {
    loadLogs()
  }, [])
  
  const loadLogs = async (token?: string) => {
    setLoading(true)
    setError(null)
    
    try {
      const data = await api.listAuditLogs({
        limit: 50,
        next_token: token,
        admin_email: filters.admin_email || undefined,
        action: filters.action || undefined
      })
      
      if (token) {
        setLogs(prev => [...prev, ...data.logs])
      } else {
        setLogs(data.logs)
      }
      
      setNextToken(data.next_token || null)
    } catch (err: any) {
      setError(err.error || 'Failed to load audit logs')
      console.error('Error loading audit logs:', err)
    } finally {
      setLoading(false)
    }
  }
  
  const formatTimestamp = (timestamp: number) => {
    try {
      return new Date(timestamp).toLocaleString('zh-TW')
    } catch {
      return timestamp.toString()
    }
  }
  
  const getStatusBadge = (status: string) => {
    const classes = status === 'success' 
      ? 'bg-green-100 text-green-800' 
      : 'bg-red-100 text-red-800'
    return (
      <span className={`px-2 py-1 rounded text-xs font-medium ${classes}`}>
        {status === 'success' ? '✅ 成功' : '❌ 失敗'}
      </span>
    )
  }
  
  const toggleExpand = (logId: string) => {
    setExpandedLog(expandedLog === logId ? null : logId)
  }
  
  return (
    <div className="audit-log-page">
      <h2>審計日誌</h2>
      
      {/* 篩選器 */}
      <div className="filter-panel">
        <div className="filter-row">
          <div className="filter-item">
            <label>管理員：</label>
            <input
              type="text"
              placeholder="email..."
              value={filters.admin_email}
              onChange={(e) => setFilters({...filters, admin_email: e.target.value})}
            />
          </div>
          
          <div className="filter-item">
            <label>操作類型：</label>
            <input
              type="text"
              placeholder="action..."
              value={filters.action}
              onChange={(e) => setFilters({...filters, action: e.target.value})}
            />
          </div>
          
          <button 
            onClick={() => {
              setFilters({ admin_email: '', action: '' })
              loadLogs()
            }}
            className="btn-primary"
          >
            重新載入
          </button>
        </div>
      </div>
      
      {/* 審計日誌列表 */}
      {error && (
        <div className="error-message">❌ {error}</div>
      )}
      
      {loading && logs.length === 0 ? (
        <div className="loading">載入中...</div>
      ) : (
        <>
          <div className="logs-table">
            <table>
              <thead>
                <tr>
                  <th>時間</th>
                  <th>管理員</th>
                  <th>操作</th>
                  <th>資源</th>
                  <th>狀態</th>
                  <th>耗時</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <>
                    <tr key={log.log_id} className="log-row">
                      <td>{formatTimestamp(log.timestamp)}</td>
                      <td>{log.admin_email}</td>
                      <td className="action-cell">{log.action}</td>
                      <td>
                        <span className="resource-type">{log.resource_type}</span>
                        {log.resource_id !== 'N/A' && (
                          <span className="resource-id">#{log.resource_id.substring(0, 8)}</span>
                        )}
                      </td>
                      <td>{getStatusBadge(log.status)}</td>
                      <td>{log.request_duration_ms}ms</td>
                      <td>
                        <button
                          onClick={() => toggleExpand(log.log_id)}
                          className="btn-expand"
                        >
                          {expandedLog === log.log_id ? '▼' : '▶'}
                        </button>
                      </td>
                    </tr>
                    
                    {expandedLog === log.log_id && (
                      <tr className="detail-row">
                        <td colSpan={7}>
                          <div className="log-details">
                            <div className="detail-item">
                              <strong>Log ID:</strong> {log.log_id}
                            </div>
                            <div className="detail-item">
                              <strong>Admin ID:</strong> {log.admin_id}
                            </div>
                            <div className="detail-item">
                              <strong>Admin Role:</strong> {log.admin_role}
                            </div>
                            {log.ip_address && (
                              <div className="detail-item">
                                <strong>IP Address:</strong> {log.ip_address}
                              </div>
                            )}
                            {log.user_agent && (
                              <div className="detail-item">
                                <strong>User Agent:</strong> {log.user_agent}
                              </div>
                            )}
                            {log.request_id && (
                              <div className="detail-item">
                                <strong>Request ID:</strong> {log.request_id}
                              </div>
                            )}
                            {log.error_message && (
                              <div className="detail-item error">
                                <strong>Error:</strong> {log.error_message}
                              </div>
                            )}
                            {log.details && (
                              <div className="detail-item">
                                <strong>Details:</strong>
                                <pre>{JSON.stringify(log.details, null, 2)}</pre>
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
            
            {logs.length === 0 && !loading && (
              <div className="empty-state">沒有審計記錄</div>
            )}
          </div>
          
          {nextToken && (
            <div className="load-more">
              <button 
                onClick={() => loadLogs(nextToken)}
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
        .audit-log-page {
          max-width: 1600px;
          margin: 0 auto;
        }
        
        .audit-log-page h2 {
          margin-bottom: 1.5rem;
          color: #ffffff;
        }
        
        .filter-panel {
          background: #2d2d2d;
          padding: 1.5rem;
          border-radius: 8px;
          margin-bottom: 1.5rem;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
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
          color: #a0a0a0;
          font-weight: 500;
        }
        
        .filter-item input {
          padding: 0.5rem;
          border: 1px solid #404040;
          border-radius: 4px;
          font-size: 0.9rem;
          width: 200px;
          background: #1a1a1a;
          color: #ffffff;
        }
        
        .logs-table {
          background: #2d2d2d;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        
        .logs-table table {
          width: 100%;
          border-collapse: collapse;
        }
        
        .logs-table thead {
          background-color: #3a3a3a;
        }
        
        .logs-table th {
          padding: 1rem;
          text-align: left;
          font-weight: 600;
          color: #ffffff;
          border-bottom: 2px solid #404040;
          font-size: 0.9rem;
        }
        
        .logs-table td {
          padding: 0.75rem 1rem;
          border-bottom: 1px solid #404040;
          font-size: 0.85rem;
          color: #ffffff;
        }
        
        .log-row:hover {
          background-color: #3a3a3a;
        }
        
        .action-cell {
          font-family: monospace;
          font-size: 0.8rem;
          color: #a0a0a0;
        }
        
        .resource-type {
          background-color: #e3f2fd;
          color: #1976d2;
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
          margin-right: 0.5rem;
        }
        
        .resource-id {
          font-family: monospace;
          font-size: 0.75rem;
          color: #a0a0a0;
        }
        
        .btn-expand {
          background: none;
          border: none;
          cursor: pointer;
          font-size: 1rem;
          color: #a0a0a0;
          padding: 0.25rem 0.5rem;
        }
        
        .btn-expand:hover {
          color: #ffffff;
          background-color: #3a3a3a;
          border-radius: 4px;
        }
        
        .detail-row td {
          background-color: #3a3a3a;
          padding: 1.5rem;
        }
        
        .log-details {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 1rem;
        }
        
        .detail-item {
          font-size: 0.85rem;
        }
        
        .detail-item strong {
          display: block;
          margin-bottom: 0.25rem;
          color: #a0a0a0;
        }
        
        .detail-item pre {
          background-color: #1a1a1a;
          color: #ffffff;
          padding: 0.5rem;
          border-radius: 4px;
          overflow-x: auto;
          font-size: 0.75rem;
        }
        
        .detail-item.error {
          color: #d32f2f;
        }
        
        .btn-primary {
          padding: 0.5rem 1.5rem;
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
        
        .load-more {
          text-align: center;
          margin-top: 1.5rem;
        }
        
        .loading, .empty-state {
          text-align: center;
          padding: 3rem;
          color: #a0a0a0;
          background: #2d2d2d;
          border-radius: 8px;
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
          .logs-table {
            overflow-x: auto;
          }
          
          .logs-table table {
            min-width: 900px;
          }
        }
      `}</style>
    </div>
  )
}

export default AuditLogPage