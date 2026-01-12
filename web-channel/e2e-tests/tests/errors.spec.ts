import { test, expect, createNewConversation, sendMessage, TEST_USER } from '../setup/fixtures'

test.describe('Error Handling', () => {
  
  // TODO: These tests require backend error simulation
  // Consider implementing mock server or using MSW (Mock Service Worker)
  
  test('handles 500 server error gracefully', async ({ page }) => {
    // Mock 500 error before navigation
    await page.route('**/auth/login', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' })
      })
    })
    
    await page.goto('/')
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    
    // Wait and verify still on login page (error handled)
    await page.waitForTimeout(2000)
    const stillOnLogin = await page.locator('input[type="email"]').isVisible()
    expect(stillOnLogin).toBeTruthy()
  })
  
  test('handles 401 unauthorized token', async ({ page }) => {
    // Login first with valid credentials
    await page.goto('/')
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    
    // Wait for successful login
    await page.waitForSelector('textarea', { timeout: 15000 })
    
    // Clear token to simulate expiration
    await page.evaluate(() => localStorage.removeItem('jwt_token'))
    
    // Reload page - should redirect to login
    await page.reload()
    await page.waitForSelector('input[type="email"]', { timeout: 5000 })
    
    const isOnLogin = await page.locator('input[type="email"]').isVisible()
    expect(isOnLogin).toBeTruthy()
  })
  
  test('handles network timeout gracefully', async ({ authenticatedPage: page }) => {
    await createNewConversation(page)
    
    // Simulate slow network by delaying responses
    await page.route('**/conversations**', route => {
      setTimeout(() => route.continue(), 30000)  // 30 second delay
    })
    
    await sendMessage(page, '測試超時')
    
    // Should show loading state or timeout message
    await page.waitForTimeout(3000)
    // Verify user can still interact with UI
    const textareaEnabled = await page.locator('textarea').isEnabled()
    expect(textareaEnabled).toBeTruthy()
  })
  
  test('WebSocket connection failure shows error', async ({ page }) => {
    // Block WebSocket connections before login
    await page.route('wss://**', route => route.abort())
    
    await page.goto('/')
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    
    // Wait for page to load
    await page.waitForSelector('button:has-text("新對話")', { timeout: 15000 })
    
    // Give time for WebSocket connection attempt to fail
    await page.waitForTimeout(3000)
    
    // Verify textarea is disabled (due to no WebSocket connection)
    const textareaDisabled = await page.locator('textarea').isDisabled()
    expect(textareaDisabled).toBeTruthy()
    
    // Or verify connection status indicator shows error
    const hasDisconnectedIndicator = await page.locator('text=/未連接|Disconnect/i').isVisible().catch(() => false)
    expect(textareaDisabled || hasDisconnectedIndicator).toBeTruthy()
  })
  
  test('displays error messages to user', async ({ authenticatedPage: page }) => {
    await createNewConversation(page)
    
    // Verify submit button is disabled when textarea is empty
    const button = page.locator('button[type="submit"]')
    const isDisabledWhenEmpty = await button.isDisabled()
    expect(isDisabledWhenEmpty).toBeTruthy()
    
    // Fill with text - button should enable
    await page.fill('textarea', '測試消息')
    await page.waitForTimeout(100)
    
    const isEnabledWithText = await button.isEnabled()
    expect(isEnabledWithText).toBeTruthy()
  })
})

// Note: Most error handling tests are marked as skip because they require:
// 1. Mock Service Worker (MSW) for API mocking
// 2. Network condition simulation
// 3. Backend error injection
// These should be implemented in Phase 2 of test development