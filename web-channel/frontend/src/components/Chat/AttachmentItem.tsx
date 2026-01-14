import { useState } from 'react'
import { Download, FileText, Image as ImageIcon, Loader2, Eye } from 'lucide-react'
import { api } from '@/services/api'
import type { Attachment } from '@/stores/chatStore'

interface AttachmentItemProps {
  attachment: Attachment
}

function formatFileSize(size: number): string {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  if (size < 1024 * 1024 * 1024) return `${(size / (1024 * 1024)).toFixed(1)} MB`
  return `${(size / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

export default function AttachmentItem({ attachment }: AttachmentItemProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const isImage = attachment.content_type.startsWith('image/')

  const handleDownload = async () => {
    try {
      setIsLoading(true)
      const response = await api.getAttachmentDownloadUrl(attachment.key)
      window.open(response.download_url, '_blank', 'noopener')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePreview = async () => {
    if (previewUrl) {
      window.open(previewUrl, '_blank', 'noopener')
      return
    }

    try {
      setIsLoading(true)
      const response = await api.getAttachmentDownloadUrl(attachment.key)
      setPreviewUrl(response.download_url)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex items-center gap-3 rounded-lg border border-dark-border bg-dark-surface/70 px-3 py-2">
      <div className="flex h-9 w-9 items-center justify-center rounded-md bg-dark-bg">
        {isImage ? (
          <ImageIcon className="h-5 w-5 text-brand-400" />
        ) : (
          <FileText className="h-5 w-5 text-brand-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-dark-text truncate">{attachment.name}</p>
        <p className="text-xs text-dark-text-secondary">{formatFileSize(attachment.size)}</p>
        {previewUrl && isImage && (
          <img
            src={previewUrl}
            alt={attachment.name}
            className="mt-2 max-h-40 rounded-md border border-dark-border object-cover"
          />
        )}
      </div>
      <div className="flex items-center gap-2">
        {isImage && (
          <button
            type="button"
            className="btn-secondary px-2 py-1 text-xs"
            onClick={handlePreview}
            disabled={isLoading}
          >
            {isLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Eye className="h-3 w-3" />}
          </button>
        )}
        <button
          type="button"
          className="btn-primary px-2 py-1 text-xs"
          onClick={handleDownload}
          disabled={isLoading}
        >
          {isLoading ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
        </button>
      </div>
    </div>
  )
}
