"""
Tests for utils.response module - 回應工具測試
"""

from utils.response import (
    bad_request_response,
    create_response,
    error_response,
    internal_error_response,
    success_response,
    unauthorized_response,
)


class TestCreateResponse:
    """測試 create_response 函數"""

    def test_create_success_response(self):
        """測試創建成功回應"""
        response = create_response(200, {"status": "ok"})

        assert response["statusCode"] == 200
        assert "body" in response
        assert "headers" in response
        assert response["headers"]["Content-Type"] == "application/json"

    def test_create_error_response_400(self):
        """測試創建 400 錯誤回應"""
        response = create_response(400, {"error": "Bad request"})

        assert response["statusCode"] == 400
        body_dict = __import__("json").loads(response["body"])
        assert body_dict["error"] == "Bad request"

    def test_create_response_with_custom_headers(self):
        """測試自訂 headers"""
        custom_headers = {"X-Custom-Header": "custom_value"}
        response = create_response(200, {"data": "test"}, custom_headers)

        assert response["headers"]["X-Custom-Header"] == "custom_value"
        assert response["headers"]["Content-Type"] == "application/json"

    def test_create_response_without_custom_headers(self):
        """測試沒有自訂 headers"""
        response = create_response(200, {"data": "test"})

        assert "Content-Type" in response["headers"]

    def test_create_response_body_is_json_string(self):
        """測試 body 是 JSON 字串"""
        response = create_response(200, {"key": "value"})

        import json

        body_dict = json.loads(response["body"])
        assert body_dict["key"] == "value"


class TestSuccessResponse:
    """測試 success_response 函數"""

    def test_success_with_data(self):
        """測試成功回應帶資料"""
        response = success_response({"user_id": 123}, "Operation completed")

        assert response["statusCode"] == 200
        import json

        body_dict = json.loads(response["body"])
        assert body_dict["success"] is True
        assert body_dict["message"] == "Operation completed"
        assert body_dict["data"]["user_id"] == 123

    def test_success_default_message(self):
        """測試預設訊息"""
        response = success_response({"result": "ok"})

        import json

        body_dict = json.loads(response["body"])
        assert body_dict["message"] == "Success"


class TestErrorResponse:
    """測試 error_response 函數"""

    def test_error_basic(self):
        """測試基本錯誤回應"""
        response = error_response(500, "Internal server error")

        assert response["statusCode"] == 500
        import json

        body_dict = json.loads(response["body"])
        assert body_dict["success"] is False
        assert body_dict["error"] == "Internal server error"

    def test_error_with_code(self):
        """測試帶錯誤代碼的回應"""
        response = error_response(404, "Not found", "RESOURCE_NOT_FOUND")

        import json

        body_dict = json.loads(response["body"])
        assert body_dict["error_code"] == "RESOURCE_NOT_FOUND"

    def test_error_without_code(self):
        """測試沒有錯誤代碼"""
        response = error_response(403, "Forbidden")

        import json

        body_dict = json.loads(response["body"])
        assert "error_code" not in body_dict


class TestConvenienceFunctions:
    """測試便利函數"""

    def test_unauthorized_response(self):
        """測試 unauthorized_response"""
        response = unauthorized_response("Access denied")

        assert response["statusCode"] == 403
        import json

        body_dict = json.loads(response["body"])
        assert body_dict["error"] == "Access denied"
        assert body_dict["error_code"] == "UNAUTHORIZED"

    def test_unauthorized_default_message(self):
        """測試預設未授權訊息"""
        response = unauthorized_response()

        import json

        body_dict = json.loads(response["body"])
        assert body_dict["error"] == "Unauthorized"

    def test_bad_request_response(self):
        """測試 bad_request_response"""
        response = bad_request_response("Invalid input")

        assert response["statusCode"] == 400
        import json

        body_dict = json.loads(response["body"])
        assert body_dict["error"] == "Invalid input"
        assert body_dict["error_code"] == "BAD_REQUEST"

    def test_internal_error_response(self):
        """測試 internal_error_response"""
        response = internal_error_response("Database error")

        assert response["statusCode"] == 500
        import json

        body_dict = json.loads(response["body"])
        assert body_dict["error"] == "Database error"
        assert body_dict["error_code"] == "INTERNAL_ERROR"
