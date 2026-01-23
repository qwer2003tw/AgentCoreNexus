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
from services.memory_service import MemoryService
from tools import AVAILABLE_TOOLS
from utils.audit import MemoryAuditLogger
from utils.logger import get_logger
from utils.security import secure_actor_id, validate_user_id

logger = get_logger(__name__)

# 初始化 Memory 服務（全域單例）
memory_service = MemoryService()

# 動態導入對話服務（如果配置了表名稱）
_conversation_service = None


def get_conversation_service():
    """取得對話服務單例（如果已配置）"""
    global _conversation_service
    if _conversation_service is None:
        history_table = os.getenv("CONVERSATION_HISTORY_TABLE")
        metadata_table = os.getenv("CONVERSATION_METADATA_TABLE")

        if history_table and metadata_table:
            # 導入並創建服務
            import sys

            sys.path.insert(0, "/opt/python")  # Lambda Layer 路徑
            from conversation_service import ConversationService

            _conversation_service = ConversationService(history_table, metadata_table)
            logger.info(
                "ConversationService initialized",
                extra={"history_table": history_table, "metadata_table": metadata_table},
            )
        else:
            logger.info("Conversation storage not configured, conversation history disabled")
            _conversation_service = False  # 標記為已檢查但未配置

    return _conversation_service if _conversation_service else None


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
    channel_info = normalized_message.get("channel", {})
    channel_type = channel_info.get("type", "unknown")
    channel_id = channel_info.get("channelId", "unknown")

    logger.info(
        f"Processing message from {channel_type}",
        extra={
            "message_id": message_id,
            "channel": channel_type,
            "channel_id": channel_id,
            "channel_full": channel_info,
        },
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


def build_attachment_message(attachments: list) -> str:
    """
    為所有附件構建統一的訊息格式

    讓 Agent 看到附件的 S3 URL 和描述，
    由 Agent 決定是否需要分析以及如何分析。

    Args:
        attachments: 附件列表

    Returns:
        附件資訊的文字描述
    """
    if not attachments:
        return ""

    attachment_messages = []

    for att in attachments:
        # 檢查權限
        if att.get("permission_denied"):
            continue

        # 提取資訊
        att_type = att.get("type", "document")
        file_name = att.get("file_name", "unknown")
        s3_url = att.get("s3_url", "")
        task = att.get("task", "")

        if not s3_url:
            continue

        # 根據類型使用不同的描述
        type_display = "圖片" if att_type == "photo" else "檔案"

        # 構建訊息
        msg = f"[系統通知] 用戶上傳了{type_display}：\n  檔名：{file_name}\n  位置：{s3_url}"

        if task:
            msg += f"\n  用戶要求：{task}"

        attachment_messages.append(msg)

    if attachment_messages:
        return "\n\n".join(attachment_messages)

    return ""


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
        conversation_id = context_info.get("conversationId", session_id)

        logger.info(
            f"Processing {message_type} message from {display_name}",
            extra={
                "user_id": user_id,
                "session_id": session_id,
                "conversation_id": conversation_id,
                "message_type": message_type,
                "has_attachments": len(attachments) > 0,
                "memory_enabled": memory_service.enabled,
            },
        )

        # ✅ 檢查是否為群組對話（需要完整上下文）
        channel_metadata = normalized.get("channel", {}).get("metadata", {})
        is_group = channel_metadata.get("chat_type") == "group"

        # ✅ 如果是群組，從 DynamoDB 讀取對話歷史（完整上下文）
        group_context = ""
        if is_group:
            conversation_service = get_conversation_service()
            if conversation_service:
                try:
                    # 取得群組對話歷史（最近 30 條，包含發送者名稱）
                    group_context = conversation_service.format_messages_for_ai(
                        conversation_id=f"tg:group:{conversation_id}",
                        limit=30,
                        include_sender_name=True,
                    )
                    if group_context:
                        logger.info(f"Loaded group context for conversation {conversation_id}")
                except Exception as e:
                    logger.warning(f"Failed to load group context: {str(e)}", exc_info=True)

        # ✅ 新架構：統一處理所有附件（圖片 + 檔案）
        # 構建訊息給 Agent，由 Agent 決定是否需要調用 tools
        message_parts = []

        # 1. 群組上下文（如果有）
        if group_context:
            message_parts.append("【群組對話歷史】\n" + group_context + "\n【當前訊息】")

        # 2. 用戶文字
        if text:
            message_parts.append(text)

        # 3. 附件資訊（統一格式）
        if attachments:
            attachment_info = build_attachment_message(attachments)
            if attachment_info:
                message_parts.append(attachment_info)

        # 4. 組合完整訊息
        full_message = "\n\n".join(message_parts)

        # 處理文字訊息或附件訊息
        if message_type in ["text", "file", "image", "video", "audio"] and full_message:
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

            # ✅ 建立帶 Memory 的 Agent（不再禁用 Memory！）
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

            # ✅ 建立 ConversationAgent（Memory 啟用，Agent 自主決策）
            agent = ConversationAgent(tools=AVAILABLE_TOOLS, session_manager=session_manager)

            # ✅ 傳遞完整訊息給 Agent（包含附件的 S3 URL）
            # Agent 會自己決定是否需要調用 analyze_image_tool 或 analyze_file_tool
            response_dict = agent.process_message(full_message)

            # 提取回應字串
            response_text = (
                response_dict.get("response", "")
                if isinstance(response_dict, dict)
                else str(response_dict)
            )

            # ✨ 儲存 AI 回應到對話歷史（雙寫架構）
            conversation_service = get_conversation_service()
            if conversation_service and response_text:
                try:
                    # 構建 conversation_id（與 Telegram handler 一致）
                    channel_type = normalized.get("channel", {}).get("type", "unknown")
                    if is_group:
                        conv_id = f"{channel_type}:group:{conversation_id}"
                    else:
                        conv_id = f"{channel_type}:{conversation_id}"

                    # 儲存 AI 回應
                    conversation_service.save_message(
                        conversation_id=conv_id,
                        sender_id="ai",
                        sender_name="AI Assistant",
                        content=response_text,
                        message_type="text",
                        channel=channel_type,
                        metadata={
                            "has_memory": session_manager is not None,
                        },
                    )
                    logger.debug(f"AI response saved to conversation history: {conv_id}")
                except Exception as e:
                    # 對話記錄失敗不應阻止回應發送
                    logger.warning(
                        f"Failed to save AI response to history: {str(e)}", exc_info=True
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
