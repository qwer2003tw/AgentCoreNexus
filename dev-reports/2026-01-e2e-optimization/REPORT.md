# E2E 測試優化報告

**優化日期**: 2026-01-12  
**優化前時間**: 9 分鐘  
**目標**: 盡可能縮短執行時間

---

## 📊 實施的優化措施

### 1. 啟用 Playwright 並行化 ⭐⭐⭐
**修改檔案**: `playwright.config.ts`

```typescript
// Before
fullyParallel: false
workers: 1

// After
fullyParallel: true
workers: process.env.CI ? 4 : 2  // CI 用 4 workers
```

**預期效果**: 測試執行時間減少 60-75%

---

### 2. Playwright 瀏覽器快取 ⭐⭐⭐
**修改檔案**: `.github/workflows/tests.yml`

新增了 Playwright 瀏覽器快取機制：
- 快取路徑: `~/.cache/ms-playwright`
- 快取 key: 基於 `package-lock.json` 的 hash
- 首次執行: 下載並快取瀏覽器（~500MB）
- 後續執行: 從快取恢復（10-20 秒）

**預期效果**: 瀏覽器安裝時間從 2-3 分鐘降到 10-20 秒

---

### 3. npm 依賴快取 ⭐⭐
**修改檔案**: `.github/workflows/tests.yml`

```yaml
- name: Set up Node.js
  uses: actions/setup-node@v4
  with:
    node-version: '18'
    cache: 'npm'  # 新增快取
```

**預期效果**: npm ci 時間從 30-60 秒降到 10-20 秒

---

### 4. Concurrency 控制 ⭐
**修改檔案**: `.github/workflows/tests.yml`

```yaml
concurrency:
  group: tests-${{ github.ref }}
  cancel-in-progress: true
```

**效果**: 新的 push 會自動取消正在執行的舊測試，避免排隊等待

---

### 5. 優化 Trace 收集
**修改檔案**: `playwright.config.ts`

```typescript
// Before
trace: 'on-first-retry'

// After
trace: 'retain-on-failure'  // 只在失敗時保留
```

**效果**: 減少不必要的 trace 儲存和處理開銷

---

## 🎯 預期改善效果

### 首次執行（無快取）
| 階段 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 瀏覽器安裝 | 2-3 分鐘 | 2-3 分鐘 | - |
| npm 安裝 | 0.5-1 分鐘 | 0.2-0.3 分鐘 | 50% |
| 測試執行 | 5-6 分鐘 | 1.5-2 分鐘 | 65-70% |
| **總計** | **9 分鐘** | **2.5-3 分鐘** | **65-70%** ✅ |

### 後續執行（有快取）
| 階段 | 優化前 | 優化後 | 改善 |
|------|--------|--------|------|
| 瀏覽器安裝 | 2-3 分鐘 | 0.1-0.2 分鐘 | 90% |
| npm 安裝 | 0.5-1 分鐘 | 0.2-0.3 分鐘 | 50% |
| 測試執行 | 5-6 分鐘 | 1.5-2 分鐘 | 65-70% |
| **總計** | **9 分鐘** | **1.5-2 分鐘** | **80-85%** ✅ |

---

## 📝 驗證步驟

### 1. 首次執行驗證
```bash
# Push 程式碼觸發 CI
git push

# 在 GitHub Actions 觀察：
# - 是否使用了 4 workers
# - 瀏覽器安裝時間（預期：2-3 分鐘，cache miss）
# - 總執行時間（預期：2.5-3 分鐘）
```

### 2. 第二次執行驗證
```bash
# 再次 push 觸發 CI（或建立 dummy commit）
git commit --allow-empty -m "test: verify E2E cache"
git push

# 在 GitHub Actions 觀察：
# - 瀏覽器快取命中（預期：Cache restored）
# - 瀏覽器安裝時間（預期：10-20 秒）
# - 總執行時間（預期：1.5-2 分鐘）
```

---

## 🔍 監控指標

在 GitHub Actions 中查看以下指標：

### 1. Cache 命中率
```
✅ Cache hit: playwright-browsers-...
❌ Cache miss: playwright-browsers-...
```

### 2. 各階段耗時
- Set up Node.js: < 30 秒
- Install E2E test dependencies: < 30 秒  
- Cache Playwright browsers: < 5 秒（hit）/ 2-3 分鐘（miss）
- Run E2E tests: 1.5-2 分鐘

### 3. Worker 使用情況
在測試輸出中應該看到：
```
Running 54 tests using 4 workers
```

---

## 🚀 進一步優化選項

如果 1.5-2 分鐘還不夠快，可以考慮：

### Option 1: Sharding（多 runner 並行）
在 `.github/workflows/tests.yml` 中新增 matrix strategy：

```yaml
test-frontend:
  strategy:
    fail-fast: false
    matrix:
      shard: [1/4, 2/4, 3/4, 4/4]
  steps:
    # ...
    - name: Run E2E tests
      run: |
        cd web-adapter/e2e-tests
        npx playwright test --shard=${{ matrix.shard }}
```

**預期效果**: 再減少 40-50%，總時間降到約 **1 分鐘**

### Option 2: Smoke 測試分流
只在 push 時跑關鍵測試：

```yaml
- name: Run E2E tests
  run: |
    cd web-adapter/e2e-tests
    if [ "${{ github.event_name }}" == "push" ]; then
      npm test -- --grep @smoke
    else
      npm test
    fi
```

標記關鍵測試：
```typescript
test.describe('Critical path @smoke', () => {
  // 最重要的測試
})
```

---

## 📊 實際結果記錄

### 執行 1（首次，無快取）
- **日期**: _待填寫_
- **總耗時**: _待填寫_
- **瀏覽器安裝**: _待填寫_
- **測試執行**: _待填寫_
- **Cache 狀態**: miss

### 執行 2（有快取）
- **日期**: _待填寫_
- **總耗時**: _待填寫_
- **瀏覽器安裝**: _待填寫_
- **測試執行**: _待填寫_
- **Cache 狀態**: hit

### 對比分析
- **改善百分比**: _待計算_
- **是否達到目標**: _待評估_
- **需要進一步優化**: _是/否_

---

## 🎓 學習要點

1. **並行化是最有效的優化** - 從 1 worker 到 4 workers 直接減少 75% 執行時間
2. **快取瀏覽器很重要** - 避免每次下載 ~500MB
3. **Concurrency 控制避免浪費** - 取消過時的測試執行
4. **合理的 trace 策略** - 只在需要時保留，減少開銷

---

## 📞 後續行動

- [ ] 驗證首次執行效果
- [ ] 驗證快取命中效果
- [ ] 記錄實際執行資料
- [ ] 評估是否需要 sharding
- [ ] 考慮 smoke 測試分流策略

**優化負責人**: Cline AI  
**GitHub Actions 連結**: https://github.com/qwer2003tw/AgentCoreNexus/actions