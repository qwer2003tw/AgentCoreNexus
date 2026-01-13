import { test as base, Page } from '@playwright/test'

// ✅ Support 4 test accounts for 4 workers (worker isolation)
const TEST_USERS = [
  {
    email: process.env.TEST_USER_1_EMAIL || 'test1@test.com',
    password: process.env.TEST_USER_1_PASSWORD || 'Test123!'
  },
  {
    email: process.env.TEST_USER_2_EMAIL || 'test2@test.com',
    password: process.env.TEST_USER_2_PASSWORD || 'Test123!'
  },
  {
    email: process.env.TEST_USER_3_EMAIL || 'test3@test.com',
    password: process.env.TEST_USER_3_PASSWORD || 'Test123!'
  },
  {
    email: process.env.TEST_USER_4_EMAIL || 'test4@test.com',
    password: process.env.TEST_USER_4_PASSWORD || 'Test123!'
  }
]

// ✅ Export TEST_USER for backward compatibility (tests that directly import it)
export const TEST_USER = TEST_USERS[0]

// Extended test with authenticated page
export const test = base.extend<{ authenticatedPage: Page }>({
  authenticatedPage: async ({ page }, use, testInfo) => {
    // ✅ Select test account based on worker ID
    const workerIndex = testInfo.parallelIndex % TEST_USERS.length
    const TEST_USER = TEST_USERS[workerIndex]
    
    console.log(`🔵 Worker ${testInfo.parallelIndex} using ${TEST_USER.email}`)
    
    try {
      // Step 1: Navigate to login page
      await page.goto('/')
      console.log(`📍 Worker ${testInfo.parallelIndex}: Navigated to login page`)
      
      // Step 2: Fill login form
      await page.fill('input[type="email"]', TEST_USER.email)
      await page.fill('input[type="password"]', TEST_USER.password)
      console.log(`📍 Worker ${testInfo.parallelIndex}: Login form filled`)
      
      // Step 3: Submit login
      await page.click('button[type="submit"]')
      console.log(`📍 Worker ${testInfo.parallelIndex}: Login submitted`)
      
      // Step 4: Wait for login API response
      await page.waitForResponse(
        response => response.url().includes('/auth/login') && response.status() === 200,
        { timeout: 10000 }
      )
      console.log(`📍 Worker ${testInfo.parallelIndex}: Login API responded successfully`)
      
      // Step 5: Wait for user load (App.tsx calls loadUser() after login)
      await page.waitForResponse(
        response => response.url().includes('/auth/me'),
        { timeout: 10000 }
      ).catch(() => console.log(`⚠️ Worker ${testInfo.parallelIndex}: User load API not detected, continuing...`))
      
      // Step 6: Wait for DOM to load
      await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
      console.log(`📍 Worker ${testInfo.parallelIndex}: DOM content loaded`)
      
      // Step 7: Verify URL navigation (CRITICAL FIX)
      const currentUrl = page.url()
      console.log(`📍 Worker ${testInfo.parallelIndex}: Current URL after login: ${currentUrl}`)
      
      // Check if NOT on login page (should be on chat page at root "/")
      if (currentUrl.includes('/login')) {
        console.log(`⚠️ Worker ${testInfo.parallelIndex}: Still on login page, attempting manual navigation...`)
        await page.goto('/')
        await page.waitForLoadState('domcontentloaded', { timeout: 5000 })
        console.log(`📍 Worker ${testInfo.parallelIndex}: Manually navigated to: ${page.url()}`)
      }
      
      // Step 8: Wait for chat page sidebar to appear
      await page.waitForSelector('button:has-text("新對話")', { timeout: 10000 })
      console.log(`📍 Worker ${testInfo.parallelIndex}: Chat page loaded - "新對話" button found`)
      
      // Step 9: Wait for conversations to load (optimized timeout after WebSocket fix)
      await Promise.race([
        // Option 1: Wait for conversation to appear in sidebar
        page.waitForFunction(
          () => document.querySelectorAll('.p-2 button h3').length > 0,
          { timeout: 15000 }
        ),
        // Option 2: Wait for textarea (in case conversation loads very quickly)
        page.waitForSelector('textarea:not([disabled])', { timeout: 15000 })
      ]).catch(async (error) => {
        console.log(`⚠️ Worker ${testInfo.parallelIndex}: No conversation, creating manually...`)
        await page.click('button:has-text("新對話")').catch(() => {})
        await page.waitForTimeout(2000)
      })
      
      console.log(`📍 Worker ${testInfo.parallelIndex}: Conversation ready`)
      
      // Step 10: Wait for WebSocket connection (now should be fast after IAM fix)
      await page.waitForFunction(
        () => document.querySelector('.connection-status')?.textContent?.includes('已連接'),
        { timeout: 5000 }
      ).catch(() => {
        console.log(`⚠️ Worker ${testInfo.parallelIndex}: WebSocket not connected`)
      })
      
      // Step 11: Final verification - textarea available
      await page.waitForSelector('textarea:not([disabled])', { timeout: 10000 })
      console.log(`✅ Worker ${testInfo.parallelIndex}: Authenticated`)
      
    } catch (error) {
      // Diagnostic information on failure
      console.error(`❌ Authentication failed for worker ${testInfo.parallelIndex}`)
      console.error(`Current URL: ${page.url()}`)
      
      // Take screenshot for diagnosis
      await page.screenshot({ 
        path: `test-results/auth-failure-worker-${testInfo.parallelIndex}.png`,
        fullPage: true
      }).catch(() => console.error('Failed to take screenshot'))
      
      // Log page state
      const pageTitle = await page.title().catch(() => 'unknown')
      console.error(`Page title: ${pageTitle}`)
      
      // Check for error messages on page
      const bodyText = await page.locator('body').textContent().catch(() => '')
      if (bodyText.includes('錯誤') || bodyText.toLowerCase().includes('error')) {
        console.error(`Error message detected on page`)
      }
      
      throw error
    }
    
    await use(page)
  },
})

export { expect } from '@playwright/test'

// Helper functions (optimized timeouts after WebSocket fix)
export async function createNewConversation(page: Page): Promise<string> {
  await page.click('button:has-text("新對話")')
  
  // Wait for API response
  await page.waitForResponse(
    response => response.url().includes('/conversations') && response.status() === 200,
    { timeout: 5000 }
  ).catch(() => console.log('⚠️ Conversation API timeout'))
  
  // Wait for new conversation to appear
  await page.waitForTimeout(1000)
  
  // Get the newly created conversation title
  const newConvTitle = await page.locator('.p-2 button h3').first().textContent({ timeout: 5000 })
  
  return newConvTitle || '新對話'
}

export async function sendMessage(page: Page, message: string) {
  await page.fill('textarea', message)
  await page.click('button[type="submit"]')
  await page.waitForTimeout(500)
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

export async function openConversationContextMenu(page: Page, index: number = 0): Promise<void> {
  const conversationButton = page.locator('.p-2 button:has(h3)').nth(index)
  await conversationButton.waitFor({ state: 'visible', timeout: 5000 })
  await conversationButton.scrollIntoViewIfNeeded()

  const box = await conversationButton.boundingBox()
  const clientX = box ? Math.round(box.x + box.width / 2) : 10
  const clientY = box ? Math.round(box.y + box.height / 2) : 10

  await conversationButton.dispatchEvent('contextmenu', {
    bubbles: true,
    cancelable: true,
    clientX,
    clientY
  })

  const contextMenu = page.locator('[data-testid="conversation-context-menu"]')
  try {
    await contextMenu.waitFor({ state: 'visible', timeout: 2000 })
  } catch {
    await page.mouse.click(clientX, clientY, { button: 'right' })
    await contextMenu.waitFor({ state: 'visible', timeout: 2000 })
  }
}
