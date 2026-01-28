/**
 * Admin 測試輔助函數
 */

import { Page, expect } from '@playwright/test'

export const ADMIN_USER = {
  email: 'admin@test.com',
  password: 'Admin123!'
}

export const REGULAR_USER = {
  email: 'test1@test.com',
  password: 'Test123!'
}

/**
 * 登入為 Admin 用戶
 */
export async function loginAsAdmin(page: Page) {
  await page.goto('/login')
  await page.fill('input[type="email"]', ADMIN_USER.email)
  await page.fill('input[type="password"]', ADMIN_USER.password)
  await page.click('button[type="submit"]')
  
  // 等待登入完成（導向對話頁面）
  await page.waitForSelector('button:has-text("新對話")', { timeout: 10000 })
}

/**
 * 登入為普通用戶（完整流程，參考 authenticatedPage）
 */
export async function loginAsUser(page: Page) {
  await page.goto('/login')
  await page.fill('input[type="email"]', REGULAR_USER.email)
  await page.fill('input[type="password"]', REGULAR_USER.password)
  await page.click('button[type="submit"]')
  
  // 等待 login API 響應
  await page.waitForResponse(
    response => response.url().includes('/auth/login') && response.status() === 200,
    { timeout: 10000 }
  )
  
  // 等待 user load API（可能沒有，所以 catch）
  await page.waitForResponse(
    response => response.url().includes('/auth/me'),
    { timeout: 10000 }
  ).catch(() => {})
  
  // 等待 DOM 載入
  await page.waitForLoadState('domcontentloaded', { timeout: 10000 })
  
  // 驗證導航到聊天頁面
  await page.waitForURL('/', { timeout: 10000 })
  
  // 等待「新對話」按鈕出現
  await page.waitForSelector('button:has-text("新對話")', { timeout: 10000 })
  
  // 等待 conversations 載入或 textarea 可用
  await Promise.race([
    page.waitForFunction(
      () => document.querySelectorAll('.p-2 button h3').length > 0,
      { timeout: 10000 }
    ),
    page.waitForSelector('textarea:not([disabled])', { timeout: 10000 })
  ]).catch(() => {})
  
  // 等待 WebSocket 連接（關鍵！）
  await page.waitForFunction(
    () => document.querySelector('.connection-status')?.textContent?.includes('已連接'),
    { timeout: 15000 }
  ).catch(() => {})
}

/**
 * 檢查 localStorage 中的值
 */
export async function getLocalStorage(page: Page, key: string): Promise<any> {
  return page.evaluate((k) => {
    const value = localStorage.getItem(k)
    if (!value) return null
    try {
      return JSON.parse(value)
    } catch {
      return value
    }
  }, key)
}

/**
 * 獲取 localStorage 中的 user
 */
export async function getUserFromStorage(page: Page) {
  return getLocalStorage(page, 'user')
}

/**
 * 獲取 localStorage 中的 token
 */
export async function getTokenFromStorage(page: Page) {
  return getLocalStorage(page, 'jwt_token')
}

/**
 * 等待 Admin Panel 載入
 */
export async function waitForAdminPanel(page: Page) {
  await expect(page.locator('.admin-layout')).toBeVisible({ timeout: 10000 })
}

/**
 * 導航到審計日誌頁面
 */
export async function navigateToAuditLogs(page: Page) {
  await page.goto('/admin/audit-logs')
  await expect(page.locator('h2').filter({ hasText: '審計日誌' })).toBeVisible({ timeout: 10000 })
}

/**
 * 清除所有 localStorage
 * 注意：必須在有頁面上下文時調用
 */
export async function clearStorage(page: Page) {
  // 先導向登入頁（確保有頁面上下文）
  await page.goto('/login')
  
  // 然後清除 storage
  await page.evaluate(() => {
    localStorage.clear()
    sessionStorage.clear()
  })
}
