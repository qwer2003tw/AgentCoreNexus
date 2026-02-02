# 安全合規檢查清單

> 基於公司 aws-security-rules.csv 與 aws-palisade-slats.pdf

---

## 🔴 關鍵規則

### 1. 密碼/憑證
- ❌ 禁止硬編碼
- ✅ 使用 Secrets Manager / SSM Parameter Store

### 2. Container
- ❌ 禁止外部 Registry (DockerHub, gcr.io)
- ✅ 只用 ECR (先 mirror 再用)

### 3. IAM
- ❌ 禁止 `Principal: "*"` 或 `Action: "*"`
- ✅ 最小權限原則

### 4. 加密
- ✅ EFS: Encrypted=true + TLS in-transit
- ✅ ALB: TLS 1.2+ (ELBSecurityPolicy-TLS13-1-2-2021-06)

### 5. Python
- ❌ `yaml.load()`
- ✅ `yaml.safe_load()`

---

## 📋 Commit 前檢查

- [ ] 沒有硬編碼的密碼/Token/Key
- [ ] Container image 來自 ECR
- [ ] IAM policy 使用最小權限
- [ ] 使用 yaml.safe_load()

## 📋 PR 前檢查

```bash
ruff check .
cfn-lint infrastructure/**/*.yaml
bandit -r runner/src/ ai-processor/
```

## 📋 部署前檢查

- [ ] EFS 加密已啟用
- [ ] ALB 使用 TLS 1.2+
- [ ] CloudWatch Logs 已設定
