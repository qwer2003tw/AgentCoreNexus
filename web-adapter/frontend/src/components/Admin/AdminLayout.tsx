/**
 * AdminLayout - 管理員頁面布局
 * 
 * 包含側邊欄導航和主內容區域
 */

import { useState } from 'react'
import { Link, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

export function AdminLayout() {
  const location = useLocation()
  const { user, logout } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  
  const menuItems = [
    { path: '/admin', label: '對話管理', icon: '💬' },
    { path: '/admin/audit-logs', label: '審計日誌', icon: '📋' },
  ]
  
  return (
    <div className="admin-layout">
      {/* 頂部導航欄 */}
      <header className="admin-header">
        <div className="admin-header-left">
          <button 
            className="sidebar-toggle"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            aria-label="Toggle sidebar"
          >
            ☰
          </button>
          <h1>AgentCore 管理中心</h1>
        </div>
        <div className="admin-header-right">
          <span className="admin-user">
            👤 {user?.email} ({user?.role})
          </span>
          <Link to="/" className="btn-secondary">返回聊天</Link>
          <button onClick={logout} className="btn-secondary">登出</button>
        </div>
      </header>
      
      {/* 主容器 */}
      <div className="admin-container">
        {/* 側邊欄 */}
        {sidebarOpen && (
          <aside className="admin-sidebar">
            <nav className="admin-nav">
              {menuItems.map(item => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`admin-nav-item ${location.pathname === item.path ? 'active' : ''}`}
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span className="nav-label">{item.label}</span>
                </Link>
              ))}
            </nav>
          </aside>
        )}
        
        {/* 主內容區域 */}
        <main className="admin-main">
          <Outlet />
        </main>
      </div>
      
      <style>{`
        .admin-layout {
          display: flex;
          flex-direction: column;
          height: 100vh;
          background-color: #f5f5f5;
        }
        
        .admin-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 1rem 1.5rem;
          background-color: #2c3e50;
          color: white;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .admin-header-left {
          display: flex;
          align-items: center;
          gap: 1rem;
        }
        
        .admin-header-left h1 {
          margin: 0;
          font-size: 1.5rem;
        }
        
        .sidebar-toggle {
          background: none;
          border: none;
          color: white;
          font-size: 1.5rem;
          cursor: pointer;
          padding: 0.5rem;
        }
        
        .admin-header-right {
          display: flex;
          align-items: center;
          gap: 1rem;
        }
        
        .admin-user {
          font-size: 0.9rem;
        }
        
        .admin-container {
          display: flex;
          flex: 1;
          overflow: hidden;
        }
        
        .admin-sidebar {
          width: 250px;
          background-color: white;
          border-right: 1px solid #e0e0e0;
          overflow-y: auto;
        }
        
        .admin-nav {
          padding: 1rem 0;
        }
        
        .admin-nav-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem 1.5rem;
          color: #333;
          text-decoration: none;
          transition: background-color 0.2s;
        }
        
        .admin-nav-item:hover {
          background-color: #f0f0f0;
        }
        
        .admin-nav-item.active {
          background-color: #e3f2fd;
          color: #1976d2;
          border-left: 3px solid #1976d2;
        }
        
        .nav-icon {
          font-size: 1.2rem;
        }
        
        .nav-label {
          font-size: 1rem;
        }
        
        .admin-main {
          flex: 1;
          padding: 2rem;
          overflow-y: auto;
          background-color: #fafafa;
        }
        
        .btn-secondary {
          padding: 0.5rem 1rem;
          background-color: #34495e;
          color: white;
          border: none;
          border-radius: 4px;
          cursor: pointer;
          text-decoration: none;
          font-size: 0.9rem;
        }
        
        .btn-secondary:hover {
          background-color: #2c3e50;
        }
        
        @media (max-width: 768px) {
          .admin-header-left h1 {
            font-size: 1.2rem;
          }
          
          .admin-sidebar {
            width: 200px;
          }
          
          .admin-main {
            padding: 1rem;
          }
        }
      `}</style>
    </div>
  )
}

export default AdminLayout