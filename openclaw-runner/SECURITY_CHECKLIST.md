# 安全合規檢查清單

> 基於公司 aws-security-rules.csv 與 aws-palisade-slats.pdf

---

## 🔴 關鍵規則（必須遵守）

### 1. 密碼/憑證管理

| 規則 | 嚴重性 | 合規做法 |
|------|--------|----------|
| **禁止硬編碼憑證** | HIGH | 使用 Secrets Manager / SSM Parameter Store |
| **禁止硬編碼 API Key** | HIGH | 環境變數注入，不寫入程式碼 |
| **禁止硬編碼 HMAC Key** | HIGH | 運行時從 Secrets Manager 取得 |

```yaml
# ✅ 正確做法：Task Definition 引用 Secrets Manager
secrets:
  - name: EXEC_SECRET
    valueFrom: arn:aws:secretsmanager:region:account:secret:exec-hmac-key

# ❌ 錯誤做法：硬編碼
environment:
  - name: EXEC_SECRET
    value: "abc123..."  # 違規！
```

---

### 2. Container 安全

| 規則 | 嚴重性 | 合規做法 |
|------|--------|----------|
| **禁止外部 Docker Registry** | HIGH | 只用 ECR |
| **禁止 DockerHub Image** | HIGH | 先 pull 到 ECR 再用 |

```yaml
# ✅ 正確做法：使用 ECR
image: 123456789.dkr.ecr.us-west-2.amazonaws.com/openclaw-runner:latest

# ❌ 錯誤做法：直接用 DockerHub
image: python:3.11-slim  # 違規！需要先 mirror 到 ECR
```

---

### 3. IAM 權限

| 規則 | 嚴重性 | 合規做法 |
|------|--------|----------|
| **禁止過度寬鬆的 AssumeRole** | HIGH | 明確指定 Principal |
| **最小權限原則** | HIGH | 只給必要的權限 |

```yaml
# ✅ 正確做法：明確指定
AssumeRolePolicyDocument:
  Statement:
    - Effect: Allow
      Principal:
        Service: ecs-tasks.amazonaws.com
      Action: sts:AssumeRole

# ❌ 錯誤做法：過度寬鬆
Principal: "*"  # 違規！
```

---

### 4. 網路安全

| 規則 | 嚴重性 | 合規做法 |
|------|--------|----------|
| **禁止 SSLv3/TLSv1** | HIGH | 最低 TLS 1.2 |
| **EFS 必須加密** | HIGH | 啟用 at-rest + in-transit 加密 |

---

### 5. Python 安全

| 規則 | 嚴重性 | 合規做法 |
|------|--------|----------|
| **禁止 yaml.load()** | HIGH | 用 yaml.safe_load() |

```python
# ❌ 錯誤
data = yaml.load(file)  # 違規！

# ✅ 正確
data = yaml.safe_load(file)
```

---

## 📋 開發檢查清單

### 每次 Commit 前

- [ ] 沒有硬編碼的密碼/Token/Key
- [ ] Container image 來自 ECR
- [ ] IAM policy 使用最小權限
- [ ] 使用 yaml.safe_load()

### 每個 PR 前

- [ ] 執行 `ruff check .`
- [ ] 執行 `cfn-lint template.yaml`
- [ ] 執行 `bandit -r src/`
- [ ] 檢查 Secrets Manager 引用正確

### 部署前

- [ ] EFS 加密已啟用
- [ ] ALB 使用 TLS 1.2+
- [ ] CloudWatch Logs 已設定
