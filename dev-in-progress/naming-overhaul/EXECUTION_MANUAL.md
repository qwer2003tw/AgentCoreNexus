# 完整重構執行手冊

**版本**: v1.0  
**創建**: 2026-01-15 15:26 PM  
**狀態**: Phase 1-2 完成，剩餘工作指南

---

## ✅ 已完成工作（Phase 1-2）

**Commit**: 827ab7f  
**變更**: 283 files

### Phase 1: 數據備份
- ✅ 5 個 DynamoDB 表
- ✅ 3 個 Stack 配置
- ✅ Secrets Manager
- ✅ 位置：dev-in-progress/naming-overhaul/backup/

### Phase 2: 目錄重組
- ✅ telegram-agentcore-bot → ai-processor
- ✅ telegram-lambda → telegram-adapter
- ✅ web-channel → web-adapter
- ✅ tests/e2e → tests/integration
- ✅ Makefile 完全更新
- ✅ 兩個 template.yaml 更新

---

## 📋 剩餘工作（Phase 3-11）

### Phase 3: 代碼完整更新（6-8h）

#### 3.1 run_all_tests.sh（需手動執行 sed）
```bash
cd /home/ec2-user/Projects/AgentCoreNexus
sed -i 's/telegram-agentcore-bot/ai-processor/g' run_all_tests.sh
sed -i 's/telegram-lambda/telegram-adapter/g' run_all_tests.sh
sed -i 's/web-channel/web-adapter/g' run_all_tests.sh
```

#### 3.2 README.md 更新（所有組件路徑）
- 搜尋並替換所有舊路徑

#### 3.3 web-adapter/infrastructure/web-channel-template.yaml
- Stack 名稱：agentcore-web-adapter
- 所有 Function 名稱
- Exports 名稱
- ImportValue 更新

#### 3.4 各組件 README 和文檔更新
- ai-processor/README.md
- telegram-adapter/README.md
- telegram-adapter/docs/
- web-adapter/README.md

#### 3.5 .clinerules/ 路徑更新
- deployment/ 下的文檔

#### 3.6 docs/ 核心文檔更新
- docs/architecture-guide.md
- docs/README.md
- docs/STACK_MANAGEMENT.md
- docs/deployment-guide.md

---

### Phase 4: Schema 與 Tags（2h）

#### 4.1 Universal Message Schema
**文件**: schemas/message.schema.json
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Universal Message Schema",
  "version": "1.0.0",
  "type": "object",
  "required": ["messageId", "timestamp", "channel", "user", "content"],
  "properties": {
    "messageId": {"type": "string"},
    "timestamp": {"type": "string", "format": "date-time"},
    "channel": {
      "type": "object",
      "required": ["type", "channelId"],
      "properties": {
        "type": {"enum": ["telegram", "web", "discord", "slack"]},
        "channelId": {"type": "string"},
        "metadata": {"type": "object"}
      }
    },
    "user": {
      "type": "object",
      "required": ["id", "channelUserId"],
      "properties": {
        "id": {"type": "string"},
        "channelUserId": {"type": "string"},
        "username": {"type": "string"},
        "displayName": {"type": "string"}
      }
    },
    "content": {
      "type": "object",
      "required": ["messageType"],
      "properties": {
        "text": {"type": "string"},
        "messageType": {"enum": ["text", "image", "file", "video", "audio"]},
        "attachments": {"type": "array"}
      }
    }
  }
}
```

**文件**: schemas/README.md
```markdown
# Universal Message Schema

所有 Channel Adapters 必須遵循此 schema

## Version: 1.0.0

## 驗證
使用 jsonschema 驗證訊息格式
```

#### 4.2 統一 Tags（所有 templates）
```yaml
Tags:
  - Key: Project
    Value: AgentCoreNexus
  - Key: Component
    Value: [ai-processor|telegram-adapter|web-adapter]
  - Key: Environment
    Value: !Ref Environment
  - Key: ManagedBy
    Value: SAM
```

#### 4.3 EventBridge DLQ
**在 telegram-adapter/template.yaml 添加**：
```yaml
EventBridgeDLQ:
  Type: AWS::SQS::Queue
  Properties:
    QueueName: !Sub '${AWS::StackName}-eventbridge-dlq'
    MessageRetentionPeriod: 1209600

# 在 Rules 添加 DeadLetterConfig
MessageReceivedRule:
  Properties:
    DeadLetterConfig:
      Arn: !GetAtt EventBridgeDLQ.Arn
```

---

### Phase 5: 專業化文檔（2-3h）

#### 5.1 LICENSE（MIT）
```
MIT License

Copyright (c) 2026 AgentCoreNexus Team

Permission is hereby granted...
```

#### 5.2 CONTRIBUTING.md
（完整貢獻指南）

#### 5.3 CHANGELOG.md
```markdown
# Changelog

## [0.9.0] - 2026-01-15
### Changed
- Major refactoring: Complete naming overhaul
- telegram-agentcore-bot → ai-processor
- telegram-lambda → telegram-adapter
- web-channel → web-adapter
- All Stacks renamed with agentcore- prefix
```

#### 5.4 其他文檔
- SECURITY.md
- ENV.md
- API.md
- NEW_CHANNEL_GUIDE.md

#### 5.5 Makefile 補充
```makefile
setup:
	@echo "🔧 初始化開發環境..."
	# 安裝依賴

lint:
	@echo "🔍 執行代碼檢查..."
	ruff check .

format:
	@echo "🎨 格式化代碼..."
	ruff format .

validate:
	@echo "✅ 驗證配置..."
	# SAM validate
```

---

### Phase 6: .clinerules 更新（1h）

**需要創建的 4 個文件**：

1. `.clinerules/rules/naming-standards.md`
2. `.clinerules/rules/refactoring-protocol.md`
3. `.clinerules/workflows/backup-restore.md`
4. `.clinerules/deployment/stack-management-best-practices.md`

（內容在前面已詳細定義）

---

### Phase 7-11: Stack 重建（6-8h）

**⚠️ 破壞性變更，需要謹慎執行**

#### Phase 7: 準備刪除
```bash
# 1. Disable EventBridge Rules
aws events disable-rule \
  --name telegram-lambda-receiver-message-received \
  --event-bus-name telegram-lambda-receiver-events \
  --region us-west-2

# 2. 最終備份確認
ls -lh dev-in-progress/naming-overhaul/backup/

# 3. 記錄當前 Exports
aws cloudformation describe-stacks ...
```

#### Phase 8-9: Stack 刪除與重建
（詳細步驟在 EXECUTION_SUMMARY.md）

#### Phase 10: 數據恢復
（使用 backup/ 下的數據）

#### Phase 11: 測試驗證
（所有測試必須通過）

---

## 🎯 續接指南（下次對話）

### 開始指令
```bash
# 1. 切換到重構分支
cd /home/ec2-user/Projects/AgentCoreNexus
git checkout refactor/complete-naming-overhaul

# 2. 查看進度
cat dev-in-progress/naming-overhaul/MASTER_PROGRESS.md
cat dev-in-progress/naming-overhaul/EXECUTION_MANUAL.md

# 3. 從 Phase 3 繼續...
```

### 檢查點狀態
- Checkpoint 1（代碼）：Phase 1-2 ✅
- Checkpoint 2（文檔）：待執行
- Checkpoint 3（Stack）：待執行

---

## 📊 進度追蹤

**完成**: 2/11 Phases（18%）  
**剩餘**: Phase 3-11（82%）  
**預計時間**: 還需 14-18 小時

---

**使用此手冊**：下次對話直接讀取並按步驟執行