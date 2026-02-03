#!/bin/bash
# Manual deployment for AgentCoreNexus Runner
# Run this locally with AWS credentials for AgentCore_Nexus_Test account

set -e

export AWS_REGION="us-west-2"
export AWS_ACCOUNT_ID="658483440814"
export ENVIRONMENT="dev"
export STACK_NAME="agentcore-runner-${ENVIRONMENT}"
export ECR_REPO="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/agentcore-runner"

echo "=== AgentCoreNexus Runner Deployment ==="
echo "Account: $AWS_ACCOUNT_ID (AgentCore_Nexus_Test)"
echo "Region: $AWS_REGION"
echo "Stack: $STACK_NAME"
echo ""

# Verify identity
echo "=== Verifying AWS credentials ==="
aws sts get-caller-identity

echo ""
echo "=== Step 1: Create ECR Repository ==="
aws ecr describe-repositories --repository-names agentcore-runner 2>/dev/null || \
    aws ecr create-repository --repository-name agentcore-runner --image-scanning-configuration scanOnPush=true

echo ""
echo "=== Step 2: Create HMAC Secret ==="
aws secretsmanager describe-secret --secret-id agentcore-runner/exec-hmac-secret 2>/dev/null || \
    aws secretsmanager create-secret \
        --name agentcore-runner/exec-hmac-secret \
        --description "HMAC secret for Runner exec authentication" \
        --generate-secret-string '{"PasswordLength":32,"ExcludePunctuation":true}'

echo ""
echo "=== Step 3: Mirror Python base image to ECR ==="
# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $ECR_REPO

# Create python repo if not exists
aws ecr describe-repositories --repository-names python 2>/dev/null || \
    aws ecr create-repository --repository-name python

# Pull and push python base image
docker pull --platform linux/arm64 python:3.11-slim
docker tag python:3.11-slim ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/python:3.11-slim
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/python:3.11-slim

echo ""
echo "=== Step 4: Build Runner image ==="
cd runner

# Update Dockerfile to use ECR base image
sed -i "s|FROM python:3.11-slim|FROM ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/python:3.11-slim|" docker/Dockerfile

# Build for ARM64
docker buildx build --platform linux/arm64 -t ${ECR_REPO}:latest -f docker/Dockerfile --push .

echo ""
echo "=== Step 5: Deploy CloudFormation Stack ==="
cd ../infrastructure/runner

sam deploy \
    --template-file template.yaml \
    --stack-name $STACK_NAME \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        ImageUri=${ECR_REPO}:latest \
    --capabilities CAPABILITY_NAMED_IAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset \
    --region $AWS_REGION

echo ""
echo "=== Deployment Complete ==="
RUNNER_ENDPOINT=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --query "Stacks[0].Outputs[?OutputKey=='RunnerEndpoint'].OutputValue" \
    --output text \
    --region $AWS_REGION)

echo ""
echo "Runner Endpoint: $RUNNER_ENDPOINT"
echo ""
echo "To test:"
echo "  curl ${RUNNER_ENDPOINT}/health"
