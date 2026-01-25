import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Link2, CheckCircle, AlertCircle, Loader2, X } from 'lucide-react'

interface BindingDialogProps {
  isOpen: boolean
  onClose: () => void
}

export default function BindingDialog({ isOpen, onClose }: BindingDialogProps) {
  const [code, setCode] = useState('')
  
  // Query binding status
  const { data: status, isLoading: statusLoading, refetch } = useQuery({
    queryKey: ['binding-status'],
    queryFn: () => api.getBindingStatus(),
    enabled: isOpen
  })
  
  // Verify binding code mutation
  const verifyCode = useMutation({
    mutationFn: (code: string) => api.verifyBindingCode(code),
    onSuccess: () => {
      setCode('')
      refetch()
    }
  })
  
  // Unbind mutation
  const unbind = useMutation({
    mutationFn: () => api.unbindIdentity(),
    onSuccess: () => {
      refetch()
    }
  })
  
  const handleCodeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6)
    setCode(value)
  }
  
  const handleVerify = () => {
    if (code.length === 6) {
      verifyCode.mutate(code)
    }
  }
  
  if (!isOpen) return null
  
  const isBound = status?.bound === true
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Link2 className="w-5 h-5" />
            綁定 Telegram 帳號
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-dark-surface-hover rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6">
          {statusLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-primary" />
            </div>
          ) : isBound ? (
            // Already bound
            <div>
              <div className="text-center py-6">
                <CheckCircle className="w-16 h-16 mx-auto mb-4 text-success" />
                <h3 className="text-lg font-semibold mb-2">已綁定</h3>
                <p className="text-sm text-dark-text-secondary mb-4">
                  您的 Telegram 帳號已經與此 Web 帳號綁定
                </p>
              </div>
              
              {/* Bound identities */}
              {status?.bound_identities && status.bound_identities.length > 0 && (
                <div className="bg-dark-bg border border-dark-border rounded-lg p-4 mb-4">
                  <p className="text-sm font-semibold mb-2">已綁定的身份：</p>
                  <div className="space-y-2">
                    {status.bound_identities.map((identity, idx) => (
                      <div key={idx} className="text-sm flex items-center gap-2">
                        <span className="text-dark-text-secondary">
                          {identity.platform === 'telegram' ? '📱' : '🖥️'}
                        </span>
                        <span>{identity.platform}: {identity.user_id}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Unified conversation ID */}
              {status?.unified_conversation_id && (
                <div className="text-xs text-dark-text-secondary text-center mb-4">
                  統一對話 ID: {status.unified_conversation_id}
                </div>
              )}
              
              {/* Unbind button */}
              <button
                onClick={() => {
                  if (confirm('確定要解除綁定嗎？\n\n對話歷史會保留，但各通道將恢復獨立。')) {
                    unbind.mutate()
                  }
                }}
                disabled={unbind.isPending}
                className="w-full btn-secondary text-error flex items-center justify-center gap-2"
              >
                {unbind.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    解除中...
                  </>
                ) : (
                  '解除綁定'
                )}
              </button>
            </div>
          ) : (
            // Not bound yet - Input code mode
            <div>
              <p className="text-sm text-dark-text-secondary mb-4">
                綁定後，您可以在 Web 和 Telegram 之間：
              </p>
              <ul className="text-sm text-dark-text-secondary space-y-2 mb-6 ml-4 list-disc">
                <li>共享對話記錄</li>
                <li>共享 AI 記憶</li>
                <li>在任一平台查看完整歷史</li>
                <li>無縫切換使用體驗</li>
              </ul>
              
              {/* Instructions */}
              <div className="bg-primary/10 border border-primary/20 rounded-lg p-4 mb-4">
                <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                  <AlertCircle className="w-4 h-4" />
                  綁定步驟
                </h4>
                <ol className="text-sm text-dark-text-secondary space-y-2 ml-4 list-decimal">
                  <li>在 Telegram 與 Bot 的對話中</li>
                  <li>發送指令：<code className="bg-dark-surface px-2 py-0.5 rounded">/bind</code></li>
                  <li>Bot 會回覆 6 位數字綁定碼</li>
                  <li>在下方輸入該綁定碼</li>
                </ol>
              </div>
              
              {/* Input code */}
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    輸入綁定碼
                  </label>
                  <input
                    type="text"
                    value={code}
                    onChange={handleCodeChange}
                    placeholder="6 位數字"
                    maxLength={6}
                    className="w-full px-4 py-3 bg-dark-bg border border-dark-border rounded-lg text-center text-2xl font-mono tracking-widest focus:outline-none focus:ring-2 focus:ring-primary"
                    disabled={verifyCode.isPending}
                  />
                  <p className="text-xs text-dark-text-secondary mt-1 text-center">
                    綁定碼有效期 10 分鐘
                  </p>
                </div>
                
                <button
                  onClick={handleVerify}
                  disabled={code.length !== 6 || verifyCode.isPending}
                  className="w-full btn-primary flex items-center justify-center gap-2"
                >
                  {verifyCode.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      驗證中...
                    </>
                  ) : (
                    <>
                      <Link2 className="w-4 h-4" />
                      驗證並綁定
                    </>
                  )}
                </button>
              </div>
              
              {/* Success message */}
              {verifyCode.isSuccess && (
                <div className="mt-4 p-3 bg-success/10 border border-success/20 rounded-lg flex items-start gap-2 text-success">
                  <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span className="text-sm">
                    綁定成功！您的 Telegram 和 Web 帳號已連結。
                  </span>
                </div>
              )}
              
              {/* Error message */}
              {verifyCode.error && (
                <div className="mt-4 p-3 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2 text-error">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span className="text-sm">
                    {(verifyCode.error as any).error || '驗證綁定碼失敗'}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-6 border-t border-dark-border flex justify-end gap-3">
          <button
            onClick={onClose}
            className="btn-secondary"
          >
            關閉
          </button>
          {isBound && (
            <button
              onClick={() => refetch()}
              className="btn-primary"
            >
              重新檢查狀態
            </button>
          )}
        </div>
      </div>
    </div>
  )
}