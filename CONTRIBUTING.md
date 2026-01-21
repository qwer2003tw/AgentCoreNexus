# 貢獻指南

感謝你考慮為 AgentCore Nexus 做出貢獻！

---

## 🎯 貢獻方式

### 報告 Bug
- 使用 GitHub Issues
- 提供詳細的重現步驟
- 包含環境資訊
- 附上相關日誌

### 提出功能建議
- 使用 GitHub Issues
- 說明使用場景
- 描述預期行為

### 提交代碼
- Fork 專案
- 創建功能分支
- 提交 Pull Request

---

## 📋 開發流程

### 1. 環境設置

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/AgentCoreNexus.git
cd AgentCoreNexus

# Install dependencies
cd ai-processor && pip install -r requirements.txt
cd ../telegram-adapter && pip install -r requirements.txt
cd ../web-adapter/frontend && npm install
```

### 2. 創建功能分支

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 3. 開發與測試

**代碼規範**：
- 使用 Ruff 檢查：`ruff check .`
- 格式化：`ruff format .`
- 遵循 PEP 8（Python）
- 遵循 ESLint + Prettier（TypeScript）

**測試要求**：
- 新功能必須有測試
- 測試覆蓋率 > 80%
- 所有測試必須通過

```bash
# 執行測試
make test

# 或單獨測試各組件
make test-agentcore   # AI Processor
make test-lambda      # Telegram Adapter
make test-web         # Web Adapter
```

### 4. Commit 規範

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```bash
feat: 添加新功能
fix: 修復 bug
docs: 文檔更新
test: 測試相關
refactor: 代碼重構
chore: 維護任務
```

**範例**：
```bash
git commit -m "feat(ai-processor): add support for video attachments"
git commit -m "fix(telegram-adapter): handle empty messages correctly"
git commit -m "docs: update deployment guide with new Stack names"
```

### 5. 提交 Pull Request

**PR 檢查清單**：
- [ ] 所有測試通過（`make test`）
- [ ] Ruff 檢查通過（`ruff check .`）
- [ ] 代碼已格式化（`ruff format .`）
- [ ] 文檔已更新
- [ ] Commit 訊息符合規範
- [ ] PR 描述清楚（做了什麼、為什麼、如何測試）

**PR Template**：
```markdown
## 變更描述
（簡述你的變更）

## 變更類型
- [ ] 新功能
- [ ] Bug 修復
- [ ] 文檔更新
- [ ] 性能優化
- [ ] 重構

## 測試
（如何測試你的變更）

## 相關 Issue
Closes #XXX
```

---

## 🧪 測試指南

### 單元測試
- 測試代碼邏輯
- Mock 外部依賴
- 快速執行（< 10秒）

### 整合測試
- 測試組件間互動
- Mock 部分外部服務
- 中等速度（< 1分鐘）

### E2E 測試
- 測試完整流程
- 連接真實 AWS（或 Mock）
- 較慢（幾分鐘）

**運行真實 AWS E2E**：
```bash
cd web-adapter/tests
E2E_ENV=aws npm test
```

---

## 📝 代碼規範

### Python（ai-processor, telegram-adapter）

**風格**：
- PEP 8
- Type hints
- Docstrings（Google style）

**範例**：
```python
def process_message(text: str, user_id: str) -> dict[str, Any]:
    """
    處理用戶消息
    
    Args:
        text: 消息文本
        user_id: 用戶 ID
        
    Returns:
        處理結果字典
    """
    # 實現...
```

### TypeScript（web-adapter/frontend）

**風格**：
- ESLint + Prettier
- Functional components
- TypeScript strict mode

**範例**：
```typescript
interface Message {
  id: string
  content: string
  timestamp: string
}

export const MessageList: React.FC<{ messages: Message[] }> = ({ messages }) => {
  // 實現...
}
```

---

## 🏗️ 架構指南

### 添加新的 Channel Adapter

參考 `docs/NEW_CHANNEL_GUIDE.md`（待創建）

**基本步驟**：
1. 創建 `[channel]-adapter/` 目錄
2. 實現 webhook 接收或 API
3. 標準化訊息為 Universal Message Schema
4. 發送到 EventBridge
5. 實現 Response Router
6. 添加測試
7. 更新文檔

---

## 📚 相關資源

- [架構設計指南](docs/architecture-guide.md)
- [部署指南](docs/deployment-guide.md)
- [測試指南](docs/TESTING.md)
- [代碼質量指南](docs/CODE_QUALITY.md)

---

## 🤝 社群

- GitHub Issues: 提問和討論
- Pull Requests: 代碼貢獻

---

## 📜 行為準則

請尊重所有貢獻者，保持專業和友善的態度。

---

**感謝你的貢獻！** 🎉