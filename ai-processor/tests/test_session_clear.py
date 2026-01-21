"""
Tests for session clearing functionality
測試 /new 命令的 session 清除功能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from services.memory_service import MemoryService


class TestSessionClear:
    """測試 session 清除功能"""

    @patch('services.memory_service.settings')
    def test_clear_session_disabled_memory(self, mock_settings):
        """測試當 Memory 未啟用時"""
        mock_settings.MEMORY_ID = "test-memory"
        mock_settings.MEMORY_ENABLED = False
        
        service = MemoryService()
        result = service.clear_session("test-actor")
        
        assert result is False

    @patch('services.memory_service.settings')
    @patch('boto3.client')
    def test_clear_session_no_sessions_found(self, mock_boto_client, mock_settings):
        """測試當找不到 sessions 時"""
        mock_settings.MEMORY_ID = "test-memory"
        mock_settings.MEMORY_ENABLED = True
        mock_settings.AWS_REGION = "us-west-2"
        
        # Mock boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.list_sessions.return_value = {"sessions": []}
        
        service = MemoryService()
        service.enabled = True  # 強制啟用
        result = service.clear_session("test-actor")
        
        # 驗證
        assert result is True
        mock_client.list_sessions.assert_called_once_with(
            memoryId="test-memory",
            actorId="test-actor",
            maxResults=100
        )

    @patch('services.memory_service.settings')
    @patch('boto3.client')
    def test_clear_session_success(self, mock_boto_client, mock_settings):
        """測試成功清除 sessions"""
        mock_settings.MEMORY_ID = "test-memory"
        mock_settings.MEMORY_ENABLED = True
        mock_settings.AWS_REGION = "us-west-2"
        
        # Mock boto3 client
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # Mock list_sessions 返回
        mock_client.list_sessions.return_value = {
            "sessions": [
                {"sessionId": "session-1"},
                {"sessionId": "session-2"}
            ]
        }
        
        # Mock delete_session
        mock_client.delete_session.return_value = {}
        
        service = MemoryService()
        service.enabled = True
        result = service.clear_session("test-actor")
        
        # 驗證
        assert result is True
        assert mock_client.list_sessions.call_count == 1
        assert mock_client.delete_session.call_count == 2
        
        # 驗證 delete_session 調用
        mock_client.delete_session.assert_any_call(
            memoryId="test-memory",
            sessionId="session-1"
        )
        mock_client.delete_session.assert_any_call(
            memoryId="test-memory",
            sessionId="session-2"
        )

    @patch('services.memory_service.settings')
    @patch('boto3.client')
    def test_clear_session_partial_failure(self, mock_boto_client, mock_settings):
        """測試部分 session 刪除失敗"""
        mock_settings.MEMORY_ID = "test-memory"
        mock_settings.MEMORY_ENABLED = True
        mock_settings.AWS_REGION = "us-west-2"
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        mock_client.list_sessions.return_value = {
            "sessions": [
                {"sessionId": "session-1"},
                {"sessionId": "session-2"}
            ]
        }
        
        # 第一個成功，第二個失敗
        mock_client.delete_session.side_effect = [
            {},  # session-1 成功
            Exception("Delete failed")  # session-2 失敗
        ]
        
        service = MemoryService()
        service.enabled = True
        result = service.clear_session("test-actor")
        
        # 即使部分失敗，仍返回 True（盡力而為）
        assert result is True

    @patch('services.memory_service.settings')
    @patch('boto3.client')
    def test_clear_session_list_api_error(self, mock_boto_client, mock_settings):
        """測試 list_sessions API 失敗"""
        mock_settings.MEMORY_ID = "test-memory"
        mock_settings.MEMORY_ENABLED = True
        mock_settings.AWS_REGION = "us-west-2"
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        mock_client.list_sessions.side_effect = Exception("API Error")
        
        service = MemoryService()
        service.enabled = True
        result = service.clear_session("test-actor")
        
        # API 失敗時返回 False
        assert result is False

    @patch('services.memory_service.settings')
    @patch('boto3.client')
    def test_clear_session_with_empty_session_id(self, mock_boto_client, mock_settings):
        """測試當 session 沒有 sessionId 時"""
        mock_settings.MEMORY_ID = "test-memory"
        mock_settings.MEMORY_ENABLED = True
        mock_settings.AWS_REGION = "us-west-2"
        
        mock_client = MagicMock()
        mock_boto_client.return_value = mock_client
        
        # 返回沒有 sessionId 的 session
        mock_client.list_sessions.return_value = {
            "sessions": [
                {},  # 沒有 sessionId
                {"sessionId": "session-1"}
            ]
        }
        
        service = MemoryService()
        service.enabled = True
        result = service.clear_session("test-actor")
        
        # 應該跳過沒有 sessionId 的，只刪除 session-1
        assert result is True
        mock_client.delete_session.assert_called_once_with(
            memoryId="test-memory",
            sessionId="session-1"
        )