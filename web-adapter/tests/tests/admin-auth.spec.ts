/**
 * Admin Authentication & Authorization Tests
 * 
 * 測試 admin 權限驗證和頁面重載後的狀態恢復
 */

import { test, expect } from '@playwright/test'
import {
  loginAsAdmin,
  loginAsUser,
  getUserFromStorage,
  getTokenFromStorage,
  clearStorage,
  waitForAdminPanel,
  ADMIN_USER,
  REGULAR_USER
} from '../setup/admin-helpers'

test.describe('Admin Authentication & Authorization', () => {
  
  test.beforeEach(async ({ page }) => {
    // 清除 storage 確保乾淨環境
    await clearStorage(page)
  })
  
  test('T1: 普通用戶無法訪問 admin 路由', async ({ page }) => {
    // 用普通用戶登入
    await loginAsUser(page)
    
    // 嘗試訪問 admin 路由
    await page.goto('/admin')
    
    // 預期：被重定向到對話頁面（首頁）
    await expect(page).toHaveURL('/')
    
    // 驗證在對話頁面
    await expect(page.locator('button:has-text("新對話")')).toBeVisible()
  })
  
  test('T2: Admin 用戶可以訪問 admin 路由', async ({ page }) => {
    // 用 admin 登入
    await loginAsAdmin(page)
    
    // 訪問 admin 路由
    await page.goto('/admin')
    
    // 預期：成功顯示對話管理頁面
    await waitForAdminPanel(page)
    await expect(page.locator('h1').filter({ hasText: '管理中心' })).toBeVisible()
    
    // 驗證側邊欄存在
    await expect(page.locator('.admin-sidebar')).toBeVisible()
  })
  
  test('T3: Admin 可以訪問審計日誌頁面', async ({ page }) => {
    // 用 admin 登入
    await loginAsAdmin(page)
    
    // 訪問審計日誌
    await page.goto('/admin/audit-logs')
    
    // 預期：顯示審計日誌頁面
    await expect(page.locator('h2').filter({ hasText: '審計日誌' })).toBeVisible()
    
    // 驗證表格存在
    await expect(page.locator('.logs-table table')).toBeVisible()
  })
  
  test('T4: ⭐ 頁面重載後 admin 仍可訪問（測試 localStorage 持久化）', async ({ page }) => {
    // 用 admin 登入
    await loginAsAdmin(page)
    
    // 訪問審計日誌
    await page.goto('/admin/audit-logs')
    await expect(page.locator('h2').filter({ hasText: '審計日誌' })).toBeVisible()
    
    // ⭐ 關鍵：重新整理頁面
    console.log('📍 測試重點：頁面重載...')
    await page.reload()
    
    // 預期：仍在審計日誌頁面（不被導向 /）
    await page.waitForLoadState('networkidle')
    
    // 驗證 URL
    expect(page.url()).toContain('/admin/audit-logs')
    
    // 驗證頁面內容
    await expect(page.locator('h2').filter({ hasText: '審計日誌' })).toBeVisible({ timeout: 10000 })
    
    // ⭐ 驗證 localStorage 中有 user
    const user = await getUserFromStorage(page)
    console.log('📍 localStorage user:', user)
    
    expect(user).toBeTruthy()
    expect(user.email).toBe(ADMIN_USER.email)
    expect(user.role).toBe('admin')
  })
  
  test('T5: 登出後無法訪問 admin 路由', async ({ page }) => {
    // 登入並訪問 admin
    await loginAsAdmin(page)
    await page.goto('/admin')
    await waitForAdminPanel(page)
    
    // 登出 - 使用 once 避免重複處理對話框
    page.once('dialog', dialog => dialog.accept())
    await page.click('button:has-text("登出")')
    
    // 等待導向登入頁
    await page.waitForURL('**/login', { timeout: 10000 })
    
    // 確認在登入頁面
    await expect(page.locator('input[type="email"]')).toBeVisible()
    
    // 嘗試訪問 admin（應該被導向登入頁）
    await page.goto('/admin')
    
    // 預期：仍在登入頁面或被重定向回登入頁
    await page.waitForURL('**/login', { timeout: 10000 })
    await expect(page.locator('input[type="email"]')).toBeVisible()
  })
  
  test('T6: Token 和 User 狀態一致性', async ({ page }) => {
    // 登入
    await loginAsAdmin(page)
    
    // 檢查 localStorage 狀態
    const token = await getTokenFromStorage(page)
    const user = await getUserFromStorage(page)
    
    console.log('📍 Token 存在:', !!token)
    console.log('📍 User 存在:', !!user)
    console.log('📍 User role:', user?.role)
    
    // 預期：token 和 user 都存在
    expect(token).toBeTruthy()
    expect(user).toBeTruthy()
    expect(user.role).toBe('admin')
  })
})