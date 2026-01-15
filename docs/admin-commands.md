# 🔧 AgentCore Nexus 管理員指令完整指南

## 📋 概述

AgentCore Nexus 管理員系統提供完整的用戶和群組管理功能，支持通過 Telegram 指令進行所有管理操作。

**部署狀態：** ✅ 已部署到 us-west-2  
**權限系統：** 基於 DynamoDB role 欄位  
**支持類型：** 👤 私聊用戶 + 👥 Telegram 群組

---

## 🔑 權限系統

### 角色類型
- **Admin** (`role: "admin"`) - 👑 完整管理權限
- **User** (`role: "user"`) - 👤 基本使用權限
- **None** - 未授權用戶

### DynamoDB 數據結構
```json
{
  "chat_id": 316743844,        // 主鍵：正數=私聊，負數=群組
  "username": "qwer2003tw",    // Telegram 用戶名
  "enabled": true,              // 啟用狀態（布林值）
  "role": "admin",             // 角色：admin 或 user
  "added_by": "system",        // 添加者（可選）
  "added_at": "2026-01-06T..."  // 添加時間（可選）
}
```

---

## 📖 指令參考

### 1. 用戶管理指令

#### `/admin add <chat_id> [username]`
添加用戶或群組到允許名單

**示例：**
```
/admin add 123456789 john_doe        # 添加私聊用戶
/admin add -1001234567890 my_group   # 添加群組
/admin add 987654321                 # 自動生成用戶名
```

**回應：**
```
✅ 已添加到允許名單

👤 私聊
ID: 123456789
用戶名: @john_doe
狀態: 已啟用
角色: user
```

---

#### `/admin remove <chat_id>`
從允許名單移除用戶或群組

**示例：**
```
/admin remove 123456789              # 移除用戶
/admin remove -1001234567890         # 移除群組
```

**保護機制：**
- ⚠️ 無法移除自己

---

#### `/admin list`
列出所有允許名單中的用戶和群組

**示例：**
```
/admin list
```

**回應格式：**
```
📋 允許名單

👥 ✅ 👑 @my_group
   ID: -1001234567890 | 角色: admin

👤 ✅ 👑 @qwer2003tw
   ID: 316743844 | 角色: admin

👤 ✅ 👤 @testuser
   ID: 123456789 | 角色: user

總計: 3 個用戶/群組
```

**圖標說明：**
- 👥 = 群組，👤 = 私聊
- ✅ = 已啟用，❌ = 已禁用
- 👑 = 管理員，👤 = 普通用戶

---

#### `/admin info <chat_id>`
查看用戶或群組的詳細信息

**示例：**
```
/admin info 316743844
```

**回應：**
```
ℹ️ 用戶詳細信息

類型: 👤 私聊
ID: 316743844
用戶名: @qwer2003tw
狀態: ✅ 已啟用
角色: 👑 管理員
加入時間: 2026-01-06T12:00:00Z
添加者: system
```

---

### 2. 狀態控制指令

#### `/admin enable <chat_id>`
啟用已禁用的用戶（軟啟用）

**示例：**
```
/admin enable 123456789
```

---

#### `/admin disable <chat_id>`
禁用用戶但不刪除記錄（軟刪除）

**示例：**
```
/admin disable 123456789
```

**保護機制：**
- ⚠️ 無法禁用自己

---

### 3. 權限管理指令

#### `/admin promote <chat_id>`
將普通用戶升級為管理員

**示例：**
```
/admin promote 123456789
```

**回應：**
```
👑 已升級為管理員

ID: 123456789
用戶名: @john_doe
```

---

#### `/admin demote <chat_id>`
將管理員降級為普通用戶

**示例：**
```
/admin demote 123456789
```

**保護機制：**
- ⚠️ 無法降級自己
- 檢查是否已是普通用戶

---

### 4. 系統管理指令

#### `/admin stats`
查看系統統計信息

**示例：**
```
/admin stats
```

**回應：**
```
📊 系統統計信息

總用戶數: 5
  ├─ 👤 私聊: 3
  └─ 👥 群組: 2

啟用狀態:
  ├─ ✅ 已啟用: 4
  └─ ❌ 已禁用: 1

權限分布:
  ├─ 👑 管理員: 2
  └─ 👤 普通用戶: 3
```

---

#### `/admin broadcast <message>`
向所有啟用的用戶和群組廣播消息

**示例：**
```
/admin broadcast 系統將於今晚 23:00 進行維護，預計 30 分鐘
```

**行為：**
1. 先發送確認消息（包含預覽）
2. 向所有啟用用戶發送
3. 跳過發送者自己
4. 顯示發送結果統計

**回應：**
```
📢 準備廣播給 10 個用戶/群組

預覽：
系統將於今晚 23:00 進行維護...

發送中...

✅ 廣播完成

成功: 9
失敗: 0
總計: 10
```

---

#### `/admin help`
顯示所有可用的管理員指令

---

## 🎯 使用場景

### 場景 1：添加新用戶
```bash
# 用戶發送消息後，管理員添加
/admin add 123456789 new_user
```

### 場景 2：管理 Telegram 群組
```bash
# 將 Bot 添加到群組後，獲取群組 ID（從日誌）
# 然後添加群組到允許名單
/admin add -1001234567890 project_team
```

### 場景 3：臨時禁用騷擾用戶
```bash
# 禁用但不刪除記錄
/admin disable 123456789

# 稍後可以重新啟用
/admin enable 123456789
```

### 場景 4：系統公告
```bash
# 向所有用戶廣播重要消息
/admin broadcast 🎉 新功能上線！現在支持圖片分析功能
```

### 場景 5：升級信任用戶為管理員
```bash
# 檢查用戶信息
/admin info 123456789

# 確認後升級
/admin promote 123456789
```

---

## ⚠️ 安全保護

系統內建多重保護機制：

1. **權限驗證**
   - 所有 /admin 指令都需要管理員權限
   - `@require_admin` 裝飾器自動驗證

2. **自我保護**
   - 無法移除自己
   - 無法禁用自己
   - 無法降級自己

3. **存在性檢查**
   - 操作前檢查用戶是否存在
   - 防止重複添加相同用戶

4. **日誌記錄**
   - 所有管理操作記錄到 CloudWatch
   - 包含操作者、目標、時間戳

---

## 📊 監控與日誌

### CloudWatch Logs
所有管理操作都會記錄：
```json
{
  "event_type": "admin_command",
  "chat_id": 316743844,
  "username": "qwer2003tw",
  "subcommand": "add",
  "target_chat_id": 123456789
}
```

### 查看日誌
```bash
aws logs tail /aws/lambda/telegram-adapter-receiver \
  --region us-west-2 \
  --filter-pattern "admin_command"
```

---

## 🔄 快速操作指南

### 查看當前所有用戶
```
/admin list
```

### 批量管理流程
1. `/admin stats` - 查看整體狀況
2. `/admin list` - 查看詳細名單
3. `/admin info <ID>` - 檢查特定用戶
4. 根據需要執行操作

### 緊急廣播
```
/admin broadcast ⚠️ 緊急通知：系統將在 5 分鐘後重啟
```

---

## 💡 最佳實踐

1. **定期審查**
   - 每週執行 `/admin stats` 檢查用戶數量
   - 每月執行 `/admin list` 審查用戶列表

2. **謹慎授權**
   - 新用戶先添加為普通用戶
   - 觀察一段時間後再考慮升級管理員
   - 至少保持 2 個管理員以防萬一

3. **善用禁用功能**
   - 可疑用戶先禁用而非刪除
   - 保留記錄方便追蹤
   - 確認無誤後再永久刪除

4. **廣播使用**
   - 重要公告前先測試
   - 避免頻繁廣播（用戶體驗）
   - 消息簡潔明確

---

## 🚀 下一步擴展

可以考慮添加的功能：

1. **日誌查看** - `/admin logs` 直接在 Telegram 查看日誌
2. **配置管理** - `/admin config` 動態修改系統配置
3. **工具管理** - `/admin tools` 啟用/禁用特定 AI 工具
4. **自動批准** - `/admin auto_approve` 新用戶自動加入
5. **臨時訪問** - `/admin temp_access` 給予時限訪問權

---

## 📞 技術支持

如有問題，請查看：
- CloudWatch Logs: `/aws/lambda/telegram-adapter-receiver`
- DynamoDB Table: `telegram-allowlist`
- EventBridge Bus: `telegram-adapter-events`

**系統狀態：** ✅ 完全運作  
**最後更新：** 2026-01-06  
**區域：** us-west-2
