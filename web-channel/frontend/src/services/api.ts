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

class ApiClient {
  private baseUrl: string
  
  constructor() {
    this.baseUrl = config.apiEndpoint
  }
  
  private getAuthHeader(): HeadersInit {
    const token = localStorage.getItem('jwt_token')
    return token ? { 'Authorization': `Bearer ${token}` } : {}
  }
  
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
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
  
  // Binding endpoints
  async generateBindingCode(): Promise<{
    code: string
    expires_at: string
    expires_in: number
    message: string
  }> {
    return this.request('/binding/generate-code', { method: 'POST' })
  }
  
  async getBindingStatus(): Promise<{
    bound: boolean
    unified_user_id?: string
    telegram_bound?: boolean
    binding_status?: string
    created_at?: string
  }> {
    return this.request('/binding/status')
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
}

export const api = new ApiClient()