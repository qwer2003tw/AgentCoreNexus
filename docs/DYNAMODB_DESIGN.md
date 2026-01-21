# DynamoDB Tables Design Document

**Last Updated**: 2026-01-21  
**Version**: 1.0  
**Maintainer**: AgentCoreNexus Team

---

## Overview

本文檔記錄 AgentCoreNexus 專案中所有 DynamoDB tables 的設計決策、access patterns 和優化策略。

---

## 1. telegram-allowlist Table

### Purpose
管理 Telegram 用戶和群組的訪問權限，提供細粒度的權限控制。

### Schema Design

#### Primary Key
- **Partition Key**: `chat_id` (Number)
  - Telegram chat ID（正數為私人對話，負數為群組）
  - 唯一標識符

#### Attributes
| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| chat_id | Number | Yes | Telegram chat ID（主鍵） |
| username | String | Yes | Telegram username |
| enabled | Boolean | Yes | 是否啟用訪問權限 |
| role | String | No | 用戶角色：'admin' 或 'user' |
| permissions | Map | No | 細粒度權限：{ file_reader: Boolean } |
| created_at | String | No | 創建時間（ISO8601） |
| updated_at | String | No | 最後更新時間（ISO8601） |

#### Example Item
```json
{
  "chat_id": 316743844,
  "username": "qwer2003tw",
  "enabled": true,
  "role": "admin",
  "permissions": {
    "file_reader": true
  },
  "created_at": "2025-12-01T00:00:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

---

### Access Patterns

按頻率和重要性排序：

#### Pattern 1: Check User Permission (高頻 - 關鍵路徑)
**Operation**: GetItem  
**Frequency**: 每個訊息一次（~100-1000 次/天）  
**Latency**: ~5-10ms  
**Key**: chat_id

**Usage**:
```python
# telegram-adapter/src/allowlist.py
response = table.get_item(Key={"chat_id": chat_id})
```

**Performance Characteristics**:
- ✅ 使用主鍵查詢（最優性能）
- ✅ 平均延遲 < 10ms
- ✅ 一致性讀取

---

#### Pattern 2: Check File Permission (中頻)
**Operation**: GetItem + 權限檢查  
**Frequency**: 檔案上傳時（~10-50 次/天）  
**Latency**: ~5-10ms

**Usage**:
```python
response = table.get_item(Key={"chat_id": chat_id})
has_permission = response['Item'].get('permissions', {}).get('file_reader', False)
```

---

#### Pattern 3: List All Users (低頻 - 管理功能)
**Operation**: Scan  
**Frequency**: 管理員操作（~1-5 次/天）  
**Latency**: 100-500ms（可接受）

**Usage**:
```python
response = table.scan(Limit=50)
items = response.get('Items', [])
```

**Notes**:
- ⚠️ Scan 操作成本較高
- ✅ 僅用於低頻管理功能
- ✅ 預期數據量小（< 1000 users）

---

#### Pattern 4: Update User Status (低頻)
**Operation**: UpdateItem  
**Frequency**: 配置變更（~5-10 次/天）  
**Latency**: ~10-20ms

**Usage**:
```python
table.update_item(
    Key={"chat_id": chat_id},
    UpdateExpression="SET enabled = :enabled",
    ExpressionAttributeValues={":enabled": enabled}
)
```

---

#### Pattern 5: Get Statistics (低頻 - 監控)
**Operation**: Scan + 聚合  
**Frequency**: Dashboard 更新（~10-20 次/天）  
**Latency**: 200-1000ms（可接受）

**Notes**:
- ⚠️ 全表掃描
- ✅ 可考慮快取結果
- ✅ 預期數據量小

---

### Indexing Strategy

#### Current Indexes
- **Primary Key Only**: chat_id
  - ✅ 已優化主要查詢（Pattern 1, 2, 4）
  - ✅ 無需額外 GSI/LSI

#### Why No GSI/LSI?
1. **主要查詢已優化**: 99% 查詢使用主鍵
2. **數據量小**: < 1000 users，Scan 可接受
3. **成本考量**: GSI 增加成本和複雜度
4. **簡單性**: 維護更容易

#### Future Considerations
**如果需要以下查詢模式，才考慮添加 GSI**:

| Query Pattern | GSI Design | When Needed |
|--------------|------------|-------------|
| 按 username 查詢 | GSI: username (String) | 需要反向查找 chat_id |
| 按 role 過濾 | GSI: role (String) | 需要快速列出所有管理員 |
| 按 enabled 過濾 | GSI: enabled (Boolean) | 需要快速列出啟用/禁用用戶 |

**決策標準**:
- 查詢頻率 > 100 次/天
- 數據量 > 5000 records
- Scan 延遲 > 2 秒

---

### Performance Characteristics

#### Read Performance
- **GetItem**: 5-10ms (p95)
- **Scan**: 100-500ms（數據量 < 1000）
- **Consistency**: Strong consistency

#### Write Performance
- **PutItem**: 10-20ms (p95)
- **UpdateItem**: 10-20ms (p95)
- **DeleteItem**: 10-20ms (p95)

#### Capacity Planning
**Current Configuration**:
- **Billing Mode**: PAY_PER_REQUEST（按需計費）
- **Why**: 流量不可預測，避免過度配置
- **Cost**: ~$0.25-$1/month

**Provisioned Capacity 考量**:
- ❌ 不建議：流量波動大
- ✅ 適合場景：穩定的高流量（> 10,000 讀取/秒）

---

### Data Volume & Growth

#### Current State
- **Record Count**: ~100 users
- **Average Item Size**: ~300 bytes
- **Total Storage**: ~30 KB

#### Growth Projection
- **Growth Rate**: ~10 users/month
- **1 Year**: ~220 users
- **5 Years**: ~700 users

#### Retention Policy
- **Current**: 無限期保留
- **Cleanup**: 手動管理（disable 而非刪除）
- **Future**: 考慮添加 TTL 清理長期未使用帳號

---

### Backup & Recovery

#### Point-in-Time Recovery (PITR)
- **Status**: ✅ Enabled (2026-01-21)
- **Retention**: 35 days
- **Cost**: ~$1/month
- **Recovery Time**: ~幾分鐘

#### Use Cases
- 誤刪除恢復
- 誤修改回滾
- 災難恢復

#### Recovery Procedure
```bash
# 恢復到特定時間點
aws dynamodb restore-table-to-point-in-time \
  --source-table-name telegram-allowlist \
  --target-table-name telegram-allowlist-restored \
  --restore-date-time "2026-01-20T12:00:00Z"
```

---

### Optimization History

| Date | Change | Reason | Impact |
|------|--------|--------|--------|
| 2026-01-21 | 啟用 PITR | 數據保護 | +$1/month，數據安全 |
| 2026-01-21 | 添加 Connection Pooling | 減少冷啟動 | -10-15% 延遲 |

---

### Monitoring & Alerts

#### Key Metrics
- **Read Capacity**: < 10 RCU/秒
- **Write Capacity**: < 1 WCU/秒
- **Latency**: GetItem < 10ms (p95)
- **Throttles**: 0（PAY_PER_REQUEST 不會 throttle）

#### CloudWatch Alarms
```yaml
# 建議設置
- UserErrorsAlarm: > 10 errors/5min
- SystemErrorsAlarm: > 5 errors/5min
- HighLatencyAlarm: p95 > 50ms
```

---

### Security

#### Access Control
- **Least Privilege**: Lambda IAM roles 僅授予必要權限
- **Encryption at Rest**: ✅ AWS-managed key
- **Encryption in Transit**: ✅ TLS 1.2+

#### Sensitive Data
- **PII**: username（需謹慎處理）
- **Logging**: 不記錄完整 items，僅記錄 chat_id

---

### Cost Optimization

#### Current Costs (~$1-2/month)
- **Read**: $0.25/million requests × ~0.1M = $0.025
- **Write**: $1.25/million requests × ~0.01M = $0.0125
- **Storage**: $0.25/GB × 0.00003 GB = $0.000008
- **PITR**: ~$1/month

#### Optimization Strategies
1. ✅ Use PAY_PER_REQUEST（已實施）
2. ✅ 避免不必要的 Scan（已優化）
3. ✅ 使用 Connection Pooling（已實施）
4. ⚠️ 未來：考慮 batch operations

---

### Testing Strategy

#### Unit Tests
```python
# tests/test_allowlist.py
def test_check_allowed():
    assert check_allowed(316743844, "qwer2003tw") == True
    
def test_check_file_permission():
    assert check_file_permission(316743844) == True
```

#### Integration Tests
- Mock DynamoDB with moto
- Test error handling（table not found, item not found）
- Test concurrent access

---

### Future Enhancements

#### Planned (Next 6 Months)
- [ ] 添加 `last_access_at` timestamp
- [ ] 實施自動化清理（TTL）
- [ ] 添加使用統計（訊息數、檔案數）

#### Considering (Next 12 Months)
- [ ] 跨通道身份映射（unified_user_id）
- [ ] 群組權限管理（group_registry table）
- [ ] 權限繼承機制

---

## 2. Future Tables (計劃中)

### identity_map (跨通道身份)
**Purpose**: 統一管理跨通道用戶身份

**Schema**:
- PK: unified_user_id (String)
- Attributes: telegram_id, discord_id, web_id, groups[]

**Status**: 規劃階段

---

### group_registry (群組管理)
**Purpose**: 群組權限和成員管理

**Schema**:
- PK: group_id (String)
- Attributes: members[], policies, roles

**Status**: 規劃階段

---

## References

### Documentation
- [AWS DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [DynamoDB Pricing](https://aws.amazon.com/dynamodb/pricing/)
- [PITR Documentation](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html)

### Related Docs
- [Architecture Guide](./architecture-guide.md)
- [Deployment Guide](./deployment-guide.md)
- [Testing Guide](./TESTING.md)

---

**Version History**:
- v1.0 (2026-01-21): Initial documentation with comprehensive design details