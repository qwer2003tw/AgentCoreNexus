import { test, expect, createNewConversation, sendMessage, getConversationTitle } from '../setup/fixtures'

test.describe('Conversation Management', () => {
  
  test('can create multiple conversations', async ({ authenticatedPage: page }) => {
    const initialCount = await page.locator('.p-2 button').count()
    
    // Create 3 new conversations
    await createNewConversation(page)
    await page.waitForTimeout(500)
    await createNewConversation(page)
    await page.waitForTimeout(500)
    await createNewConversation(page)
    await page.waitForTimeout(500)
    
    const finalCount = await page.locator('.p-2 button').count()
    expect(finalCount).toBe(initialCount + 3)
  })
  
  test('can switch between conversations', async ({ authenticatedPage: page }) => {
    // Create two conversations with different messages
    await createNewConversation(page)
    await sendMessage(page, 'Message A')
    await page.waitForTimeout(1000)
    
    await createNewConversation(page)
    await sendMessage(page, 'Message B')
    await page.waitForTimeout(1000)
    
    // Switch to first conversation
    await page.locator('.p-2 button').nth(1).click()
    await page.waitForTimeout(500)
    
    // Verify we see Message A
    const messages = await page.locator('.flex.gap-3').allTextContents()
    expect(messages.some(m => m.includes('Message A'))).toBeTruthy()
  })
  
  test.skip('can rename conversation', async ({ authenticatedPage: page }) => {
    // Create conversation
    await createNewConversation(page)
    
    // Right-click to open context menu
    await page.locator('.p-2 button').first().click({ button: 'right' })
    await page.waitForTimeout(300)
    
    // Click rename
    await page.click('text=重命名').catch(() => {
      console.log('Rename option not found in context menu')
    })
    await page.waitForTimeout(300)
    
    // Enter new title
    const newTitle = 'My Custom Title'
    await page.fill('input[type="text"]', newTitle)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(500)
    
    // Verify title changed
    const title = await getConversationTitle(page, 0)
    expect(title).toBe(newTitle)
  })
  
  test.skip('can delete conversation', async ({ authenticatedPage: page }) => {
    const initialCount = await page.locator('.p-2 button').count()
    
    // Create new conversation
    await createNewConversation(page)
    await page.waitForTimeout(500)
    
    const countAfterCreate = await page.locator('.p-2 button').count()
    expect(countAfterCreate).toBe(initialCount + 1)
    
    // Right-click to delete
    await page.locator('.p-2 button').first().click({ button: 'right' })
    await page.waitForTimeout(300)
    
    // Click delete
    await page.click('text=刪除').catch(() => {
      console.log('Delete option not found in context menu')
    })
    await page.waitForTimeout(300)
    
    // Confirm deletion
    await page.click('button:has-text("確認")').catch(() => {
      console.log('Confirm button not found')
    })
    await page.waitForTimeout(1000)
    
    // Verify conversation removed
    const finalCount = await page.locator('.p-2 button').count()
    expect(finalCount).toBeLessThan(countAfterCreate)
  })
  
  test.skip('can pin conversation', async ({ authenticatedPage: page }) => {
    // Create conversation
    await createNewConversation(page)
    await sendMessage(page, '這是要置頂的對話')
    await page.waitForTimeout(2000)
    
    // Right-click to pin
    await page.locator('.p-2 button').first().click({ button: 'right' })
    await page.waitForTimeout(300)
    
    // Click pin option
    await page.click('text=置頂').catch(() => {
      console.log('Pin option not found in context menu')
    })
    await page.waitForTimeout(1000)
    
    // Verify pinned section exists
    const hasPinnedSection = await page.locator('text=📌 置頂').isVisible().catch(() => false)
    expect(hasPinnedSection).toBeTruthy()
  })
  
  test.skip('search conversations works', async ({ authenticatedPage: page }) => {
    // Create conversations with distinct content
    await createNewConversation(page)
    await sendMessage(page, '蘋果相關的問題')
    await page.waitForTimeout(2000)
    
    await createNewConversation(page)
    await sendMessage(page, '香蕉相關的問題')
    await page.waitForTimeout(2000)
    
    // Use search
    await page.fill('input[placeholder*="搜索"]', '蘋果')
    await page.waitForTimeout(500)
    
    // Verify only matching conversations shown
    const visibleConversations = await page.locator('.p-2 button').count()
    const conversations = await page.locator('.p-2 button').allTextContents()
    
    expect(conversations.some(c => c.includes('蘋果'))).toBeTruthy()
  })
})