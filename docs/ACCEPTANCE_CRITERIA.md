# Phase 1 驗收標準

## 📊 功能驗收

| 功能 | 成功標準 | 測試方式 |
|------|----------|----------|
| ECS Service | RUNNING 狀態 | `aws ecs describe-services` |
| WebSocket Exec | P95 <500ms | 100x `echo test` |
| Sandbox 隔離 | Session A ≠ B | 跨 session cat |
| EFS 持久化 | 重啟後檔案在 | 寫→重啟→讀 |

## 🧪 測試覆蓋

| 類型 | 目標 | 標準 |
|------|------|------|
| Unit | exec_agent, sandbox | ≥80% coverage |
| Integration | WS + EFS + Sandbox | 全 PASS |
| E2E | 完整流程 | 5/5 場景 |
| Security | SAST scan | 0 HIGH |

## ✅ 過關條件

### 功能
- [ ] ECS 穩定 24hr
- [ ] Exec P95 <500ms
- [ ] Sandbox 隔離 PASS
- [ ] EFS 持久化 PASS

### 測試
- [ ] Unit ≥80%
- [ ] Integration 全 PASS
- [ ] E2E 5/5

### 安全
- [ ] 0 HIGH severity
- [ ] 遵循 SECURITY_CHECKLIST.md

## 📝 E2E 場景

1. `echo hello` → 收到 `hello`
2. `echo test > f.txt && cat f.txt` → 收到 `test`
3. 寫檔 → 重連 → 讀檔成功
4. Session A 寫 → Session B 讀不到
5. 不存在命令 → 正確 stderr

## 📈 效能基準

| 指標 | 目標 | 可接受 | 不可接受 |
|------|------|--------|----------|
| Exec P50 | <200ms | <300ms | >500ms |
| Exec P95 | <500ms | <800ms | >2s |
| Cold start | <15s | <30s | >60s |
