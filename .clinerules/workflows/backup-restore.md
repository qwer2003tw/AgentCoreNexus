---
name: backup-restore
description: Workflow for backing up and restoring AgentCoreNexus data
trigger: manual
estimated_time: 30-60 minutes
---

# Backup & Restore Workflow

Complete workflow for backing up all AgentCoreNexus data and restoring it after infrastructure changes.

## 🎯 When to Use

- Before major infrastructure changes
- Before Stack deletions/recreations
- Before risky deployments
- Regular backup schedule (weekly/monthly)
- Before version upgrades

---

## 📦 Phase 1: Backup (15-20 minutes)

### Step 1: Create Backup Directory

```bash
mkdir -p backups/$(date +%Y%m%d-%H%M%S)
cd backups/$(date +%Y%m%d-%H%M%S)
```

### Step 2: Backup DynamoDB Tables

**List all tables**:
```bash
aws dynamodb list-tables --region us-west-2 | \
  jq -r '.TableNames[] | select(contains("agentcore") or contains("telegram"))'
```

**Backup each table**:
```bash
# telegram-allowlist
aws dynamodb scan --table-name telegram-allowlist --region us-west-2 | \
  jq '{telegram-allowlist: [.Items[] | {PutRequest: {Item: .}}]}' > telegram-allowlist.json

# agentcore-web-adapter tables
for table in web-users user-bindings conversations conversation-history; do
  aws dynamodb scan --table-name agentcore-web-adapter-$table --region us-west-2 | \
    jq "{\"agentcore-web-adapter-$table\": [.Items[] | {PutRequest: {Item: .}}]}" > ${table}.json
done
```

### Step 3: Backup Secrets Manager

```bash
# Telegram secrets
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text > secret-telegram.json

# Web adapter JWT secret (if needed)
aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id agentcore-web-adapter/jwt-secret \
  --query SecretString --output text > secret-web-jwt.json 2>/dev/null || echo "Not found"
```

### Step 4: Backup Stack Configurations

```bash
# Save all stack outputs
for stack in agentcore-telegram-adapter agentcore-ai-processor agentcore-web-adapter; do
  aws cloudformation describe-stacks \
    --region us-west-2 \
    --stack-name $stack \
    --query 'Stacks[0]' > stack-${stack}.json 2>/dev/null || echo "Stack $stack not found"
done
```

### Step 5: Backup S3 Frontend (if needed)

```bash
# Get bucket name
BUCKET=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

# Sync to local
if [ ! -z "$BUCKET" ]; then
  aws s3 sync s3://$BUCKET/ frontend-backup/
fi
```

### Step 6: Verify Backups

```bash
# Check all files exist
ls -lh *.json
wc -l *.json

# Should see:
# - 5+ DynamoDB backups
# - 1-2 Secrets backups
# - 3 Stack config backups
```

---

## 🔄 Phase 2: Restore (20-30 minutes)

### Prerequisites

- [ ] New stacks deployed successfully
- [ ] All Lambda functions in Active state
- [ ] DynamoDB tables created and ready

### Step 1: Restore DynamoDB Data

```bash
cd backups/YYYYMMDD-HHMMSS

# Restore telegram-allowlist
aws dynamodb batch-write-item \
  --request-items file://telegram-allowlist.json \
  --region us-west-2

# Restore web tables
for table in web-users user-bindings conversations conversation-history; do
  echo "Restoring ${table}..."
  aws dynamodb batch-write-item \
    --request-items file://${table}.json \
    --region us-west-2
done
```

**Handle Batch Write Limits**:
- DynamoDB batch-write-item max 25 items per request
- For large tables, split into chunks:

```bash
# For large tables (>1000 items)
jq -c '.[] | ._[0:25]' conversation-history.json | while read chunk; do
  aws dynamodb batch-write-item --request-items "$chunk" --region us-west-2
  sleep 0.5  # Rate limiting
done
```

### Step 2: Verify Data Restoration

```bash
# Check item counts
aws dynamodb scan --table-name telegram-allowlist --region us-west-2 --select COUNT
aws dynamodb scan --table-name agentcore-web-adapter-conversations --region us-west-2 --select COUNT

# Sample some data
aws dynamodb scan --table-name telegram-allowlist --region us-west-2 --limit 5
```

### Step 3: Restore Secrets (if needed)

```bash
# Secrets usually don't change or are recreated
# Only restore if absolutely necessary

# Update bot token if changed
aws secretsmanager update-secret \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --secret-string file://secret-telegram.json
```

### Step 4: Restore Frontend (if needed)

```bash
# Get new bucket name
NEW_BUCKET=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text)

# Upload frontend
aws s3 sync frontend-backup/ s3://$NEW_BUCKET/

# Invalidate CloudFront
DIST_ID=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-web-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

aws cloudfront create-invalidation \
  --distribution-id $DIST_ID \
  --paths "/*"
```

### Step 5: Re-configure External Services

**Telegram Webhook**:
```bash
BOT_TOKEN=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .bot_token)

WEBHOOK_URL=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name agentcore-telegram-adapter \
  --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' \
  --output text)

WEBHOOK_SECRET=$(aws secretsmanager get-secret-value \
  --region us-west-2 \
  --secret-id telegram-adapter-receiver-secrets \
  --query SecretString --output text | jq -r .webhook_secret_token)

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"${WEBHOOK_URL}\",\"secret_token\":\"${WEBHOOK_SECRET}\"}"
```

---

## ✅ Verification Checklist

### After Backup
- [ ] All JSON files created
- [ ] File sizes reasonable (not 0 bytes)
- [ ] Can parse JSON files (`jq . file.json`)
- [ ] Stack configs contain Outputs
- [ ] Secrets contain expected keys

### After Restore
- [ ] DynamoDB item counts match
- [ ] Sample data looks correct
- [ ] Secrets accessible
- [ ] Frontend loads correctly
- [ ] Webhook connected (pending_update_count = 0)

---

## 🚨 Emergency Restore

If something goes wrong during infrastructure changes:

### Step 1: Stop All Operations
```bash
# Disable EventBridge rules
aws events disable-rule --name RULE_NAME --event-bus-name BUS_NAME --region us-west-2
```

### Step 2: Restore from Backup
```bash
# Follow restore steps above
cd backups/LATEST_BACKUP
# Run all restore commands
```

### Step 3: Verify System Health
```bash
# Test message flow
# Check Lambda logs
# Verify user can interact
```

---

## 📋 Backup Schedule

### Automated Backups (Future)

Consider setting up:
- **Daily**: DynamoDB on-demand backups (native)
- **Weekly**: Complete backup to S3
- **Before Changes**: Manual backup (this workflow)

### Retention Policy

- **Daily backups**: Keep 7 days
- **Weekly backups**: Keep 4 weeks
- **Monthly backups**: Keep 12 months
- **Pre-change backups**: Keep indefinitely

---

## 🔧 Troubleshooting

### Backup Failed

**DynamoDB scan timeout**:
```bash
# Use pagination for large tables
aws dynamodb scan --table-name TABLE \
  --max-items 1000 \
  --starting-token TOKEN
```

**Access denied**:
```bash
# Check IAM permissions
aws iam get-user
# Ensure dynamodb:Scan, secretsmanager:GetSecretValue permissions
```

### Restore Failed

**Batch write throttled**:
```bash
# Add sleep between batches
# Reduce batch size to 10 items
```

**Item already exists**:
```bash
# Expected if table not empty
# Use delete-item first if needed
```

---

## 📚 Related Documentation

- [Stack Management](../docs/STACK_MANAGEMENT.md)
- [Deployment Guide](../docs/deployment-guide.md)
- [Environment Variables](../docs/ENV.md)

---

**Workflow Version**: 1.0  
**Last Updated**: 2026-01-15  
**Maintained by**: AgentCoreNexus Team