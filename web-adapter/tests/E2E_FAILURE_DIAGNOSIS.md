# E2E 測試失敗診斷報告

**診斷日期**: 2026-01-28  
**失敗測試**: 5/49（10%）  
**根本原因**: Response Router Lambda 代碼損壞  
**修復方式**: 重新部署 web-adapter stack

---

## 🚨 根本原因發現

### Response Router Lambda 代碼損壞

**錯誤訊息**：
```
[ERROR] Runtime.UserCodeSyntaxError: 
Syntax error in module 'router': 
source code string cannot contain null bytes
```

**發生時間**: 測試運行期間（07:04-07:11）

**影響範圍**: 所有需要 AI 回覆的測試
- AI 處理完成 ✅
- 但回覆無法路由到前端 ❌
- 前端等待超時 ❌

---

## 📊 完整診斷流程

### 1. 初步假設（錯誤）

**假設**: 超時配置不足
```
Lambda p95: 25.7 秒
測試超時: 15 秒
結論: 需要增加超時
```

**為什麼錯誤**: 即使增加到 60 秒仍然 100% 失敗

---

### 2. 深入診斷（正確）

**Step 1: 檢查 WebSocket 連接**
```bash
aws logs tail /aws/lambda/agentcore-web-adapter-ws-connect --since 30m

結果: ✅ 連接成功
- 所有 4 個測試帳號都連接成功
- Connection established for aws-e2e-test1@test.com
```

**Step 2: 檢查訊息接收**
```bash
aws logs tail /aws/lambda/agentcore-web-adapter-ws-default --since 30m

結果: ✅ 訊息收到
- Received WebSocket message from: X4kpJdttPHcCHqQ=
- 處理時間: 30-180ms（非常快）
```

**Step 3: 檢查 AI 處理**
```bash
aws logs filter-log-events --log-group-name /aws/lambda/agentcore-ai-processor-main

結果: ✅ AI 有處理
- Processing EventBridge event
- Processing message from web
- Processing text message from Unknown
```

**Step 4: 檢查回覆路由（發現問題）**
```bash
aws logs tail /aws/lambda/agentcore-web-adapter-response-router --since 30m

結果: ❌ Lambda 完全無法執行
- Runtime.UserCodeSyntaxError: null bytes in source code
- 100% 失敗率
- Memory Used: 只有 46 MB（正常是 89 MB）
- 說明連初始化都失敗
```

---

## 🎯 問題根源

### Lambda 代碼損壞的可能原因

1. **部署過程中的文件損壞**
   - SAM build 或 upload 時出錯
   - S3 存儲損壞
   - 網絡傳輸問題

2. **編輯器問題**
   - 不太可能（源代碼檢查正常）

3. **Lambda Runtime 更新**
   - AWS 自動更新 Lambda runtime
   - 可能觸發了某些不兼容問題

---

## ✅ 修復方案

### 重新部署整個 Stack

```bash
cd web-adapter/infrastructure
sam build -t web-channel-template.yaml
sam deploy --template-file web-channel-template.yaml \
  --stack-name agentcore-web-adapter \
  --region us-west-2 \
  --resolve-s3 \
  --no-confirm-changeset \
  --capabilities CAPABILITY_IAM
```

**結果**：
- ✅ ResponseRouterFunction UPDATE_COMPLETE
- ✅ 所有 Lambda 重新部署
- ✅ 錯誤消失

---

## 📋 診斷總結

### 請求流分析

**完整流程**：
```
Frontend (測試) 
  ↓ WebSocket
✅ ws-connect (77ms) - 連接成功
  ↓
✅ ws-default (30-180ms) - 訊息接收
  ↓ EventBridge
✅ AI Processor (13-26 秒) - AI 處理
  ↓ EventBridge (message.completed)
❌ Response Router (CRASH) - 代碼損壞
  ↓ (斷點)
❌ Frontend 等待 60 秒 - 超時
```

### 為什麼花了這麼久診斷？

**錯誤的方向**：
1. 先假設是超時配置問題
2. 增加超時到 60 秒
3. 測試仍失敗
4. 診斷性能（p95: 25.7秒）
5. 發現配置應該足夠

**正確的方向**（最終）：
1. 檢查完整的請求流
2. 逐層診斷（由外到內）
3. 發現 Response Router 完全 CRASH
4. 重新部署修復

**教訓**: 
- 不要假設錯誤訊息就是根本原因
- "Timeout" 可能是症狀，不是病因
- 系統性失敗（100%）通常是配置或代碼問題，不是性能問題

---

## 🎯 預期結果

### 修復後的狀態

**1. Response Router 正常**
```
之前: Runtime.UserCodeSyntaxError (100% 失敗)
現在: ✅ 沒有錯誤
```

**2. AI 回覆可以送達**
```
AI 處理 (15-25秒)
  ↓
Response Router ✅（現在正常）
  ↓
Frontend 收到回覆
  ↓
測試通過
```

**3. 測試失敗預期**
```
修復前: 5/49 失敗
修復後: 預期 0-1 失敗

剩餘問題: T1 Admin 測試（loginAsUser 問題）
可能需要單獨修復
```

---

## 📝 後續行動

### 1. 重新運行 CI/CD（立即）

```bash
# Trigger GitHub Actions
git commit --allow-empty -m "test: verify response router fix"
git push
```

### 2. 驗證修復（10 分鐘後）

- 查看 GitHub Actions 結果
- 預期：Chat 測試全部通過（4/4）
- Admin T1 可能仍失敗（不同的問題）

### 3. 如果 Admin T1 仍失敗（單獨處理）

需要診斷：
- 為什麼 `loginAsUser` 找不到「新對話」按鈕？
- 查看失敗截圖
- 可能是權限或路由問題

---

## 🎓 關鍵學習

### 1. 診斷順序很重要

**錯誤順序**：
```
看到超時 → 假設是慢 → 增加超時
```

**正確順序**：
```
看到超時 → 診斷完整流程 → 找到斷點 → 修復根本原因
```

### 2. 100% 失敗 ≠ 慢

```
如果是性能問題:
- 有些會成功，有些會失敗
- 失敗率隨超時增加而降低

如果是功能問題:
- 100% 失敗，無論超時多長
- 這是我們的情況
```

### 3. Lambda 代碼損壞是罕見但嚴重的問題

**特徵**：
- `null bytes` 錯誤
- 連初始化都失敗
- Memory Used 異常低（46 MB vs 正常 89 MB）

**修復**：
- 重新部署（清除損壞的代碼）
- 確保 SAM build 乾淨

### 4. 不要只調整配置，要修復根本問題

**我們做的**：
- ✅ 診斷了性能（p95: 25.7秒）
- ✅ 調整了超時（60秒，合理）
- ✅ 修復了 GitHub workflow（E2E_ENV=aws）
- ✅ 發現並修復了 Router 損壞

**如果只調超時**：
- ❌ 測試仍會失敗
- ❌ 問題被隱藏
- ❌ 生產環境受影響

---

## 📚 相關文檔

- `PERFORMANCE_OPTIMIZATION.md` - 性能改善計劃（仍然需要）
- `GITHUB_SECRETS_REQUIRED.md` - CI/CD 配置指南
- `.github/workflows/tests.yml` - 已修復的 workflow

---

**報告版本**: v1.0  
**診斷耗時**: 約 2.5 小時  
**修復狀態**: Response Router 已修復，等待測試驗證  
**維護者**: DevOps Team