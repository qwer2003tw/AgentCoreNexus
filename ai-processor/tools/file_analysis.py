"""
檔案分析工具
負責使用 AgentCore Code Interpreter 分析各種類型的檔案
"""

from services.file_service import file_service
from utils.logger import get_logger

logger = get_logger(__name__)


def analyze_file_tool(file_s3_url: str, task: str = "摘要檔案內容") -> str:
    """
    分析存儲在 S3 的各種類型檔案。

    此工具使用 AgentCore Code Interpreter 執行 Python 代碼來分析檔案，
    支援 PDF、TXT、CSV、JSON、Excel 等多種格式。

    使用時機：
    - 用戶上傳文件並詢問相關問題
    - 用戶提到「這份文件」、「剛才那個報告」等（從 Memory 獲取 S3 URL）
    - 需要讀取、分析、摘要或統計檔案內容

    支援的任務範例：
    - "摘要檔案內容"：生成檔案的摘要
    - "分析檔案"：進行深入分析（適合 CSV, JSON, Excel）
    - "統計資訊"：計算統計數據（行數、欄位數、平均值等）
    - "提取特定資訊"：從檔案中提取用戶關心的特定內容
    - "第 X 章說了什麼"：讀取特定章節或部分
    - 自訂任務：根據用戶的具體問題調整

    支援的檔案類型：
    - 文字檔：TXT, MD, LOG
    - 數據檔：CSV, JSON, XML
    - 文檔：PDF（需要 Code Interpreter 解析）
    - 試算表：Excel（需要適當的 Python 套件）

    Args:
        file_s3_url: 檔案的 S3 URL (格式: s3://bucket/key)
        task: 分析任務的具體描述

    Returns:
        檔案分析結果（文字）

    範例：
        >>> analyze_file_tool("s3://bucket/report.pdf", "摘要這份報告")
        "這份報告包含 50 頁內容，主要討論..."

        >>> analyze_file_tool("s3://bucket/data.csv", "統計資訊")
        "CSV 檔案包含 1000 行數據，5 個欄位..."
    """
    logger.info("📁 File Analysis Tool called", extra={"s3_url": file_s3_url, "task": task})

    try:
        # 檢查 file service 是否可用
        if not file_service.is_available():
            error_msg = "檔案處理服務未啟用或未配置 S3 bucket"
            logger.warning(error_msg)
            return f"❌ {error_msg}"

        # 提取檔名
        filename = file_s3_url.split("/")[-1]

        logger.info(f"📄 Processing file: {filename}", extra={"filename": filename, "task": task})

        # 調用 file_service 處理檔案
        result = file_service.process_file(
            s3_url=file_s3_url,
            filename=filename,
            task=task,
            user_id="system",  # Tool 調用使用系統 ID
        )

        if result["success"]:
            logger.info(
                "✅ File analysis completed",
                extra={"filename": filename, "result_length": len(str(result["result"]))},
            )
            return result["result"]
        else:
            error_msg = result.get("error", "未知錯誤")
            logger.warning(f"File analysis failed: {error_msg}")
            return f"檔案分析失敗：{error_msg}\n請確認檔案格式正確且可訪問。"

    except Exception as e:
        logger.error(f"File analysis tool error: {e}", exc_info=True)
        return f"檔案分析工具執行失敗：{str(e)}"
