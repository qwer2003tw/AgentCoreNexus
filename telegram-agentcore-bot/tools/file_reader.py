"""
檔案讀取工具模組
提供檔案處理能力
"""

from strands import tool

from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# 檔案服務初始化狀態
file_service = None
file_available = False


def init_file_service():
    """初始化檔案服務"""
    global file_service, file_available

    if not settings.FILE_ENABLED:
        logger.info("📁 檔案處理功能已停用")
        return False

    try:
        from services.file_service import file_service as fs

        file_service = fs
        file_available = file_service.is_available()
        logger.info(f"📁 檔案服務初始化: {'成功' if file_available else '失敗（S3 未配置）'}")
        return file_available
    except Exception as e:
        logger.error(f"檔案服務初始化錯誤: {str(e)}", exc_info=True)
        file_available = False
        return False


@tool
def read_file(file_description: str) -> str:
    """
    讀取和處理用戶上傳的檔案

    當用戶上傳檔案到 Telegram 時，此工具會自動被觸發。
    用戶可以在上傳檔案時添加 Caption 來描述想要執行的任務。

    Args:
        file_description: 檔案處理請求描述，包含檔案資訊和任務。
                        系統會自動從訊息上下文中提取：
                        - 檔案名稱
                        - S3 URL
                        - 處理任務（來自 Caption 或預設為"摘要"）

                        範例：
                        - "處理檔案 data.csv，任務：分析"
                        - "讀取 report.txt"

    Returns:
        檔案處理結果的文字描述

    注意：
        - 用戶必須有 file_reader 權限
        - 檔案會先被下載到 S3，然後由此工具處理
        - 支援的檔案類型：CSV, JSON, TXT, MD 等文字檔案
    """
    # 確保檔案服務已初始化
    if not file_available:
        if not init_file_service():
            return "❌ 檔案處理功能不可用。請確認：\n1. FILE_ENABLED 已設為 true\n2. FILE_STORAGE_BUCKET 已配置\n3. Code Interpreter 權限已添加"

    logger.info(f"📁 檔案處理工具被調用: {file_description[:100]}...")

    # 注意：實際實作中，檔案資訊需要從 processor_entry.py 的 context 中傳遞
    # 這個工具函數會被 Agent 自動調用，檔案資訊會透過 context 提供

    return (
        "📁 檔案讀取工具已就緒。\n\n"
        "使用方式：\n"
        "1. 透過 Telegram 上傳檔案\n"
        "2. 可選：添加 Caption 描述要執行的任務\n"
        "3. 系統會自動處理檔案並返回結果\n\n"
        "支援的任務：\n"
        "- 摘要（預設）\n"
        "- 分析（適用於 CSV, JSON）\n"
        "- 統計（適用於資料檔案）\n\n"
        "支援的檔案類型：\n"
        "- 文字檔：TXT, MD, CSV, JSON\n"
        "- 文件：PDF, DOC, DOCX（未來支援）\n"
        "- 圖片：JPG, PNG（需要 Caption 指示任務）"
    )


# 初始化檔案服務（延遲載入）
# 這將在第一次使用時初始化
