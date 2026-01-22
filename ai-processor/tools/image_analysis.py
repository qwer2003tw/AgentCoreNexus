"""
圖片分析工具
負責從 S3 讀取圖片、分析並記錄到 Memory
"""

from typing import Any

import boto3
from strands import tool

from services.file_service import file_service
from utils.logger import get_logger

logger = get_logger(__name__)

# Bedrock 客戶端（延遲初始化）
_bedrock_client = None


def get_bedrock_client():
    """獲取 Bedrock 客戶端單例"""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client("bedrock-runtime", region_name="us-west-2")
    return _bedrock_client


def analyze_image(
    image_s3_url: str, user_id: str, task: str = "請詳細描述這張圖片的內容", filename: str = "image"
) -> dict[str, Any]:
    """
    分析圖片並記錄到 Memory

    此工具負責：
    1. 從 S3 讀取圖片
    2. 呼叫 Bedrock Converse API 分析圖片
    3. 將分析結果寫入 AgentCore Memory
    4. 返回分析結果供 Agent 使用

    Args:
        image_s3_url: S3 URL (格式：s3://bucket/key)
        user_id: 用戶 ID
        task: 分析任務描述
        filename: 圖片檔名

    Returns:
        {
            "success": True/False,
            "analysis": "分析結果文字",
            "source": "s3_url",
            "filename": "filename",
            "error": "錯誤訊息（如有）"
        }
    """
    logger.info(
        f"🖼️ Image Analysis Tool: 分析圖片 {filename}",
        extra={"user_id": user_id, "s3_url": image_s3_url, "task": task},
    )

    try:
        # 1. 從 S3 讀取圖片
        image_bytes = file_service.read_from_s3(image_s3_url)
        if not image_bytes:
            error_msg = f"無法從 S3 讀取圖片：{image_s3_url}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg, "source": image_s3_url}

        logger.info(f"✅ 從 S3 讀取圖片：{len(image_bytes)} bytes")

        # 2. 判斷圖片格式
        image_format = _detect_image_format(filename)

        # 3. 呼叫 Bedrock Converse API 分析圖片
        bedrock = get_bedrock_client()

        logger.info(f"🤖 呼叫 Bedrock 分析圖片（格式：{image_format}）")

        # ✅ 修復：Bedrock Converse API 不使用 "type"，直接用 key 名稱
        response = bedrock.converse(
            modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"image": {"format": image_format, "source": {"bytes": image_bytes}}},
                        {"text": task},
                    ],
                }
            ],
            inferenceConfig={"maxTokens": 2048, "temperature": 0.7},
        )

        # 4. 提取分析結果
        analysis_text = response["output"]["message"]["content"][0]["text"]

        logger.info(
            f"✅ 圖片分析完成：{len(analysis_text)} 字元",
            extra={"analysis_length": len(analysis_text)},
        )

        # 5. 返回結果（Memory 記錄將在 Processor 層處理）
        return {
            "success": True,
            "analysis": analysis_text,
            "source": image_s3_url,
            "filename": filename,
            "format": image_format,
        }

    except Exception as e:
        error_msg = f"圖片分析失敗：{str(e)}"
        logger.error(error_msg, exc_info=True)
        return {"success": False, "error": error_msg, "source": image_s3_url, "filename": filename}


def _detect_image_format(filename: str) -> str:
    """
    根據檔案名稱判斷圖片格式（Converse API 格式）

    Args:
        filename: 檔案名稱

    Returns:
        圖片格式：'jpeg' | 'png' | 'gif' | 'webp'
    """
    import os

    ext = os.path.splitext(filename)[1].lower()

    formats = {".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".gif": "gif", ".webp": "webp"}

    return formats.get(ext, "jpeg")


# Tool 函數（供 Strands Agent 註冊使用）
@tool
def analyze_image_tool(image_s3_url: str, task: str = "描述圖片內容") -> str:
    """
    分析存儲在 S3 的圖片內容。

    此工具使用 Bedrock Claude Vision API 分析圖片，支援各種視覺任務。

    使用時機：
    - 用戶上傳圖片並詢問相關問題
    - 用戶提到「這張圖片」、「剛才那張圖」等（從 Memory 獲取 S3 URL）
    - 需要視覺分析、OCR 識別、物體檢測等任務

    支援的任務範例：
    - "描述圖片內容"：完整的圖片描述
    - "識別圖片中的物體"：列出圖片中的物體
    - "讀取圖片中的文字"：OCR 文字識別
    - "分析左邊/右邊/中間的部分"：聚焦特定區域
    - 自訂任務：根據用戶的具體問題調整

    Args:
        image_s3_url: 圖片的 S3 URL (格式: s3://bucket/key)
        task: 分析任務的具體描述

    Returns:
        圖片的詳細分析結果（文字）

    範例：
        >>> analyze_image_tool("s3://bucket/photo.jpg", "描述這張圖片")
        "這張圖片顯示一碗泡麵，包含麵餅和多個調味包..."
    """
    logger.info("🖼️ Image Analysis Tool called", extra={"s3_url": image_s3_url, "task": task})

    try:
        # 提取檔名（用於日誌和錯誤訊息）
        filename = image_s3_url.split("/")[-1]

        # 調用核心分析函數
        result = analyze_image(
            image_s3_url=image_s3_url,
            user_id="system",  # Tool 調用使用系統 ID
            task=task,
            filename=filename,
        )

        if result["success"]:
            logger.info(f"✅ Image analysis completed: {len(result['analysis'])} chars")
            return result["analysis"]
        else:
            error_msg = result.get("error", "未知錯誤")
            logger.warning(f"Image analysis failed: {error_msg}")
            return f"圖片分析失敗：{error_msg}\n請確認圖片格式正確且可訪問。"

    except Exception as e:
        logger.error(f"Image analysis tool error: {e}", exc_info=True)
        return f"圖片分析工具執行失敗：{str(e)}"
