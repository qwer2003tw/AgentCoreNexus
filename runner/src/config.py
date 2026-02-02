"""Configuration management.

All secrets loaded from AWS Secrets Manager at runtime.
NO hardcoded credentials.
"""

import os
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.exceptions import ClientError


@dataclass
class Config:
    """Runtime configuration."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    ws_path: str = "/ws/exec"
    health_path: str = "/health"

    # Workspace
    workspace_root: str = "/workspace"
    efs_mount: str = "/efs"

    # Timeouts
    exec_timeout_seconds: int = 300
    ws_ping_interval: int = 30

    # Secrets (loaded at runtime)
    exec_hmac_secret: Optional[str] = None

    # AWS
    region: str = "us-west-2"


def get_secret(secret_name: str, region: str = "us-west-2") -> str:
    """Retrieve secret from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=region)
    try:
        response = client.get_secret_value(SecretId=secret_name)
        return response["SecretString"]
    except ClientError as e:
        raise RuntimeError(f"Failed to retrieve secret {secret_name}: {e}") from e


def load_config() -> Config:
    """Load configuration from environment and Secrets Manager."""
    config = Config(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8080")),
        workspace_root=os.getenv("WORKSPACE_ROOT", "/workspace"),
        efs_mount=os.getenv("EFS_MOUNT", "/efs"),
        exec_timeout_seconds=int(os.getenv("EXEC_TIMEOUT", "300")),
        region=os.getenv("AWS_REGION", "us-west-2"),
    )

    hmac_secret_name = os.getenv("EXEC_HMAC_SECRET_NAME")
    if hmac_secret_name:
        config.exec_hmac_secret = get_secret(hmac_secret_name, config.region)

    return config
