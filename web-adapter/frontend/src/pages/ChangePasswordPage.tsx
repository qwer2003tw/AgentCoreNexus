import { useState } from 'react'
import { useAuthStore } from '@/stores/authStore'
import { AlertCircle, CheckCircle, Loader2 } from 'lucide-react'

export default function ChangePasswordPage() {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [localError, setLocalError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  
  const { changePassword, isLoading, error, clearError, logout } = useAuthStore()
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    setLocalError(null)
    setSuccess(false)
    
    // Validate passwords match
    if (newPassword !== confirmPassword) {
      setLocalError('新密碼不一致')
      return
    }
    
    // Validate password strength
    if (newPassword.length < 8) {
      setLocalError('密碼至少需要 8 個字元')
      return
    }
    
    if (!/[A-Z]/.test(newPassword)) {
      setLocalError('密碼必須包含至少一個大寫字母')
      return
    }
    
    if (!/[a-z]/.test(newPassword)) {
      setLocalError('密碼必須包含至少一個小寫字母')
      return
    }
    
    if (!/[0-9]/.test(newPassword)) {
      setLocalError('密碼必須包含至少一個數字')
      return
    }
    
    try {
      await changePassword(oldPassword, newPassword)
      setSuccess(true)
      
      // Clear form
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
      
    } catch (err) {
      // Error handled by store
    }
  }
  
  const displayError = localError || error
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-dark-bg px-4">
      <div className="w-full max-w-md">
        {/* Title */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-dark-text mb-2">
            修改密碼
          </h1>
          <p className="text-dark-text-secondary">
            首次登入需要修改密碼
          </p>
        </div>
        
        {/* Card */}
        <div className="card">
          {/* Error message */}
          {displayError && (
            <div className="mb-4 p-3 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2 text-error">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span className="text-sm">{displayError}</span>
            </div>
          )}
          
          {/* Success message */}
          {success && (
            <div className="mb-4 p-3 bg-success/10 border border-success/20 rounded-lg flex items-start gap-2 text-success">
              <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span className="text-sm">密碼修改成功！</span>
            </div>
          )}
          
          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="oldPassword" className="block text-sm font-medium mb-2">
                臨時密碼
              </label>
              <input
                id="oldPassword"
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg input-field"
                placeholder="管理員提供的臨時密碼"
                required
                disabled={isLoading}
              />
            </div>
            
            <div>
              <label htmlFor="newPassword" className="block text-sm font-medium mb-2">
                新密碼
              </label>
              <input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg input-field"
                placeholder="至少 8 字元，含大小寫和數字"
                required
                disabled={isLoading}
              />
            </div>
            
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium mb-2">
                確認新密碼
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full px-3 py-2 rounded-lg input-field"
                placeholder="再次輸入新密碼"
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
                  處理中...
                </>
              ) : (
                '修改密碼'
              )}
            </button>
          </form>
          
          {/* Password requirements */}
          <div className="mt-4 p-3 bg-dark-bg rounded-lg">
            <p className="text-xs text-dark-text-secondary mb-2">密碼要求：</p>
            <ul className="text-xs text-dark-text-secondary space-y-1 ml-4 list-disc">
              <li>至少 8 個字元</li>
              <li>至少一個大寫字母</li>
              <li>至少一個小寫字母</li>
              <li>至少一個數字</li>
            </ul>
          </div>
          
          {/* Logout option */}
          <div className="mt-6 pt-6 border-t border-dark-border text-center">
            <button
              onClick={() => logout()}
              className="text-sm text-dark-text-secondary hover:text-dark-text transition-colors"
            >
              登出
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}