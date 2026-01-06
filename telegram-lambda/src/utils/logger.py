"""
Logger Utility - 統一日誌處理
"""
import logging
import os
import json
from typing import Any, Dict

# 從環境變數獲取日誌等級
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()


class JSONFormatter(logging.Formatter):
    """
    自定義 JSON 格式化器，用於結構化日誌
    """
    # LogRecord 的標準屬性列表
    STANDARD_ATTRS = {
        'name', 'msg', 'args', 'created', 'filename', 'funcName', 'levelname',
        'levelno', 'lineno', 'module', 'msecs', 'message', 'pathname', 'process',
        'processName', 'relativeCreated', 'thread', 'threadName', 'exc_info',
        'exc_text', 'stack_info', 'asctime', 'taskName'
    }
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # 添加額外的上下文資訊（從 extra 參數傳入的字段）
        for key, value in record.__dict__.items():
            if key not in self.STANDARD_ATTRS and not key.startswith('_'):
                log_data[key] = value
        
        # 添加異常資訊
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    """
    獲取配置好的 logger 實例
    
    Args:
        name: Logger 名稱（通常使用 __name__）
        
    Returns:
        logging.Logger: 配置好的 logger
    """
    logger = logging.getLogger(name)
    
    # 避免重複添加 handler
    if logger.handlers:
        return logger
    
    logger.setLevel(LOG_LEVEL)
    
    # 建立 StreamHandler
    handler = logging.StreamHandler()
    handler.setLevel(LOG_LEVEL)
    
    # 使用 JSON 格式化器
    formatter = JSONFormatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    
    # 防止日誌傳播到父 logger
    logger.propagate = False
    
    return logger


def log_with_context(logger: logging.Logger, level: str, message: str, **kwargs: Any) -> None:
    """
    記錄帶有額外上下文的日誌
    
    Args:
        logger: Logger 實例
        level: 日誌等級 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: 日誌訊息
        **kwargs: 額外的上下文資訊
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=kwargs)
