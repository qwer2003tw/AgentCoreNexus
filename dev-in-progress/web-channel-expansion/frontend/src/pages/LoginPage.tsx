import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { AlertCircle, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const { login, isLoading, error, clearError } = useAuthStore()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    
    try {
      await login(email, password)
      // Navigation handled by App.tsx
    } catch (err) {
      // Error handled by store
    }
  }
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg px-4">
      <div className="w-full max-w-md">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-dark-text mb-2">
            AgentCore Chat
          </h1>
          <p className="text-dark-text-secondary">
            AI 助理 - 網頁版
          </p>
        </div>
        
        {/* Login Card */}
        <div className="card">
          <h2 className="text-2xl font-semibold mb-6">登入</h2>
          
          {/* Error message */}
          {error && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2 text-error">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span className="text-sm">{error}</span>
            </div>
          )}
          
          {/* Login form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-2">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 rounded-lg input-field"
                placeholder="your@email.com"
                required
                disabled={isLoading}
              />
            </div>
            
            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-2">
                密碼
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg input-field"
                placeholder="••••••••"
                required
                disabled={isLoading}
              />
            </div>
            
            <button
              type="submit"
              className="w-full btn-primary flex items-center justify-center gap-2"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  登入中...
                </>
              ) : (
                '登入'
              )}
            </button>
          </form>
          
          {/* Info */}
          <div className="mt-6 pt-6 border-t border-dark-border">
            <p className="text-sm text-dark-text-secondary text-center">
              需要帳號？請聯絡管理員
            </p>
          </div>
        </div>
        
        {/* Footer */}
        <div className="mt-8 text-center text-sm text-dark-text-secondary">
          <p>AgentCore Nexus © 2026</p>
        </div>
      </div>
    </div>
  )
}