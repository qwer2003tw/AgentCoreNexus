"""
AWS Embedded Metrics Format (EMF) utilities
提供 CloudWatch 指標記錄的輔助函數和常數定義
"""

from aws_embedded_metrics import metric_scope
from aws_embedded_metrics.logger.metrics_logger import MetricsLogger

# 指標命名空間
NAMESPACE = "TelegramLambda"

# 維度名稱
DIMENSION_ENVIRONMENT = "Environment"
DIMENSION_FUNCTION = "FunctionName"

# 指標名稱 - 安全事件
METRIC_INVALID_TOKEN = "InvalidTokenAttempts"
METRIC_TOKEN_VALIDATION_SUCCESS = "TokenValidationSuccess"
METRIC_ALLOWLIST_DENIED = "AllowlistDenied"
METRIC_ALLOWLIST_APPROVED = "AllowlistApproved"

# 指標名稱 - 訊息處理
METRIC_MESSAGES_RECEIVED = "MessagesReceived"
METRIC_MESSAGES_PROCESSED = "MessagesProcessed"

# 指標名稱 - SQS 操作
METRIC_SQS_SUCCESS = "SQSSendSuccess"
METRIC_SQS_FAILURE = "SQSSendFailure"

# 指標名稱 - 功能使用
METRIC_DEBUG_COMMAND_RECEIVED = "DebugCommandReceived"

# 指標名稱 - 錯誤
METRIC_LAMBDA_ERROR = "LambdaError"
METRIC_INVALID_PAYLOAD = "InvalidPayload"
METRIC_WEBHOOK_PARSING_FALLBACK = "WebhookParsingFallback"

# 指標名稱 - 訊息類型
METRIC_MESSAGE_TYPE_TEXT = "MessageTypeText"
METRIC_MESSAGE_TYPE_PHOTO = "MessageTypePhoto"
METRIC_MESSAGE_TYPE_DOCUMENT = "MessageTypeDocument"
METRIC_MESSAGE_TYPE_VIDEO = "MessageTypeVideo"
METRIC_MESSAGE_TYPE_AUDIO = "MessageTypeAudio"
METRIC_MESSAGE_TYPE_OTHER = "MessageTypeOther"

# 指標名稱 - 效能
METRIC_TOTAL_DURATION = "TotalDuration"
METRIC_SQS_DURATION = "SQSSendDuration"

# 單位
UNIT_COUNT = "Count"
UNIT_MILLISECONDS = "Milliseconds"


def set_default_dimensions(
    metrics: MetricsLogger, function_name: str, environment: str = "production"
) -> None:
    """
    設定預設維度

    Args:
        metrics: MetricsLogger 實例
        function_name: Lambda 函數名稱
        environment: 環境名稱（預設為 production）
    """
    metrics.set_namespace(NAMESPACE)
    metrics.set_dimensions({DIMENSION_FUNCTION: function_name, DIMENSION_ENVIRONMENT: environment})


def record_count_metric(metrics: MetricsLogger, metric_name: str, value: float = 1.0) -> None:
    """
    記錄計數類指標

    Args:
        metrics: MetricsLogger 實例
        metric_name: 指標名稱
        value: 指標值（預設為 1.0）
    """
    metrics.put_metric(metric_name, value, UNIT_COUNT)


def record_duration_metric(metrics: MetricsLogger, metric_name: str, duration_ms: float) -> None:
    """
    記錄持續時間指標

    Args:
        metrics: MetricsLogger 實例
        metric_name: 指標名稱
        duration_ms: 持續時間（毫秒）
    """
    metrics.put_metric(metric_name, duration_ms, UNIT_MILLISECONDS)


# 匯出 metric_scope 裝飾器供外部使用
__all__ = [
    "metric_scope",
    "NAMESPACE",
    "DIMENSION_ENVIRONMENT",
    "DIMENSION_FUNCTION",
    # 安全事件
    "METRIC_INVALID_TOKEN",
    "METRIC_TOKEN_VALIDATION_SUCCESS",
    "METRIC_ALLOWLIST_DENIED",
    "METRIC_ALLOWLIST_APPROVED",
    # 訊息處理
    "METRIC_MESSAGES_RECEIVED",
    "METRIC_MESSAGES_PROCESSED",
    # SQS 操作
    "METRIC_SQS_SUCCESS",
    "METRIC_SQS_FAILURE",
    # 功能使用
    "METRIC_DEBUG_COMMAND_RECEIVED",
    # 錯誤
    "METRIC_LAMBDA_ERROR",
    "METRIC_INVALID_PAYLOAD",
    "METRIC_WEBHOOK_PARSING_FALLBACK",
    # 訊息類型
    "METRIC_MESSAGE_TYPE_TEXT",
    "METRIC_MESSAGE_TYPE_PHOTO",
    "METRIC_MESSAGE_TYPE_DOCUMENT",
    "METRIC_MESSAGE_TYPE_VIDEO",
    "METRIC_MESSAGE_TYPE_AUDIO",
    "METRIC_MESSAGE_TYPE_OTHER",
    # 效能
    "METRIC_TOTAL_DURATION",
    "METRIC_SQS_DURATION",
    # 單位
    "UNIT_COUNT",
    "UNIT_MILLISECONDS",
    # 輔助函數
    "set_default_dimensions",
    "record_count_metric",
    "record_duration_metric",
]
