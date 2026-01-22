"""
CloudWatch Logs 查詢工具
用於驗證 Lambda 內部行為
"""

import time

import boto3


class CloudWatchLogFetcher:
    """查詢 CloudWatch Logs 驗證內部行為"""

    def __init__(self, region: str = "us-west-2"):
        """
        初始化 Log Fetcher

        Args:
            region: AWS 區域
        """
        self.logs_client = boto3.client("logs", region_name=region)
        self.region = region

    def check_tool_called(
        self, lambda_name: str, tool_name: str, since_seconds: int = 90
    ) -> bool:
        """
        檢查特定 tool 是否被調用

        Args:
            lambda_name: Lambda 函數名稱
            tool_name: Tool 名稱（如 "Image Analysis Tool"）
            since_seconds: 查詢最近幾秒的日誌

        Returns:
            是否找到 tool 調用記錄
        """
        log_group = f"/aws/lambda/{lambda_name}"

        try:
            # 查詢日誌
            response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=int((time.time() - since_seconds) * 1000),
                filterPattern=f'"{tool_name}"',
            )

            events = response.get("events", [])
            return len(events) > 0

        except Exception as e:
            print(f"⚠️ 查詢日誌失敗：{e}")
            return False

    def check_memory_recorded(self, lambda_name: str, keyword: str, since_seconds: int = 90) -> bool:
        """
        檢查 Memory 是否記錄了特定內容

        Args:
            lambda_name: Lambda 函數名稱
            keyword: 關鍵字（如 "s3://" 或特定檔名）
            since_seconds: 查詢最近幾秒的日誌

        Returns:
            是否找到記錄
        """
        log_group = f"/aws/lambda/{lambda_name}"

        try:
            response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=int((time.time() - since_seconds) * 1000),
                filterPattern=f'"{keyword}"',
            )

            events = response.get("events", [])
            return len(events) > 0

        except Exception as e:
            print(f"⚠️ 查詢日誌失敗：{e}")
            return False

    def get_recent_logs(self, lambda_name: str, since_seconds: int = 60, limit: int = 50) -> list:
        """
        獲取最近的日誌事件

        Args:
            lambda_name: Lambda 函數名稱
            since_seconds: 查詢最近幾秒的日誌
            limit: 最多返回幾條

        Returns:
            日誌事件列表
        """
        log_group = f"/aws/lambda/{lambda_name}"

        try:
            response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=int((time.time() - since_seconds) * 1000),
                limit=limit,
            )

            return response.get("events", [])

        except Exception as e:
            print(f"⚠️ 查詢日誌失敗：{e}")
            return []

    def check_error_in_logs(self, lambda_name: str, since_seconds: int = 90) -> bool:
        """
        檢查日誌中是否有錯誤

        Args:
            lambda_name: Lambda 函數名稱
            since_seconds: 查詢最近幾秒的日誌

        Returns:
            是否有錯誤
        """
        log_group = f"/aws/lambda/{lambda_name}"

        try:
            response = self.logs_client.filter_log_events(
                logGroupName=log_group,
                startTime=int((time.time() - since_seconds) * 1000),
                filterPattern='"ERROR"',
            )

            return len(response.get("events", [])) > 0

        except Exception as e:
            print(f"⚠️ 查詢日誌失敗：{e}")
            return False