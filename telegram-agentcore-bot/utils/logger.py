"""
日誌配置模組
提供統一的日誌配置和管理
"""
import logging
import sys
from typing import Optional
from config.settings import settings

# 日誌格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日誌級別對映
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    取得配置好的 logger
    
    Args:
        name: logger 名稱（通常使用 __name__）
        level: 日誌級別（可選，預設使用設定檔中的級別）
    
    Returns:
        配置好的 logger 實例
    """
    logger = logging.getLogger(name)
    
    # 如果 logger 已經配置過，直接返回
    if logger.handlers:
        return logger
    
    # 設定日誌級別
    log_level = level or settings.LOG_LEVEL
    logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
    
    # 建立控制台處理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))
    
    # 設定格式化器
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
    console_handler.setFormatter(formatter)
    
    # 添加處理器到 logger
    logger.addHandler(console_handler)
    
    # 防止日誌重複輸出
    logger.propagate = False
    
    return logger

def configure_root_logger(level: Optional[str] = None):
    """
    配置根 logger
    
    Args:
        level: 日誌級別
    """
    log_level = level or settings.LOG_LEVEL
    logging.basicConfig(
        level=LOG_LEVELS.get(log_level.upper(), logging.INFO),
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)]
    )

# 建立預設 logger
default_logger = get_logger("telegram-agent")
