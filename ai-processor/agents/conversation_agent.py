"""
對話 Agent 實作
封裝 Agent 的建立和執行邏輯
"""

from typing import Any

from strands import Agent
from strands.models import BedrockModel

from config.prompts import SYSTEM_PROMPT
from config.settings import settings
from utils.context_analyzer import analyze_context_size, log_context_analysis
from utils.error_messages import format_error_response
from utils.logger import get_logger
from utils.retry_handler import retry_with_fallback

logger = get_logger(__name__)


class ConversationAgent:
    """對話 Agent 類"""

    def __init__(self, tools: list[Any], session_manager: Any = None):
        """
        初始化對話 Agent

        Args:
            tools: 工具列表
            session_manager: Session Manager (可選)
        """
        self.tools = tools
        self.session_manager = session_manager
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        """
        建立 Agent 實例

        Returns:
            Agent 實例
        """
        try:
            # 建立 Bedrock 模型
            model = BedrockModel(
                model_id=settings.BEDROCK_MODEL_ID, region_name=settings.AWS_REGION
            )

            # 建立 Agent
            agent = Agent(
                model=model,
                session_manager=self.session_manager,
                system_prompt=SYSTEM_PROMPT,
                tools=self.tools,
            )

            logger.info(f"✅ Agent 建立成功 (模型: {settings.BEDROCK_MODEL_ID})")
            return agent

        except Exception as e:
            logger.error(f"❌ Agent 建立失敗: {str(e)}", exc_info=True)
            raise

    def process_message(self, message: str) -> dict[str, Any]:
        """
        處理用戶訊息 - 帶重試和友善錯誤處理

        ✅ 新架構：只處理純文字訊息
        圖片處理已移至 tools/image_analysis.py

        Args:
            message: 用戶訊息文字

        Returns:
            處理結果字典
        """
        # 驗證訊息
        if not message:
            message = "你好，我需要協助"

        message = message.strip()

        # 記錄處理信息
        logger.info(f"📥 處理訊息: {message[:100]}...")

        # ✅ 簡化：content 就是 message（純文字）
        content = message

        # 分析 context 大小（用於診斷）
        context_analysis = analyze_context_size(
            messages=content,
            memory_context=None,
            images=None,  # 不再有圖片
        )
        log_context_analysis(context_analysis, operation="process_message")

        # 使用重試機制執行 Agent
        retry_context = {"message_length": len(message)}

        # 定義降級函數（無 Memory 重試）
        def fallback_without_memory():
            """降級策略：不使用 Memory 重新執行"""
            if self.session_manager:
                logger.info("🔄 降級：不使用 Memory 重新執行")
                # 創建無 Memory 的臨時 agent
                from strands.models import BedrockModel

                temp_model = BedrockModel(
                    model_id=settings.BEDROCK_MODEL_ID, region_name=settings.AWS_REGION
                )
                temp_agent = Agent(
                    model=temp_model,
                    session_manager=None,
                    system_prompt=SYSTEM_PROMPT,
                    tools=self.tools,
                )
                return temp_agent(content)
            else:
                # 已經沒有 Memory，無法降級
                raise Exception("Already without memory, cannot fallback further")

        # 執行帶重試的 Agent 調用
        result_dict = retry_with_fallback(
            func=lambda: self.agent(content),
            fallback_func=fallback_without_memory if self.session_manager else None,
            context=retry_context,
        )

        # 處理執行結果
        if result_dict["success"]:
            # 提取回應文字
            agent_result = result_dict["result"]
            response_text = self._extract_response(agent_result)

            # 記錄成功信息
            attempts = result_dict.get("attempts", 1)
            used_fallback = result_dict.get("used_fallback", False)

            extra_info = f"📤 回應長度: {len(response_text)} 字元"
            if attempts > 1:
                extra_info += f" (重試 {attempts} 次)"
            if used_fallback:
                extra_info += " (使用降級模式)"

            logger.info(extra_info)

            return {"success": True, "response": response_text}

        else:
            # 執行失敗，返回友善錯誤訊息
            error = result_dict.get("error")
            attempts = result_dict.get("attempts", 0)

            logger.error(
                f"❌ 訊息處理失敗（{attempts} 次嘗試）: {error}",
                extra={"error_type": result_dict.get("error_type"), "context": retry_context},
                exc_info=True,
            )

            # 生成用戶友善的錯誤訊息
            error_context = {
                "retry_count": attempts,
                "has_memory": bool(self.session_manager),
                "processing_image": False,  # ✅ 不再處理圖片
            }
            friendly_message = format_error_response(error, error_context)

            return {
                "success": False,
                "response": friendly_message,
                "error": str(error),
                "error_type": result_dict.get("error_type"),
            }

    def _extract_response(self, result: Any) -> str:
        """
        從 Agent 結果提取回應文字

        Args:
            result: Agent 執行結果

        Returns:
            回應文字
        """
        response_text = ""

        try:
            # 方法1: 檢查 result.message
            if hasattr(result, "message") and result.message:
                response_text = self._extract_from_message(result.message)

            # 方法2: 檢查 result.content
            if not response_text and hasattr(result, "content"):
                response_text = self._extract_from_content(result.content)

            # 方法3: 嘗試字串化
            if not response_text:
                result_str = str(result)
                if result_str and result_str not in ["", "None", "{}", "[]"]:
                    response_text = result_str

            # 清理和驗證
            response_text = response_text.strip() if response_text else ""

            # 過濾無意義的回應
            if response_text in ["{}", "[]", "None", '{"role": "assistant", "content": []}']:
                response_text = ""

            # 最終檢查
            if not response_text:
                logger.warning("⚠️ 回應內容為空")
                response_text = "處理完成，但回應內容為空。請嘗試重新描述您的需求。"

            return response_text

        except Exception as e:
            logger.error(f"❌ 回應提取異常: {str(e)}", exc_info=True)
            return f"回應提取時發生問題: {str(e)}"

    def _extract_from_message(self, message: Any) -> str:
        """從 message 提取文字"""
        if isinstance(message, dict):
            # 檢查 content 陣列
            content = message.get("content", [])
            if content and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        return item["text"]

            # 檢查 text 鍵
            if "text" in message:
                return message["text"]

            # 檢查 role/content 格式
            if message.get("role") == "assistant":
                msg_content = message.get("content", [])
                if msg_content and isinstance(msg_content, list):
                    for item in msg_content:
                        if isinstance(item, dict) and "text" in item:
                            return item["text"]

        return str(message) if message else ""

    def _extract_from_content(self, content: Any) -> str:
        """從 content 提取文字"""
        if isinstance(content, list) and content:
            first_item = content[0]
            if isinstance(first_item, dict):
                return first_item.get("text", str(content))
            return str(first_item)
        return str(content) if content else ""
