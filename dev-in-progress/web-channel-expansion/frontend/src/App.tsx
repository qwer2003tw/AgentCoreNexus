import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useChatStore } from '@/stores/chatStore'

// Pages (to be created)
import LoginPage from '@/pages/LoginPage'
import ChatPage from '@/pages/ChatPage'
import ChangePasswordPage from '@/pages/ChangePasswordPage'

function App() {
  const { token, user, loadUser } = useAuthStore()
  const { initialize: initializeChat } = useChatStore()
  
  useEffect(() => {
    // Load user info if token exists
    if (token && !user) {
      loadUser()
    }
  }, [token, user, loadUser])
  
  useEffect(() => {
    // Initialize chat store (WebSocket subscriptions)
    const cleanup = initializeChat()
    return cleanup
  }, [initializeChat])
  
  // Check if user needs to change password
  const requiresPasswordChange = user?.require_password_change === true
  
  return (
    <BrowserRouter>
      <Routes>
        {/* Public routes */}
        <Route 
          path="/login" 
          element={token && user ? <Navigate to="/" replace /> : <LoginPage />} 
        />
        
        {/* Protected routes */}
        {!token || !user ? (
          <Route path="*" element={<Navigate to="/login" replace />} />
        ) : requiresPasswordChange ? (
          <>
            <Route path="/change-password" element={<ChangePasswordPage />} />
            <Route path="*" element={<Navigate to="/change-password" replace />} />
          </>
        ) : (
          <>
            <Route path="/" element={<ChatPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </>
        )}
      </Routes>
    </BrowserRouter>
  )
}

export default App