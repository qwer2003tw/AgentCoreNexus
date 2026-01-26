/**
 * ProtectedRoute - 管理員路由保護
 * 
 * 確保只有 admin 角色的用戶可以訪問管理員頁面
 */

import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
  requiredRole?: string
}

export function ProtectedRoute({ children, requiredRole = 'admin' }: ProtectedRouteProps) {
  const { user } = useAuthStore()
  
  // 檢查用戶是否有所需角色
  if (!user || user.role !== requiredRole) {
    // 重定向到主頁面（或顯示 403）
    return <Navigate to="/" replace />
  }
  
  return <>{children}</>
}

export default ProtectedRoute