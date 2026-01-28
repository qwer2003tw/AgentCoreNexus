import { test, expect, createNewConversation, sendMessage, waitForAIReply, switchToConversation, getConversationTitle, getMessageCount } from '../setup/fixtures'

test.describe('Chat Core Functionality', () => {
  // Set desktop viewport for all tests in this suite
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.setViewportSize({ width: 1920, height: 1080 })
  })
  
  test('user can send message and receive AI reply', async ({ authenticatedPage: page }) => {
    // Increase timeout based on actual p95: 25.7s (45s default + margin)
    test.setTimeout(120000)
    
    // Create new conversation
    await createNewConversation(page)
    
    // Send message
    await sendMessage(page, '1+1等於多少？')
    
    // Wait for AI reply (45s default covers p95)
    await waitForAIReply(page, 60000)
    
    // Verify reply exists
    const messages = await page.locator('.flex.gap-3').allTextContents()
    const hasReply = messages.some(msg => msg.includes('2') || msg.includes('等於'))
    expect(hasReply).toBeTruthy()
  })
  
  test('replies route to correct conversation', async ({ authenticatedPage: page }) => {
    // Create conversation A
    const titleA = await createNewConversation(page)
    await page.waitForTimeout(1000)
    
    // Create conversation B
    const titleB = await createNewConversation(page)
    await page.waitForTimeout(1000)
    
    // Switch to conversation A (second in list)
    await page.locator('.p-2 button').nth(1).click()
    await page.waitForTimeout(500)
    
    // Send message in conversation A
    await sendMessage(page, '測試對話 A')
    
    // Immediately switch to conversation B (first in list)
    await page.locator('.p-2 button').first().click()
    await page.waitForTimeout(500)
    
    // Record message count in conversation B before waiting
    const convBMessageCountBefore = await getMessageCount(page)
    
    // Wait for AI to process (10 seconds)
    await page.waitForTimeout(10000)
    
    // Verify conversation B did not receive messages from conversation A
    const convBMessageCountAfter = await getMessageCount(page)
    // Allow for auto-created empty conversation messages
    expect(convBMessageCountAfter).toBeLessThanOrEqual(convBMessageCountBefore + 1)
    
    // Switch back to conversation A
    await page.locator('.p-2 button').nth(1).click()
    await page.waitForTimeout(500)
    
    // Verify conversation A has at least 2 messages (user + AI reply)
    const convAMessageCount = await getMessageCount(page)
    expect(convAMessageCount).toBeGreaterThanOrEqual(2)  // User message + AI reply
  })
  
  test('conversation title gets updated', async ({ authenticatedPage: page }) => {
    // Increase timeout for AI processing + title update
    test.setTimeout(120000)
    
    // Create new conversation
    await createNewConversation(page)
    await page.waitForTimeout(500)
    
    // Send message
    await sendMessage(page, '今天是星期幾？')
    
    // Wait for AI reply (ensures title update has completed)
    await waitForAIReply(page, 60000)
    
    // Wait a bit for title update to propagate
    await page.waitForTimeout(2000)
    
    // Reload page to get fresh state
    await page.reload()
    await page.waitForSelector('textarea', { timeout: 10000 })
    await page.waitForTimeout(1000)
    
    // Check sidebar shows updated title (not "新對話")
    const sidebarTitles = await page.locator('.p-2 button h3').allTextContents()
    const hasUpdatedTitle = sidebarTitles.some(t => 
      t !== '新對話' && (t.includes('星期') || t.length > 10)
    )
    expect(hasUpdatedTitle).toBeTruthy()
  })
  
  test('multiple rapid messages are handled correctly', async ({ authenticatedPage: page }) => {
    // Increase timeout for multiple AI processing (3 × p95)
    test.setTimeout(180000)
    
    // Create new conversation
    await createNewConversation(page)
    
    // Send multiple messages rapidly
    await sendMessage(page, '第一條消息')
    await page.waitForTimeout(100)
    await sendMessage(page, '第二條消息')
    await page.waitForTimeout(100)
    await sendMessage(page, '第三條消息')
    
    // Wait for all replies (3 AI responses may take up to 90s based on p95)
    await page.waitForTimeout(90000)
    
    // Verify all messages are present
    const messageCount = await getMessageCount(page)
    expect(messageCount).toBeGreaterThanOrEqual(6)  // 3 user + 3 AI
  })

  test('user can upload attachment and send message', async ({ authenticatedPage: page }) => {
    await createNewConversation(page)

    const fileInput = page.locator('input[type=\"file\"]')
    await fileInput.setInputFiles('fixtures/sample.txt')

    await page.waitForSelector('text=sample.txt', { timeout: 10000 })

    await page.click('button[aria-label=\"發送訊息\"]')

    await page.waitForSelector('text=sample.txt', { timeout: 10000 })
  })
  
  test('attachments display correctly in conversation history without crashing', async ({ authenticatedPage: page }) => {
    // Increase timeout for attachment + AI processing
    test.setTimeout(120000)
    
    await createNewConversation(page)
    
    // Track JavaScript errors
    const jsErrors: string[] = []
    page.on('pageerror', (err) => {
      jsErrors.push(err.message)
      console.error('Page error:', err.message)
    })
    
    // Upload and send
    const fileInput = page.locator('input[type=\"file\"]')
    await fileInput.setInputFiles('fixtures/sample.txt')
    await page.waitForSelector('text=sample.txt', { timeout: 10000 })
    await page.click('button[aria-label=\"發送訊息\"]')
    
    // Wait for AI to process
    await waitForAIReply(page, 60000)
    
    // Reload page to trigger loading from history
    await page.reload()
    await page.waitForSelector('textarea', { timeout: 10000 })
    await page.waitForTimeout(2000)
    
    // Verify no JavaScript errors occurred
    expect(jsErrors).toHaveLength(0)
    
    // Page should still be functional (not black screen)
    const textarea = page.locator('textarea')
    await expect(textarea).toBeVisible()
  })
  
  test('WebSocket reconnection works', async ({ authenticatedPage: page }) => {
    // Increase timeout for reconnection + AI processing
    test.setTimeout(120000)
    
    // Create conversation and send message
    await createNewConversation(page)
    await sendMessage(page, '測試重連')
    
    // Simulate disconnect by reloading page
    await page.reload()
    
    // Wait for page to load and reconnect (increased timeout for concurrent environment)
    await page.waitForSelector('textarea', { timeout: 10000 })
    await page.waitForTimeout(3000)
    
    // Verify can send message after reconnection
    await sendMessage(page, '重連後的消息')
    await waitForAIReply(page, 60000)
    
    // Verify reply received
    const messageCount = await getMessageCount(page)
    expect(messageCount).toBeGreaterThanOrEqual(2)
  })
})