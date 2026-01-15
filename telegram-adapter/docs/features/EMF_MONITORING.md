# AWS Embedded Metrics Format (EMF) 監控

本文檔說明如何使用 AWS Embedded Metrics Format (EMF) 監控 Telegram Lambda 專案。

## 概述

專案使用 AWS EMF 將自訂指標直接從 Lambda 函數發送到 CloudWatch，無需額外配置 Metric Filters。EMF 提供：

- **即時指標**：指標在 Lambda 執行時立即發送
- **低配置**：無需配置 Metric Filters，減少 90% 的設定工作
- **靈活性**：可在程式碼中動態調整指標
- **高效能**：以 JSON 格式寫入 CloudWatch Logs，自動提取為指標

## 收集的指標

### 安全事件指標

| 指標名稱 | 描述 | 單位 |
|---------|------|------|
| `InvalidTokenAttempts` | Secret Token 驗證失敗次數 | Count |
| `TokenValidationSuccess` | Secret Token 驗證成功次數 | Count |
| `AllowlistDenied` | 被白名單拒絕的請求次數 | Count |
| `AllowlistApproved` | 通過白名單驗證的請求次數 | Count |

### 訊息處理指標

| 指標名稱 | 描述 | 單位 |
|---------|------|------|
| `MessagesReceived` | 收到的訊息總數 | Count |
| `MessagesProcessed` | 成功處理的訊息數 | Count |

### 功能使用指標

| 指標名稱 | 描述 | 單位 |
|---------|------|------|
| `DebugCommandReceived` | 收到 /debug 指令的次數 | Count |

### 訊息類型指標

| 指標名稱 | 描述 | 單位 |
|---------|------|------|
| `MessageTypeText` | 純文字訊息數量 | Count |
| `MessageTypePhoto` | 圖片訊息數量 | Count |
| `MessageTypeDocument` | 文件訊息數量 | Count |
| `MessageTypeVideo` | 視訊訊息數量 | Count |
| `MessageTypeAudio` | 音訊訊息數量（含語音） | Count |
| `MessageTypeOther` | 其他類型訊息數量（貼圖、位置、聯絡人、投票等） | Count |

### SQS 操作指標

| 指標名稱 | 描述 | 單位 |
|---------|------|------|
| `SQSSendSuccess` | SQS 發送成功次數 | Count |
| `SQSSendFailure` | SQS 發送失敗次數 | Count |
| `SQSSendDuration` | SQS 發送操作耗時 | Milliseconds |

### 效能指標

| 指標名稱 | 描述 | 單位 |
|---------|------|------|
| `TotalDuration` | Lambda 總執行時間 | Milliseconds |

### 錯誤指標

| 指標名稱 | 描述 | 單位 |
|---------|------|------|
| `LambdaError` | Lambda 函數錯誤次數 | Count |
| `InvalidPayload` | 無效 payload 次數（缺少 chat_id 或 JSON 解析失敗） | Count |
| `WebhookParsingFallback` | Update 物件解析失敗，使用降級解析的次數 | Count |

## 指標維度

所有指標都包含以下維度：

- `FunctionName`：Lambda 函數名稱
- `Environment`：環境名稱（預設為 "production"）

## CloudWatch Dashboard

部署後會自動創建名為 `telegram-lambda-monitoring` 的 Dashboard，包含以下 widgets：

### 1. Security Events（安全事件）
顯示 Invalid Token 嘗試和 Allowlist 拒絕的趨勢圖。

**指標：**
- Invalid Token Attempts
- Allowlist Denied

### 2. Message Processing Flow（訊息處理流程）
追蹤從接收到處理的完整流程。

**指標：**
- Messages Received
- Messages Processed
- SQS Success
- SQS Failure

### 3. Performance Metrics（效能指標）
監控執行時間（毫秒）。

**指標：**
- 平均總執行時間
- 最大總執行時間
- 平均 SQS 發送時間

### 4. Error Metrics（錯誤指標）
追蹤各類錯誤。

**指標：**
- Lambda 錯誤
- AWS Lambda 系統錯誤
- 節流事件

### 5. Feature Usage & Error Handling（功能使用與錯誤處理）
監控系統功能使用情況與錯誤處理狀態。

**指標：**
- Token Validation Success - Token 驗證成功次數
- Allowlist Approved - 通過白名單驗證的請求
- Debug Commands - /debug 指令使用次數
- Invalid Payload - 無效 payload（缺少 chat_id 或 JSON 錯誤）
- Parsing Fallback - Update 物件解析失敗，使用降級解析

### 6. Message Types Distribution（訊息類型分佈）
以堆疊圖顯示不同訊息類型的分佈，幫助了解用戶使用模式。

**指標（堆疊顯示）：**
- Text - 純文字訊息
- Photo - 圖片訊息
- Document - 文件訊息
- Video - 視訊訊息
- Audio - 音訊訊息（含語音）
- Other - 其他類型（貼圖、位置、聯絡人、投票等）

### 7. Recent Security Events（最近安全事件）
顯示最近 20 筆安全相關日誌（Invalid Token 和未授權存取）。

## 部署

### 1. 安裝依賴

確保 `src/requirements.txt` 包含：

```txt
aws-embedded-metrics>=3.0.0
```

### 2. 部署 SAM Stack

```bash
sam build
sam deploy
```

### 3. 訪問 Dashboard

部署完成後：

1. 前往 AWS Console → CloudWatch → Dashboards
2. 選擇 `telegram-lambda-monitoring`
3. Dashboard 會在 Lambda 開始處理請求後顯示數據

## 查看指標

### 在 CloudWatch Metrics 中查看

1. 前往 AWS Console → CloudWatch → Metrics
2. 選擇命名空間：`TelegramLambda`
3. 選擇維度查看各項指標

### 使用 AWS CLI 查詢

```bash
# 查詢特定指標
aws cloudwatch get-metric-statistics \
  --namespace TelegramLambda \
  --metric-name MessagesReceived \
  --start-time 2025-01-01T00:00:00Z \
  --end-time 2025-01-01T23:59:59Z \
  --period 3600 \
  --statistics Sum

# 查詢所有指標
aws cloudwatch list-metrics \
  --namespace TelegramLambda
```

## 告警配置（未來擴展）

雖然目前僅實施指標收集和 Dashboard，未來可以基於這些指標配置告警：

```yaml
# 範例：高錯誤率告警（未來可添加到 template.yaml）
HighErrorRateAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: telegram-lambda-high-error-rate
    MetricName: LambdaError
    Namespace: TelegramLambda
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 2
    Threshold: 10
    ComparisonOperator: GreaterThanThreshold
```

## 最佳實踐

### 1. 定期檢查 Dashboard
建議每日查看 Dashboard 以了解系統運作狀況。

### 2. 監控趨勢
關注指標趨勢而非單一數值，特別是：
- 安全事件的突增
- 錯誤率的變化
- 效能退化

### 3. 設定基準線
運行一段時間後建立指標基準線，用於：
- 識別異常行為
- 設定合理的告警閾值
- 容量規劃

### 4. 日誌相關性
結合 CloudWatch Logs Insights 深入分析：

```
# 查詢高延遲請求
fields @timestamp, chat_id, @message
| filter @message like /Message processed successfully/
| stats avg(@duration) as avg_duration by bin(5m)
| sort avg_duration desc
```

## 成本考量

EMF 指標的成本：

- **CloudWatch Logs**：EMF 數據以 JSON 格式寫入日誌（已包含在現有日誌費用中）
- **CloudWatch Metrics**：每個指標資料點 $0.01/1000（前 10,000 個免費）
- **Dashboard**：每個 Dashboard 每月 $3（前 3 個免費）

預估成本（每月 10,000 次請求）：
- Metrics：~$0.80（8 個指標 × 10,000 次請求）
- Dashboard：$0（在免費額度內）
- **總計**：~$0.80/月

## 疑難排解

### Dashboard 沒有顯示數據

1. 確認 Lambda 已處理至少一個請求
2. 等待 1-2 分鐘讓指標傳播
3. 檢查 CloudWatch Logs 是否有 EMF JSON 格式的日誌

### 指標值不正確

1. 檢查 `src/handler.py` 中的 `record_count_metric` 呼叫
2. 驗證指標名稱與 `src/utils/metrics.py` 中的定義一致
3. 確認維度設定正確

### Lambda 錯誤

查看 CloudWatch Logs 中的錯誤訊息：

```bash
aws logs tail /aws/lambda/telegram-lambda-receiver --follow
```

## 參考資料

- [AWS Embedded Metrics Format 規範](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Embedded_Metric_Format_Specification.html)
- [aws-embedded-metrics Python 庫](https://github.com/awslabs/aws-embedded-metrics-python)
- [CloudWatch Metrics 定價](https://aws.amazon.com/cloudwatch/pricing/)
