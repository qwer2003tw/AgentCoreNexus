# Phase 1 驗收標準

> 定義 Phase 1 完成的量化標準

---

## 📊 功能驗收 Matrix

| 功能項目 | 成功標準 | 失敗條件 | 測試方式 |
|----------|----------|----------|----------|
| **ECS Service 啟動** | 容器 RUNNING 狀態 | 反覆 crash / OOM | `aws ecs describe-services` |
| **WebSocket Exec** | 延遲 <500ms (P95) | >2s 或連線失敗 | 執行 100 次 `echo test` 量測 |
| **命令執行** | stdout/stderr 正確回傳 | 輸出遺失/亂碼 | 跑 `ls -la`, `cat file` |
| **Sandbox 隔離** | Session A 看不到 Session B 檔案 | 跨 session 讀取成功 | 建兩個 session 互相 cat |
| **EFS 持久化** | 重啟容器後檔案還在 | 檔案消失 | 寫檔 → 重啟 → 讀檔 |
| **Cold Start** | <30s (新 task) | >60s | 砍掉 task 重新啟動計時 |
| **健康檢查** | ALB health check pass | 持續 unhealthy | CloudWatch 監控 |
| **安全合規** | 0 個 HIGH severity 違規 | 任何 HIGH 違規 | cfn-lint + bandit scan |

---

## 🧪 測試覆蓋 Matrix

| 測試類型 | 覆蓋目標 | 成功標準 | 失敗條件 |
|----------|----------|----------|----------|
| **Unit Tests** | 核心邏輯 (exec agent, sandbox allocator) | ≥80% line coverage | <70% |
| **Integration Tests** | WebSocket + EFS + Sandbox 整合 | 全部 PASS | 任一 FAIL |
| **E2E Tests** | 完整流程 (連線→執行→回傳) | 5 個核心場景 PASS | 任一 FAIL |
| **Security Tests** | SAST scan (bandit + cfn-lint) | 0 HIGH, <5 MEDIUM | 任何 HIGH |
| **Load Tests** | 併發連線 | 10 concurrent sessions 穩定 | crash 或 >2s 延遲 |

---

## ✅ Phase 1 過關條件

**全部打勾才算完成：**

### 功能
- [ ] ECS Service 穩定運行 24hr 無 crash
- [ ] WebSocket exec P95 < 500ms
- [ ] Sandbox 隔離測試通過
- [ ] EFS 持久化測試通過

### 測試
- [ ] Unit test coverage ≥ 80%
- [ ] Integration tests 全 PASS
- [ ] E2E 核心場景 5/5 PASS

### 安全
- [ ] 安全掃描 0 HIGH severity
- [ ] 遵循 `SECURITY_CHECKLIST.md`

---

## 📝 E2E 核心場景

1. **基本執行**: 連線 → `echo hello` → 收到 `hello`
2. **檔案操作**: `echo test > file.txt` → `cat file.txt` → 收到 `test`
3. **持久化**: 寫檔 → 斷線重連 → 讀檔成功
4. **隔離性**: Session A 寫檔 → Session B 讀不到
5. **錯誤處理**: 執行不存在命令 → 收到正確 stderr

---

## 📈 效能基準 (Baseline)

| 指標 | 目標 | 可接受 | 不可接受 |
|------|------|--------|----------|
| Exec 延遲 (P50) | <200ms | <300ms | >500ms |
| Exec 延遲 (P95) | <500ms | <800ms | >2s |
| Exec 延遲 (P99) | <1s | <1.5s | >3s |
| Cold start | <15s | <30s | >60s |
| 記憶體使用 | <512MB | <768MB | >1GB |

---

## 🔄 驗收流程

1. **開發完成** → 跑 Unit Tests
2. **Unit Tests PASS** → 部署到 Dev 環境
3. **Dev 部署成功** → 跑 Integration + E2E Tests
4. **Tests PASS** → 跑 Security Scan
5. **Security PASS** → 24hr 穩定性測試
6. **穩定性 PASS** → Phase 1 完成 ✅
