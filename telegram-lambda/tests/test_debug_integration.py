"""
集成測試 - 測試完整的 /debug 命令流程（包含日誌驗證）
"""
import json
import logging
from unittest.mock import Mock, patch, MagicMock
from src.telegram_client import send_debug_info, SENSITIVE_FIELDS


def test_debug_command_with_logging(caplog, monkeypatch):
    """測試 /debug 命令的完整流程，驗證日誌輸出"""
    
    # 獲取 logger 並臨時啟用 propagate 以便 caplog 能夠捕獲
    import src.telegram_client
    test_logger = logging.getLogger('src.telegram_client')
    original_propagate = test_logger.propagate
    original_level = test_logger.level
    test_logger.propagate = True
    test_logger.setLevel(logging.DEBUG)  # 設置為 DEBUG 級別以捕獲所有日誌
    
    # 設定日誌級別
    caplog.set_level(logging.DEBUG)
    
    # 準備測試 event
    test_event = {
        "headers": {
            "X-Telegram-Bot-Api-Secret-Token": "test_secret_token_12345",
            "Content-Type": "application/json"
        },
        "multiValueHeaders": {
            "X-Telegram-Bot-Api-Secret-Token": ["test_secret_token_12345"]
        },
        "requestContext": {
            "accountId": "123456789012",
            "stage": "prod"
        },
        "body": '{"message": {"text": "/debug"}}'
    }
    
    chat_id = 316743844
    
    # Mock send_message 函數避免實際發送
    with patch('src.telegram_client.send_message') as mock_send:
        mock_send.return_value = True
        
        # 執行 send_debug_info
        result = send_debug_info(chat_id, test_event)
        
        # 驗證結果
        assert result is True
        assert mock_send.called
        
        # 獲取發送的訊息內容
        call_args = mock_send.call_args
        sent_message = call_args[0][1]  # 第二個參數是訊息內容
        
        # 驗證訊息內容
        assert "🔍 **Debug Information**" in sent_message
        assert "_Note: Sensitive fields have been redacted_" in sent_message
        assert "[REDACTED]" in sent_message
        assert "test_secret_token_12345" not in sent_message
        assert "123456789012" not in sent_message
        
        print("\n" + "="*60)
        print("📋 日誌輸出驗證：")
        print("="*60)
        
        # 驗證日誌記錄
        log_messages = [record.message for record in caplog.records]
        log_extras = [record.__dict__ for record in caplog.records]
        
        # 檢查關鍵日誌
        has_start_log = False
        has_complete_log = False
        has_prepare_log = False
        
        for i, record in enumerate(caplog.records):
            extra = record.__dict__
            
            if 'event_type' in extra:
                if extra['event_type'] == 'debug_redaction_start':
                    has_start_log = True
                    print(f"\n✅ 找到開始遮蔽日誌:")
                    print(f"   - chat_id: {extra.get('chat_id')}")
                    print(f"   - sensitive_fields_count: {extra.get('sensitive_fields_count')}")
                
                elif extra['event_type'] == 'debug_redaction_complete':
                    has_complete_log = True
                    print(f"\n✅ 找到完成遮蔽日誌:")
                    print(f"   - chat_id: {extra.get('chat_id')}")
                    print(f"   - redacted_fields: {extra.get('redacted_fields')}")
                    print(f"   - redacted_count: {extra.get('redacted_count')}")
                
                elif extra['event_type'] == 'debug_message_prepared':
                    has_prepare_log = True
                    print(f"\n✅ 找到訊息準備日誌:")
                    print(f"   - chat_id: {extra.get('chat_id')}")
                    print(f"   - message_length: {extra.get('message_length')}")
        
        print("\n" + "="*60)
        print("📊 日誌檢查結果：")
        print("="*60)
        print(f"開始遮蔽日誌: {'✅ 已記錄' if has_start_log else '❌ 未找到'}")
        print(f"完成遮蔽日誌: {'✅ 已記錄' if has_complete_log else '❌ 未找到'}")
        print(f"訊息準備日誌: {'✅ 已記錄' if has_prepare_log else '❌ 未找到'}")
        print("="*60)
        
        # 斷言所有關鍵日誌都存在
        assert has_start_log, "缺少開始遮蔽日誌"
        assert has_complete_log, "缺少完成遮蔽日誌"
        assert has_prepare_log, "缺少訊息準備日誌"
        
        print("\n✅ 所有日誌驗證通過！")
        
        # 恢復原始設置
        test_logger.propagate = original_propagate
        test_logger.setLevel(original_level)


def test_debug_command_redaction_fields():
    """測試遮蔽欄位的詳細檢查"""
    
    test_event = {
        "headers": {
            "X-Telegram-Bot-Api-Secret-Token": "QDJxJf37waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd",
            "Content-Type": "application/json"
        },
        "multiValueHeaders": {
            "X-Telegram-Bot-Api-Secret-Token": ["QDJxJf37waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd"]
        },
        "requestContext": {
            "accountId": "190825685292",
            "stage": "Prod"
        }
    }
    
    with patch('src.telegram_client.send_message') as mock_send:
        mock_send.return_value = True
        
        result = send_debug_info(316743844, test_event)
        assert result is True
        
        # 檢查發送的訊息內容
        sent_message = mock_send.call_args[0][1]
        
        # 解析 JSON 部分
        json_start = sent_message.find('```json\n') + 8
        json_end = sent_message.find('\n```', json_start)
        json_content = sent_message[json_start:json_end]
        parsed = json.loads(json_content)
        
        print("\n" + "="*60)
        print("🔍 遮蔽欄位詳細檢查：")
        print("="*60)
        
        # 檢查每個敏感欄位
        for path in SENSITIVE_FIELDS:
            field_name = '.'.join(path)
            current = parsed
            found = True
            
            for key in path:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    found = False
                    break
            
            if found:
                if isinstance(current, list):
                    status = "✅ 已遮蔽 (列表)" if all(v == "[REDACTED]" for v in current) else "❌ 未遮蔽"
                else:
                    status = "✅ 已遮蔽" if current == "[REDACTED]" else "❌ 未遮蔽"
                print(f"  {field_name}: {status}")
                assert current == "[REDACTED]" or (isinstance(current, list) and all(v == "[REDACTED]" for v in current))
            else:
                print(f"  {field_name}: ⚠️  欄位不存在於此 event")
        
        print("="*60)
        print("✅ 所有敏感欄位都已正確遮蔽！")


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v', '-s'])
