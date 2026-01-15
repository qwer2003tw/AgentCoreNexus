# Stack Management Best Practices

Best practices for managing CloudFormation stacks in AgentCoreNexus, learned from real-world experience.

## 🎯 Core Principles

### 1. Infrastructure as Code (IaC)
**All infrastructure must be in CloudFormation/SAM templates.**

```yaml
# ✅ Good: Everything in template
Resources:
  MyBucket:
    Type: AWS::S3::Bucket
    Properties:
      CorsConfiguration:
        CorsRules: [...]

# ❌ Bad: Manual configuration
# aws s3api put-bucket-cors --bucket my-bucket --cors-configuration file://cors.json
```

### 2. Stack Naming Convention
**Format**: `agentcore-[component]-[env]`

```
agentcore-telegram-adapter
agentcore-ai-processor
agentcore-web-adapter-dev
agentcore-web-adapter-prod
```

### 3. Use Dynamic Names
**Always use `!Sub '${AWS::StackName}-resource'`**

```yaml
# ✅ Good: Dynamic naming
FunctionName: !Sub '${AWS::StackName}-receiver'
TableName: !Sub '${AWS::StackName}-users'

# ❌ Bad: Hardcoded names
FunctionName: telegram-receiver
TableName: users-table
```

---

## 📋 Deployment Workflow

### Standard Deployment Order

**First Deploy** (新系統):
1. telegram-adapter (provides EventBus)
2. ai-processor (uses EventBus)
3. web-adapter (uses EventBus)

**Updates** (現有系統):
- Independent: Any stack can be updated independently
- Breaking Changes: Follow order above

### Deployment Commands

```bash
# Deploy with SAM
cd component-directory
sam build
sam deploy \
  --stack-name agentcore-component-name \
  --region us-west-2 \
  --capabilities CAPABILITY_IAM \
  --resolve-s3 \
  --no-confirm-changeset

# Or use Makefile
make deploy-telegram
make deploy-processor
make deploy-web
```

---

## 🔗 Cross-Stack References

### Export Pattern

```yaml
# In telegram-adapter/template.yaml
Outputs:
  EventBusName:
    Description: EventBridge bus name
    Value: !Ref EventBus
    Export:
      Name: !Sub '${AWS::StackName}-EventBusName'
  
  EventBusArn:
    Description: EventBridge bus ARN
    Value: !GetAtt EventBus.Arn
    Export:
      Name: !Sub '${AWS::StackName}-EventBusArn'
```

### Import Pattern

```yaml
# In ai-processor/template.yaml
Environment:
  Variables:
    EVENT_BUS_NAME: !ImportValue agentcore-telegram-adapter-EventBusName

# In EventBridge rule
EventBusName: !ImportValue agentcore-telegram-adapter-EventBusName
```

### Best Practices

✅ **Do**:
- Export with stack name prefix
- Import using full export name
- Document what each export is for
- Version exports if breaking changes possible

❌ **Don't**:
- Hardcode ARNs or names
- Use generic export names
- Create circular dependencies
- Import from unstable stacks

---

## 🏷️ Resource Tagging

### Standard Tags

All resources should have:

```yaml
Tags:
  - Key: Project
    Value: AgentCoreNexus
  - Key: Component
    Value: telegram-adapter  # or ai-processor, web-adapter
  - Key: Environment
    Value: !Ref Environment  # dev, staging, prod
  - Key: ManagedBy
    Value: SAM
```

### Benefits

- **Cost Allocation**: Track costs by component
- **Resource Discovery**: Find all resources for a component
- **Compliance**: Meet organizational requirements
- **Automation**: Tag-based operations

---

## 🗑️ Stack Deletion

### Safe Deletion Order

**Reverse dependency order**:
1. web-adapter (depends on telegram-adapter EventBus)
2. ai-processor (depends on telegram-adapter EventBus)
3. telegram-adapter (provides EventBus, delete last)

### Before Deletion

```bash
# 1. Disable EventBridge rules (prevent events during deletion)
aws events disable-rule \
  --name agentcore-telegram-adapter-message-received \
  --event-bus-name agentcore-telegram-adapter-events \
  --region us-west-2

# 2. Backup all data (use /backup-restore.md workflow)
# 3. Record all Stack outputs
# 4. Notify users if needed
```

### Deletion Commands

```bash
# Delete in reverse order
aws cloudformation delete-stack --stack-name agentcore-web-adapter --region us-west-2
aws cloudformation wait stack-delete-complete --stack-name agentcore-web-adapter --region us-west-2

aws cloudformation delete-stack --stack-name agentcore-ai-processor --region us-west-2
aws cloudformation wait stack-delete-complete --stack-name agentcore-ai-processor --region us-west-2

# Delete telegram last (may need manual EventBridge cleanup)
aws cloudformation delete-stack --stack-name agentcore-telegram-adapter --region us-west-2
```

### Common Deletion Issues

**EventBridge Rules Block Deletion**:
```bash
# List rules
aws events list-rules --event-bus-name agentcore-telegram-adapter-events --region us-west-2

# Remove targets
aws events remove-targets \
  --rule RULE_NAME \
  --event-bus-name BUS_NAME \
  --ids TARGET_ID \
  --region us-west-2

# Delete rule
aws events delete-rule \
  --name RULE_NAME \
  --event-bus-name BUS_NAME \
  --region us-west-2
```

**DynamoDB Retain Policy**:
```yaml
# If you want to keep data after stack deletion
MyTable:
  Type: AWS::DynamoDB::Table
  DeletionPolicy: Retain
  UpdateReplacePolicy: Retain
```

---

## 🔄 Stack Updates

### Types of Updates

1. **No Downtime**: Lambda code, environment variables
2. **Brief Downtime**: API Gateway changes
3. **Risky**: DynamoDB schema, IAM roles

### Update Strategy

```bash
# 1. Create changeset
sam deploy --stack-name STACK_NAME ... --no-execute-changeset

# 2. Review changes
aws cloudformation describe-change-set \
  --change-set-name CHANGESET_NAME \
  --stack-name STACK_NAME

# 3. Execute if safe
aws cloudformation execute-change-set \
  --change-set-name CHANGESET_NAME \
  --stack-name STACK_NAME
```

### Rollback Strategy

```bash
# If update fails, CloudFormation auto-rolls back
# To manually rollback:
aws cloudformation cancel-update-stack --stack-name STACK_NAME --region us-west-2
```

---

## 🔐 Secrets Management

### Best Practices

```yaml
# ✅ Good: Reference secret ARN
Environment:
  Variables:
    TELEGRAM_SECRETS_ARN: !Ref TelegramSecrets

Policies:
  - AWSSecretsManagerGetSecretValuePolicy:
      SecretArn: !Ref TelegramSecrets

# ❌ Bad: Hardcode or expose secrets
Environment:
  Variables:
    BOT_TOKEN: '1234567890:ABCDEF'  # Never do this!
```

### Updating Secrets

```bash
# Update secret value
aws secretsmanager update-secret \
  --secret-id telegram-adapter-receiver-secrets \
  --secret-string '{"bot_token":"new-token","webhook_secret_token":"secret"}'

# Clear Lambda cache (必須！)
aws lambda update-function-configuration \
  --function-name agentcore-telegram-adapter-receiver \
  --environment Variables={DUMMY_UPDATE=1} \
  --region us-west-2

aws lambda wait function-updated \
  --function-name agentcore-telegram-adapter-receiver \
  --region us-west-2
```

---

## 📊 Monitoring & Observability

### Essential CloudWatch Alarms

```yaml
# Lambda errors
LambdaErrorAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: !Sub '${AWS::StackName}-lambda-errors'
    MetricName: Errors
    Namespace: AWS/Lambda
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 1
    Threshold: 5
    Dimensions:
      - Name: FunctionName
        Value: !Ref MyFunction

# API Gateway 5xx errors
ApiErrorAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: !Sub '${AWS::StackName}-api-5xx'
    MetricName: 5XXError
    Namespace: AWS/ApiGateway
    Statistic: Sum
    Period: 300
    EvaluationPeriods: 1
    Threshold: 10
```

### Log Retention

```yaml
# Always set log retention
MyFunctionLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub '/aws/lambda/${MyFunction}'
    RetentionInDays: 14  # 7, 14, 30, 60, 90, 120, etc.
```

---

## 💰 Cost Optimization

### Lambda Configuration

```yaml
# Right-size memory and timeout
Function:
  Type: AWS::Serverless::Function
  Properties:
    MemorySize: 256      # Start small, increase if needed
    Timeout: 30          # Not 900 by default
    ReservedConcurrentExecutions: 10  # Prevent runaway costs
```

### DynamoDB

```yaml
# Use on-demand for variable workloads
BillingMode: PAY_PER_REQUEST

# Use provisioned for predictable workloads
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 5
  WriteCapacityUnits: 5
```

### S3 Lifecycle

```yaml
# Automatically move old data to cheaper storage
LifecycleConfiguration:
  Rules:
    - Id: MoveToIA
      Status: Enabled
      Transitions:
        - StorageClass: STANDARD_IA
          TransitionInDays: 30
```

---

## 🚨 Common Mistakes to Avoid

### 1. Empty Parameter Defaults with ARNs

```yaml
# ❌ Bad: Empty default for ARN
Parameters:
  EventBusArn:
    Type: String
    Default: ''  # Causes IAM policy error

# ✅ Good: Use wildcard or condition
Resource: '*'
# or
Resource: !If [HasEventBus, !Ref EventBusArn, '*']
```

### 2. Hardcoded Lambda ARNs

```yaml
# ❌ Bad: Hardcoded ARN
Targets:
  - Arn: arn:aws:lambda:us-west-2:123:function:my-func

# ✅ Good: Use ImportValue or GetAtt
Targets:
  - Arn: !ImportValue stack-name-FunctionArn
```

### 3. Forgetting Lambda Permissions

```yaml
# ✅ Always add permission for EventBridge
MyFunctionPermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref MyFunction
    Action: lambda:InvokeFunction
    Principal: events.amazonaws.com
    SourceArn: !GetAtt MyRule.Arn
```

### 4. Not Using DeletionPolicy

```yaml
# For critical data
MyTable:
  Type: AWS::DynamoDB::Table
  DeletionPolicy: Retain  # Keep data if stack deleted
  UpdateReplacePolicy: Retain
```

---

## 🧪 Testing Infrastructure

### Before Deployment

```bash
# 1. Validate template
sam validate

# 2. Create changeset (dry run)
sam deploy --stack-name STACK --no-execute-changeset

# 3. Review changes
aws cloudformation describe-change-set ...

# 4. Deploy
sam deploy --stack-name STACK
```

### After Deployment

```bash
# 1. Check stack status
make status

# 2. Check Lambda health
aws lambda get-function --function-name FUNCTION \
  --query 'Configuration.{State:State,LastUpdateStatus:LastUpdateStatus}'

# 3. Check logs for errors
aws logs tail /aws/lambda/FUNCTION --since 5m

# 4. Test functionality
# (API call, Telegram message, etc.)
```

---

## 📈 Scaling Considerations

### Lambda Concurrency

```yaml
# Set reserved concurrency to prevent runaway
ReservedConcurrentExecutions: 100

# Or use provisioned concurrency for consistency
ProvisionedConcurrencyConfig:
  ProvisionedConcurrentExecutions: 5
```

### DynamoDB Auto Scaling

```yaml
# Enable auto scaling for provisioned mode
AutoScalingRoleArn: !GetAtt ScalingRole.Arn
```

### API Gateway Throttling

```yaml
# Set per-method throttling
ThrottlingBurstLimit: 500
ThrottlingRateLimit: 100
```

---

## 🔒 Security Best Practices

### 1. Least Privilege IAM

```yaml
# ✅ Specific permissions
Policies:
  - Statement:
      - Effect: Allow
        Action: dynamodb:GetItem
        Resource: !GetAtt MyTable.Arn

# ❌ Overly permissive
Policies:
  - Statement:
      - Effect: Allow
        Action: dynamodb:*
        Resource: '*'
```

### 2. Enable Encryption

```yaml
# DynamoDB
SSESpecification:
  SSEEnabled: true

# S3
BucketEncryption:
  ServerSideEncryptionConfiguration:
    - ServerSideEncryptionByDefault:
        SSEAlgorithm: AES256

# Secrets Manager (automatic)
```

### 3. Enable Point-in-Time Recovery

```yaml
# For critical DynamoDB tables
PointInTimeRecoverySpecification:
  PointInTimeRecoveryEnabled: true
```

---

## 📝 Documentation Requirements

### Stack Description

```yaml
# Clear, specific description
Description: >
  AgentCoreNexus - Telegram Channel Adapter
  Webhook receiver and response router for Telegram Bot
```

### Parameter Documentation

```yaml
Parameters:
  Environment:
    Type: String
    Description: Deployment environment (dev/staging/prod)
    AllowedValues: [dev, staging, prod]
    Default: dev
```

### Output Documentation

```yaml
Outputs:
  WebhookUrl:
    Description: Telegram webhook URL for bot configuration
    Value: !Sub 'https://${Api}.execute-api.${AWS::Region}.amazonaws.com/webhook'
    Export:
      Name: !Sub '${AWS::StackName}-WebhookUrl'
```

---

## 🔄 Stack Migration Strategy

### Renaming Stacks (This Project's Experience)

**Phases**:
1. ✅ Update all code to new names
2. ✅ Update all documentation
3. ⚠️ Backup all data
4. ⚠️ Delete old stacks
5. ⚠️ Deploy new stacks
6. ⚠️ Restore data
7. ✅ Verify functionality

**Critical Points**:
- Cannot rename stacks in-place
- Must delete and recreate
- Plan for downtime
- Have rollback strategy

### Breaking Changes

**When making breaking changes**:
1. Create parallel stack with new name
2. Migrate traffic gradually
3. Verify new stack works
4. Delete old stack
5. Update references

---

## 🚨 Emergency Procedures

### Stack Stuck in UPDATE_ROLLBACK_FAILED

```bash
# Option 1: Continue rollback
aws cloudformation continue-update-rollback \
  --stack-name STACK_NAME \
  --region us-west-2

# Option 2: Skip problematic resources
aws cloudformation continue-update-rollback \
  --stack-name STACK_NAME \
  --resources-to-skip ResourceLogicalId \
  --region us-west-2
```

### Stack Deletion Hanging

```bash
# Find problematic resources
aws cloudformation describe-stack-resources \
  --stack-name STACK_NAME \
  --region us-west-2 \
  | jq '.StackResources[] | select(.ResourceStatus == "DELETE_FAILED")'

# Manually delete resources
# Then retry stack deletion
```

### Lost Stack Outputs

```bash
# If you deleted a stack but need its exports
# Check backup files
cat backups/YYYYMMDD/stack-STACK_NAME.json | jq '.Outputs'
```

---

## 📊 Stack Health Monitoring

### Daily Checks

```bash
# Check all stacks are healthy
aws cloudformation describe-stacks --region us-west-2 \
  --query 'Stacks[?contains(StackName, `agentcore`)].{Name:StackName,Status:StackStatus}' \
  --output table

# Check for drift (config changed manually)
aws cloudformation detect-stack-drift --stack-name STACK --region us-west-2
```

### Weekly Reviews

- Review CloudWatch alarms
- Check Lambda error rates
- Review cost trends
- Update stack templates if needed

---

## 💡 Pro Tips

### 1. Use SAM Accelerate for Dev

```bash
# Fast feedback loop
sam sync --stack-name STACK --watch
```

### 2. Template Validation

```bash
# Validate before deploy
sam validate --lint

# Check for security issues
cfn-lint template.yaml
```

### 3. Cost Estimation

```bash
# Before deploying, estimate costs
# Use AWS Pricing Calculator
# Monitor actual costs after deployment
```

### 4. Blue-Green Deployments

```yaml
# For zero-downtime updates
DeploymentPreference:
  Type: AllAtOnce  # or Canary10Percent5Minutes, Linear10PercentEvery1Minute
  Alarms:
    - !Ref MyAlarm
```

---

## 🎓 Lessons Learned

### From AgentCoreNexus Development

1. **Always specify region in boto3 clients**
   - Prevents 307 redirects in S3 presigned URLs
   
2. **Use template parameters for cross-stack values**
   - Easier to update than hardcoded

3. **Test IAM permissions before deployment**
   - Many issues only appear at runtime

4. **EventBridge rules must be manually cleaned**
   - Before deleting event bus

5. **Lambda caches environment and secrets**
   - Update function config to clear cache

---

## 📚 Related Documentation

- [Deployment Guide](../../docs/deployment-guide.md)
- [Stack Management](../../docs/STACK_MANAGEMENT.md)
- [Backup/Restore Workflow](../workflows/backup-restore.md)
- [AWS Lambda Issues](./aws-lambda-telegram-bot-deployment-issues.md)

---

## ✅ Pre-Deployment Checklist

- [ ] Template validates successfully
- [ ] All parameters have descriptions
- [ ] All outputs are exported with stack name prefix
- [ ] IAM permissions follow least privilege
- [ ] Resources are properly tagged
- [ ] Log retention configured
- [ ] Deletion policy set for critical resources
- [ ] Cross-stack references use ImportValue
- [ ] Backup created before risky changes

---

**Version**: 1.0.0  
**Last Updated**: 2026-01-15  
**Based on**: Real AgentCoreNexus deployment experience  
**Maintained by**: AgentCoreNexus Team