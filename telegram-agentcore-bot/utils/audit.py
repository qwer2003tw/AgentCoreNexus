"""
審計日誌模組
記錄 Memory 存取和安全事件
"""
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional
from utils.logger import get_logger

logger = get_logger(__name__)


class MemoryAuditLogger:
    """Memory 存取審計日誌類"""
    
    @staticmethod
    def log_memory_access(
        operation: str,
        user_id: str,
        actor_id: str,
        session_id: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        記錄 Memory 存取操作
        
        Args:
            operation: 操作類型 (create_session, retrieve_memory, store_event, etc.)
            user_id: 原始用戶 ID
            actor_id: 雜湊後的 actor_id
            session_id: Session ID
            success: 操作是否成功
            details: 額外資訊
        
        Examples:
            >>> MemoryAuditLogger.log_memory_access(
            ...     operation='create_session',
            ...     user_id='tg:316743844',
            ...     actor_id='actor-f3a8b2c1d4e5f6g7',
            ...     session_id='session-123',
            ...     success=True
            ... )
        """
        # 雜湊 user_id 以保護隱私（不在日誌中記錄原始 ID）
        user_id_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8]
        
        audit_log = {
            'event_type': 'memory_audit',
            'operation': operation,
            'user_id_hash': user_id_hash,  # 只記錄雜湊值
            'actor_id': actor_id,
            'session_id': session_id,
            'success': success,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'details': details or {}
        }
        
        if success:
            logger.info(
                f"Memory operation: {operation}",
                extra=audit_log
            )
        else:
            logger.warning(
                f"Memory operation failed: {operation}",
                extra=audit_log
            )
    
    @staticmethod
    def log_session_created(
        user_id: str,
        actor_id: str,
        session_id: str,
        memory_id: str
    ):
        """記錄 Session 創建"""
        MemoryAuditLogger.log_memory_access(
            operation='create_session',
            user_id=user_id,
            actor_id=actor_id,
            session_id=session_id,
            success=True,
            details={'memory_id': memory_id}
        )
    
    @staticmethod
    def log_session_failed(
        user_id: str,
        actor_id: str,
        session_id: str,
        error: str
    ):
        """記錄 Session 創建失敗"""
        MemoryAuditLogger.log_memory_access(
            operation='create_session',
            user_id=user_id,
            actor_id=actor_id,
            session_id=session_id,
            success=False,
            details={'error': error}
        )
    
    @staticmethod
    def log_memory_retrieval(
        user_id: str,
        actor_id: str,
        session_id: str,
        retrieved_count: int
    ):
        """記錄記憶檢索"""
        MemoryAuditLogger.log_memory_access(
            operation='retrieve_memory',
            user_id=user_id,
            actor_id=actor_id,
            session_id=session_id,
            success=True,
            details={'retrieved_count': retrieved_count}
        )
    
    @staticmethod
    def log_security_event(
        event_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        記錄安全事件
        
        Args:
            event_type: 事件類型 (unauthorized_access, suspicious_pattern, rate_limit_exceeded, etc.)
            severity: 嚴重程度 (low, medium, high, critical)
            description: 事件描述
            user_id: 相關用戶 ID（如果有）
            details: 額外資訊
        
        Examples:
            >>> MemoryAuditLogger.log_security_event(
            ...     event_type='unauthorized_access',
            ...     severity='high',
            ...     description='Attempted to access another user memory',
            ...     user_id='tg:316743844'
            ... )
        """
        security_log = {
            'event_type': 'security_audit',
            'security_event': event_type,
            'severity': severity,
            'description': description,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'details': details or {}
        }
        
        if user_id:
            security_log['user_id_hash'] = hashlib.sha256(user_id.encode()).hexdigest()[:8]
        
        # 根據嚴重程度選擇日誌等級
        if severity in ['high', 'critical']:
            logger.error(
                f"Security event: {event_type} - {description}",
                extra=security_log
            )
        elif severity == 'medium':
            logger.warning(
                f"Security event: {event_type} - {description}",
                extra=security_log
            )
        else:
            logger.info(
                f"Security event: {event_type} - {description}",
                extra=security_log
            )
    
    @staticmethod
    def log_access_denied(
        user_id: str,
        resource: str,
        reason: str
    ):
        """記錄拒絕存取事件"""
        MemoryAuditLogger.log_security_event(
            event_type='access_denied',
            severity='medium',
            description=f"Access denied to {resource}: {reason}",
            user_id=user_id,
            details={'resource': resource, 'reason': reason}
        )
    
    @staticmethod
    def log_suspicious_activity(
        user_id: str,
        activity: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """記錄可疑活動"""
        MemoryAuditLogger.log_security_event(
            event_type='suspicious_activity',
            severity='high',
            description=f"Suspicious activity detected: {activity}",
            user_id=user_id,
            details=details
        )


def audit_log(
    user_id: str,
    action: str,
    resource: str,
    details: Optional[Dict[str, Any]] = None
):
    """
    通用審計日誌函數
    用於記錄各種操作（檔案處理、API 調用等）
    
    Args:
        user_id: 用戶 ID
        action: 操作類型（如 FILE_PROCESS_START, FILE_PROCESS_SUCCESS）
        resource: 資源名稱（如檔案名稱）
        details: 額外資訊
    
    Examples:
        >>> audit_log(
        ...     user_id='tg:316743844',
        ...     action='FILE_PROCESS_START',
        ...     resource='data.csv',
        ...     details={'task': 'analyze', 's3_url': 's3://...'}
        ... )
    """
    # 雜湊 user_id 保護隱私
    user_id_hash = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    
    audit_entry = {
        'event_type': 'audit_log',
        'action': action,
        'resource': resource,
        'user_id_hash': user_id_hash,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'details': details or {}
    }
    
    logger.info(
        f"Audit: {action} on {resource}",
        extra=audit_entry
    )
