import { test, expect, createNewConversation } from '../setup/fixtures'

test.describe('Responsive Enter Key Behavior', () => {
  
  test.describe('Desktop Mode (1920x1080)', () => {
    test.beforeEach(async ({ authenticatedPage: page }) => {
      await page.setViewportSize({ width: 1920, height: 1080 })
    })
    
    test('should show desktop placeholder', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const textarea = page.locator('textarea')
      const placeholder = await textarea.getAttribute('placeholder')
      
      // Desktop should show "Enter 發送，Shift+Enter 換行"
      expect(placeholder).toContain('Enter 發送')
      expect(placeholder).toContain('Shift+Enter 換行')
    })
    
    test('should NOT show "發送" text on button (desktop)', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const sendButton = page.locator('button[type="submit"]')
      const buttonText = await sendButton.textContent()
      
      // Desktop button should NOT have "發送" text (icon only)
      expect(buttonText?.trim() || '').toBe('')
    })
    
    test('can send message via button click (desktop)', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const textarea = page.locator('textarea')
      const sendButton = page.locator('button[type="submit"]')
      
      // Type message
      await textarea.fill('測試桌面發送')
      
      // Click send button
      await sendButton.click()
      await page.waitForTimeout(500)
      
      // Verify message was sent (textarea cleared)
      const textareaValue = await textarea.inputValue()
      expect(textareaValue).toBe('')
    })
  })
  
  test.describe('Mobile Mode (375x667)', () => {
    test.beforeEach(async ({ authenticatedPage: page }) => {
      await page.setViewportSize({ width: 375, height: 667 })
    })
    
    test('should show mobile placeholder', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const textarea = page.locator('textarea')
      const placeholder = await textarea.getAttribute('placeholder')
      
      // Mobile should show "Enter 換行，點擊發送"
      expect(placeholder).toContain('Enter 換行')
      expect(placeholder).toContain('點擊發送')
    })
    
    test('should show "發送" text on button (mobile)', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const sendButton = page.locator('button[type="submit"]')
      const buttonText = await sendButton.textContent()
      
      // Mobile button should have "發送" text
      expect(buttonText).toContain('發送')
    })
    
    test('button should be larger on mobile', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const sendButton = page.locator('button[type="submit"]')
      
      // Get button classes
      const buttonClasses = await sendButton.getAttribute('class')
      
      // Mobile button should have min-w-[64px] and min-h-[48px]
      expect(buttonClasses).toContain('min-w-[64px]')
      expect(buttonClasses).toContain('min-h-[48px]')
    })
    
    test('can send message via button click (mobile)', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      // 移動端：按 Escape 關閉側邊欄（現已支援）
      await page.keyboard.press('Escape')
      await page.waitForTimeout(500)
      
      const textarea = page.locator('textarea')
      const sendButton = page.locator('button[type="submit"]')
      
      // Type message
      await textarea.fill('測試移動發送')
      
      // Click send button (primary way to send on mobile)
      await sendButton.click()
      await page.waitForTimeout(500)
      
      // Verify message was sent
      const textareaValue = await textarea.inputValue()
      expect(textareaValue).toBe('')
    })
  })
  
  test.describe('Tablet Mode (768x1024)', () => {
    test.beforeEach(async ({ authenticatedPage: page }) => {
      await page.setViewportSize({ width: 768, height: 1024 })
    })
    
    test('should behave as mobile (show mobile placeholder)', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const textarea = page.locator('textarea')
      const placeholder = await textarea.getAttribute('placeholder')
      
      // Tablet should behave as mobile
      expect(placeholder).toContain('Enter 換行')
      expect(placeholder).toContain('點擊發送')
    })
    
    test('should show "發送" text on button (tablet)', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      const sendButton = page.locator('button[type="submit"]')
      const buttonText = await sendButton.textContent()
      
      // Tablet button should have "發送" text (mobile behavior)
      expect(buttonText).toContain('發送')
    })
  })
  
  test.describe('Responsive Switching', () => {
    test('should switch placeholder when resizing desktop → mobile', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      // Start as desktop
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.waitForTimeout(200) // Wait for debounce
      
      let textarea = page.locator('textarea')
      let placeholder = await textarea.getAttribute('placeholder')
      expect(placeholder).toContain('Enter 發送')
      
      // Resize to mobile
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForTimeout(200) // Wait for debounce
      
      textarea = page.locator('textarea')
      placeholder = await textarea.getAttribute('placeholder')
      expect(placeholder).toContain('Enter 換行')
    })
    
    test('should switch placeholder when resizing mobile → desktop', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      // Start as mobile
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForTimeout(200)
      
      let textarea = page.locator('textarea')
      let placeholder = await textarea.getAttribute('placeholder')
      expect(placeholder).toContain('Enter 換行')
      
      // Resize to desktop
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.waitForTimeout(200)
      
      textarea = page.locator('textarea')
      placeholder = await textarea.getAttribute('placeholder')
      expect(placeholder).toContain('Enter 發送')
    })
    
    test('should switch button text when resizing', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      // Start as desktop (no button text)
      await page.setViewportSize({ width: 1920, height: 1080 })
      await page.waitForTimeout(200)
      
      let sendButton = page.locator('button[type="submit"]')
      let buttonText = await sendButton.textContent()
      expect(buttonText?.trim() || '').toBe('')
      
      // Resize to mobile (should show button text)
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForTimeout(200)
      
      sendButton = page.locator('button[type="submit"]')
      buttonText = await sendButton.textContent()
      expect(buttonText).toContain('發送')
    })
    
    test('functionality remains stable after multiple resizes', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      const textarea = page.locator('textarea')
      const sendButton = page.locator('button[type="submit"]')
      
      // Resize multiple times
      const sizes = [
        { width: 1920, height: 1080 }, // Desktop
        { width: 375, height: 667 },   // Mobile
        { width: 768, height: 1024 },  // Tablet
        { width: 1920, height: 1080 }, // Desktop again
      ]
      
      for (const size of sizes) {
        await page.setViewportSize(size)
        await page.waitForTimeout(200)
        
        // 如果是移動尺寸，按 Escape 關閉側邊欄
        if (size.width < 1024) {
          await page.keyboard.press('Escape')
          await page.waitForTimeout(300)
        }
        
        // Verify can still send message
        await textarea.fill(`測試 ${size.width}x${size.height}`)
        await sendButton.click()
        await page.waitForTimeout(300)
        
        // Verify message was sent
        const value = await textarea.inputValue()
        expect(value).toBe('')
      }
    })
  })
  
  test.describe('Edge Cases', () => {
    test('should handle boundary viewport width (767px vs 768px)', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      // 767px should be mobile
      await page.setViewportSize({ width: 767, height: 600 })
      await page.waitForTimeout(200)
      
      let textarea = page.locator('textarea')
      let placeholder = await textarea.getAttribute('placeholder')
      expect(placeholder).toContain('Enter 換行') // Mobile
      
      // 768px should be mobile/tablet (still mobile behavior)
      await page.setViewportSize({ width: 768, height: 600 })
      await page.waitForTimeout(200)
      
      textarea = page.locator('textarea')
      placeholder = await textarea.getAttribute('placeholder')
      expect(placeholder).toContain('Enter 換行') // Still mobile
    })
    
    test('should handle disconnected state properly on all screen sizes', async ({ authenticatedPage: page }) => {
      await createNewConversation(page)
      
      // Disconnect by reloading
      await page.reload()
      await page.waitForSelector('textarea', { timeout: 10000 })
      
      // Test both mobile and desktop while disconnected/reconnecting
      await page.setViewportSize({ width: 375, height: 667 })
      await page.waitForTimeout(1000)
      
      let textarea = page.locator('textarea')
      let placeholder = await textarea.getAttribute('placeholder')
      
      // Should show appropriate placeholder even when disconnected/reconnecting
      expect(placeholder).toBeTruthy()
      
      // Wait for reconnection
      await page.waitForTimeout(3000)
      
      // Verify placeholder updated after reconnection
      textarea = page.locator('textarea')
      placeholder = await textarea.getAttribute('placeholder')
      expect(placeholder).toContain('Enter 換行')
    })
  })
})