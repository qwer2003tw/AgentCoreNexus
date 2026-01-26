#!/bin/bash
# Update Conversation Storage Infrastructure
# Add GSI to conversation_history table for admin queries

set -e

# Configuration
REGION="${AWS_REGION:-us-west-2}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="agentcore-conversation-storage-${ENVIRONMENT}"

echo "🚀 Updating Conversation Storage Infrastructure"
echo "   Region: $REGION"
echo "   Environment: $ENVIRONMENT"
echo "   Stack: $STACK_NAME"
echo ""

echo "⚠️  Important Notes:"
echo "   - Adding GSI to existing table takes 5-10 minutes"
echo "   - Table remains available during update"
echo "   - GSI will be empty initially (existing data won't be backfilled)"
echo "   - New writes will populate the GSI automatically"
echo ""

# Skip confirmation for automated deployment
# To cancel, use Ctrl+C before running

# Deploy the stack
echo "📦 Updating CloudFormation stack..."
aws cloudformation deploy \
  --region "$REGION" \
  --template-file conversation-storage.yaml \
  --stack-name "$STACK_NAME" \
  --parameter-overrides Environment="$ENVIRONMENT" \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset

# Check deployment status
if [ $? -eq 0 ]; then
    echo "✅ Stack updated successfully!"
    
    # Get GSI status
    echo ""
    echo "📊 Checking GSI status..."
    aws dynamodb describe-table \
      --region "$REGION" \
      --table-name "agentcore-conversation-history-${ENVIRONMENT}" \
      --query 'Table.GlobalSecondaryIndexes[*].{Name:IndexName,Status:IndexStatus}' \
      --output table
    
    echo ""
    echo "🎉 Update complete!"
    echo ""
    echo "Added GSI:"
    echo "  - GlobalTimestampIndex (for fast admin queries)"
    echo "  - ChannelTimestampIndex (for channel filtering)"
    echo ""
    echo "⚠️  Note: GSI backfill may take 5-10 minutes to complete"
    echo "   New data will use GSI immediately"
    echo "   Existing data will be available once backfill completes"
else
    echo "❌ Stack update failed!"
    exit 1
fi