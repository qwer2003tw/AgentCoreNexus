/**
 * REST API client service
 */

import { config } from '@/config/env'

export interface ApiError {
  error: string
  statusCode?: number
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  token: string
  user: {
    email: string
    role: string
    require_password_change: boolean
  }
}

export interface ChangePasswordRequest {
  old_password: string
  new_password: string
}

export interface User {
  email: string
  role: string
  require_password_change: boolean
  created_at?: string
}

export interface Attachment {
  id: string
  name: string
  size: number
  content_type: string
  key: string
}

class ApiClient {
  private baseUrl: string
  
  constructor() {
    this.baseUrl = config.apiEndpoint
  }

  private mockState = {
    token: 'mock-token',
    user: {
      email: 'test1@test.com',
      role: 'user',
      require_password_change: false
    },
    conversations: [] as Array<{
      conversation_id: string
      title: string
      created_at: string
      last_message_time: string
      message_count: number
      is_pinned: boolean
      is_deleted?: boolean
    }>,
    messages: {} as Record<string, any[]>
  }
  
  private getAuthHeader(): HeadersInit {
    const token = localStorage.getItem('jwt_token')
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }
  
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    if (config.features.mockApi) {
      return this.mockRequest<T>(endpoint, options)
    }

    const url = `${this.baseUrl}${endpoint}`
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeader(),
        ...options.headers
      }
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      throw {
        error: data.error || 'Request failed',
        statusCode: response.status
      } as ApiError
    }
    
    return data
  }

  private async mockRequest<T>(endpoint: string, options: RequestInit): Promise<T> {
    const method = (options.method || 'GET').toUpperCase()
    const now = new Date().toISOString()
    this.loadMockState()

    if (endpoint === '/auth/login' && method === 'POST') {
      const body = JSON.parse(options.body as string)
      if (body.password !== 'Test123!') {
        throw { error: 'Invalid credentials', statusCode: 401 } as ApiError
      }
      this.mockState.user.email = body.email
      return {
        token: this.mockState.token,
        user: this.mockState.user
      } as T
    }

    if (endpoint === '/auth/me' && method === 'GET') {
      return this.mockState.user as T
    }

    if (endpoint === '/auth/logout' && method === 'POST') {
      return { message: 'Logged out' } as T
    }

    if (endpoint.startsWith('/conversations') && method === 'GET') {
      const conversationIdMatch = endpoint.match(/\/conversations\/([^/]+)\/messages/)
      if (conversationIdMatch) {
        const conversationId = conversationIdMatch[1]
        const messages = this.mockState.messages[conversationId] || []
        return { messages, count: messages.length } as T
      }

      const activeConversations = this.mockState.conversations.filter(c => !c.is_deleted)
      return {
        conversations: {
          pinned: activeConversations.filter(c => c.is_pinned),
          recent: activeConversations.filter(c => !c.is_pinned)
        },
        count: activeConversations.length
      } as T
    }

    if (endpoint === '/conversations' && method === 'POST') {
      const body = JSON.parse(options.body as string)
      const conversation = {
        conversation_id: `conv-${Date.now()}`,
        title: body.title || '新對話',
        created_at: now,
        last_message_time: now,
        message_count: 0,
        is_pinned: false
      }
      this.mockState.conversations.unshift(conversation)
      this.saveMockState()
      return { ...conversation, message: 'Created' } as T
    }

    const updateMatch = endpoint.match(/\/conversations\/([^/]+)$/)
    if (updateMatch && method === 'PUT') {
      const conversationId = updateMatch[1]
      const updates = JSON.parse(options.body as string)
      this.mockState.conversations = this.mockState.conversations.map(conv =>
        conv.conversation_id === conversationId
          ? { ...conv, ...updates, last_message_time: now }
          : conv
      )
      this.saveMockState()
      return { message: 'Updated' } as T
    }

    if (updateMatch && method === 'DELETE') {
      const conversationId = updateMatch[1]
      this.mockState.conversations = this.mockState.conversations.map(conv =>
        conv.conversation_id === conversationId ? { ...conv, is_deleted: true } : conv
      )
      this.saveMockState()
      return { message: 'Deleted' } as T
    }

    if (endpoint === '/attachments/presign' && method === 'POST') {
      const body = JSON.parse(options.body as string)
      const response = {
        upload_url: 'https://example.com/mock-upload',
        attachment: {
          id: `att-${Date.now()}`,
          name: body.filename,
          size: body.size,
          content_type: body.content_type,
          key: `attachments/mock/${Date.now()}/${body.filename}`
        }
      } as T
      return response
    }

    if (endpoint === '/attachments/download' && method === 'POST') {
      return { download_url: 'https://example.com/mock-download' } as T
    }

    this.saveMockState()
    return {} as T
  }

  private loadMockState() {
    try {
      const stored = localStorage.getItem('mock_api_state')
      if (stored) {
        this.mockState = JSON.parse(stored)
      }
    } catch {
      // ignore
    }
  }

  private saveMockState() {
    try {
      localStorage.setItem('mock_api_state', JSON.stringify(this.mockState))
    } catch {
      // ignore
    }
  }
  
  // Auth endpoints
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    return this.request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials)
    })
  }
  
  async logout(): Promise<void> {
    await this.request('/auth/logout', { method: 'POST' })
  }
  
  async changePassword(data: ChangePasswordRequest): Promise<{ message: string }> {
    return this.request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }
  
  async getCurrentUser(): Promise<User> {
    return this.request<User>('/auth/me')
  }
  
  // History endpoints
  async getHistory(params?: {
    limit?: number
    last_key?: string
    channel?: string
  }): Promise<any> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.set('limit', params.limit.toString())
    if (params?.last_key) queryParams.set('last_key', params.last_key)
    if (params?.channel) queryParams.set('channel', params.channel)
    
    const query = queryParams.toString()
    return this.request(`/history${query ? '?' + query : ''}`)
  }
  
  async exportHistory(format: 'json' | 'markdown', channel?: string): Promise<any> {
    const queryParams = new URLSearchParams({ format })
    if (channel) queryParams.set('channel', channel)
    
    return this.request(`/history/export?${queryParams}`)
  }
  
  async getHistoryStats(): Promise<any> {
    return this.request('/history/stats')
  }
  
  // Binding endpoints - Phase 2
  async verifyBindingCode(code: string): Promise<{
    success: boolean
    unified_conversation_id: string
    telegram_user_id: string
    message: string
  }> {
    return this.request('/binding/verify', {
      method: 'POST',
      body: JSON.stringify({ code })
    })
  }
  
  async getBindingStatus(): Promise<{
    bound: boolean
    identity_id?: string
    unified_conversation_id?: string
    telegram_bound?: boolean
    bound_identities?: Array<{
      platform: string
      user_id: string
      identity_id: string
      bound_at: number
    }>
    created_at?: number
    message?: string
  }> {
    return this.request('/binding/status')
  }
  
  async unbindIdentity(): Promise<{
    success: boolean
    message: string
  }> {
    return this.request('/binding/unbind', { method: 'DELETE' })
  }
  
  // Conversations endpoints
  async getConversations(params?: {
    limit?: number
    last_key?: string
    include_deleted?: boolean
  }): Promise<{
    conversations: {
      pinned: any[]
      recent: any[]
    }
    count: number
    last_key?: string
  }> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.set('limit', params.limit.toString())
    if (params?.last_key) queryParams.set('last_key', params.last_key)
    if (params?.include_deleted) queryParams.set('include_deleted', 'true')
    
    const query = queryParams.toString()
    return this.request(`/conversations${query ? '?' + query : ''}`)
  }
  
  async createConversation(title: string = 'New Chat'): Promise<{
    conversation_id: string
    title: string
    created_at: string
    message: string
  }> {
    return this.request('/conversations', {
      method: 'POST',
      body: JSON.stringify({ title })
    })
  }
  
  async updateConversation(
    conversationId: string,
    updates: {
      title?: string
      is_pinned?: boolean
    }
  ): Promise<{ message: string }> {
    return this.request(`/conversations/${conversationId}`, {
      method: 'PUT',
      body: JSON.stringify(updates)
    })
  }
  
  async deleteConversation(conversationId: string): Promise<{ message: string }> {
    return this.request(`/conversations/${conversationId}`, {
      method: 'DELETE'
    })
  }
  
  async getConversationMessages(
    conversationId: string,
    params?: {
      limit?: number
      last_key?: string
    }
  ): Promise<{
    messages: any[]
    count: number
    last_key?: string
  }> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.set('limit', params.limit.toString())
    if (params?.last_key) queryParams.set('last_key', params.last_key)
    
    const query = queryParams.toString()
    return this.request(`/conversations/${conversationId}/messages${query ? '?' + query : ''}`)
  }

  // Attachments endpoints
  async createAttachmentUpload(data: {
    filename: string
    content_type: string
    size: number
  }): Promise<{ upload_url: string; attachment: Attachment }> {
    return this.request('/attachments/presign', {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }

  async getAttachmentDownloadUrl(key: string): Promise<{ download_url: string }> {
    return this.request('/attachments/download', {
      method: 'POST',
      body: JSON.stringify({ key })
    })
  }
  
  // Admin endpoints
  async createUser(email: string, role: 'user' | 'admin' = 'user'): Promise<{
    email: string
    role: string
    temporary_password: string
    require_password_change: boolean
    message: string
  }> {
    return this.request('/admin/users', {
      method: 'POST',
      body: JSON.stringify({ email, role })
    })
  }
  
  async listUsers(params?: { limit?: number; last_key?: string }): Promise<{
    users: User[]
    count: number
    last_key?: string
  }> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.set('limit', params.limit.toString())
    if (params?.last_key) queryParams.set('last_key', params.last_key)
    
    const query = queryParams.toString()
    return this.request(`/admin/users${query ? '?' + query : ''}`)
  }
  
  async resetUserPassword(email: string, newPassword?: string): Promise<{
    email: string
    temporary_password: string
    message: string
  }> {
    return this.request(`/admin/users/${encodeURIComponent(email)}/password`, {
      method: 'PUT',
      body: JSON.stringify({ new_password: newPassword })
    })
  }
  
  async updateUserRole(email: string, role: 'user' | 'admin'): Promise<{
    email: string
    role: string
    message: string
  }> {
    return this.request(`/admin/users/${encodeURIComponent(email)}/role`, {
      method: 'PUT',
      body: JSON.stringify({ role })
    })
  }
  
  // Admin conversation management endpoints - Day 5-6
  async listAllConversations(params?: {
    limit?: number
    next_token?: string
    channel?: string
    start_time?: string
    end_time?: string
  }): Promise<{
    conversations: Array<{
      conversation_id: string
      user_id: string
      channel: string
      timestamp: string
      message_count?: number
      last_message?: string
    }>
    count: number
    next_token?: string
  }> {
    const queryParams = new URLSearchParams()
    if (params?.limit) queryParams.set('limit', params.limit.toString())
    if (params?.next_token) queryParams.set('next_token', params.next_token)
    if (params?.channel) queryParams.set('channel', params.channel)
    if (params?.start_time) queryParams.set('start_time', params.start_time)
    if (params?.end_time) queryParams.set('end_time', params.end_time)
    
    const query = queryParams.toString()
    return this.request(`/admin/conversations${query ? '?' + query : ''}`)
  }
  
  async getConversationDetail(conversationId: string): Promise<{
    conversation_id: string
    user_id: string
    channel: string
    messages: Array<{
      role: 'user' | 'assistant'
      content: string
      timestamp?: string
      attachments?: Array<{
        type: string
        url?: string
        file_name?: string
        content_type?: string
      }>
    }>
    created_at?: string
    updated_at?: string
    statistics?: {
      message_count: number
      attachments: {
        images: number
        files: number
        total: number
      }
    }
  }> {
    return this.request(`/admin/conversations/${conversationId}`)
  }
  
  async generateConversationSummary(conversationId: string): Promise<{
    summary: string
    generated_at: string
  }> {
    return this.request(`/admin/conversations/${conversationId}/summary`, {
      method: 'POST'
    })
  }
}

export const api = new ApiClient()
