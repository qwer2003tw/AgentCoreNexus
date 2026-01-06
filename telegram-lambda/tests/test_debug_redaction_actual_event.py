"""
測試使用實際 API Gateway event 的遮蔽功能
"""
import json
import pytest
from src.telegram_client import redact_sensitive_data, SENSITIVE_FIELDS


def test_redact_actual_event():
    """測試使用實際的 API Gateway event"""
    # 實際的 event（修正 body 格式）
    actual_event = {
        "resource": "/webhook",
        "path": "/webhook",
        "httpMethod": "POST",
        "headers": {
            "Accept-Encoding": "gzip, deflate",
            "Content-Type": "application/json",
            "Host": "vnqlzx6b9f.execute-api.us-west-2.amazonaws.com",
            "X-Amzn-Trace-Id": "Root=1-690b0f2d-135b5b874442686006f97020",
            "X-Forwarded-For": "91.108.5.11",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
            "X-Telegram-Bot-Api-Secret-Token": "B8TJHR47waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd"
        },
        "multiValueHeaders": {
            "Accept-Encoding": ["gzip, deflate"],
            "Content-Type": ["application/json"],
            "Host": ["vnqlzx6b9f.execute-api.us-west-2.amazonaws.com"],
            "X-Amzn-Trace-Id": ["Root=1-690b0f2d-135b5b874442686006f97020"],
            "X-Forwarded-For": ["91.108.5.11"],
            "X-Forwarded-Port": ["443"],
            "X-Forwarded-Proto": ["https"],
            "X-Telegram-Bot-Api-Secret-Token": ["B8TJHR47waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd"]
        },
        "queryStringParameters": None,
        "multiValueQueryStringParameters": None,
        "pathParameters": None,
        "stageVariables": None,
        "requestContext": {
            "resourceId": "k7rwow",
            "resourcePath": "/webhook",
            "httpMethod": "POST",
            "extendedRequestId": "Tj9PME0IPHcEZ_Q=",
            "requestTime": "05/Nov/2025:08:47:41 +0000",
            "path": "/Prod/webhook",
            "accountId": "154829345364",
            "protocol": "HTTP/1.1",
            "stage": "Prod",
            "domainPrefix": "vnqlzx6b9f",
            "requestTimeEpoch": 1762332461660,
            "requestId": "34da3bbf-5809-4224-a39b-8f4e129c6ca6",
            "identity": {
                "cognitoIdentityPoolId": None,
                "accountId": None,
                "cognitoIdentityId": None,
                "caller": None,
                "sourceIp": "91.108.5.11",
                "principalOrgId": None,
                "accessKey": None,
                "cognitoAuthenticationType": None,
                "cognitoAuthenticationProvider": None,
                "userArn": None,
                "userAgent": None,
                "user": None
            },
            "domainName": "vnqlzx6b9f.execute-api.us-west-2.amazonaws.com",
            "deploymentId": "soo4he",
            "apiId": "vnqlzx6b9f"
        },
        "body": '{"update_id":106948325,"message":{"message_id":29018,"from":{"id":316743844,"is_bot":false,"first_name":"Steven","last_name":"Peng","username":"qwer2003tw","language_code":"en"},"chat":{"id":316743844,"first_name":"Steven","last_name":"Peng","username":"qwer2003tw","type":"private"},"date":1762332461,"text":"/debug test","entities":[{"offset":0,"length":6,"type":"bot_command"}]}}',
        "isBase64Encoded": False
    }
    
    # 執行遮蔽
    redacted_event = redact_sensitive_data(actual_event, SENSITIVE_FIELDS)
    
    # 驗證遮蔽效果
    assert redacted_event['headers']['X-Telegram-Bot-Api-Secret-Token'] == '[REDACTED]'
    assert redacted_event['multiValueHeaders']['X-Telegram-Bot-Api-Secret-Token'] == ['[REDACTED]']
    assert redacted_event['requestContext']['accountId'] == '[REDACTED]'
    
    # 驗證非敏感欄位未被修改
    assert redacted_event['headers']['Content-Type'] == 'application/json'
    assert redacted_event['requestContext']['stage'] == 'Prod'
    assert redacted_event['body'] == actual_event['body']  # body 內容不應該被遮蔽
    
    # 驗證可以序列化為 JSON
    json_output = json.dumps(redacted_event, indent=2)
    assert '[REDACTED]' in json_output
    assert 'B8TJHR47waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd' not in json_output
    assert '154829345364' not in json_output
    
    # 驗證原始 event 未被修改
    assert actual_event['headers']['X-Telegram-Bot-Api-Secret-Token'] == 'B8TJHR47waXXxacORJXtPYEJ3JTjxRH1pcarospeAAfn8pJC0dfPHfOqcgJqGkPd'
    assert actual_event['requestContext']['accountId'] == '154829345364'
    
    print("\n✅ 遮蔽後的 event (前 500 字元):")
    print(json_output[:500])


def test_debug_info_format():
    """測試 debug info 的格式化輸出"""
    event = {
        "headers": {
            "X-Telegram-Bot-Api-Secret-Token": "secret123",
            "Content-Type": "application/json"
        },
        "requestContext": {
            "accountId": "123456789012"
        }
    }
    
    redacted = redact_sensitive_data(event, SENSITIVE_FIELDS)
    
    # 模擬 send_debug_info 的格式化邏輯
    debug_text = "🔍 **Debug Information**\n"
    debug_text += "_Note: Sensitive fields have been redacted_\n\n"
    debug_text += "```json\n"
    debug_text += json.dumps(redacted, indent=2, ensure_ascii=False)
    debug_text += "\n```"
    
    # 驗證格式
    assert "🔍 **Debug Information**" in debug_text
    assert "_Note: Sensitive fields have been redacted_" in debug_text
    assert "[REDACTED]" in debug_text
    assert "secret123" not in debug_text
    assert "123456789012" not in debug_text
    
    print("\n✅ Debug 訊息格式:")
    print(debug_text)


if __name__ == '__main__':
    test_redact_actual_event()
    test_debug_info_format()
    print("\n✅ 所有測試通過！")
