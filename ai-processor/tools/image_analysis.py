"""
圖片分析工具
負責從 S3 讀取圖片、分析並記錄到 Memory
"""

from typing import Any

import boto3

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
def analyze_image_tool(image_url: str, task: str = "描述這張圖片") -> str:
    """
    圖片分析工具（供 Agent 主動調用）

    當 Agent 決定需要分析圖片時，可以調用此工具。

    Args:
        image_url: 圖片的 S3 URL
        task: 分析任務描述

    Returns:
        圖片分析結果（文字）
    """
    # 注意：user_id 需要從 context 獲取
    # 這裡先使用 "system" 作為預設值
    result = analyze_image(image_s3_url=image_url, user_id="system", task=task)

    if result["success"]:
        return f"圖片分析結果：\n{result['analysis']}"
    else:
        return f"圖片分析失敗：{result.get('error', '未知錯誤')}"
