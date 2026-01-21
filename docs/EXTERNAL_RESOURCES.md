# External Resources & Migration Guide

**Last Updated**: 2026-01-21  
**Version**: 1.0  
**Purpose**: Document all resources not managed by CloudFormation/SAM that may cause issues during migration

---

## 🎯 Overview

This document identifies all external dependencies in AgentCoreNexus that are not fully managed by Infrastructure as Code (IaC), providing solutions for seamless migration to new environments or regions.

---

## 📋 Complete External Resources Inventory

### 🔴 Critical Resources (High Risk)

#### 1. DynamoDB Table: telegram-allowlist
**Status**: ✅ Now in IaC (conditional creation)  
**Location**: `telegram-adapter/template.yaml`

**Historical Issue**:
- Previously: Table existed outside CloudFormation
- Impact: New environment deployments would fail

**Solution Implemented**:
```yaml
Parameters:
  CreateAllowlistTable: 'false'  # Use existing table in current env

Conditions:
  ShouldCreateAllowlistTable: !Equals [!Ref CreateAllowlistTable, 'true']

Resources:
  AllowlistTable:
    Type: AWS::DynamoDB::Table
    Condition: ShouldCreateAllowlistTable
    Properties:
      TableName: !Sub '${AWS::StackName}-allowlist'
      BillingMode: PAY_PER_REQUEST
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: true
      # ... full configuration
```

**Migration**:
- **Existing Environment**: Deploy with `CreateAllowlistTable=false`
- **New Environment**: Deploy with `CreateAllowlistTable=true`

---

#### 2. SSM Parameter: /agentcore/memory/telegram-bot
**Status**: ✅ Now in IaC (conditional creation)  
**Location**: `ai-processor/template.yaml`

**Historical Issue**:
- Previously: Created manually or via `create_memory.py`
- Impact: Stack deployment would fail if parameter doesn't exist

**Solution Implemented**:
```yaml
Parameters:
  CreateMemoryParameter: 'false'
  MemoryId: ''  # Bedrock Memory ID

Conditions:
  ShouldCreateMemoryParameter: !Equals [!Ref CreateMemoryParameter, 'true']

Resources:
  MemoryIdParameter:
    Type: AWS::SSM::Parameter
    Condition: ShouldCreateMemoryParameter
    Properties:
      Name: !Sub '/agentcore/memory/${AWS::StackName}'
      Value: !Ref MemoryId
```

**Migration**:
- **Existing**: `CreateMemoryParameter=false` (uses existing /agentcore/memory/telegram-bot)
- **New**: `CreateMemoryParameter=true` + provide MemoryId

---

#### 3. Bedrock AgentCore Memory
**Status**: ⚠️ Cannot be managed by CloudFormation  
**Creation**: Via Bedrock API (`ai-processor/create_memory.py`)

**Why Not in IaC**:
- Bedrock resources don't support CloudFormation
- Memory is created via AWS SDK/CLI
- Memory ID stored in SSM Parameter (which IS in IaC)

**Migration Steps**:
```bash
# Step 1: Create Memory (in new environment)
cd ai-processor
python create_memory.py
# Outputs: TelegramBotMemory-XXXXX

# Step 2: Deploy stack with Memory ID
sam deploy --parameter-overrides \
  CreateMemoryParameter=true \
  MemoryId=TelegramBotMemory-XXXXX
```

**Current Value**:
- Memory ID: `TelegramBotMemory-6UH9fyDyIf`
- SSM Path: `/agentcore/memory/telegram-bot`
- Created: 2026-01-19

---

### 🟡 Medium Risk Resources

#### 4. Web Attachments S3 Bucket
**Status**: ✅ Fixed (removed hardcoded account ID)  
**Location**: `ai-processor/template.yaml`

**Historical Issue**:
```yaml
# ❌ Before: Hardcoded account ID
Resource: 'arn:aws:s3:::agentcore-web-channel-attachments-190825685292/*'
```

**Solution Implemented**:
```yaml
# ✅ After: Dynamic account ID
Resource: !Sub 'arn:aws:s3:::agentcore-web-adapter-attachments-${AWS::AccountId}/*'
```

**Migration**: No action needed (automatic)

---

#### 5. Web-Adapter Infrastructure
**Status**: ✅ Managed by SAM  
**Location**: `web-adapter/infrastructure/web-channel-template.yaml`

**Resources Defined**:
- AttachmentsBucket (S3)
- Frontend Bucket (S3)
- Lambda functions
- API Gateway

**Verification**:
```bash
aws cloudformation describe-stacks \
  --stack-name agentcore-web-adapter \
  --region us-west-2
```

**Migration**: Deploy web-adapter stack first

---

### 🟢 Low Risk Resources

#### 6. Bedrock Model Access
**Status**: ⚠️ Account-level configuration (manual)  
**Configuration**: AWS Bedrock Console

**Required Models**:
- `anthropic.claude-3-5-sonnet-20241022-v2:0`

**Migration Steps**:
1. Go to AWS Bedrock Console in target region
2. Navigate to "Model access"
3. Request access for Claude 3.5 Sonnet
4. Wait for approval (~5 minutes)

**Cannot be automated**: This is AWS account-level configuration

---

#### 7. Telegram Bot & Webhook
**Status**: ⚠️ External API (Telegram)  
**Configuration**: Telegram BotFather + Webhook API

**Migration Steps**:
```bash
# Get webhook URL from stack outputs
WEBHOOK_URL=$(aws cloudformation describe-stacks \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text)

# Get bot token from Secrets Manager
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --secret-id agentcore-telegram-adapter-secrets \
  --query SecretString --output text | jq -r .bot_token)

# Set webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${WEBHOOK_URL}\"}"
```

**Documentation**: `docs/deployment-guide.md` Step 4

---

## 🚀 Complete Migration Checklist

### Pre-Migration (Planning)
- [ ] Identify target AWS account and region
- [ ] Verify Bedrock availability in target region
- [ ] Request Bedrock model access (if needed)
- [ ] Plan deployment schedule (consider dependencies)

### Phase 1: Core Infrastructure
```bash
# 1. Deploy telegram-adapter (provides EventBus, buckets)
cd telegram-adapter
sam deploy \
  --stack-name agentcore-telegram-adapter-new \
  --region <target-region> \
  --parameter-overrides \
    CreateAllowlistTable=true \
    TelegramBotToken=<your-token>
```

### Phase 2: AI Processor
```bash
# 2. Create Bedrock Memory first
cd ai-processor
python create_memory.py
# Note the Memory ID

# 3. Deploy ai-processor
sam deploy \
  --stack-name agentcore-ai-processor-new \
  --region <target-region> \
  --parameter-overrides \
    CreateMemoryParameter=true \
    MemoryId=<memory-id-from-step-2> \
    ReceiverStackName=agentcore-telegram-adapter-new
```

### Phase 3: Web Adapter (Optional)
```bash
# 4. Deploy web-adapter
cd web-adapter/infrastructure
sam deploy \
  --stack-name agentcore-web-adapter-new \
  --region <target-region>
```

### Phase 4: Post-Deployment Configuration
```bash
# 5. Configure Telegram webhook
# See step 7 above

# 6. Populate allowlist
aws dynamodb put-item \
  --table-name agentcore-telegram-adapter-new-allowlist \
  --item '{"chat_id":{"N":"YOUR_CHAT_ID"},"username":{"S":"YOUR_USERNAME"},"enabled":{"BOOL":true}}'

# 7. Test end-to-end
# Send message to Telegram bot
```

---

## 📊 Resource Dependency Map

```
Bedrock Model Access (Manual)
    ↓
Bedrock Memory (create_memory.py)
    ↓
SSM Parameter (SAM - conditional)
    ↓
telegram-adapter Stack
    ├─ DynamoDB Table (SAM - conditional)
    ├─ EventBus (SAM)
    ├─ S3 Buckets (SAM)
    └─ Secrets (SAM)
    ↓
ai-processor Stack
    └─ References telegram-adapter exports
    ↓
web-adapter Stack (optional)
    └─ S3 Buckets (SAM)
    ↓
Telegram Webhook (Manual API call)
```

---

## 🎯 Deployment Order

**Critical**: Must follow this order to avoid dependency failures

1. ✅ **telegram-adapter** (provides exports for others)
2. ✅ **ai-processor** (depends on telegram-adapter)
3. ✅ **web-adapter** (optional, can be deployed anytime)

**Reverse order for deletion**:
1. web-adapter
2. ai-processor  
3. telegram-adapter (last, as it provides exports)

---

## ⚠️ Common Migration Issues

### Issue 1: ImportValue Not Found
**Symptom**: Stack creation fails with "Export <name> not found"

**Cause**: Dependent stack not deployed yet

**Solution**: Deploy stacks in correct order (see above)

---

### Issue 2: SSM Parameter Not Found
**Symptom**: Stack creation fails reading SSM parameter

**Cause**: Memory not created or parameter not set

**Solution**:
```bash
# Option 1: Create memory and parameter
python create_memory.py

# Option 2: Deploy with CreateMemoryParameter=true
```

---

### Issue 3: Model Access Denied
**Symptom**: Lambda fails with "AccessDeniedException" for Bedrock

**Cause**: Model access not requested in new account/region

**Solution**: Request model access in Bedrock Console (takes ~5 min)

---

### Issue 4: Webhook Not Working
**Symptom**: Bot doesn't respond to messages

**Cause**: Telegram webhook not configured

**Solution**: Run webhook configuration script (see Phase 4 above)

---

## 📚 Related Documentation

- [Deployment Guide](./deployment-guide.md) - Complete deployment instructions
- [DynamoDB Design](./DYNAMODB_DESIGN.md) - Table schema and patterns
- [Stack Management](./STACK_MANAGEMENT.md) - Stack operations guide
- [Architecture Guide](./architecture-guide.md) - System architecture

---

## 🔄 Maintenance

### Monthly Checks
- [ ] Verify PITR enabled on all DynamoDB tables
- [ ] Check SSM parameters exist and are valid
- [ ] Verify Bedrock Memory status
- [ ] Test webhook connectivity

### Before Major Migration
- [ ] Review this document for updates
- [ ] Test deployment in staging environment
- [ ] Backup all data (DynamoDB, S3)
- [ ] Document any new external dependencies

---

## ✅ IaC Coverage Summary

| Resource Type | In IaC? | Migration Ready? | Notes |
|--------------|---------|------------------|-------|
| DynamoDB Tables | ✅ Yes | ✅ Yes | Conditional creation |
| S3 Buckets | ✅ Yes | ✅ Yes | Fully managed |
| Lambda Functions | ✅ Yes | ✅ Yes | Fully managed |
| EventBridge | ✅ Yes | ✅ Yes | Fully managed |
| SQS Queues | ✅ Yes | ✅ Yes | Fully managed |
| Secrets Manager | ✅ Yes | ✅ Yes | Fully managed |
| API Gateway | ✅ Yes | ✅ Yes | Fully managed |
| CloudWatch | ✅ Yes | ✅ Yes | Fully managed |
| SSM Parameters | ✅ Yes | ✅ Yes | Conditional creation |
| Bedrock Memory | ❌ No | ⚠️ Manual | API-created, scripted |
| Model Access | ❌ No | ⚠️ Manual | Console configuration |
| Telegram Webhook | ❌ No | ⚠️ Manual | External API |

**IaC Coverage**: ~85% (11/13 resource types)

---

## 🎓 Lessons Learned

### What Worked Well
1. ✅ Conditional resource creation pattern
2. ✅ Dynamic ARN construction with !Sub
3. ✅ Clear separation of environments
4. ✅ Comprehensive exports for cross-stack references

### What to Improve
1. ⚠️ Document external dependencies earlier
2. ⚠️ Automate Bedrock Memory creation (Custom Resource?)
3. ⚠️ Create deployment automation scripts
4. ⚠️ Add pre-flight checks to deployment

### Future Enhancements
- [ ] Custom Resource for Bedrock Memory management
- [ ] Automated Telegram webhook configuration
- [ ] Multi-region deployment templates
- [ ] Disaster recovery automation

---

**Version History**:
- v1.0 (2026-01-21): Initial documentation after IaC improvements