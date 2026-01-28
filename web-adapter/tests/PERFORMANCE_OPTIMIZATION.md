# Web Adapter 性能優化計劃

**創建日期**: 2026-01-28  
**觸發原因**: E2E 測試診斷發現性能偏慢  
**優先級**: Medium（2 週內完成）

---

## 📊 當前性能基準（2026-01-28）

### Lambda 執行時間（agentcore-ai-processor-main）

**數據來源**: 過去 24 小時，217 個樣本

```
最小值：   0.3 秒（簡單查詢/冷啟動前）
平均值：  15.2 秒
中位數：  15.3 秒 ⚠️
p95：     25.7 秒 ⚠️
p99：     29.1 秒
最大值：  32.3 秒
```

### 冷啟動影響
- Init Duration: ~2 秒（1.9-2.1 秒）
- 記憶體使用: 119-213 MB（平均 ~180 MB）

### 與競爭對手對比

| 服務 | 典型響應時間 | 我們的 p95 | 差距 |
|------|-------------|-----------|------|
| ChatGPT | 2-5 秒 | 25.7 秒 | **5-13 倍** |
| Claude | 3-8 秒 | 25.7 秒 | **3-9 倍** |

**結論**: 性能可接受但不理想，需要優化

---

## 🎯 優化目標

### 短期目標（2 週）
- **p95**: 25.7秒 → **15秒**（改善 42%）
- **平均**: 15.2秒 → **10秒**（改善 34%）
- **冷啟動**: 2秒 → **0秒**（Provisioned Concurrency）

### 長期目標（1-2 月）
- **p95**: 15秒 → **8秒**（接近競爭對手）
- **平均**: 10秒 → **5秒**
- **用戶感知**: 添加 streaming（立即回應）

---

## 🔧 優化方案

### Phase 1: Lambda 配置優化（預期改善 20-30%）

**1.1 增加 Lambda 內存**
```yaml
# template.yaml
MemorySize: 1024  # 當前
↓
MemorySize: 2048  # 建議（更快的 CPU）
```

**預期效果**:
- CPU 性能提升 ~2 倍
- 處理時間減少 20-30%
- 成本增加 ~100%（但處理更快，實際成本增加 <50%）

**1.2 啟用 Provisioned Concurrency**
```yaml
ProvisionedConcurrencyConfig:
  ProvisionedConcurrentExecutions: 1
```

**預期效果**:
- 消除 2 秒冷啟動
- 改善 ~13% 總時間（2秒 / 15秒）
- 成本: +$30-40/月

---

### Phase 2: Bedrock 調用優化（預期改善 10-20%）

**2.1 Prompt 優化**
- 檢查是否有不必要的長 system prompt
- 減少 context 長度
- 使用更精簡的指令

**2.2 考慮使用更快的模型**
```
當前: Claude 3.5 Sonnet
替代: 
- Claude 3 Haiku（更快但稍弱）
- 根據查詢類型動態選擇模型
```

**2.3 實施 Streaming**
```python
# 不減少總時間，但改善用戶感知
# 用戶立即看到回應開始
```

---

### Phase 3: 架構優化（預期改善 5-10%）

**3.1 EventBridge 延遲**
- 測量 EventBridge 傳遞時間
- 考慮直接調用（如果延遲顯著）

**3.2 WebSocket 優化**
- 使用更快的訊息傳遞
- 減少輪詢間隔

**3.3 數據庫查詢**
- 檢查是否有不必要的 DynamoDB 讀取
- 優化記憶體載入

---

## 📈 成本效益分析

### 方案 A: 最小投入
- 增加內存到 1536 MB
- **成本**: +$15/月
- **效果**: p95 降到 20 秒

### 方案 B: 平衡方案（推薦）
- 增加內存到 2048 MB
- 啟用 1 個 Provisioned Concurrency
- **成本**: +$50-60/月
- **效果**: p95 降到 15 秒

### 方案 C: 激進優化
- 內存 2048 MB
- Provisioned Concurrency × 2
- Streaming 實施
- **成本**: +$100-120/月
- **效果**: p95 降到 8-10 秒

---

## 🧪 驗證方法

### 測試腳本

```bash
# 測試 AI 處理時間
for i in {1..20}; do
  echo "Test $i"
  time aws lambda invoke \
    --function-name agentcore-ai-processor-main \
    --payload '{"message":"1+1等於多少？"}' \
    --region us-west-2 \
    response.json
  sleep 1
done
```

### 監控指標

**需要追蹤**:
- Lambda Duration (p50, p95, p99)
- ConcurrentExecutions
- Throttles（如果有）
- Memory utilization

**CloudWatch Dashboard**:
- 創建自動化監控面板
- 每週檢查性能趨勢

---

## 📋 實施計劃

### Week 1: Lambda 配置
- [ ] 增加內存到 2048 MB
- [ ] 部署並測試
- [ ] 測量改善效果

### Week 2: Provisioned Concurrency
- [ ] 啟用 1 個 instance
- [ ] 監控成本和效果
- [ ] 調整配置

### Week 3-4: Bedrock 優化
- [ ] Prompt 審查和優化
- [ ] 考慮動態模型選擇
- [ ] 實施 streaming（如可行）

---

## ⚠️ 重要提醒

### 不要過早優化
- 當前性能「可接受」，不是「崩潰」
- 用戶目前可以使用
- 優先處理更高價值的功能

### 但也不要忽視
- 15-25 秒確實比競爭對手慢 3-5 倍
- 影響用戶體驗和留存率
- 2 週內應該啟動優化

### 測試配置已調整
- 當前測試超時：45-60 秒
- 優化後可調整回：30-45 秒
- 但不要低於 p95 × 1.5

---

## 📚 參考資料

### AWS 最佳實踐
- [Lambda Performance Optimization](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Bedrock Performance Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/optimization.html)

### 相關文檔
- `.clinerules/deployment/development-and-debugging-guide.md`
- `dev-reports/2026-01-browser-sandbox/REPORT.md`

---

**文檔版本**: v1.0  
**下次審查**: 2026-02-11（2 週後）  
**負責人**: Backend Team