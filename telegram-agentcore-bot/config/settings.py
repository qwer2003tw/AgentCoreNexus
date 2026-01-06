"""
環境配置管理
使用環境變數驅動配置，避免硬編碼
"""
import os
from typing import Optional

class Settings:
    """統一的配置管理類"""
    
    def __init__(self):
        # AWS 相關配置
        self.AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
        self.BEDROCK_MODEL_ID = os.getenv(
            "BEDROCK_MODEL_ID",
            "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
        )
        
        # Memory 配置
        self.MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
        self.MEMORY_ENABLED = self.MEMORY_ID is not None
        
        # 日誌配置
        self.LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        # 瀏覽器配置
        self.BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))
        self.BROWSER_ENABLED = os.getenv("BROWSER_ENABLED", "true").lower() == "true"
        
        # Agent 配置
        self.AGENT_NAME = os.getenv("AGENT_NAME", "Telegram Agent")
        self.DEFAULT_SESSION_ID = os.getenv("DEFAULT_SESSION_ID", "default")
        
    @property
    def is_production(self) -> bool:
        """檢查是否為生產環境"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @property
    def memory_config(self) -> Optional[dict]:
        """取得 Memory 配置"""
        if not self.MEMORY_ENABLED:
            return None
        
        return {
            "memory_id": self.MEMORY_ID,
            "region": self.AWS_REGION,
            "enabled": True
        }
    
    def validate(self) -> bool:
        """驗證必要配置是否存在"""
        required_vars = []
        
        # 檢查必要的環境變數
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(f"缺少必要的環境變數: {', '.join(missing_vars)}")
        
        return True
    
    def __str__(self) -> str:
        """配置摘要"""
        return (
            f"Settings:\n"
            f"  AWS Region: {self.AWS_REGION}\n"
            f"  Model: {self.BEDROCK_MODEL_ID}\n"
            f"  Memory: {'Enabled' if self.MEMORY_ENABLED else 'Disabled'}\n"
            f"  Browser: {'Enabled' if self.BROWSER_ENABLED else 'Disabled'}\n"
            f"  Environment: {'Production' if self.is_production else 'Development'}"
        )

# 建立全域配置實例
settings = Settings()
