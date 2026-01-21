import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Link2, Copy, CheckCircle, AlertCircle, Loader2, X } from 'lucide-react'

interface BindingDialogProps {
  isOpen: boolean
  onClose: () => void
}

export default function BindingDialog({ isOpen, onClose }: BindingDialogProps) {
  const [copied, setCopied] = useState(false)
  
  // Query binding status
  const { data: status, isLoading: statusLoading, refetch } = useQuery({
    queryKey: ['binding-status'],
    queryFn: () => api.getBindingStatus(),
    enabled: isOpen
  })
  
  // Generate binding code mutation
  const generateCode = useMutation({
    mutationFn: () => api.generateBindingCode(),
    onSuccess: () => {
      refetch()
    }
  })
  
  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  
  if (!isOpen) return null
  
  const isBound = status?.telegram_bound === true
  const bindingCode = (generateCode.data as any)?.code
  
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
            <div className="text-center py-6">
              <CheckCircle className="w-16 h-16 mx-auto mb-4 text-success" />
              <h3 className="text-lg font-semibold mb-2">已綁定</h3>
              <p className="text-sm text-dark-text-secondary">
                您的 Telegram 帳號已經與此 Web 帳號綁定
              </p>
              <p className="text-xs text-dark-text-secondary mt-4">
                綁定時間: {status?.created_at ? new Date(status.created_at).toLocaleString('zh-TW') : '未知'}
              </p>
            </div>
          ) : (
            // Not bound yet
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
              
              {!bindingCode ? (
                // Generate code button
                <button
                  onClick={() => generateCode.mutate()}
                  disabled={generateCode.isPending}
                  className="w-full btn-primary flex items-center justify-center gap-2"
                >
                  {generateCode.isPending ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      生成中...
                    </>
                  ) : (
                    <>
                      <Link2 className="w-4 h-4" />
                      生成綁定碼
                    </>
                  )}
                </button>
              ) : (
                // Show binding code
                <div>
                  <div className="bg-dark-bg border border-dark-border rounded-lg p-6 mb-4">
                    <p className="text-sm text-dark-text-secondary mb-3 text-center">
                      您的綁定碼（5 分鐘內有效）：
                    </p>
                    <div className="flex items-center justify-center gap-3">
                      <p className="text-4xl font-mono font-bold text-primary tracking-wider">
                        {bindingCode}
                      </p>
                      <button
                        onClick={() => handleCopy(bindingCode)}
                        className="p-2 hover:bg-dark-surface-hover rounded-lg transition-colors"
                        title="複製"
                      >
                        {copied ? (
                          <CheckCircle className="w-5 h-5 text-success" />
                        ) : (
                          <Copy className="w-5 h-5 text-dark-text-secondary" />
                        )}
                      </button>
                    </div>
                  </div>
                  
                  {/* Instructions */}
                  <div className="bg-primary/10 border border-primary/20 rounded-lg p-4">
                    <h4 className="text-sm font-semibold mb-2 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4" />
                      使用說明
                    </h4>
                    <ol className="text-sm text-dark-text-secondary space-y-2 ml-4 list-decimal">
                      <li>打開 Telegram 並找到 AgentCore Bot</li>
                      <li>發送指令：<code className="bg-dark-surface px-2 py-0.5 rounded">/bind {bindingCode}</code></li>
                      <li>等待綁定成功訊息</li>
                      <li>重新載入此頁面確認綁定狀態</li>
                    </ol>
                  </div>
                  
                  {/* Regenerate button */}
                  <button
                    onClick={() => generateCode.mutate()}
                    disabled={generateCode.isPending}
                    className="w-full mt-4 btn-secondary text-sm"
                  >
                    重新生成綁定碼
                  </button>
                </div>
              )}
              
              {/* Error */}
              {generateCode.error && (
                <div className="mt-4 p-3 bg-error/10 border border-error/20 rounded-lg flex items-start gap-2 text-error">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span className="text-sm">
                    {(generateCode.error as any).error || '生成綁定碼失敗'}
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