"""
E2E 測試配置和 Fixtures
"""

import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from .helpers import CloudWatchLogFetcher, E2EBotClient

# 載入環境變數
load_dotenv("tests/e2e_real/.env.test")


@pytest.fixture(scope="session")
def test_config():
    """測試配置"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    test_chat_id = os.getenv("TEST_CHAT_ID")

    if not bot_token:
        pytest.skip("需要設置 TELEGRAM_BOT_TOKEN 環境變數")

    if not test_chat_id:
        pytest.skip("需要設置 TEST_CHAT_ID 環境變數")

    return {
        "bot_token": bot_token,
        "test_chat_id": int(test_chat_id),
        "aws_region": os.getenv("AWS_REGION", "us-west-2"),
        "processor_lambda": os.getenv("PROCESSOR_LAMBDA", "agentcore-ai-processor-main"),
        "e2e_timeout": int(os.getenv("E2E_TIMEOUT", "60")),
        "poll_interval": int(os.getenv("E2E_POLL_INTERVAL", "2")),
    }


@pytest_asyncio.fixture
async def bot_client(test_config):
    """創建 Bot 客戶端（每個測試獨立）"""
    client = E2EBotClient(test_config["bot_token"], test_config["test_chat_id"])

    yield client

    # Teardown: 關閉 bot session
    await client.close()


@pytest.fixture(scope="session")
def log_fetcher(test_config):
    """創建 Log Fetcher（session 級別）"""
    return CloudWatchLogFetcher(region=test_config["aws_region"])


@pytest_asyncio.fixture
async def clean_session(bot_client):
    """每個測試前清除 session（確保測試獨立）"""
    await bot_client.clear_session()
    yield


# Pytest markers
def pytest_configure(config):
    """配置 pytest markers"""
    config.addinivalue_line("markers", "real_e2e: 真實環境 E2E 測試（需要 AWS Lambda）")
    config.addinivalue_line("markers", "image: 圖片相關測試")
    config.addinivalue_line("markers", "file: 檔案相關測試")
    config.addinivalue_line("markers", "memory: Memory 功能測試")
    config.addinivalue_line("markers", "slow: 慢速測試（> 30 秒）")