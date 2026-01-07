"""
Tests for file_handler module - 檔案處理模組測試
測試 Telegram 檔案下載和 S3 上傳功能
"""

import os
from unittest.mock import Mock, patch

import file_handler
import pytest
import requests
from botocore.exceptions import ClientError
from moto import mock_aws


@pytest.fixture
def mock_s3():
    """Mock S3"""
    with mock_aws():
        import boto3

        # 創建 S3 bucket
        s3 = boto3.client("s3", region_name="us-west-2")
        bucket_name = "test-telegram-files"
        s3.create_bucket(
            Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
        )

        # 設置環境變數
        with patch.dict(os.environ, {"FILE_STORAGE_BUCKET": bucket_name}):
            # 重新初始化 file_handler 的 S3_BUCKET
            file_handler.S3_BUCKET = bucket_name
            file_handler._s3_client = None  # 重置客戶端

            yield s3


@pytest.fixture
def sample_file_content():
    """測試用檔案內容"""
    return b"This is a test file content with some data: \x00\x01\x02\x03"


class TestGetBotToken:
    """測試 get_bot_token 函數"""

    @patch("file_handler.get_telegram_secrets")
    def test_get_token_success(self, mock_secrets):
        """測試成功獲取 token"""
        mock_secrets.return_value = {"bot_token": "test_token_123"}

        token = file_handler.get_bot_token()

        assert token == "test_token_123"

    @patch("file_handler.get_telegram_secrets")
    def test_get_token_no_secrets(self, mock_secrets):
        """測試 secrets 為 None"""
        mock_secrets.return_value = None

        token = file_handler.get_bot_token()

        assert token == ""

    @patch("file_handler.get_telegram_secrets")
    def test_get_token_no_bot_token_key(self, mock_secrets):
        """測試沒有 bot_token key"""
        mock_secrets.return_value = {"webhook_secret_token": "secret"}

        token = file_handler.get_bot_token()

        assert token == ""

    @patch("file_handler.get_telegram_secrets")
    def test_get_token_exception(self, mock_secrets):
        """測試發生異常"""
        mock_secrets.side_effect = Exception("Secrets error")

        token = file_handler.get_bot_token()

        assert token == ""


class TestDownloadTelegramFile:
    """測試 download_telegram_file 函數"""

    @patch("file_handler.get_bot_token")
    @patch("file_handler.requests.get")
    def test_download_success(self, mock_get, mock_token, sample_file_content):
        """測試成功下載檔案"""
        mock_token.return_value = "test_token_123"

        # Mock getFile API 回應
        mock_file_info = Mock()
        mock_file_info.json.return_value = {
            "ok": True,
            "result": {"file_path": "photos/file_123.jpg", "file_size": len(sample_file_content)},
        }
        mock_file_info.raise_for_status = Mock()

        # Mock file download 回應
        mock_download = Mock()
        mock_download.content = sample_file_content
        mock_download.raise_for_status = Mock()

        # 設置 requests.get 的兩次調用
        mock_get.side_effect = [mock_file_info, mock_download]

        result = file_handler.download_telegram_file("test_file_id")

        assert result == sample_file_content
        assert mock_get.call_count == 2

    @patch("file_handler.get_bot_token")
    def test_download_no_bot_token(self, mock_token):
        """測試沒有 bot token"""
        mock_token.return_value = ""

        result = file_handler.download_telegram_file("test_file_id")

        assert result is None

    @patch("file_handler.get_bot_token")
    @patch("file_handler.requests.get")
    def test_download_get_file_fails(self, mock_get, mock_token):
        """測試 getFile API 失敗"""
        mock_token.return_value = "test_token_123"

        # Mock getFile API 返回失敗
        mock_response = Mock()
        mock_response.json.return_value = {"ok": False, "description": "File not found"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = file_handler.download_telegram_file("test_file_id")

        assert result is None

    @patch("file_handler.get_bot_token")
    @patch("file_handler.requests.get")
    def test_download_http_error(self, mock_get, mock_token):
        """測試 HTTP 錯誤"""
        mock_token.return_value = "test_token_123"
        mock_get.side_effect = requests.exceptions.ConnectionError("Network error")

        result = file_handler.download_telegram_file("test_file_id")

        assert result is None

    @patch("file_handler.get_bot_token")
    @patch("file_handler.requests.get")
    def test_download_timeout(self, mock_get, mock_token):
        """測試超時"""
        mock_token.return_value = "test_token_123"
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")

        result = file_handler.download_telegram_file("test_file_id")

        assert result is None

    @patch("file_handler.get_bot_token")
    @patch("file_handler.requests.get")
    def test_download_unexpected_error(self, mock_get, mock_token):
        """測試非預期錯誤"""
        mock_token.return_value = "test_token_123"
        mock_get.side_effect = RuntimeError("Unexpected error")

        result = file_handler.download_telegram_file("test_file_id")

        assert result is None


class TestUploadToS3:
    """測試 upload_to_s3 函數"""

    def test_upload_success(self, mock_s3, sample_file_content):
        """測試成功上傳到 S3"""
        result = file_handler.upload_to_s3(
            sample_file_content,
            chat_id=12345,
            message_id=67890,
            filename="test.pdf",
            mime_type="application/pdf",
        )

        assert result is not None
        assert result == "s3://test-telegram-files/12345/67890/test.pdf"

        # 驗證檔案確實上傳了
        s3_key = "12345/67890/test.pdf"
        obj = mock_s3.get_object(Bucket="test-telegram-files", Key=s3_key)
        assert obj["Body"].read() == sample_file_content
        assert obj["ContentType"] == "application/pdf"

    def test_upload_without_mime_type(self, mock_s3, sample_file_content):
        """測試沒有 MIME 類型的上傳"""
        result = file_handler.upload_to_s3(
            sample_file_content, chat_id=12345, message_id=67890, filename="test.bin"
        )

        assert result is not None

        # 驗證使用預設 ContentType
        obj = mock_s3.get_object(Bucket="test-telegram-files", Key="12345/67890/test.bin")
        assert obj["ContentType"] == "application/octet-stream"

    @patch.dict(os.environ, {"FILE_STORAGE_BUCKET": ""})
    def test_upload_no_bucket_configured(self, sample_file_content):
        """測試沒有配置 bucket"""
        file_handler.S3_BUCKET = ""  # 重置

        result = file_handler.upload_to_s3(
            sample_file_content, chat_id=12345, message_id=67890, filename="test.pdf"
        )

        assert result is None

    @patch("file_handler.get_s3_client")
    def test_upload_s3_error(self, mock_get_client, sample_file_content):
        """測試 S3 上傳錯誤"""
        # 設置環境變數
        file_handler.S3_BUCKET = "test-bucket"

        mock_s3 = Mock()
        mock_s3.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access denied"}}, "PutObject"
        )
        mock_get_client.return_value = mock_s3

        result = file_handler.upload_to_s3(
            sample_file_content, chat_id=12345, message_id=67890, filename="test.pdf"
        )

        assert result is None

    @patch("file_handler.get_s3_client")
    def test_upload_unexpected_error(self, mock_get_client, sample_file_content):
        """測試非預期錯誤"""
        file_handler.S3_BUCKET = "test-bucket"

        mock_s3 = Mock()
        mock_s3.put_object.side_effect = RuntimeError("Unexpected S3 error")
        mock_get_client.return_value = mock_s3

        result = file_handler.upload_to_s3(
            sample_file_content, chat_id=12345, message_id=67890, filename="test.pdf"
        )

        assert result is None


class TestProcessFileAttachment:
    """測試 process_file_attachment 函數"""

    @patch("file_handler.upload_to_s3")
    @patch("file_handler.download_telegram_file")
    def test_process_photo_success(self, mock_download, mock_upload):
        """測試成功處理圖片"""
        mock_download.return_value = b"fake_image_data"
        mock_upload.return_value = "s3://bucket/chat/message/photo.jpg"

        result = file_handler.process_file_attachment(
            file_id="file_123",
            filename="photo.jpg",
            chat_id=12345,
            message_id=67890,
            mime_type="image/jpeg",
            file_size=1024,
            caption="測試圖片",
        )

        assert result["type"] == "photo"
        assert result["file_id"] == "file_123"
        assert result["s3_url"] == "s3://bucket/chat/message/photo.jpg"
        assert result["task"] == "測試圖片"
        assert "error" not in result

    @patch("file_handler.upload_to_s3")
    @patch("file_handler.download_telegram_file")
    def test_process_document_success(self, mock_download, mock_upload):
        """測試成功處理文件"""
        mock_download.return_value = b"fake_pdf_data"
        mock_upload.return_value = "s3://bucket/chat/message/doc.pdf"

        result = file_handler.process_file_attachment(
            file_id="file_456",
            filename="doc.pdf",
            chat_id=12345,
            message_id=67890,
            mime_type="application/pdf",
        )

        assert result["type"] == "document"
        assert result["task"] == "摘要此檔案的內容"
        assert result["s3_url"] == "s3://bucket/chat/message/doc.pdf"

    @patch("file_handler.download_telegram_file")
    def test_process_download_fails(self, mock_download):
        """測試下載失敗"""
        mock_download.return_value = None

        result = file_handler.process_file_attachment(
            file_id="file_789", filename="test.pdf", chat_id=12345, message_id=67890
        )

        assert result["error"] == "檔案下載失敗"
        assert "s3_url" not in result

    @patch("file_handler.upload_to_s3")
    @patch("file_handler.download_telegram_file")
    def test_process_upload_fails(self, mock_download, mock_upload):
        """測試上傳失敗"""
        mock_download.return_value = b"file_content"
        mock_upload.return_value = None

        result = file_handler.process_file_attachment(
            file_id="file_789", filename="test.pdf", chat_id=12345, message_id=67890
        )

        assert result["error"] == "檔案上傳失敗"
        assert "s3_url" not in result

    @patch("file_handler.upload_to_s3")
    @patch("file_handler.download_telegram_file")
    def test_process_updates_file_size(self, mock_download, mock_upload):
        """測試更新實際檔案大小"""
        actual_content = b"actual_file_content_here"
        mock_download.return_value = actual_content
        mock_upload.return_value = "s3://bucket/file"

        result = file_handler.process_file_attachment(
            file_id="file_id",
            filename="file.txt",
            chat_id=123,
            message_id=456,
            file_size=100,  # 提供的大小不準
        )

        # 應該使用實際下載的大小
        assert result["file_size"] == len(actual_content)


class TestDetectAttachmentType:
    """測試 _detect_attachment_type 函數"""

    def test_detect_jpg(self):
        """測試 JPG 檔案"""
        assert file_handler._detect_attachment_type("photo.jpg") == "photo"
        assert file_handler._detect_attachment_type("IMG_001.JPG") == "photo"

    def test_detect_png(self):
        """測試 PNG 檔案"""
        assert file_handler._detect_attachment_type("image.png") == "photo"

    def test_detect_gif(self):
        """測試 GIF 檔案"""
        assert file_handler._detect_attachment_type("animation.gif") == "photo"

    def test_detect_webp(self):
        """測試 WebP 檔案"""
        assert file_handler._detect_attachment_type("sticker.webp") == "photo"

    def test_detect_by_mime_type(self):
        """測試通過 MIME 類型判斷"""
        assert file_handler._detect_attachment_type("unknown.bin", "image/jpeg") == "photo"
        assert file_handler._detect_attachment_type("file", "image/png") == "photo"

    def test_detect_document(self):
        """測試文件類型"""
        assert file_handler._detect_attachment_type("doc.pdf") == "document"
        assert file_handler._detect_attachment_type("file.txt") == "document"
        assert file_handler._detect_attachment_type("data.json") == "document"

    def test_detect_no_extension(self):
        """測試沒有副檔名"""
        assert file_handler._detect_attachment_type("noextension") == "document"

    def test_detect_unknown_extension(self):
        """測試未知副檔名"""
        assert file_handler._detect_attachment_type("file.xyz") == "document"

    def test_detect_case_insensitive(self):
        """測試大小寫不敏感"""
        assert file_handler._detect_attachment_type("PHOTO.PNG") == "photo"
        assert file_handler._detect_attachment_type("Image.JPEG") == "photo"


class TestValidateFileSize:
    """測試 validate_file_size 函數"""

    def test_valid_small_file(self):
        """測試小檔案"""
        is_valid, message = file_handler.validate_file_size(1024)  # 1KB

        assert is_valid is True
        assert message == ""

    def test_valid_medium_file(self):
        """測試中等大小檔案"""
        is_valid, message = file_handler.validate_file_size(10 * 1024 * 1024)  # 10MB

        assert is_valid is True

    def test_valid_max_size(self):
        """測試最大允許大小"""
        is_valid, message = file_handler.validate_file_size(20 * 1024 * 1024)  # 20MB

        assert is_valid is True

    def test_invalid_too_large(self):
        """測試檔案過大"""
        is_valid, message = file_handler.validate_file_size(25 * 1024 * 1024)  # 25MB

        assert is_valid is False
        assert "檔案過大" in message
        assert "25.0MB" in message

    def test_invalid_zero_size(self):
        """測試零大小"""
        is_valid, message = file_handler.validate_file_size(0)

        assert is_valid is False
        assert "無效" in message

    def test_invalid_negative_size(self):
        """測試負數大小"""
        is_valid, message = file_handler.validate_file_size(-100)

        assert is_valid is False
        assert "無效" in message

    def test_custom_max_size(self):
        """測試自訂最大大小"""
        max_size = 5 * 1024 * 1024  # 5MB

        # 4MB - 應該通過
        is_valid, _ = file_handler.validate_file_size(4 * 1024 * 1024, max_size)
        assert is_valid is True

        # 6MB - 應該失敗
        is_valid, message = file_handler.validate_file_size(6 * 1024 * 1024, max_size)
        assert is_valid is False
        assert "6.0MB" in message
        assert "5MB" in message


class TestGetS3Client:
    """測試 get_s3_client 函數"""

    def test_s3_client_singleton(self):
        """測試 S3 客戶端是單例"""
        # 重置
        file_handler._s3_client = None

        client1 = file_handler.get_s3_client()
        client2 = file_handler.get_s3_client()

        assert client1 is client2


class TestIntegrationScenarios:
    """測試整合場景"""

    @patch("file_handler.upload_to_s3")
    @patch("file_handler.download_telegram_file")
    def test_process_multiple_file_types(self, mock_download, mock_upload):
        """測試處理多種檔案類型"""
        mock_download.return_value = b"content"
        mock_upload.side_effect = lambda c, chat, msg, name, mime: f"s3://bucket/{name}"

        # 圖片
        result_photo = file_handler.process_file_attachment(
            "id1", "photo.jpg", 123, 1, mime_type="image/jpeg"
        )
        assert result_photo["type"] == "photo"

        # PDF
        result_pdf = file_handler.process_file_attachment(
            "id2", "doc.pdf", 123, 2, mime_type="application/pdf"
        )
        assert result_pdf["type"] == "document"

        # 影片
        result_video = file_handler.process_file_attachment(
            "id3", "video.mp4", 123, 3, mime_type="video/mp4"
        )
        assert result_video["type"] == "document"

    @patch("file_handler.upload_to_s3")
    @patch("file_handler.download_telegram_file")
    def test_process_with_caption(self, mock_download, mock_upload):
        """測試帶 caption 的處理"""
        mock_download.return_value = b"content"
        mock_upload.return_value = "s3://url"

        result = file_handler.process_file_attachment(
            "id", "file.pdf", 123, 1, caption="請分析這份文件"
        )

        assert result["task"] == "請分析這份文件"

    @patch("file_handler.upload_to_s3")
    @patch("file_handler.download_telegram_file")
    def test_process_without_caption(self, mock_download, mock_upload):
        """測試沒有 caption 的處理"""
        mock_download.return_value = b"content"
        mock_upload.return_value = "s3://url"

        # 圖片 - 預設任務
        result_photo = file_handler.process_file_attachment(
            "id1", "photo.jpg", 123, 1, mime_type="image/jpeg"
        )
        assert "請描述這張圖片" in result_photo["task"]

        # 文件 - 預設任務
        result_doc = file_handler.process_file_attachment("id2", "doc.pdf", 123, 2)
        assert "摘要此檔案" in result_doc["task"]
