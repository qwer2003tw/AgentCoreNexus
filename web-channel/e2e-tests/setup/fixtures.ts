import { test as base, Page } from '@playwright/test'

// Test credentials
export const TEST_USER = {
  email: 'test@test.com',
  password: 'Test123!'
}

// Extended test with authenticated page
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use) => {
    // Perform login
    await page.goto('/')
    
    // Fill login form
    await page.fill('input[type="email"]', TEST_USER.email)
    await page.fill('input[type="password"]', TEST_USER.password)
    await page.click('button[type="submit"]')
    
    // Wait for chat page to load
    await page.waitForSelector('textarea', { timeout: 10000 })
    
    // Wait for WebSocket connection
    await page.waitForFunction(
      () => document.querySelector('.connection-status')?.textContent?.includes('已連接'),
      { timeout: 5000 }
    ).catch(() => {
      console.log('WebSocket connection indicator not found, continuing anyway')
    })
    
    await use(page)
  },
})

export { expect } from '@playwright/test'

// Helper functions
export async function createNewConversation(page: Page): Promise<string> {
  await page.click('button:has-text("新對話")')
  
  // Wait for API response
  await page.waitForResponse(
    response => response.url().includes('/conversations') && response.status() === 200,
    { timeout: 5000 }
  ).catch(() => console.log('Conversation create API call not detected'))
  
  // Wait for new conversation to appear in sidebar
  await page.waitForTimeout(1000)
  
  // Get the newly created conversation title (first h3 in sidebar)
  const newConvTitle = await page.locator('.p-2 button h3').first().textContent({ timeout: 5000 })
  
  return newConvTitle || '新對話'
}

export async function sendMessage(page: Page, message: string) {
  await page.fill('textarea', message)
  await page.click('button[type="submit"]')
  await page.waitForTimeout(500)  // Wait for optimistic update
}

export async function waitForAIReply(page: Page, timeout = 15000) {
  const initialMessageCount = await page.locator('.flex.gap-3').count()
  
  // Wait for new message to appear
  await page.waitForFunction(
    (count) => {
      const messages = document.querySelectorAll('.flex.gap-3')
      return messages.length > count
    },
    initialMessageCount,
    { timeout }
  )
}

export async function switchToConversation(page: Page, conversationTitle: string) {
  await page.click(`.p-2 button:has-text("${conversationTitle}")`)
  await page.waitForTimeout(500)
}

export async function getConversationTitle(page: Page, index: number = 0): Promise<string> {
  const title = await page.locator('.p-2 button h3').nth(index).textContent({ timeout: 5000 })
  return title || ''
}

export async function getMessageCount(page: Page): Promise<number> {
  return await page.locator('.flex.gap-3').count()
}