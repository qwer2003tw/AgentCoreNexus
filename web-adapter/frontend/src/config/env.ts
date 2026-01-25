/**
 * Environment configuration
 * Update these values after deploying the backend
 */

export const config = {
  // API endpoints (will be replaced with actual values after deployment)
  apiEndpoint: (import.meta as any).env?.VITE_API_ENDPOINT || 'https://jooap0xv8l.execute-api.us-west-2.amazonaws.com/prod',
  wsEndpoint: (import.meta as any).env?.VITE_WS_ENDPOINT || 'wss://356rrmw4pg.execute-api.us-west-2.amazonaws.com/prod',
  
  // App settings
  appName: 'AgentCore Chat',
  maxMessageLength: 4000,
  historyPageSize: 50,
  tokenExpiryDays: 7,
  maxAttachmentSizeBytes: 25 * 1024 * 1024,
  
  // WebSocket settings
  wsReconnectInterval: 1000, // Start with 1 second
  wsMaxReconnectInterval: 30000, // Max 30 seconds
  wsReconnectMultiplier: 2, // Exponential backoff
  
  // Features
  features: {
    export: true,
    binding: true,
    darkMode: true,
    mockApi: (import.meta as any).env?.VITE_E2E_MOCK === 'true',
    mockWebSocket: (import.meta as any).env?.VITE_E2E_MOCK === 'true'
  }
}

// Helper to check if environment is configured
export const isConfigured = () => {
  return !config.apiEndpoint.includes('YOUR_API_ID') && 
         !config.wsEndpoint.includes('YOUR_WS_API_ID')
}
