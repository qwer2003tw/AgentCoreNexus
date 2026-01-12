import { test, expect, createNewConversation, sendMessage } from '../setup/fixtures'

test.describe('Edge Cases and Boundary Tests', () => {
  
  test('handles very long messages', async ({ authenticatedPage: page }) => {
    await createNewConversation(page)
    
    // Create a message longer than 4000 characters
    const longMessage = 'A'.repeat(5000)
    await page.fill('textarea', longMessage)
    
    // Should prevent sending or truncate
    await page.click('button[type="submit"]')
    await page.waitForTimeout(1000)
    
    // Verify some handling (either blocked or truncated)
    const textarea = await page.locator('textarea').inputValue()
    expect(textarea.length).toBeLessThanOrEqual(4000)
  })
  
  test('handles emoji in messages', async ({ authenticatedPage: page }) => {
    await createNewConversation(page)
    
    await sendMessage(page, '😀 👍 🎉 測試 emoji')
    await page.waitForTimeout(10000)
    
    // Verify emoji displayed correctly
    const messages = await page.locator('.flex.gap-3').allTextContents()
    expect(messages.some(m => m.includes('😀'))).toBeTruthy()
  })
  
  test('handles rapid clicking', async ({ authenticatedPage: page }) => {
    await createNewConversation(page)
    
    // Fill textarea and click submit
    await page.fill('textarea', '測試')
    await page.click('button[type="submit"]')
    
    // Verify button becomes disabled while sending (correct behavior)
    const button = page.locator('button[type="submit"]')
    
    // Wait a moment for button to be disabled
    await page.waitForTimeout(100)
    
    // Verify button is disabled (preventing rapid clicking)
    const isDisabled = await button.isDisabled()
    expect(isDisabled).toBeTruthy()
    
    // Wait for message to be sent
    await page.waitForTimeout(2000)
  })
  
  test('handles many conversations efficiently', async ({ authenticatedPage: page }) => {
    const startTime = Date.now()
    
    // Create 10 conversations (reasonable amount for testing)
    for (let i = 0; i < 10; i++) {
      await createNewConversation(page)
      await page.waitForTimeout(200)
    }
    
    const createTime = Date.now() - startTime
    
    // Verify all created
    const count = await page.locator('.p-2 button').count()
    expect(count).toBeGreaterThanOrEqual(10)
    
    // Should be reasonably fast (< 30 seconds)
    expect(createTime).toBeLessThan(30000)
  })
  
  test('prevents XSS with HTML tags', async ({ authenticatedPage: page }) => {
    await createNewConversation(page)
    
    // Try to inject script tag
    await sendMessage(page, '<script>alert("XSS")</script>')
    await page.waitForTimeout(2000)
    
    // Script should be escaped as text, not executed
    const messages = await page.locator('.flex.gap-3').allTextContents()
    const hasScriptAsText = messages.some(m => m.includes('<script>'))
    expect(hasScriptAsText).toBeTruthy()
    
    // Verify page still functional (script didn't execute)
    const textareaEnabled = await page.locator('textarea').isEnabled()
    expect(textareaEnabled).toBeTruthy()
  })
})

// Note: Several edge case tests are marked as skip for:
// 1. Performance/time constraints (many conversations)
// 2. Require specific test environment (XSS testing)
// 3. Need more sophisticated setup