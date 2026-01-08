# AgentCoreNexus Makefile
# 統一管理多個 CloudFormation Stacks

.PHONY: help deploy-all deploy-telegram deploy-processor deploy-web update-frontend status logs clean info

# AWS 配置
AWS_REGION ?= us-west-2

# Stack 名稱
TELEGRAM_STACK = telegram-lambda-receiver
PROCESSOR_STACK = telegram-unified-bot
WEB_STACK = agentcore-web-channel

# 顯示幫助
help:
	@echo "╔═══════════════════════════════════════════════════════════════╗"
	@echo "║          AgentCoreNexus 部署管理工具                          ║"
	@echo "╚═══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "📦 部署指令："
	@echo "  make deploy-all       - 部署所有 stacks（首次部署）"
	@echo "  make deploy-telegram  - 部署 Telegram 接收層"
	@echo "  make deploy-processor - 部署 AI 處理層"
	@echo "  make deploy-web       - 部署 Web 通道層（含前端）"
	@echo ""
	@echo "🚀 快速更新："
	@echo "  make update-frontend  - 快速更新前端（開發用）"
	@echo ""
	@echo "📊 監控指令："
	@echo "  make status           - 檢查所有 stacks 狀態"
	@echo "  make info             - 顯示詳細資訊"
	@echo "  make logs STACK=web   - 查看指定 stack 日誌"
	@echo "                         （STACK: telegram, processor, web）"
	@echo ""
	@echo "🧹 清理指令："
	@echo "  make clean            - 清理所有部署（危險！）"
	@echo ""
	@echo "📚 文檔："
	@echo "  docs/STACK_MANAGEMENT.md - Stack 管理指南"
	@echo ""

# 部署所有 stacks（按順序，首次部署用）
deploy-all:
	@echo "🚀 開始部署所有 stacks..."
	@echo ""
	@$(MAKE) deploy-telegram
	@echo ""
	@$(MAKE) deploy-processor
	@echo ""
	@$(MAKE) deploy-web
	@echo ""
	@echo "✅ 所有 stacks 部署完成！"
	@$(MAKE) status

# 部署 Telegram 接收層
deploy-telegram:
	@echo "📱 部署 Telegram 接收層..."
	cd telegram-lambda && \
	sam build && \
	sam deploy \
		--stack-name $(TELEGRAM_STACK) \
		--region $(AWS_REGION) \
		--capabilities CAPABILITY_IAM \
		--resolve-s3 \
		--no-confirm-changeset

# 部署 AI 處理層
deploy-processor:
	@echo "🤖 部署 AI 處理層..."
	cd telegram-agentcore-bot && \
	sam build && \
	sam deploy \
		--stack-name $(PROCESSOR_STACK) \
		--region $(AWS_REGION) \
		--capabilities CAPABILITY_IAM \
		--resolve-s3 \
		--no-confirm-changeset

# 部署 Web 通道層（含 S3 + CloudFront）
deploy-web:
	@echo "🌐 部署 Web 通道層..."
	@echo "📦 安裝 Lambda 依賴..."
	@cd dev-in-progress/web-channel-expansion/lambdas/websocket && \
		pip3.11 install -r requirements.txt -t . --quiet
	@cd dev-in-progress/web-channel-expansion/lambdas/rest && \
		pip3.11 install -r requirements.txt -t . --quiet
	@cd dev-in-progress/web-channel-expansion/lambdas/router && \
		pip3.11 install -r requirements.txt -t . --quiet
	@echo "✅ 依賴安裝完成"
	@echo "🔨 建構和部署..."
	cd dev-in-progress/web-channel-expansion/infrastructure && \
	sam build -t web-channel-template.yaml && \
	sam deploy \
		--template-file web-channel-template.yaml \
		--stack-name $(WEB_STACK) \
		--region $(AWS_REGION) \
		--capabilities CAPABILITY_IAM \
		--resolve-s3 \
		--parameter-overrides \
			Environment=dev \
			ExistingEventBusName=telegram-lambda-receiver-events \
		--no-confirm-changeset
	@echo ""
	@echo "📋 前端 URL:"
	@aws cloudformation describe-stacks \
		--region $(AWS_REGION) \
		--stack-name $(WEB_STACK) \
		--query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
		--output text

# 快速更新前端（不重新部署 stack）
update-frontend:
	@echo "📦 快速更新前端..."
	cd dev-in-progress/web-channel-expansion && \
	./scripts/deploy-frontend.sh

# 檢查所有 stacks 狀態
status:
	@echo "📊 檢查所有 Stacks 狀態..."
	@echo ""
	@aws cloudformation describe-stacks \
		--region $(AWS_REGION) \
		--query 'Stacks[?StackName==`$(TELEGRAM_STACK)` || StackName==`$(PROCESSOR_STACK)` || StackName==`$(WEB_STACK)`].{Name:StackName,Status:StackStatus,Updated:LastUpdatedTime}' \
		--output table

# 顯示詳細資訊
info:
	@echo "📋 AgentCoreNexus 詳細資訊"
	@echo ""
	@echo "【Telegram 接收層】"
	@aws cloudformation describe-stacks \
		--region $(AWS_REGION) \
		--stack-name $(TELEGRAM_STACK) \
		--query 'Stacks[0].{Status:StackStatus,Updated:LastUpdatedTime}' \
		--output table 2>/dev/null || echo "  ⚠️  Stack 不存在"
	@echo ""
	@echo "【AI 處理層】"
	@aws cloudformation describe-stacks \
		--region $(AWS_REGION) \
		--stack-name $(PROCESSOR_STACK) \
		--query 'Stacks[0].{Status:StackStatus,Updated:LastUpdatedTime}' \
		--output table 2>/dev/null || echo "  ⚠️  Stack 不存在"
	@echo ""
	@echo "【Web 通道層】"
	@aws cloudformation describe-stacks \
		--region $(AWS_REGION) \
		--stack-name $(WEB_STACK) \
		--query 'Stacks[0].{Status:StackStatus,Updated:LastUpdatedTime}' \
		--output table 2>/dev/null || echo "  ⚠️  Stack 不存在"
	@echo ""
	@echo "🌐 前端 URL:"
	@aws cloudformation describe-stacks \
		--region $(AWS_REGION) \
		--stack-name $(WEB_STACK) \
		--query 'Stacks[0].Outputs[?OutputKey==`FrontendUrl`].OutputValue' \
		--output text 2>/dev/null || echo "  未部署"

# 查看日誌
logs:
	@if [ "$(STACK)" = "telegram" ]; then \
		echo "📱 Telegram 接收層日誌:"; \
		aws logs tail /aws/lambda/telegram-lambda-receiver --region $(AWS_REGION) --since 10m --follow; \
	elif [ "$(STACK)" = "processor" ]; then \
		echo "🤖 AI 處理層日誌:"; \
		aws logs tail /aws/lambda/telegram-unified-bot-processor --region $(AWS_REGION) --since 10m --follow; \
	elif [ "$(STACK)" = "web" ]; then \
		echo "🌐 Web 通道層日誌:"; \
		aws logs tail /aws/lambda/$(WEB_STACK)-ws-default --region $(AWS_REGION) --since 10m --follow; \
	else \
		echo "❌ 請指定 STACK 參數"; \
		echo "用法: make logs STACK=telegram|processor|web"; \
		exit 1; \
	fi

# 清理所有部署（危險操作！）
clean:
	@echo "⚠️  警告：這會刪除所有 stacks 和資源！"
	@echo ""
	@read -p "確定要繼續嗎？輸入 'DELETE' 確認: " confirm; \
	if [ "$$confirm" != "DELETE" ]; then \
		echo "❌ 取消清理"; \
		exit 1; \
	fi
	@echo ""
	@echo "🗑️  刪除 Web Channel..."
	@aws cloudformation delete-stack --region $(AWS_REGION) --stack-name $(WEB_STACK) 2>/dev/null || echo "  Stack 不存在"
	@echo "🗑️  刪除 Processor..."
	@aws cloudformation delete-stack --region $(AWS_REGION) --stack-name $(PROCESSOR_STACK) 2>/dev/null || echo "  Stack 不存在"
	@echo "🗑️  刪除 Telegram..."
	@aws cloudformation delete-stack --region $(AWS_REGION) --stack-name $(TELEGRAM_STACK) 2>/dev/null || echo "  Stack 不存在"
	@echo ""
	@echo "✅ 清理完成"