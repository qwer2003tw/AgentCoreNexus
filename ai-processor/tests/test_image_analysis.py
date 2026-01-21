"""
Image Analysis Tool 單元測試
"""

from unittest.mock import MagicMock, patch

from tools.image_analysis import _detect_image_format, analyze_image


class TestImageAnalysisTool:
    """Image Analysis Tool 測試"""

    def test_detect_image_format_jpeg(self):
        """測試 JPEG 格式檢測"""
        assert _detect_image_format("photo.jpg") == "jpeg"
        assert _detect_image_format("image.jpeg") == "jpeg"

    def test_detect_image_format_png(self):
        """測試 PNG 格式檢測"""
        assert _detect_image_format("screenshot.png") == "png"

    def test_detect_image_format_gif(self):
        """測試 GIF 格式檢測"""
        assert _detect_image_format("animation.gif") == "gif"

    def test_detect_image_format_webp(self):
        """測試 WebP 格式檢測"""
        assert _detect_image_format("modern.webp") == "webp"

    def test_detect_image_format_unknown(self):
        """測試未知格式默認為 JPEG"""
        assert _detect_image_format("file.bmp") == "jpeg"
        assert _detect_image_format("noext") == "jpeg"

    @patch("tools.image_analysis.file_service")
    @patch("tools.image_analysis.get_bedrock_client")
    def test_analyze_image_success(self, mock_bedrock_client, mock_file_service):
        """測試圖片分析成功"""
        # Mock S3 讀取
        mock_file_service.read_from_s3.return_value = b"fake_image_bytes"

        # Mock Bedrock 回應
        mock_bedrock = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "這是一張測試圖片，包含藍天和白雲。"}]}}
        }

        # 執行
        result = analyze_image(
            image_s3_url="s3://bucket/test.jpg",
            user_id="user123",
            task="描述圖片",
            filename="test.jpg",
        )

        # 驗證
        assert result["success"] is True
        assert "測試圖片" in result["analysis"]
        assert result["source"] == "s3://bucket/test.jpg"
        assert result["filename"] == "test.jpg"
        assert result["format"] == "jpeg"

        # 驗證 S3 讀取被調用
        mock_file_service.read_from_s3.assert_called_once_with("s3://bucket/test.jpg")

        # 驗證 Bedrock 被調用
        mock_bedrock.converse.assert_called_once()
        call_args = mock_bedrock.converse.call_args
        assert call_args[1]["modelId"] == "anthropic.claude-3-5-sonnet-20241022-v2:0"

    @patch("tools.image_analysis.file_service")
    def test_analyze_image_s3_read_failure(self, mock_file_service):
        """測試 S3 讀取失敗"""
        # Mock S3 讀取失敗
        mock_file_service.read_from_s3.return_value = None

        # 執行
        result = analyze_image(
            image_s3_url="s3://bucket/missing.jpg", user_id="user123", filename="missing.jpg"
        )

        # 驗證
        assert result["success"] is False
        assert "無法從 S3 讀取圖片" in result["error"]
        assert result["source"] == "s3://bucket/missing.jpg"

    @patch("tools.image_analysis.file_service")
    @patch("tools.image_analysis.get_bedrock_client")
    def test_analyze_image_bedrock_failure(self, mock_bedrock_client, mock_file_service):
        """測試 Bedrock 調用失敗"""
        # Mock S3 成功
        mock_file_service.read_from_s3.return_value = b"image_bytes"

        # Mock Bedrock 失敗
        mock_bedrock = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock
        mock_bedrock.converse.side_effect = Exception("Bedrock API error")

        # 執行
        result = analyze_image(
            image_s3_url="s3://bucket/test.jpg", user_id="user123", filename="test.jpg"
        )

        # 驗證
        assert result["success"] is False
        assert "圖片分析失敗" in result["error"]
        assert "Bedrock API error" in result["error"]

    @patch("tools.image_analysis.file_service")
    @patch("tools.image_analysis.get_bedrock_client")
    def test_analyze_image_with_custom_task(self, mock_bedrock_client, mock_file_service):
        """測試自定義分析任務"""
        # Mock 成功
        mock_file_service.read_from_s3.return_value = b"image_bytes"
        mock_bedrock = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "圖片中有 3 隻貓"}]}}
        }

        # 執行（自定義任務）
        result = analyze_image(
            image_s3_url="s3://bucket/cats.jpg",
            user_id="user123",
            task="計算圖片中有幾隻貓",
            filename="cats.jpg",
        )

        # 驗證
        assert result["success"] is True
        assert "貓" in result["analysis"]

        # 驗證 task 被正確傳遞到 Bedrock
        call_args = mock_bedrock.converse.call_args
        messages = call_args[1]["messages"]
        content = messages[0]["content"]

        # 檢查 content 包含 task（Bedrock API 不使用 "type"）
        text_content = [c for c in content if "text" in c]
        assert len(text_content) == 1
        assert text_content[0]["text"] == "計算圖片中有幾隻貓"

    @patch("tools.image_analysis.file_service")
    @patch("tools.image_analysis.get_bedrock_client")
    def test_analyze_image_png_format(self, mock_bedrock_client, mock_file_service):
        """測試 PNG 格式圖片"""
        mock_file_service.read_from_s3.return_value = b"png_bytes"
        mock_bedrock = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = {
            "output": {"message": {"content": [{"text": "PNG 圖片"}]}}
        }

        # 執行
        result = analyze_image(
            image_s3_url="s3://bucket/screenshot.png", user_id="user123", filename="screenshot.png"
        )

        # 驗證格式正確
        assert result["format"] == "png"

        # 驗證 Bedrock 收到正確格式（Bedrock API 不使用 "type"）
        call_args = mock_bedrock.converse.call_args
        messages = call_args[1]["messages"]
        content = messages[0]["content"]
        image_content = [c for c in content if "image" in c]
        assert len(image_content) == 1
        assert image_content[0]["image"]["format"] == "png"

    @patch("tools.image_analysis.file_service")
    @patch("tools.image_analysis.get_bedrock_client")
    def test_analyze_image_empty_response(self, mock_bedrock_client, mock_file_service):
        """測試 Bedrock 返回空回應"""
        mock_file_service.read_from_s3.return_value = b"image_bytes"
        mock_bedrock = MagicMock()
        mock_bedrock_client.return_value = mock_bedrock

        # Mock 空回應
        mock_bedrock.converse.return_value = {"output": {"message": {"content": [{"text": ""}]}}}

        # 執行
        result = analyze_image(
            image_s3_url="s3://bucket/test.jpg", user_id="user123", filename="test.jpg"
        )

        # 驗證
        assert result["success"] is True
        assert result["analysis"] == ""  # 空分析結果仍視為成功
