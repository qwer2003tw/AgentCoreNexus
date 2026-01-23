#!/bin/bash
# Deploy Conversation Storage Infrastructure
# Creates DynamoDB tables for conversation history

set -e

STACK_NAME="agentcore-conversation-storage"
REGION="us-west-2"
ENVIRONMENT="prod"

echo "🚀 Deploying Conversation Storage Infrastructure..."
echo "Stack: $STACK_NAME"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Validate template
echo "📋 Validating SAM template..."
sam validate -t conversation-storage.yaml

# Deploy
echo "🔨 Building and deploying..."
sam deploy \
  --template-file conversation-storage.yaml \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --parameter-overrides Environment="$ENVIRONMENT" \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset

echo ""
echo "✅ Deployment completed!"
echo ""
echo "📊 Verify deployment:"
echo "aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION"
echo ""
echo "📋 Table names:"
echo "  - agentcore-conversation-history-$ENVIRONMENT"
echo "  - agentcore-conversation-metadata-$ENVIRONMENT"
echo "  - agentcore-identity-map-$ENVIRONMENT"