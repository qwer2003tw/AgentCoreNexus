import { test, expect, TEST_USER } from '../setup/fixtures'

test.describe('Authentication', () => {
  
  test('can login with valid credentials', async ({ page }) => {
    await page.goto('/')
    
    // Fill login form
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    
    // ✅ Wait for chat page to load - verify by checking for "新對話" button
    await page.waitForSelector('button:has-text("新對話")', { timeout: 10000 })
    
    // ✅ Verify logged in - check for logout button (simplest unique identifier)
    const logoutButton = await page.locator('button:has-text("登出")').isVisible()
    expect(logoutButton).toBeTruthy()
    
    // Note: WebSocket connection may take time, checking it is covered by dedicated test
  })
  
  test('cannot login with invalid credentials', async ({ page }) => {
    await page.goto('/')
    
    // Fill with wrong password
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', 'WrongPassword123!')
    await page.click('button[type="submit"]')
    
    // Should still be on login page
    await page.waitForTimeout(2000)
    const isStillOnLogin = await page.locator('input[type="email"]').isVisible()
    expect(isStillOnLogin).toBeTruthy()
  })
  
  test('can logout', async ({ authenticatedPage: page }) => {
    // Click logout button
    await page.click('button:has-text("登出")')
    await page.waitForTimeout(500)
    
    // Confirm logout
    page.on('dialog', dialog => dialog.accept())
    await page.click('button:has-text("登出")')
    
    // Wait for login page
    await page.waitForSelector('input[type="email"]', { timeout: 5000 })
    
    // Verify on login page
    const isOnLogin = await page.locator('input[type="email"]').isVisible()
    expect(isOnLogin).toBeTruthy()
  })
  
  test('session persists after page reload', async ({ authenticatedPage: page }) => {
    // Reload page
    await page.reload()
    
    // Wait for page to load
    await page.waitForSelector('textarea', { timeout: 10000 })
    
    // Verify still logged in (check for textarea which indicates authenticated state)
    const isStillLoggedIn = await page.locator('textarea').isVisible()
    expect(isStillLoggedIn).toBeTruthy()
  })
  
  test('WebSocket connects after login', async ({ authenticatedPage: page }) => {
    // Check connection status
    const isConnected = await page.locator('text=已連接').isVisible({ timeout: 5000 }).catch(() => false)
    expect(isConnected).toBeTruthy()
  })
})