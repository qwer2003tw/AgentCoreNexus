"""
Exec Tool - Execute commands via Runner service
OpenClaw-style command execution
"""

import hashlib
import hmac
import json
import logging
import os
import time
from typing import Any

import boto3
import urllib3

logger = logging.getLogger(__name__)

# Runner endpoint from environment
RUNNER_ENDPOINT = os.getenv("RUNNER_ENDPOINT", "")
EXEC_HMAC_SECRET = os.getenv("EXEC_HMAC_SECRET", "")

# HTTP client
http = urllib3.PoolManager()


def _sign_request(session_id: str, command: str, timestamp: int) -> str:
    """Generate HMAC signature for request."""
    if not EXEC_HMAC_SECRET:
        return ""
    message = f"{session_id}:{command}:{timestamp}"
    return hmac.new(
        EXEC_HMAC_SECRET.encode(), message.encode(), hashlib.sha256
    ).hexdigest()


def execute_command(
    session_id: str,
    command: str,
    workdir: str | None = None,
    env: dict[str, str] | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    """
    Execute a command in the Runner service.
    
    Args:
        session_id: Unique session identifier (e.g., conversation ID)
        command: Shell command to execute
        workdir: Working directory (optional, relative to session workspace)
        env: Environment variables (optional)
        timeout: Command timeout in seconds
    
    Returns:
        dict with keys: type, data, exit_code, duration_ms
    """
    if not RUNNER_ENDPOINT:
        return {
            "type": "error",
            "data": "Runner endpoint not configured",
            "exit_code": None,
            "duration_ms": None,
        }
    
    timestamp = int(time.time())
    signature = _sign_request(session_id, command, timestamp)
    
    payload = {
        "session_id": session_id,
        "command": command,
        "workdir": workdir,
        "env": env or {},
        "timeout": timeout,
        "timestamp": timestamp,
        "signature": signature,
    }
    
    try:
        response = http.request(
            "POST",
            f"{RUNNER_ENDPOINT}/exec",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=timeout + 5,  # Extra buffer for network
        )
        
        if response.status == 200:
            return json.loads(response.data.decode("utf-8"))
        else:
            return {
                "type": "error",
                "data": f"Runner returned {response.status}: {response.data.decode()}",
                "exit_code": None,
                "duration_ms": None,
            }
    
    except urllib3.exceptions.TimeoutError:
        return {
            "type": "error",
            "data": f"Request timed out after {timeout}s",
            "exit_code": None,
            "duration_ms": None,
        }
    except Exception as e:
        logger.exception("Exec request failed")
        return {
            "type": "error",
            "data": str(e),
            "exit_code": None,
            "duration_ms": None,
        }


# Tool definition for Agent
EXEC_TOOL = {
    "name": "exec",
    "description": """Execute shell commands in an isolated workspace.

Use this tool to:
- Run shell commands (ls, cat, echo, grep, etc.)
- Create and edit files
- Install packages (pip, npm, etc.)
- Run scripts (python, node, bash)

The workspace persists across commands in the same session.
Each session has its own isolated workspace directory.

Examples:
- exec(command="ls -la") - list files
- exec(command="echo 'hello' > test.txt") - create file
- exec(command="cat test.txt") - read file
- exec(command="python script.py") - run script
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "workdir": {
                "type": "string",
                "description": "Working directory (relative to workspace root)",
            },
            "timeout": {
                "type": "integer",
                "description": "Command timeout in seconds (default: 300)",
                "default": 300,
            },
        },
        "required": ["command"],
    },
}


def handle_exec_tool(session_id: str, tool_input: dict) -> str:
    """
    Handle exec tool invocation from Agent.
    
    Args:
        session_id: Session/conversation ID
        tool_input: Tool input from Agent
    
    Returns:
        Formatted result string
    """
    command = tool_input.get("command", "")
    workdir = tool_input.get("workdir")
    timeout = tool_input.get("timeout", 300)
    
    if not command:
        return "Error: No command provided"
    
    result = execute_command(
        session_id=session_id,
        command=command,
        workdir=workdir,
        timeout=timeout,
    )
    
    if result["type"] == "error":
        return f"Error: {result['data']}"
    
    output = result["data"] or "(no output)"
    exit_code = result.get("exit_code", 0)
    duration = result.get("duration_ms", 0)
    
    if exit_code == 0:
        return f"{output}\n[exit: {exit_code}, {duration}ms]"
    else:
        return f"{output}\n[exit: {exit_code}, {duration}ms] (command failed)"
