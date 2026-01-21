"""
瀏覽器服務模組
封裝瀏覽器相關功能
"""

from config.prompts import get_browser_prompt, get_error_message
from utils.logger import get_logger

logger = get_logger(__name__)


class BrowserService:
    """瀏覽器服務類"""

    def __init__(self, region: str):
        """
        初始化瀏覽器服務

        Args:
            region: AWS 區域
        """
        self.region = region
        self.browser_tool = None
        self._available = False
        self._initialize_browser()

    def _initialize_browser(self):
        """初始化瀏覽器工具"""
        try:
            # 使用 bedrock-agentcore 的 browser_session
            # 這使用 AWS 管理的 Browser sandbox 服務，不需要 Playwright
            try:
                from bedrock_agentcore.tools.browser_client import BrowserClient, browser_session

                self.browser_session = browser_session
                self.BrowserClient = BrowserClient
                self._use_agentcore_browser = True
                self._region = self.region
                self._available = True
                logger.info(f"🌐 Bedrock AgentCore 瀏覽器服務已初始化 (區域: {self.region})")
                return
            except ImportError as e:
                logger.error(f"❌ 無法導入 bedrock-agentcore browser: {e}")
                raise e

        except Exception as e:
            self._available = False
            logger.warning(f"⚠️ 瀏覽器工具初始化失敗: {str(e)}")

    def is_available(self) -> bool:
        """
        檢查瀏覽器服務是否可用

        Returns:
            是否可用
        """
        return self._available

    def browse_with_backup(self, url: str, task_description: str) -> str:
        """
        使用 AWS Browser sandbox 瀏覽網頁

        Args:
            url: 目標 URL
            task_description: 任務描述

        Returns:
            瀏覽結果
        """
        if not self._available:
            return get_error_message("browser_init_failed", error="瀏覽器服務不可用")

        try:
            logger.info(f"🔄 使用 AWS Browser sandbox 訪問: {url}")

            # 使用 browser_session 上下文管理器
            with self.browser_session(self.region) as client:
                logger.info("✅ Browser sandbox 會話已啟動")

                # 獲取 WebSocket URL 和 headers
                ws_url, headers = client.generate_ws_headers()
                logger.info("🔗 WebSocket URL 已生成")

                # 注意：實際的瀏覽器操作需要通過 WebSocket 連接到 sandbox
                # 這裡我們返回基本信息表示服務可用
                result = "🌐 AWS Browser Sandbox 服務可用\n\n"
                result += f"🔗 目標 URL: {url}\n"
                result += "✅ 瀏覽器會話已成功創建\n"
                result += f"📝 任務: {task_description}\n\n"
                result += "ℹ️ AWS Browser sandbox 需要通過 WebSocket 進行操作。\n"
                result += "此功能目前僅驗證服務連接正常。"

                return result

        except Exception as e:
            logger.error(f"❌ Browser sandbox 錯誤: {str(e)}", exc_info=True)
            return get_error_message("browser_navigation_failed", error=str(e))

    def _get_page_title(self, session_name: str) -> str:
        """
        獲取頁面標題

        Args:
            session_name: 會話名稱

        Returns:
            頁面標題
        """
        try:
            title_result = self.browser_tool.browser(
                {
                    "action": {
                        "type": "evaluate",
                        "session_name": session_name,
                        "script": "document.title",
                    }
                }
            )

            if title_result.get("status") == "success":
                title_text = title_result.get("content", [{}])[0].get("text", "")
                if "Evaluation result:" in title_text:
                    return title_text.replace("Evaluation result:", "").strip()

            return "無法取得標題"

        except Exception as e:
            logger.warning(f"⚠️ 標題提取失敗: {e}")
            return "無法取得標題"

    def _get_page_content(self, session_name: str) -> str:
        """
        獲取頁面內容

        Args:
            session_name: 會話名稱

        Returns:
            頁面內容
        """
        try:
            logger.info(get_browser_prompt("extracting_content"))

            content_result = self.browser_tool.browser(
                {"action": {"type": "get_text", "session_name": session_name, "selector": "body"}}
            )

            if content_result.get("status") == "success":
                content_text = content_result.get("content", [{}])[0].get("text", "")
                if "Text content:" in content_text:
                    page_content = content_text.replace("Text content:", "").strip()

                    # 限制內容長度
                    if len(page_content) > 1500:
                        page_content = (
                            page_content[:1500] + "\n\n" + get_browser_prompt("content_truncated")
                        )

                    return page_content

            return get_error_message("content_extraction_failed")

        except Exception as e:
            logger.warning(f"⚠️ 內容提取失敗: {e}")
            return get_error_message("content_extraction_failed")

    def _close_session(self, session_name: str):
        """
        關閉瀏覽器會話

        Args:
            session_name: 會話名稱
        """
        try:
            self.browser_tool.browser({"action": {"type": "close", "session_name": session_name}})
            logger.info(f"✅ 瀏覽器會話已清理: {session_name}")
        except Exception as e:
            logger.warning(f"⚠️ 瀏覽器會話清理警告: {e}")

    def _extract_error_text(self, result: dict) -> str:
        """
        從結果中提取錯誤文字

        Args:
            result: 操作結果

        Returns:
            錯誤文字
        """
        try:
            return result.get("content", [{}])[0].get("text", "未知錯誤")
        except:
            return "未知錯誤"

    def _format_result(self, url: str, title: str, content: str) -> str:
        """
        格式化瀏覽結果

        Args:
            url: 網址
            title: 頁面標題
            content: 頁面內容

        Returns:
            格式化的結果
        """
        result = "🔄 備用瀏覽器工具執行成功：\n\n"
        result += f"📄 標題: {title}\n"
        result += f"🔗 網址: {url}\n\n"
        result += f"📝 內容摘要:\n{content}\n"

        return result

    def get_status(self) -> dict:
        """
        獲取服務狀態

        Returns:
            狀態資訊
        """
        return {"available": self._available, "region": self.region}
