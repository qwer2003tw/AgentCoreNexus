import { describe, it, expect, beforeEach, vi } from 'vitest'
import { api } from '../api'

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(localStorage.getItem).mockReturnValue(null)
    vi.mocked(global.fetch).mockReset()
  })
  
  describe('login', () => {
    it('should call login endpoint with credentials', async () => {
      const mockResponse = {
        token: 'test-token',
        user: { email: 'test@example.com', role: 'user', require_password_change: false }
      }
      
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)
      
      const result = await api.login({
        email: 'test@example.com',
        password: 'password123'
      })
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/auth/login'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({ email: 'test@example.com', password: 'password123' })
        })
      )
      
      expect(result).toEqual(mockResponse)
    })
    
    it('should handle login error', async () => {
      const mockError = { error: 'Invalid credentials' }
      
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => mockError,
      } as Response)
      
      await expect(api.login({ email: 'test@example.com', password: 'wrong' }))
        .rejects
        .toEqual({ error: 'Invalid credentials', statusCode: 401 })
    })
  })
  
  describe('getConversations', () => {
    it('should fetch conversations with auth header', async () => {
      vi.mocked(localStorage.getItem).mockReturnValue('test-token')
      
      const mockResponse = {
        conversations: { pinned: [], recent: [] },
        count: 0
      }
      
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)
      
      const result = await api.getConversations()
      
      // Check Authorization header included
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/conversations'),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Authorization': 'Bearer test-token'
          })
        })
      )
      
      expect(result).toEqual(mockResponse)
    })
  })
  
  describe('createConversation', () => {
    it('should create conversation with title', async () => {
      vi.mocked(localStorage.getItem).mockReturnValue('test-token')
      
      const mockResponse = {
        conversation_id: 'conv-123',
        title: 'New Chat',
        created_at: '2026-01-12T00:00:00Z',
        message: 'Created'
      }
      
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)
      
      const result = await api.createConversation('New Chat')
      
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/conversations'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ title: 'New Chat' })
        })
      )
      
      expect(result.conversation_id).toBe('conv-123')
    })
  })

  describe('attachments', () => {
    it('should request presigned upload url', async () => {
      vi.mocked(localStorage.getItem).mockReturnValue('test-token')

      const mockResponse = {
        upload_url: 'https://s3.upload/test',
        attachment: {
          id: 'att-1',
          name: 'report.pdf',
          size: 1024,
          content_type: 'application/pdf',
          key: 'attachments/user/att-1/report.pdf'
        }
      }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await api.createAttachmentUpload({
        filename: 'report.pdf',
        content_type: 'application/pdf',
        size: 1024
      })

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/attachments/presign'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            filename: 'report.pdf',
            content_type: 'application/pdf',
            size: 1024
          })
        })
      )

      expect(result).toEqual(mockResponse)
    })

    it('should request presigned download url', async () => {
      const mockResponse = { download_url: 'https://s3.download/test' }

      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await api.getAttachmentDownloadUrl('attachments/user/att-1/report.pdf')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/attachments/download'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ key: 'attachments/user/att-1/report.pdf' })
        })
      )

      expect(result).toEqual(mockResponse)
    })
  })
  
  describe('error handling', () => {
    it('should handle 401 unauthorized', async () => {
      vi.mocked(global.fetch).mockResolvedValueOnce({
        ok: false,
        status: 401,
        json: async () => ({ error: 'Unauthorized' }),
      } as Response)
      
      await expect(api.getCurrentUser())
        .rejects
        .toEqual({ error: 'Unauthorized', statusCode: 401 })
    })
    
    it('should handle network errors', async () => {
      vi.mocked(global.fetch).mockRejectedValueOnce(new Error('Network error'))
      
      await expect(api.login({ email: 'test@example.com', password: 'test' }))
        .rejects
        .toThrow('Network error')
    })
  })
})
