"""
WebSocket $disconnect handler
Handles WebSocket disconnections and cleanup
"""

import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")

# Environment variables
CONNECTIONS_TABLE = os.environ["CONNECTIONS_TABLE"]

# DynamoDB table
connections_table = dynamodb.Table(CONNECTIONS_TABLE)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    Handle WebSocket $disconnect route
    
    Args:
        event: API Gateway WebSocket event
        context: Lambda context
        
    Returns:
        Response with statusCode 200
    """
    connection_id = event["requestContext"]["connectionId"]
    
    print(f"WebSocket disconnection: {connection_id}")
    
    try:
        # Delete connection from DynamoDB
        delete_connection(connection_id)
        
        print(f"Connection cleaned up: {connection_id}")
        
        return {"statusCode": 200, "body": "Disconnected"}
        
    except Exception as e:
        print(f"Error handling disconnection: {str(e)}")
        # Still return 200 even if cleanup fails
        return {"statusCode": 200, "body": "Disconnected"}


def delete_connection(connection_id: str) -> None:
    """
    Delete WebSocket connection from DynamoDB
    
    Args:
        connection_id: API Gateway connection ID
    """
    try:
        connections_table.delete_item(Key={"connection_id": connection_id})
        print(f"Deleted connection: {connection_id}")
        
    except ClientError as e:
        print(f"Error deleting connection: {str(e)}")
        # Non-critical error, just log it