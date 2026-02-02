#!/bin/bash
# Deploy Runner infrastructure
set -e

ENVIRONMENT="${1:-dev}"
AWS_REGION="${AWS_REGION:-us-west-2}"
STACK_NAME="agentcore-runner-${ENVIRONMENT}"

echo "=== AgentCoreNexus Runner Deployment ==="
echo "Environment: $ENVIRONMENT"
echo "Region: $AWS_REGION"
echo "Stack: $STACK_NAME"
echo ""

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agentcore-runner"
IMAGE_TAG="${IMAGE_TAG:-latest}"
IMAGE_URI="${ECR_REPO}:${IMAGE_TAG}"

echo "=== Step 1: Create Secrets (if not exist) ==="
aws secretsmanager describe-secret --secret-id agentcore-runner/exec-hmac-secret 2>/dev/null || \
    aws secretsmanager create-secret \
        --name agentcore-runner/exec-hmac-secret \
        --description "HMAC secret for Runner exec authentication" \
        --generate-secret-string '{"PasswordLength":32,"ExcludePunctuation":true}'
echo "Secret ready."

echo ""
echo "=== Step 2: Build and Push Docker Image ==="
cd "$(dirname "$0")/../../runner"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REPO

# Create repo if not exists
aws ecr describe-repositories --repository-names agentcore-runner 2>/dev/null || \
    aws ecr create-repository --repository-name agentcore-runner

# Build (ARM64 for Graviton)
docker buildx build --platform linux/arm64 -t $IMAGE_URI -f docker/Dockerfile --push .

echo "Image pushed: $IMAGE_URI"

echo ""
echo "=== Step 3: Deploy CloudFormation Stack ==="
cd "$(dirname "$0")"

sam deploy \
    --template-file template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        ImageUri=$IMAGE_URI \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

echo ""
echo "=== Deployment Complete ==="
echo ""

# Get outputs
RUNNER_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='RunnerEndpoint'].OutputValue" \
    --output text)

echo "Runner Endpoint: $RUNNER_ENDPOINT"
echo ""
echo "Next steps:"
echo "1. Update ai-processor environment with RUNNER_ENDPOINT=$RUNNER_ENDPOINT"
echo "2. Redeploy ai-processor"
