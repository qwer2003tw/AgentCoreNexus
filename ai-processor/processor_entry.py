"""
EventBridge Processor Entry Point
處理來自 EventBridge 的標準化訊息事件
"""

import json
import os
from typing import Any

import boto3
from botocore.config import Config

from agents.conversation_agent import ConversationAgent
from services.file_service import file_service
from services.memory_service import MemoryService
from tools import AVAILABLE_TOOLS
from utils.audit import MemoryAuditLogger
from utils.logger import get_logger
from utils.security import secure_actor_id, validate_user_id

logger = get_logger(__name__)

# 初始化 Memory 服務（全域單例）
memory_service = MemoryService()

# EventBridge 配置（優化連接池和重試策略）
_eventbridge_config = Config(
    max_pool_connections=5,  # 連接池大小
    retries={"max_attempts": 3},  # 重試策略
    connect_timeout=3,  # 連接超時（秒）
    read_timeout=10,  # 讀取超時（秒）
)

# EventBridge 客戶端
_eventbridge_client = None


def get_eventbridge_client():
    """
    取得 EventBridge 客戶端單例

    使用單例模式和連接池優化性能

    Returns:
        boto3.client: EventBridge client
    """
    global _eventbridge_client
    if _eventbridge_client is None:
        _eventbridge_client = boto3.client("events", config=_eventbridge_config)
        logger.info("EventBridge client initialized with connection pooling")
    return _eventbridge_client


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Lambda 入口函數 - 處理 EventBridge 事件

    支援三種觸發來源：
    1. EventBridge: event['detail'] 包含標準化訊息
    2. SQS (向後兼容): event['Records'] 包含 SQS 訊息
    3. EventBridge: session.clear 清除 session

    Args:
        event: EventBridge 事件或 SQS 事件
        context: Lambda context

    Returns:
        處理結果
    """
    logger.info(
        "Processor invoked",
        extra={
            "source": event.get("source", "unknown"),
            "detail_type": event.get("detail-type", "unknown"),
        },
    )

    try:
        # 判斷事件來源
        if "Records" in event:
            # SQS 事件（向後兼容）
            logger.info("Processing SQS event (legacy mode)")
            return process_sqs_event(event, context)
        elif "detail" in event:
            detail_type = event.get("detail-type", "")

            # EventBridge session.clear 事件
            if detail_type == "session.clear":
                logger.info("Processing session.clear event")
                return process_session_clear_event(event, context)

            # EventBridge message.received 事件（新架構）
            logger.info("Processing EventBridge event")
            return process_eventbridge_event(event, context)
        else:
            logger.error("Unknown event format")
            return {"statusCode": 400, "body": json.dumps({"error": "Unknown event format"})}

    except Exception as e:
        logger.error(f"Processor error: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def process_eventbridge_event(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    處理 EventBridge 事件

    Args:
        event: EventBridge 事件
        context: Lambda context

    Returns:
        處理結果
    """
    detail = event.get("detail", {})

    # 驗證事件類型
    detail_type = event.get("detail-type", "")
    if detail_type != "message.received":
        logger.warning(f"Unsupported detail-type: {detail_type}")
        return {"statusCode": 200, "body": "Event ignored"}

    # 提取標準化訊息
    normalized_message = detail
    message_id = normalized_message.get("messageId", "unknown")
    channel_type = normalized_message.get("channel", {}).get("type", "unknown")

    logger.info(
        f"Processing message from {channel_type}",
        extra={"message_id": message_id, "channel": channel_type},
    )

    # 處理訊息
    result = process_normalized_message(normalized_message)

    # 發布處理完成事件
    if result.get("success"):
        publish_completion_event(normalized_message, result)
    else:
        publish_failure_event(normalized_message, result)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {"message_id": message_id, "status": "processed" if result.get("success") else "failed"}
        ),
    }


def process_file_attachments(attachments: list, user_id: str) -> str | None:
    """
    處理檔案附件（非圖片）

    Args:
        attachments: 附件列表
        user_id: 用戶 ID

    Returns:
        檔案處理結果文字，或 None
    """
    if not file_service.is_available():
        logger.info("File service not available, skipping file processing")
        return None

    results = []

    for attachment in attachments:
        try:
            # 檢查是否有權限被拒絕標記
            if attachment.get("permission_denied"):
                logger.info(
                    f"File permission denied for {attachment.get('type')}",
                    extra={"user_id": user_id},
                )
                continue

            # 檢查是否有 S3 URL
            s3_url = attachment.get("s3_url")
            if not s3_url:
                logger.warning(f"No S3 URL in attachment: {attachment}")
                continue

            # 提取檔案資訊
            filename = attachment.get("file_name", "unknown")
            task = attachment.get("task", "摘要此檔案的內容")

            logger.info(
                f"📁 Processing file: {filename}",
                extra={"user_id": user_id, "file_name": filename, "task": task, "s3_url": s3_url},
            )

            # 使用 file_service 處理檔案
            process_result = file_service.process_file(
                s3_url=s3_url, filename=filename, task=task, user_id=user_id
            )

            if process_result.get("success"):
                result_text = process_result.get("result", "處理完成")
                results.append(f"📁 檔案：{filename}\n{result_text}")
                logger.info(f"✅ File processed successfully: {filename}")
            else:
                error = process_result.get("error", "未知錯誤")
                results.append(f"❌ 檔案 {filename} 處理失敗：{error}")
                logger.warning(f"File processing failed: {filename} - {error}")

        except Exception as e:
            logger.error(f"Error processing attachment: {e}", exc_info=True)
            results.append(f"❌ 處理附件時發生錯誤：{str(e)}")

    if results:
        return "\n\n".join(results)

    return None


def process_sqs_event(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    處理 SQS 事件（向後兼容現有系統）

    Args:
        event: SQS 事件
        context: Lambda context

    Returns:
        處理結果
    """
    records = event.get("Records", [])

    for record in records:
        try:
            body = json.loads(record.get("body", "{}"))

            # 從 Telegram 原始格式提取訊息
            message = body.get("message", {})
            from_user = message.get("from", {})
            user_id = str(from_user.get("id", "unknown"))
            text = message.get("text", "")

            if text:
                logger.info(
                    f"Processing SQS message from Telegram user {user_id}",
                    extra={"memory_enabled": memory_service.enabled},
                )

                # 建立帶 Memory 的 Agent（與 EventBridge 處理一致）
                session_manager = None
                if memory_service.enabled:
                    try:
                        # 建立 Memory 上下文
                        memory_context = type(
                            "MemoryContext",
                            (),
                            {
                                "session_id": user_id,  # SQS 事件使用 user_id 作為 session_id
                                "headers": {
                                    "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id": user_id
                                },
                            },
                        )()

                        # 取得 Session Manager
                        session_manager = memory_service.get_session_manager(memory_context)

                        if session_manager:
                            logger.info(
                                "Memory session created for SQS event", extra={"user_id": user_id}
                            )
                    except Exception as mem_error:
                        logger.warning(
                            f"Failed to create memory session for SQS, using stateless mode: {mem_error}",
                            extra={"user_id": user_id},
                        )

                # 建立 Agent
                agent = ConversationAgent(tools=AVAILABLE_TOOLS, session_manager=session_manager)

                # 處理訊息
                agent.process_message(text)

                logger.info(
                    "SQS message processed",
                    extra={"user_id": user_id, "has_memory": session_manager is not None},
                )
        except Exception as e:
            logger.error(f"Failed to process SQS record: {e}", exc_info=True)

    return {"statusCode": 200, "body": json.dumps({"processed": len(records)})}


def process_normalized_message(normalized: dict[str, Any]) -> dict[str, Any]:
    """
    處理標準化訊息

    Args:
        normalized: 標準化的訊息物件

    Returns:
        處理結果
    """
    try:
        # 提取訊息內容
        content = normalized.get("content", {})
        text = content.get("text", "")
        message_type = content.get("messageType", "text")
        attachments = content.get("attachments", [])

        # 提取用戶資訊
        user = normalized.get("user", {})
        user_id = str(user.get("id", "unknown"))
        display_name = user.get("displayName", "Unknown")

        # 提取上下文
        context_info = normalized.get("context", {})
        session_id = context_info.get("sessionId", user_id)

        logger.info(
            f"Processing {message_type} message from {display_name}",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "message_type": message_type,
                "has_attachments": len(attachments) > 0,
                "memory_enabled": memory_service.enabled,
            },
        )

        # 分離圖片附件和其他檔案附件
        image_attachments = []
        file_attachments = []

        for attachment in attachments:
            if attachment.get("type") == "photo":
                image_attachments.append(attachment)
            else:
                file_attachments.append(attachment)

        # 處理非圖片檔案附件
        file_processing_result = None
        if file_attachments:
            file_processing_result = process_file_attachments(file_attachments, user_id)

        # ✅ 新架構：使用 image_analysis tool 處理圖片
        image_analysis_results = []
        if image_attachments:
            from tools.image_analysis import analyze_image

            logger.info(f"🖼️ 使用 Image Analysis Tool 處理 {len(image_attachments)} 張圖片")

            for img_att in image_attachments:
                s3_url = img_att.get("s3_url")
                filename = img_att.get("file_name", "image")
                task = img_att.get("task", "請詳細描述這張圖片的內容")

                # 調用 image_analysis tool
                analysis_result = analyze_image(
                    image_s3_url=s3_url,
                    user_id=secure_actor_id(user_id),
                    task=task,
                    filename=filename,
                )

                if analysis_result["success"]:
                    # 成功：記錄分析結果
                    analysis_text = analysis_result["analysis"]
                    image_analysis_results.append(f"📸 圖片 {filename}：\n{analysis_text}")

                    # 寫入 Memory
                    if memory_service.enabled:
                        memory_service.create_image_event(
                            user_id=secure_actor_id(user_id),
                            image_url=s3_url,
                            analysis=analysis_text,
                            task=task,
                        )
                else:
                    # 失敗：記錄錯誤
                    error = analysis_result.get("error", "未知錯誤")
                    image_analysis_results.append(f"❌ 圖片 {filename} 分析失敗：{error}")

        # 處理文字訊息或檔案訊息
        if message_type in ["text", "file", "image", "video", "audio"] and (
            text or file_processing_result or image_analysis_results
        ):
            # 構建完整訊息文字
            full_text = text

            # 添加檔案處理結果
            if file_processing_result:
                full_text = (
                    f"{text}\n\n{file_processing_result}" if text else file_processing_result
                )

            # 添加圖片分析結果
            if image_analysis_results:
                image_summary = "\n\n".join(image_analysis_results)
                full_text = f"{full_text}\n\n{image_summary}" if full_text else image_summary
            # 驗證 user_id 格式
            if not validate_user_id(user_id):
                logger.warning(f"Invalid user_id format: {user_id}")
                MemoryAuditLogger.log_security_event(
                    event_type="invalid_user_id",
                    severity="medium",
                    description="Invalid user_id format detected",
                    user_id=user_id,
                )

            # 生成安全的 actor_id（雜湊化）
            secure_user_id = secure_actor_id(user_id)

            # 建立帶 Memory 的 Agent
            session_manager = None
            if memory_service.enabled:
                try:
                    # 建立 Memory 上下文（使用安全的 actor_id）
                    memory_context = type(
                        "MemoryContext",
                        (),
                        {
                            "session_id": session_id,
                            "headers": {
                                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id": secure_user_id
                            },
                        },
                    )()

                    # 取得 Session Manager
                    session_manager = memory_service.get_session_manager(memory_context)

                    if session_manager:
                        # 記錄審計日誌：Session 創建成功
                        MemoryAuditLogger.log_session_created(
                            user_id=user_id,
                            actor_id=secure_user_id,
                            session_id=session_id,
                            memory_id=memory_service.memory_id,
                        )

                        logger.info(
                            "Memory session created with secure actor_id",
                            extra={
                                "user_id": user_id,
                                "secure_actor_id": secure_user_id,
                                "session_id": session_id,
                            },
                        )
                except Exception as mem_error:
                    # 記錄審計日誌：Session 創建失敗
                    MemoryAuditLogger.log_session_failed(
                        user_id=user_id,
                        actor_id=secure_user_id,
                        session_id=session_id,
                        error=str(mem_error),
                    )

                    logger.warning(
                        f"Failed to create memory session, using stateless mode: {mem_error}",
                        extra={"user_id": user_id, "secure_actor_id": secure_user_id},
                    )

            # ✅ 建立 ConversationAgent（新架構：只傳文字）
            agent = ConversationAgent(tools=AVAILABLE_TOOLS, session_manager=session_manager)

            # ✅ 只傳遞文字給 Agent（圖片已通過 tool 處理並添加到 full_text）
            response_dict = agent.process_message(full_text)

            # 提取回應字串
            response_text = (
                response_dict.get("response", "")
                if isinstance(response_dict, dict)
                else str(response_dict)
            )

            logger.info(
                "Message processed successfully",
                extra={
                    "user_id": user_id,
                    "response_length": len(response_text),
                    "has_memory": session_manager is not None,
                },
            )

            return {
                "success": True,
                "response": response_text,
                "user_id": user_id,
                "session_id": session_id,
            }
        else:
            logger.warning(f"Unsupported message type: {message_type}")
            return {
                "success": False,
                "error": f"Unsupported message type: {message_type}",
                "user_id": user_id,
            }

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "user_id": normalized.get("user", {}).get("id", "unknown"),
        }


def publish_completion_event(original_message: dict[str, Any], result: dict[str, Any]) -> bool:
    """
    發布訊息處理完成事件到 EventBridge

    Args:
        original_message: 原始標準化訊息
        result: 處理結果

    Returns:
        發布是否成功
    """
    event_bus_name = os.getenv("EVENT_BUS_NAME")
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, skipping completion event")
        return False

    try:
        evb = get_eventbridge_client()

        completion_event = {
            "messageId": original_message.get("messageId", "unknown"),
            "conversation_id": original_message.get("conversation_id", "default"),
            "channel": original_message.get("channel", {}),  # Keep full channel dict
            "user": original_message.get("user", {}),
            "response": result.get("response", ""),
            "original": original_message,  # Include full original message for router
            "metadata": {
                "session_id": result.get("session_id", "unknown"),
                "original_message_id": original_message.get("messageId", "unknown"),
            },
        }

        response = evb.put_events(
            Entries=[
                {
                    "Source": "agent-processor",
                    "DetailType": "message.completed",
                    "Detail": json.dumps(completion_event),
                    "EventBusName": event_bus_name,
                }
            ]
        )

        if response.get("FailedEntryCount", 0) > 0:
            logger.error(f"Failed to publish completion event: {response}")
            return False

        logger.info(
            "Completion event published",
            extra={
                "message_id": original_message.get("messageId"),
                "event_type": "message.completed",
            },
        )
        return True

    except Exception as e:
        logger.error(f"Failed to publish completion event: {e}", exc_info=True)
        return False


def process_session_clear_event(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    處理 session.clear 事件 - 清除用戶的 Memory session

    Args:
        event: EventBridge session.clear 事件
        context: Lambda context

    Returns:
        處理結果
    """
    detail = event.get("detail", {})
    user_id = detail.get("user_id", "unknown")
    new_session_id = detail.get("new_session_id", "")

    logger.info(
        f"Clearing session for user {user_id}",
        extra={"user_id": user_id, "new_session_id": new_session_id},
    )

    if not memory_service.enabled:
        logger.warning("Memory service not enabled, cannot clear session")
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "skipped", "reason": "memory_disabled"}),
        }

    try:
        from utils.security import secure_actor_id

        secure_user_id = secure_actor_id(user_id)

        # 清除 session（通過刪除所有 session 記錄）
        # Bedrock Memory 會自動開始新 session
        success = memory_service.clear_session(secure_user_id)

        if success:
            logger.info(
                f"Session cleared successfully for user {user_id}",
                extra={"user_id": user_id, "secure_actor_id": secure_user_id},
            )
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"status": "success", "user_id": user_id, "new_session_id": new_session_id}
                ),
            }
        else:
            logger.warning(f"Failed to clear session for user {user_id}")
            return {"statusCode": 500, "body": json.dumps({"status": "failed", "user_id": user_id})}

    except Exception as e:
        logger.error(f"Error clearing session: {e}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"status": "error", "error": str(e)})}


def publish_failure_event(original_message: dict[str, Any], result: dict[str, Any]) -> bool:
    """
    發布訊息處理失敗事件到 EventBridge

    Args:
        original_message: 原始標準化訊息
        result: 處理結果（包含錯誤資訊）

    Returns:
        發布是否成功
    """
    event_bus_name = os.getenv("EVENT_BUS_NAME")
    if not event_bus_name:
        logger.warning("EVENT_BUS_NAME not configured, skipping failure event")
        return False

    try:
        evb = get_eventbridge_client()

        failure_event = {
            "original": original_message,
            "error": result.get("error", "Unknown error"),
            "channel": original_message.get("channel", {}).get("type", "unknown"),
            "user_id": result.get("user_id", "unknown"),
        }

        response = evb.put_events(
            Entries=[
                {
                    "Source": "agent-processor",
                    "DetailType": "message.failed",
                    "Detail": json.dumps(failure_event),
                    "EventBusName": event_bus_name,
                }
            ]
        )

        if response.get("FailedEntryCount", 0) > 0:
            logger.error(f"Failed to publish failure event: {response}")
            return False

        logger.info(
            "Failure event published",
            extra={"message_id": original_message.get("messageId"), "event_type": "message.failed"},
        )
        return True

    except Exception as e:
        logger.error(f"Failed to publish failure event: {e}", exc_info=True)
        return False
