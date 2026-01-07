"""
瀏覽器工具模組
提供網頁瀏覽和內容提取功能
"""

import re
import time

from strands import tool

from config.prompts import get_browser_prompt, get_error_message
from config.settings import settings
from utils.logger import get_logger

logger = get_logger(__name__)

# 瀏覽器服務初始化狀態
browser_service = None
browser_available = False


def init_browser_service():
    """初始化瀏覽器服務"""
    global browser_service, browser_available

    if not settings.BROWSER_ENABLED:
        logger.info("瀏覽器功能已停用")
        return False

    try:
        from services.browser_service import BrowserService

        browser_service = BrowserService(settings.AWS_REGION)
        browser_available = browser_service.is_available()
        logger.info(f"🌐 瀏覽器服務初始化: {'成功' if browser_available else '失敗'}")
        return browser_available
    except Exception as e:
        logger.error(f"瀏覽器服務初始化錯誤: {str(e)}", exc_info=True)
        browser_available = False
        return False


@tool
def browse_website_official(task_description: str) -> str:
    """
    使用官方 Playwright + AgentCore Browser 整合瀏覽網站

    Args:
        task_description: 瀏覽任務描述，例如：
                        - "訪問 https://example.com 並提取頁面標題"
                        - "瀏覽 https://news.com 並總結主要內容"
                        - "查看 https://docs.aws.amazon.com 的文件"

    Returns:
        str: 瀏覽結果的詳細描述
    """
    logger.info(f"🌐 使用官方 Playwright 瀏覽器開始任務: {task_description[:100]}...")

    try:
        from bedrock_agentcore.tools.browser_client import browser_session
        from playwright.sync_api import sync_playwright

        # 使用官方的 browser_session 和 Playwright 整合
        with browser_session(settings.AWS_REGION) as client:
            logger.info("✅ AgentCore Browser 會話已建立")

            # 獲取 WebSocket URL 和 headers
            ws_url, headers = client.generate_ws_headers()
            logger.info("✅ WebSocket 連接資訊已生成")

            with sync_playwright() as playwright:
                # 透過 CDP 連接到遠端 Chrome 瀏覽器
                browser = playwright.chromium.connect_over_cdp(ws_url, headers=headers)
                context = browser.contexts[0]
                page = context.pages[0]

                try:
                    # 解析任務描述，嘗試提取 URL
                    urls = extract_urls(task_description)

                    if urls:
                        # 如果找到 URL，訪問第一個
                        target_url = urls[0]
                        logger.info(f"🎯 訪問目標 URL: {target_url}")

                        # 檢查是否為 PDF 檔案
                        if target_url.lower().endswith(".pdf"):
                            logger.warning(get_browser_prompt("pdf_warning"))

                        # 導航到目標頁面
                        page.goto(
                            target_url, wait_until="networkidle", timeout=settings.BROWSER_TIMEOUT
                        )

                        # 獲取頁面標題
                        title = page.title()
                        logger.info(f"📄 頁面標題: {title}")

                        # 嘗試提取頁面內容
                        content = extract_page_content(page)

                        # 構建結果
                        result = format_browse_result(target_url, title, content)

                    else:
                        # 沒有找到 URL，回傳說明
                        result = get_error_message("invalid_url")

                    # 等待一小段時間確保頁面完全載入
                    time.sleep(2)

                finally:
                    # 確保清理資源
                    try:
                        page.close()
                        browser.close()
                        logger.info("✅ 瀏覽器資源已清理")
                    except Exception as cleanup_error:
                        logger.warning(f"⚠️ 瀏覽器資源清理警告: {cleanup_error}")

                return result

    except Exception as e:
        error_msg = f"官方瀏覽器工具執行失敗: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return get_error_message("browser_navigation_failed", error=str(e))


@tool
def browse_website_backup(task_description: str) -> str:
    """
    備用瀏覽器工具 - 使用正確的 AgentCoreBrowser 調用格式
    當官方 Playwright 方法失敗時使用此備用方案

    Args:
        task_description: 瀏覽任務描述，需包含 URL

    Returns:
        str: 瀏覽結果描述
    """
    # 確保瀏覽器服務已初始化
    if not browser_available and not init_browser_service():
        return "❌ 備用瀏覽器功能不可用，請檢查瀏覽器工具初始化狀態。"

    logger.info(f"🔄 使用備用瀏覽器工具: {task_description[:100]}...")

    # 提取 URL
    urls = extract_urls(task_description)

    if not urls:
        return get_error_message("invalid_url")

    target_url = urls[0]

    try:
        result = browser_service.browse_with_backup(target_url, task_description)
        logger.info("✅ 備用瀏覽器任務完成")
        return result

    except Exception as e:
        error_msg = f"備用瀏覽器工具執行錯誤: {str(e)}"
        logger.error(f"❌ {error_msg}", exc_info=True)
        return get_error_message("browser_navigation_failed", error=str(e))


def extract_urls(text: str) -> list:
    """
    從文字中提取 URL

    Args:
        text: 包含 URL 的文字

    Returns:
        URL 列表
    """
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def extract_page_content(page) -> str:
    """
    提取頁面內容

    Args:
        page: Playwright page 物件

    Returns:
        提取的內容文字
    """
    try:
        logger.info(get_browser_prompt("extracting_content"))

        # 獲取主要文字內容
        content = page.evaluate("""
            () => {
                // 移除腳本和樣式標籤
                const scripts = document.querySelectorAll('script, style, nav, footer, aside');
                scripts.forEach(el => el.remove());

                // 嘗試獲取主要內容
                let mainContent = document.querySelector('main, article, .content, .main-content, #main, #content');
                if (!mainContent) {
                    mainContent = document.body;
                }

                return mainContent ? mainContent.innerText.trim() : document.body.innerText.trim();
            }
        """)

        # 限制內容長度避免過長
        if content and len(content) > 2000:
            content = content[:2000] + "\n\n" + get_browser_prompt("content_truncated")

        return content if content else get_error_message("content_extraction_failed")

    except Exception as e:
        logger.warning(f"⚠️ 內容提取失敗: {e}")
        return get_error_message("content_extraction_failed")


def format_browse_result(url: str, title: str, content: str) -> str:
    """
    格式化瀏覽結果

    Args:
        url: 網址
        title: 頁面標題
        content: 頁面內容

    Returns:
        格式化的結果字串
    """
    result = "🌐 網站瀏覽結果：\n\n"
    result += f"📄 標題: {title}\n"
    result += f"🔗 網址: {url}\n\n"
    result += f"📝 內容摘要:\n{content}\n"

    return result


# 初始化瀏覽器服務（延遲載入）
# 這將在第一次使用時初始化
