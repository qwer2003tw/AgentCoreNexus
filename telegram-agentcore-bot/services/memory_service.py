"""
Memory 服務模組
管理 AgentCore Memory 功能
"""
from typing import Optional, Dict, Any
from utils.logger import get_logger
from config.settings import settings

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
                RetrievalConfig
            )
            from bedrock_agentcore.memory.integrations.strands.session_manager import (
                AgentCoreMemorySessionManager
            )
            
            logger.info(f"✅ 初始化 Memory: {self.memory_id}")
            self._memory_config_class = AgentCoreMemoryConfig
            self._retrieval_config_class = RetrievalConfig
            self._session_manager_class = AgentCoreMemorySessionManager
            
        except ImportError as e:
            logger.error(f"❌ Memory 模組匯入失敗: {str(e)}")
            self.enabled = False
    
    def get_session_manager(self, context: Any) -> Optional[Any]:
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
            session_id = getattr(context, 'session_id', settings.DEFAULT_SESSION_ID)
            actor_id = self._extract_actor_id(context)
            
            # 建立 Memory 配置
            memory_config = self._create_memory_config(session_id, actor_id)
            
            # 建立 Session Manager
            session_manager = self._session_manager_class(
                memory_config, 
                settings.AWS_REGION
            )
            
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
        actor_id = 'user'  # 預設值
        
        if hasattr(context, 'headers') and context.headers:
            actor_id = context.headers.get(
                'X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id', 
                'user'
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
            f"/users/{actor_id}/facts": self._retrieval_config_class(
                top_k=3, 
                relevance_score=0.5
            ),
            f"/users/{actor_id}/preferences": self._retrieval_config_class(
                top_k=3, 
                relevance_score=0.5
            )
        }
        
        return self._memory_config_class(
            memory_id=self.memory_id,
            session_id=session_id,
            actor_id=actor_id,
            retrieval_config=retrieval_config
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        取得 Memory 服務狀態
        
        Returns:
            狀態資訊字典
        """
        return {
            "enabled": self.enabled,
            "memory_id": self.memory_id if self.enabled else None,
            "region": settings.AWS_REGION
        }

# 建立全域 Memory 服務實例
memory_service = MemoryService()
