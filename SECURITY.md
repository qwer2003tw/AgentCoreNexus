# Security Policy

AgentCore Nexus 安全政策

---

## 🔒 支援的版本

| Version | Supported          |
| ------- | ------------------ |
| 0.9.x   | :white_check_mark: |
| 0.8.x   | :white_check_mark: |
| < 0.8   | :x:                |

---

## 🚨 報告安全漏洞

**請勿公開報告安全問題！**

### 報告方式

1. **私密報告**：發送 email 至 [security@your-domain.com]
2. **包含資訊**：
   - 漏洞描述
   - 影響範圍
   - 重現步驟
   - 建議修復（如有）

### 響應時程

- **確認**：24 小時內
- **初步評估**：48 小時內
- **修復發布**：視嚴重程度（Critical: 7天內, High: 14天內）

---

## 🛡️ 安全特性

### Telegram Adapter
- **Webhook Secret Token**: 64 字符隨機生成（A-Z/a-z/0-9）
- **白名單驗證**: DynamoDB + chat_id + username 雙重檢查
- **Secrets Manager**: 自動加密存儲

### Web Adapter
- **JWT 認證**: HS256 算法，7天有效期
- **密碼加密**: Bcrypt（12 rounds）
- **Rate Limiting**: 5次失敗鎖定15分鐘
- **Lambda Authorizer**: 驗證所有請求
- **XSS 防護**: 輸入驗證與清理
- **首次登入**: 強制修改密碼

### 基礎設施
- **HTTPS Only**: 所有 API
- **DynamoDB 加密**: SSE 自動啟用
- **最小權限**: IAM policies 遵循最小權限原則
- **安全審計**: CloudWatch 日誌記錄所有訪問

---

## 🔐 最佳實踐

### 開發者

**處理 Secrets**：
- ✅ 使用 Secrets Manager 或 Parameter Store
- ❌ 不要硬編碼在代碼中
- ❌ 不要提交到 Git

**環境變數**：
- ✅ 使用 .env.example 作為模板
- ❌ 不要提交 .env 文件
- ✅ 在 .gitignore 中排除敏感文件

**依賴管理**：
- ✅ 定期更新依賴
- ✅ 檢查已知漏洞（`pip-audit`, `npm audit`）
- ✅ 鎖定版本（requirements.txt, package-lock.json）

### 部署者

**AWS 安全**：
- ✅ 使用 IAM 角色（不要用 root）
- ✅ 啟用 MFA
- ✅ 最小權限原則
- ✅ 定期輪換 Secrets
- ✅ 啟用 CloudTrail 審計

**網絡安全**：
- ✅ 使用 VPC（生產環境）
- ✅ 配置 Security Groups
- ✅ 使用 WAF（如有公開 API）

**監控**：
- ✅ CloudWatch 告警
- ✅ 異常行為監控
- ✅ 成本告警

---

## 📊 安全檢查清單

### 代碼提交前
- [ ] 沒有硬編碼的 secrets
- [ ] 沒有敏感資訊在日誌中
- [ ] 輸入驗證完整
- [ ] 錯誤訊息不洩漏內部資訊
- [ ] 依賴無已知漏洞

### 部署前
- [ ] Secrets 已配置
- [ ] IAM 權限已檢查
- [ ] CloudWatch 告警已設置
- [ ] 備份策略已驗證

---

## 🔍 已知安全考量

### Telegram Webhook
- Secret token 驗證
- Allowlist 雙重檢查
- API Gateway rate limiting

### Web Authentication
- JWT 有效期管理
- 密碼強度要求
- Session 管理

### Cross-Channel Binding
- 6位數驗證碼（100萬組合）
- 5分鐘有效期
- 一次性使用

---

## 📜 安全更新

### 如何獲取安全更新

- Watch GitHub repository
- 訂閱 releases
- 查看 CHANGELOG.md

### 安全補丁

Critical 安全問題會發布 patch 版本（0.X.Y）

---

## 🏆 安全貢獻者

感謝所有報告和修復安全問題的貢獻者！

---

**最後更新**: 2026-01-15  
**聯絡**: security@your-domain.com（待配置）