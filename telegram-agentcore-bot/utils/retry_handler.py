"""
智能重試處理器
處理 Bedrock API 的暫時性錯誤，實施降級策略
"""

import time
from collections.abc import Callable
from typing import Any

from botocore.exceptions import ClientError, EventStreamError

from utils.logger import get_logger

logger = get_logger(__name__)


class RetryHandler:
    """重試處理器，支持降級策略"""

    def __init__(self, max_attempts: int = 3, base_delay: float = 2.0):
        """
        初始化重試處理器

        Args:
            max_attempts: 最大重試次數
            base_delay: 基礎延遲時間（秒）
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay

    def execute_with_retry(
        self,
        func: Callable,
        *args,
        fallback_func: Callable | None = None,
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        執行函數並在失敗時重試

        Args:
            func: 要執行的函數
            *args: 函數參數
            fallback_func: 降級函數（如果主函數失敗）
            context: 執行上下文（用於日誌）
            **kwargs: 函數關鍵字參數

        Returns:
            執行結果字典
        """
        context = context or {}
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.info(
                    f"Executing function (attempt {attempt}/{self.max_attempts})",
                    extra={"attempt": attempt, "context": context},
                )

                result = func(*args, **kwargs)

                if attempt > 1:
                    logger.info(
                        f"✅ Function succeeded on attempt {attempt}",
                        extra={"attempt": attempt, "context": context},
                    )

                return {"success": True, "result": result, "attempts": attempt}

            except (EventStreamError, ClientError) as e:
                last_error = e
                error_type = type(e).__name__

                logger.warning(
                    f"⚠️ Attempt {attempt} failed: {error_type}",
                    extra={
                        "attempt": attempt,
                        "error_type": error_type,
                        "error_message": str(e),
                        "context": context,
                    },
                )

                # 檢查是否是不可重試的錯誤
                if not self._is_retryable(e):
                    logger.error(
                        f"❌ Non-retryable error: {error_type}",
                        extra={"error": str(e), "context": context},
                    )
                    break

                # 如果還有重試機會，等待後重試
                if attempt < self.max_attempts:
                    delay = self._calculate_delay(attempt)
                    logger.info(
                        f"⏳ Waiting {delay:.1f}s before retry...",
                        extra={"attempt": attempt, "delay": delay},
                    )
                    time.sleep(delay)

            except Exception as e:
                last_error = e
                logger.error(
                    f"❌ Unexpected error on attempt {attempt}: {type(e).__name__}",
                    extra={"error": str(e), "context": context},
                    exc_info=True,
                )
                break

        # 所有重試都失敗了，嘗試降級策略
        if fallback_func:
            try:
                logger.info(
                    "🔄 All retries failed, trying fallback function",
                    extra={"context": context},
                )
                fallback_result = fallback_func(*args, **kwargs)
                return {
                    "success": True,
                    "result": fallback_result,
                    "attempts": self.max_attempts,
                    "used_fallback": True,
                }
            except Exception as fallback_error:
                logger.error(
                    f"❌ Fallback function also failed: {fallback_error}",
                    extra={"context": context},
                    exc_info=True,
                )
                last_error = fallback_error

        # 完全失敗
        return {
            "success": False,
            "error": last_error,
            "attempts": self.max_attempts,
            "error_type": type(last_error).__name__ if last_error else "Unknown",
        }

    def _is_retryable(self, error: Exception) -> bool:
        """
        判斷錯誤是否可重試

        Args:
            error: 異常物件

        Returns:
            是否可重試
        """
        error_str = str(error).lower()

        # EventStreamError 通常是暫時性的
        if isinstance(error, EventStreamError):
            return True

        # Throttling 錯誤可重試
        if isinstance(error, ClientError):
            error_code = error.response.get("Error", {}).get("Code", "")
            if error_code in ["ThrottlingException", "TooManyRequestsException"]:
                return True

        # 包含這些關鍵字的錯誤可重試
        retryable_keywords = [
            "timeout",
            "throttl",
            "rate limit",
            "service unavailable",
            "internal error",
            "temporary",
        ]

        return any(keyword in error_str for keyword in retryable_keywords)

    def _calculate_delay(self, attempt: int) -> float:
        """
        計算指數退避延遲

        Args:
            attempt: 當前重試次數

        Returns:
            延遲時間（秒）
        """
        # 指數退避：2, 4, 8...
        delay = self.base_delay * (2 ** (attempt - 1))
        # 最大延遲 10 秒
        return min(delay, 10.0)


# 全域重試處理器實例
default_retry_handler = RetryHandler(max_attempts=3, base_delay=2.0)


def retry_with_fallback(
    func: Callable,
    *args,
    fallback_func: Callable | None = None,
    context: dict[str, Any] | None = None,
    **kwargs,
) -> dict[str, Any]:
    """
    便利函數：使用預設重試處理器執行函數

    Args:
        func: 要執行的函數
        *args: 函數參數
        fallback_func: 降級函數
        context: 執行上下文
        **kwargs: 函數關鍵字參數

    Returns:
        執行結果字典
    """
    return default_retry_handler.execute_with_retry(
        func, *args, fallback_func=fallback_func, context=context, **kwargs
    )
