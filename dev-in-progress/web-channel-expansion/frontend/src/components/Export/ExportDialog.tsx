import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { api } from '@/services/api'
import { Download, FileText, FileJson, Loader2, CheckCircle, AlertCircle, X } from 'lucide-react'

interface ExportDialogProps {
  isOpen: boolean
  onClose: () => void
}

export default function ExportDialog({ isOpen, onClose }: ExportDialogProps) {
  const [format, setFormat] = useState<'json' | 'markdown'>('markdown')
  const [channelFilter, setChannelFilter] = useState<'all' | 'web' | 'telegram'>('all')
  
  const exportMutation = useMutation({
    mutationFn: () => api.exportHistory(
      format,
      channelFilter === 'all' ? undefined : channelFilter
    ),
    onSuccess: (data) => {
      // Download the exported data
      const blob = new Blob([data.data], { 
        type: format === 'json' ? 'application/json' : 'text/markdown'
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `agentcore-history-${new Date().toISOString().split('T')[0]}.${format === 'json' ? 'json' : 'md'}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      
      // Close dialog after 2 seconds
      setTimeout(() => {
        onClose()
        exportMutation.reset()
      }, 2000)
    }
  })
  
  if (!isOpen) return null
  
  const handleExport = () => {
    exportMutation.mutate()
  }
  
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface rounded-lg shadow-xl max-w-md w-full">
        {/* Header */}
        <div className="p-6 border-b border-dark-border flex items-center justify-between">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Download className="w-5 h-5" />
            導出對話記錄
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-dark-surface-hover rounded transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Format selection */}
          <div>
            <label className="block text-sm font-medium mb-3">
              導出格式
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setFormat('markdown')}
                className={`p-4 rounded-lg border transition-colors ${
                  format === 'markdown'
                    ? 'bg-primary/10 border-primary text-primary'
                    : 'bg-dark-bg border-dark-border text-dark-text-secondary hover:border-primary/50'
                }`}
              >
                <FileText className="w-6 h-6 mx-auto mb-2" />
                <p className="text-sm font-medium">Markdown</p>
                <p className="text-xs opacity-75 mt-1">易讀格式</p>
              </button>
              
              <button
                onClick={() => setFormat('json')}
                className={`p-4 rounded-lg border transition-colors ${
                  format === 'json'
                    ? 'bg-primary/10 border-primary text-primary'
                    : 'bg-dark-bg border-dark-border text-dark-text-secondary hover:border-primary/50'
                }`}
              >
                <FileJson className="w-6 h-6 mx-auto mb-2" />
                <p className="text-sm font-medium">JSON</p>
                <p className="text-xs opacity-75 mt-1">結構化數據</p>
              </button>
            </div>
          </div>
          
          {/* Channel filter */}
          <div>
            <label className="block text-sm font-medium mb-3">
              包含對話
            </label>
            <div className="flex gap-2">
              <button
                onClick={() => setChannelFilter('all')}
                className={`flex-1 px-3 py-2 rounded-lg text-sm transition-colors ${
                  channelFilter === 'all'
                    ? 'bg-primary text-white'
                    : 'bg-dark-bg text-dark-text-secondary hover:bg-dark-surface-hover'
                }`}
              >
                全部
              </button>
              <button
                onClick={() => setChannelFilter('web')}
                className={`flex-1 px-3 py-2 rounded-lg text-sm transition-colors ${
                  channelFilter === 'web'
                    ? 'bg-primary text-white'
                    : 'bg-dark-bg text-dark-text-secondary hover:bg-dark-surface-hover'
                }`}
              >
                僅 Web
              </button>
              <button
                onClick={() => setChannelFilter('telegram')}
                className={`flex-1 px-3 py-2 rounded-lg text-sm transition-colors ${
                  channelFilter === 'telegram'
                    ? 'bg-primary text-white'
                    : 'bg-dark-bg text-dark-text-secondary hover:bg-dark-surface-hover'
                }`}
              >
                僅 Telegram
              </button>
            </div>
          </div>
          
          {/* Info */}
          <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
            <p className="text-xs text-dark-text-secondary">
              ℹ️ 導出將包含最近 90 天內的所有對話記錄
            </p>
          </div>
          
          {/* Success message */}
          {exportMutation.isSuccess && (
            <div className="bg-success/10 border border-success/20 rounded-lg p-4 flex items-start gap-2 text-success">
              <CheckCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium">導出成功！</p>
                <p className="text-xs mt-1 opacity-75">
                  檔案已下載到您的裝置
                </p>
              </div>
            </div>
          )}
          
          {/* Error message */}
          {exportMutation.error && (
            <div className="bg-error/10 border border-error/20 rounded-lg p-4 flex items-start gap-2 text-error">
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <span className="text-sm">
                {(exportMutation.error as any).error || '導出失敗'}
              </span>
            </div>
          )}
        </div>
        
        {/* Footer */}
        <div className="p-6 border-t border-dark-border flex justify-end gap-3">
          <button
            onClick={onClose}
            className="btn-secondary"
            disabled={exportMutation.isPending}
          >
            取消
          </button>
          <button
            onClick={handleExport}
            disabled={exportMutation.isPending || exportMutation.isSuccess}
            className="btn-primary flex items-center gap-2"
          >
            {exportMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                導出中...
              </>
            ) : exportMutation.isSuccess ? (
              <>
                <CheckCircle className="w-4 h-4" />
                已完成
              </>
            ) : (
              <>
                <Download className="w-4 h-4" />
                導出
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}