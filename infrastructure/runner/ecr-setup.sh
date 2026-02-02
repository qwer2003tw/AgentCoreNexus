#!/bin/bash
# ECR Setup - Mirror base images
# Run this ONCE before building

set -e

AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPO="agentcore-runner"

echo "Creating ECR repository..."
aws ecr create-repository --repository-name $ECR_REPO --region $AWS_REGION || true

echo "Logging into ECR..."
aws ecr get-login-password --region $AWS_REGION | \
    docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

echo "Pulling and mirroring python:3.11-slim..."
docker pull python:3.11-slim
docker tag python:3.11-slim $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/python:3.11-slim
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/python:3.11-slim

echo "Done! Update Dockerfile to use:"
echo "  FROM $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/python:3.11-slim"
