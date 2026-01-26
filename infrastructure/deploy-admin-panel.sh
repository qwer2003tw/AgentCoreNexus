#!/bin/bash
# Deploy Admin Panel Infrastructure
# DynamoDB tables for admin features

set -e

# Configuration
REGION="${AWS_REGION:-us-west-2}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="agentcore-admin-panel-${ENVIRONMENT}"

echo "🚀 Deploying Admin Panel Infrastructure"
echo "   Region: $REGION"
echo "   Environment: $ENVIRONMENT"
echo "   Stack: $STACK_NAME"
echo ""

# Deploy the stack
echo "📦 Deploying CloudFormation stack..."
aws cloudformation deploy \
  --region "$REGION" \
  --template-file admin-panel.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides Environment="$ENVIRONMENT" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset

# Check deployment status
if [ $? -eq 0 ]; then
    echo "✅ Stack deployed successfully!"
    
    # Get outputs
    echo ""
    echo "📊 Stack Outputs:"
    aws cloudformation describe-stacks \
      --region "$REGION" \
      --stack-name "$STACK_NAME" \
      --query 'Stacks[0].Outputs[*].{Key:OutputKey,Value:OutputValue}' \
      --output table
    
    echo ""
    echo "🎉 Admin Panel Infrastructure is ready!"
    echo ""
    echo "Created tables:"
    echo "  - agentcore-conversation-summaries-${ENVIRONMENT}"
    echo "  - agentcore-admin-audit-logs-${ENVIRONMENT}"
    echo "  - agentcore-admin-system-config-${ENVIRONMENT}"
else
    echo "❌ Stack deployment failed!"
    exit 1
fi