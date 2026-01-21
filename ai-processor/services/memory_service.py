"""
Memory 服務模組
管理 AgentCore Memory 功能
"""

from typing import Any

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Memory 服務類"""

    def __init__(self):
        """初始化 Memory 服務"""
        self.memory_id = settings.MEMORY_ID
        self.enabled = settings.MEMORY_ENABLED
        self.session_manager = None

        if self.enabled:
            self._initialize_memory()

    def _initialize_memory(self):
        """初始化 Memory 配置"""
        try:
            from bedrock_agentcore.memory.integrations.strands.config import (
                AgentCoreMemoryConfig,
                RetrievalConfig,
            )
            from bedrock_agentcore.memory.integrations.strands.session_manager import (
                AgentCoreMemorySessionManager,
            )

            logger.info(f"✅ 初始化 Memory: {self.memory_id}")
            self._memory_config_class = AgentCoreMemoryConfig
            self._retrieval_config_class = RetrievalConfig
            self._session_manager_class = AgentCoreMemorySessionManager

        except ImportError as e:
            logger.error(f"❌ Memory 模組匯入失敗: {str(e)}")
            self.enabled = False

    def get_session_manager(self, context: Any) -> Any | None:
        """
        取得 Session Manager

        Args:
            context: AgentCore 上下文

        Returns:
            Session Manager 實例或 None
        """
        if not self.enabled:
            logger.info("ℹ️ Memory 未啟用，Agent 將以無狀態模式運行")
            return None

        try:
            # 從上下文提取必要資訊
            session_id = getattr(context, "session_id", settings.DEFAULT_SESSION_ID)
            actor_id = self._extract_actor_id(context)

            # 建立 Memory 配置
            memory_config = self._create_memory_config(session_id, actor_id)

            # 建立 Session Manager
            session_manager = self._session_manager_class(memory_config, settings.AWS_REGION)

            logger.info(f"✅ Session Manager 建立成功 (Session: {session_id}, Actor: {actor_id})")
            return session_manager

        except Exception as e:
            logger.error(f"❌ Session Manager 建立失敗: {str(e)}", exc_info=True)
            return None

    def _extract_actor_id(self, context: Any) -> str:
        """
        從上下文提取 Actor ID

        Args:
            context: AgentCore 上下文

        Returns:
            Actor ID
        """
        actor_id = "user"  # 預設值

        if hasattr(context, "headers") and context.headers:
            actor_id = context.headers.get(
                "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id", "user"
            )

        return actor_id

    def _create_memory_config(self, session_id: str, actor_id: str) -> Any:
        """
        建立 Memory 配置

        Args:
            session_id: Session ID
            actor_id: Actor ID

        Returns:
            Memory 配置物件
        """
        retrieval_config = {
            f"/users/{actor_id}/facts": self._retrieval_config_class(top_k=3, relevance_score=0.5),
            f"/users/{actor_id}/preferences": self._retrieval_config_class(
                top_k=3, relevance_score=0.5
            ),
        }

        return self._memory_config_class(
            memory_id=self.memory_id,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config,
        )

    def create_image_event(
        self, user_id: str, image_url: str, analysis: str, task: str = ""
    ) -> bool:
        """
        創建圖片分析的 Memory Event

        將圖片分析記錄到 short-term memory，
        讓 long-term memory 能自動提取 facts

        Args:
            user_id: 用戶 ID（應該是 secure_actor_id）
            image_url: 圖片 S3 URL
            analysis: 分析結果文字
            task: 分析任務描述

        Returns:
            是否成功
        """
        if not self.enabled:
            logger.info("Memory 未啟用，跳過圖片 event 記錄")
            return False

        try:
            from datetime import datetime

            from bedrock_agentcore.memory import MemoryClient

            client = MemoryClient(region_name=settings.AWS_REGION)

            # 構建 event data（結構化資訊）
            event_data = {
                "type": "image_analysis",
                "image_url": image_url,
                "task": task,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # 構建 event metadata（供檢索）
            event_metadata = {
                "source": "image_analysis_tool",
                "content_type": "image",
                "filename": image_url.split("/")[-1],
            }

            # 創建 event（寫入 short-term memory）
            # 注意：session_id 需要從當前 context 獲取
            # 這裡使用 user_id 作為 session_id（簡化處理）
            client.create_event(
                memory_id=self.memory_id,
                actor_id=user_id,
                session_id=user_id,  # 使用 user_id 作為 session
                event_data=event_data,
                event_metadata=event_metadata,
            )

            logger.info(
                "✅ 圖片分析已記錄到 Memory",
                extra={
                    "memory_id": self.memory_id,
                    "actor_id": user_id,
                    "image_url": image_url,
                },
            )
            return True

        except Exception as e:
            logger.error(f"❌ 寫入圖片 Memory 失敗：{str(e)}", exc_info=True)
            return False

    def clear_session(self, actor_id: str) -> bool:
        """
        清除用戶的 Memory session

        通過刪除 session 的所有事件來重置記憶

        Args:
            actor_id: 用戶的 actor ID（應該是 secure_actor_id）

        Returns:
            是否成功
        """
        if not self.enabled:
            logger.info("Memory 未啟用，跳過 session 清除")
            return False

        try:
            # 使用 boto3 bedrock-agentcore client（不是 MemoryClient）
            import boto3

            client = boto3.client("bedrock-agentcore", region_name=settings.AWS_REGION)

            # ListSessions API（使用 boto3 client）
            sessions_response = client.list_sessions(memoryId=self.memory_id, maxResults=100)

            sessions = sessions_response.get("sessions", [])

            if not sessions:
                logger.info(f"No sessions found for actor {actor_id}")
                return True

            # 刪除所有 sessions
            deleted_count = 0
            for session in sessions:
                session_id = session.get("sessionId")
                if session_id:
                    try:
                        client.delete_session(memoryId=self.memory_id, sessionId=session_id)
                        deleted_count += 1
                        logger.info(f"Deleted session: {session_id}")
                    except Exception as e:
                        logger.warning(f"Failed to delete session {session_id}: {e}")

            logger.info(
                "✅ Session 清除完成",
                extra={
                    "actor_id": actor_id,
                    "sessions_deleted": deleted_count,
                    "total_sessions": len(sessions),
                },
            )
            return True

        except Exception as e:
            logger.error(f"❌ 清除 session 失敗：{str(e)}", exc_info=True)
            return False

    def get_status(self) -> dict[str, Any]:
        """
        取得 Memory 服務狀態

        Returns:
            狀態資訊字典
        """
        return {
            "enabled": self.enabled,
            "memory_id": self.memory_id if self.enabled else None,
            "region": settings.AWS_REGION,
        }


# 建立全域 Memory 服務實例
memory_service = MemoryService()
