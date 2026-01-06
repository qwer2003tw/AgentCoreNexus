"""
瀏覽器服務模組
封裝瀏覽器相關功能
"""
import uuid
from typing import Optional
from utils.logger import get_logger
from config.prompts import get_error_message, get_browser_prompt

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
            import nest_asyncio
            from strands_tools.browser import AgentCoreBrowser
            
            # 允許嵌套事件循環
            nest_asyncio.apply()
            
            # 初始化瀏覽器工具
            self.browser_tool = AgentCoreBrowser(region=self.region)
            self._available = True
            logger.info(f"🌐 瀏覽器工具已初始化 (區域: {self.region})")
            
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
        使用備用瀏覽器瀏覽網頁
        
        Args:
            url: 目標 URL
            task_description: 任務描述
        
        Returns:
            瀏覽結果
        """
        if not self._available:
            return get_error_message("browser_init_failed", error="瀏覽器服務不可用")
        
        # 生成會話名稱（只能包含小寫字母、數字和連字符）
        session_name = f"session-{uuid.uuid4().hex[:8]}"
        
        try:
            # 步驟 1: 初始化會話
            logger.info(f"🔄 初始化瀏覽器會話: {session_name}")
            init_result = self.browser_tool.browser({
                "action": {
                    "type": "init_session",
                    "session_name": session_name,
                    "description": "Browser session for web scraping"
                }
            })
            
            if init_result.get("status") != "success":
                error_text = self._extract_error_text(init_result)
                return get_error_message("browser_init_failed", error=error_text)
            
            logger.info("✅ 瀏覽器會話初始化成功")
            
            # 步驟 2: 導航到目標 URL
            logger.info(f"🔄 導航到 {url}...")
            nav_result = self.browser_tool.browser({
                "action": {
                    "type": "navigate",
                    "session_name": session_name,
                    "url": url
                }
            })
            
            if nav_result.get("status") != "success":
                self._close_session(session_name)
                error_text = self._extract_error_text(nav_result)
                return get_error_message("browser_navigation_failed", error=error_text)
            
            logger.info(get_browser_prompt("navigation_success"))
            
            # 步驟 3: 獲取頁面標題
            title = self._get_page_title(session_name)
            
            # 步驟 4: 獲取頁面內容
            content = self._get_page_content(session_name)
            
            # 步驟 5: 清理會話
            self._close_session(session_name)
            
            # 構建結果
            return self._format_result(url, title, content)
            
        except Exception as e:
            # 確保清理會話
            self._close_session(session_name)
            logger.error(f"❌ 瀏覽器服務執行錯誤: {str(e)}", exc_info=True)
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
            title_result = self.browser_tool.browser({
                "action": {
                    "type": "evaluate",
                    "session_name": session_name,
                    "script": "document.title"
                }
            })
            
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
            
            content_result = self.browser_tool.browser({
                "action": {
                    "type": "get_text", 
                    "session_name": session_name,
                    "selector": "body"
                }
            })
            
            if content_result.get("status") == "success":
                content_text = content_result.get("content", [{}])[0].get("text", "")
                if "Text content:" in content_text:
                    page_content = content_text.replace("Text content:", "").strip()
                    
                    # 限制內容長度
                    if len(page_content) > 1500:
                        page_content = page_content[:1500] + "\n\n" + get_browser_prompt("content_truncated")
                    
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
            self.browser_tool.browser({
                "action": {
                    "type": "close",
                    "session_name": session_name
                }
            })
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
            return result.get('content', [{}])[0].get('text', '未知錯誤')
        except:
            return '未知錯誤'
    
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
        result = f"🔄 備用瀏覽器工具執行成功：\n\n"
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
        return {
            "available": self._available,
            "region": self.region
        }
