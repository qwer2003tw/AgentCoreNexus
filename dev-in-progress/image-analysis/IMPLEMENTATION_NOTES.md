# 圖片分析功能實現筆記

## 🔍 技術發現與關鍵學習

### 發現 1: Strands 使用 Bedrock Converse API

**問題**：最初使用了 Claude Messages API 格式
```python
# ❌ 錯誤格式（Claude Messages API）
{
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/jpeg",
        "data": base64_string
    }
}
```

**錯誤訊息**：`Input prompt must be of type: str | list[Contentblock] | Messages | None`

**正確格式**（Bedrock Converse API）：
```python
# ✅ 正確格式（Converse API）
{
    "image": {
        "format": "jpeg",  # 不是 media_type
        "source": {
            "bytes": image_bytes  # 直接用 bytes，不是 base64
        }
    }
}
```

**關鍵差異**：
- 用 `bytes` 而不是 base64 字串
- 用 `format` 而不是 `media_type`
- 結構完全不同

---

### 發現 2: AgentCore Memory 無法序列化 bytes

**問題**：當有圖片時，Memory 會失敗
```
ERROR: Failed to create message in AgentCore Memory: 
Object of type bytes is not JSON serializable
```

**根本原因**：
- AgentCore Memory 會將消息存儲為 JSON
- bytes 物件無法被 JSON 序列化
- 這是 AgentCore Memory 的架構限制

**解決方案**：
圖片分析時暫時禁用 Memory
```python
if images_data:
    # 圖片分析不使用 Memory
    agent = ConversationAgent(tools=AVAILABLE_TOOLS, session_manager=None)
else:
    # 純文字對話使用 Memory
    agent = ConversationAgent(tools=AVAILABLE_TOOLS, session_manager=session_manager)
```

**影響**：
- ✅ 圖片可以被分析
- ❌ 但無法追問「剛才那張圖片...」（Memory 不記得）
- 💡 這是 AWS 服務的限制，非我們的代碼問題

---

### 發現 3: 部署次數與問題迭代

**第一次部署（08:56）**：
- 使用錯誤的 API 格式（Claude Messages API）
- 結果：格式錯誤

**第二次部署（09:15）**：
- 修正為 Converse API 格式
- 結果：Memory 序列化錯誤

**第三次部署（09:22）**：
- 圖片時禁用 Memory
- 結果：✅ 成功

**教訓**：
- 真實測試才能發現問題
- API 格式細節非常重要
- 架構限制需要靈活應對

---

## 📊 最終實現架構

### 數據流程
```
用戶上傳圖片
    ↓
telegram-lambda/file_handler.py
    - 識別為 'photo' 類型
    - 下載並上傳到 S3
    ↓
processor_entry.py/process_image_attachments()
    - 從 S3 讀取為 bytes
    - 判斷格式（jpeg/png/gif/webp）
    ↓
conversation_agent.py/_build_multimodal_content()
    - 構建 Converse API 格式
    - {image: {format, source: {bytes}}}
    ↓
Strands Agent → Bedrock Claude
    - 圖片分析
    - 無 Memory（架構限制）
    ↓
中文回應
```

### 關鍵代碼

**圖片檢測** (file_handler.py):
```python
def _detect_attachment_type(filename: str, mime_type: Optional[str] = None) -> str:
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ext = os.path.splitext(filename)[1].lower()
    return 'photo' if ext in image_extensions else 'document'
```

**圖片處理** (processor_entry.py):
```python
def process_image_attachments(attachments: list, user_id: str) -> list:
    images_data = []
    for attachment in attachments:
        image_bytes = file_service.read_from_s3(s3_url)
        image_format = _detect_image_format(filename)
        images_data.append({"bytes": image_bytes, "format": image_format})
    return images_data
```

**多模態構建** (conversation_agent.py):
```python
def _build_multimodal_content(self, text: str, images: List[Dict]) -> List[Dict]:
    content = []
    for img in images:
        content.append({
            "image": {
                "format": img.get("format", "jpeg"),
                "source": {"bytes": img["bytes"]}
            }
        })
    if text:
        content.append({"text": text})
    return content
```

---

## ⚠️ 已知限制

### 1. **無 Memory 支援**
- **原因**：AgentCore Memory 無法序列化 bytes
- **影響**：無法追問之前的圖片
- **權衡**：功能 vs 架構限制

### 2. **圖片大小限制**
- **Bedrock**：< 5MB（建議）
- **Telegram**：最大 20MB
- **建議**：在 S3 上傳前檢查並壓縮

### 3. **Token 消耗**
- 每張圖片 ≈ 1,600 tokens
- 比純文字對話消耗更多
- 需要成本監控

---

## 🎯 功能狀態

### 支援的功能 ✅
- [x] 圖片內容描述
- [x] 視覺問答
- [x] OCR 文字識別
- [x] 多模態對話（圖片 + 文字）
- [x] 中文回應

### 不支援的功能 ❌
- [ ] Memory 連續性（無法追問之前的圖片）
- [ ] 圖片 + Tools 組合使用（理論上可行但未測試）

---

## 📚 參考文檔

### 已查詢的官方文檔
1. AWS Prescriptive Guidance - Strands Agents 多模態能力
2. Bedrock Converse API - ContentBlock 和 ImageBlock 格式
3. Bedrock AgentCore Memory - 限制說明

### 相關 API 文檔
- `Converse API`: https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-call.html
- `ContentBlock`: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ContentBlock.html
- `ImageBlock`: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_runtime_ImageBlock.html

---

## 💡 未來改進建議

### 選項 1: 文字描述 Workaround
```python
# 先分析圖片（無 Memory）
image_description = agent.process_message("", images=images)

# 將描述儲存到 Memory
text_with_context = f"[圖片內容: {image_description}]\n{user_text}"
agent_with_memory.process_message(text_with_context)
```

### 選項 2: 等待 AWS 改進
- 追蹤 AgentCore Memory 的更新
- 如果未來支援多模態序列化，立即採用

### 選項 3: 自訂 Memory 實現
- 實現自己的 Session Manager
- 將圖片儲存到 S3，Memory 只儲存 S3 URL
- 複雜度高，需要權衡

---

**文檔版本**: v1.0  
**創建日期**: 2026-01-07  
**基於**: 三次部署迭代的實戰經驗  
**狀態**: 功能可用，但有 Memory 限制
