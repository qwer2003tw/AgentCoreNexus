"""
Tests for Secrets Manager Module
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from src.secrets_manager import (
    get_secret,
    get_telegram_secrets,
    get_telegram_bot_token,
    get_telegram_secret_token,
    clear_secrets_cache,
    get_secrets_client
)


@pytest.fixture(autouse=True)
def clear_cache():
    """清除快取確保測試隔離"""
    clear_secrets_cache()
    yield
    clear_secrets_cache()


@pytest.fixture
def mock_secrets_response():
    """模擬成功的 Secrets Manager 回應（合併版）"""
    return {
        'SecretString': json.dumps({
            'bot_token': 'test-bot-token-123',
            'webhook_secret_token': 'test-webhook-token-456'
        })
    }


@pytest.fixture
def mock_env_vars(monkeypatch):
    """設定測試環境變數"""
    monkeypatch.setenv('TELEGRAM_SECRETS_ARN', 'arn:aws:secretsmanager:us-west-2:123456789012:secret:telegram-secrets')


class TestGetSecret:
    """測試 get_secret 函數"""
    
    @patch('src.secrets_manager.get_secrets_client')
    def test_get_secret_success(self, mock_client, mock_secrets_response):
        """測試成功獲取 secret"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = mock_secrets_response
        mock_client.return_value = mock_sm
        
        result = get_secret('arn:aws:secretsmanager:us-west-2:123456789012:secret:test')
        
        assert result is not None
        assert result['bot_token'] == 'test-bot-token-123'
        assert result['webhook_secret_token'] == 'test-webhook-token-456'
        mock_sm.get_secret_value.assert_called_once()
    
    @patch('src.secrets_manager.get_secrets_client')
    def test_get_secret_client_error(self, mock_client):
        """測試 ClientError 處理"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.side_effect = ClientError(
            {'Error': {'Code': 'ResourceNotFoundException'}},
            'GetSecretValue'
        )
        mock_client.return_value = mock_sm
        
        result = get_secret('arn:aws:secretsmanager:us-west-2:123456789012:secret:nonexistent')
        
        assert result is None
    
    @patch('src.secrets_manager.get_secrets_client')
    def test_get_secret_invalid_json(self, mock_client):
        """測試無效 JSON 處理"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': 'invalid json'
        }
        mock_client.return_value = mock_sm
        
        result = get_secret('arn:aws:secretsmanager:us-west-2:123456789012:secret:test')
        
        assert result is None
    
    @patch('src.secrets_manager.get_secrets_client')
    def test_get_secret_no_secret_string(self, mock_client):
        """測試沒有 SecretString 的情況"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = {}
        mock_client.return_value = mock_sm
        
        result = get_secret('arn:aws:secretsmanager:us-west-2:123456789012:secret:test')
        
        assert result is None
    
    @patch('src.secrets_manager.get_secrets_client')
    def test_get_secret_cache(self, mock_client, mock_secrets_response):
        """測試 LRU 快取機制"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = mock_secrets_response
        mock_client.return_value = mock_sm
        
        secret_arn = 'arn:aws:secretsmanager:us-west-2:123456789012:secret:test'
        
        # 第一次呼叫
        result1 = get_secret(secret_arn)
        # 第二次呼叫（應該使用快取）
        result2 = get_secret(secret_arn)
        
        assert result1 == result2
        # 應該只呼叫一次 API
        assert mock_sm.get_secret_value.call_count == 1


class TestGetTelegramSecrets:
    """測試 get_telegram_secrets 函數"""
    
    @patch('src.secrets_manager.get_secret')
    def test_get_telegram_secrets_success(self, mock_get_secret, mock_env_vars):
        """測試成功獲取所有 secrets"""
        mock_get_secret.return_value = {
            'bot_token': 'bot-token-123',
            'webhook_secret_token': 'webhook-token-456'
        }
        
        result = get_telegram_secrets()
        
        assert result is not None
        assert result['bot_token'] == 'bot-token-123'
        assert result['webhook_secret_token'] == 'webhook-token-456'
        mock_get_secret.assert_called_once()
    
    @patch('src.secrets_manager.get_secret')
    def test_get_telegram_secrets_no_arn(self, mock_get_secret, monkeypatch):
        """測試沒有設定 ARN 環境變數"""
        monkeypatch.delenv('TELEGRAM_SECRETS_ARN', raising=False)
        
        result = get_telegram_secrets()
        
        assert result is None
        mock_get_secret.assert_not_called()
    
    @patch('src.secrets_manager.get_secret')
    def test_get_telegram_secrets_missing_bot_token(self, mock_get_secret, mock_env_vars):
        """測試缺少 bot_token"""
        mock_get_secret.return_value = {
            'webhook_secret_token': 'webhook-token-456'
        }
        
        result = get_telegram_secrets()
        
        assert result is None
    
    @patch('src.secrets_manager.get_secret')
    def test_get_telegram_secrets_missing_webhook_token(self, mock_get_secret, mock_env_vars):
        """測試缺少 webhook_secret_token"""
        mock_get_secret.return_value = {
            'bot_token': 'bot-token-123'
        }
        
        result = get_telegram_secrets()
        
        assert result is None
    
    @patch('src.secrets_manager.get_secret')
    def test_get_telegram_secrets_not_found(self, mock_get_secret, mock_env_vars):
        """測試 secret 不存在"""
        mock_get_secret.return_value = None
        
        result = get_telegram_secrets()
        
        assert result is None


class TestGetTelegramBotToken:
    """測試 get_telegram_bot_token 函數"""
    
    @patch('src.secrets_manager.get_telegram_secrets')
    def test_get_bot_token_success(self, mock_get_secrets):
        """測試成功獲取 bot token"""
        mock_get_secrets.return_value = {
            'bot_token': 'bot-token-123',
            'webhook_secret_token': 'webhook-token-456'
        }
        
        result = get_telegram_bot_token()
        
        assert result == 'bot-token-123'
        mock_get_secrets.assert_called_once()
    
    @patch('src.secrets_manager.get_telegram_secrets')
    def test_get_bot_token_secrets_not_found(self, mock_get_secrets):
        """測試 secrets 不存在"""
        mock_get_secrets.return_value = None
        
        result = get_telegram_bot_token()
        
        assert result is None
    
    @patch('src.secrets_manager.get_telegram_secrets')
    def test_get_bot_token_no_token_field(self, mock_get_secrets):
        """測試 secrets 沒有 bot_token 欄位"""
        mock_get_secrets.return_value = {
            'webhook_secret_token': 'webhook-token-456'
        }
        
        result = get_telegram_bot_token()
        
        assert result is None


class TestGetTelegramSecretToken:
    """測試 get_telegram_secret_token 函數"""
    
    @patch('src.secrets_manager.get_telegram_secrets')
    def test_get_secret_token_success(self, mock_get_secrets):
        """測試成功獲取 webhook secret token"""
        mock_get_secrets.return_value = {
            'bot_token': 'bot-token-123',
            'webhook_secret_token': 'webhook-token-456'
        }
        
        result = get_telegram_secret_token()
        
        assert result == 'webhook-token-456'
        mock_get_secrets.assert_called_once()
    
    @patch('src.secrets_manager.get_telegram_secrets')
    def test_get_secret_token_secrets_not_found(self, mock_get_secrets):
        """測試 secrets 不存在"""
        mock_get_secrets.return_value = None
        
        result = get_telegram_secret_token()
        
        assert result is None
    
    @patch('src.secrets_manager.get_telegram_secrets')
    def test_get_secret_token_no_token_field(self, mock_get_secrets):
        """測試 secrets 沒有 webhook_secret_token 欄位"""
        mock_get_secrets.return_value = {
            'bot_token': 'bot-token-123'
        }
        
        result = get_telegram_secret_token()
        
        assert result is None


class TestClearSecretsCache:
    """測試 clear_secrets_cache 函數"""
    
    @patch('src.secrets_manager.get_secrets_client')
    def test_clear_cache(self, mock_client, mock_secrets_response):
        """測試清除快取功能"""
        mock_sm = MagicMock()
        mock_sm.get_secret_value.return_value = mock_secrets_response
        mock_client.return_value = mock_sm
        
        secret_arn = 'arn:aws:secretsmanager:us-west-2:123456789012:secret:test'
        
        # 第一次呼叫
        get_secret(secret_arn)
        assert mock_sm.get_secret_value.call_count == 1
        
        # 清除快取
        clear_secrets_cache()
        
        # 再次呼叫應該觸發新的 API 請求
        get_secret(secret_arn)
        assert mock_sm.get_secret_value.call_count == 2


class TestGetSecretsClient:
    """測試 get_secrets_client 函數"""
    
    @patch('src.secrets_manager.boto3')
    def test_client_singleton(self, mock_boto3):
        """測試客戶端單例模式"""
        import src.secrets_manager
        # 重置全域變數
        src.secrets_manager._secrets_client = None
        
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # 第一次呼叫
        client1 = get_secrets_client()
        # 第二次呼叫
        client2 = get_secrets_client()
        
        assert client1 is client2
        # boto3.client 應該只呼叫一次
        mock_boto3.client.assert_called_once_with('secretsmanager')
