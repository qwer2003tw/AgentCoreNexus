# AgentCoreNexus Makefile
# 統一管理多個 CloudFormation Stacks

.PHONY: help deploy-all deploy-telegram deploy-processor deploy-web update-frontend status logs clean info test test-all test-backend test-frontend test-agentcore test-lambda test-web test-quick coverage-report

# AWS 配置
AWS_REGION ?= us-west-2

# Stack 名稱（重構後）
TELEGRAM_STACK = agentcore-telegram-adapter
PROCESSOR_STACK = agentcore-ai-processor
WEB_STACK = agentcore-web-adapter

# 顯示幫助
help:
	@echo "╔═══════════════════════════════════════════════════════════════╗"
	@echo "║          AgentCoreNexus 管理工具                              ║"
	@echo "╚═══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🧪 測試指令："
	@echo "  make test             - 執行所有測試（推薦）"
	@echo "  make test-backend     - 測試後端組件"
	@echo "  make test-frontend    - 測試前端組件"
	@echo "  make test-agentcore   - 只測試 AI 處理器"
	@echo "  make test-lambda      - 只測試 Webhook 接收器"
	@echo "  make test-web         - 只測試 Web 前端"
	@echo "  make test-quick       - 快速測試（不含 Web E2E）"
	@echo "  make coverage-report  - 查看覆蓋率報告"
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
	cd telegram-adapter && \
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
	cd ai-processor && \
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
	@cd web-adapter/lambdas/websocket && \
		pip3.11 install -r requirements.txt -t . --quiet
	@cd web-adapter/lambdas/rest && \
		pip3.11 install -r requirements.txt -t . --quiet
	@cd web-adapter/lambdas/router && \
		pip3.11 install -r requirements.txt -t . --quiet
	@echo "✅ 依賴安裝完成"
	@echo "🔨 建構和部署..."
	cd web-adapter/infrastructure && \
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
	cd web-adapter && \
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

# ==========================================
# 測試指令
# ==========================================

# 所有測試（推薦）
test-all: test
test:
	@echo "🧪 執行所有組件測試..."
	@./run_all_tests.sh

# 後端測試（Python 組件）
test-backend:
	@echo "🐍 測試後端組件..."
	@$(MAKE) test-agentcore
	@echo ""
	@$(MAKE) test-lambda

# AI 處理器測試
test-agentcore:
	@echo "🤖 測試 ai-processor..."
	@cd ai-processor && \
		if [ -f "run_tests_with_coverage.sh" ]; then \
			./run_tests_with_coverage.sh; \
		else \
			python3.11 run_tests.py; \
		fi

# Webhook 接收器測試
test-lambda:
	@echo "📱 測試 telegram-adapter..."
	@cd telegram-adapter && \
		if [ -f "run_all_tests.sh" ]; then \
			./run_all_tests.sh --cov; \
		else \
			python3.11 -m pytest tests/ -v; \
		fi

# 前端測試
test-frontend: test-web
test-web:
	@echo "🌐 測試 web-adapter..."
	@if [ -d "web-adapter/tests" ]; then \
		cd web-adapter/tests && npm test; \
	else \
		echo "⚠️  web-adapter/tests 不存在"; \
	fi

# 快速測試（不含覆蓋率和 Web E2E）
test-quick:
	@echo "⚡ 快速測試（不含覆蓋率）..."
	@./run_all_tests.sh --quick

# 覆蓋率報告
coverage-report:
	@echo "📊 覆蓋率報告"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🤖 ai-processor:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ -f "ai-processor/coverage.xml" ]; then \
		cd ai-processor && python3.11 -m coverage report 2>/dev/null || echo "  請先運行測試以生成覆蓋率報告"; \
	else \
		echo "  未找到覆蓋率報告，請運行: make test-agentcore"; \
	fi
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📱 telegram-adapter:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ -f "telegram-adapter/coverage.xml" ]; then \
		cd telegram-adapter && python3.11 -m coverage report 2>/dev/null || echo "  請先運行測試以生成覆蓋率報告"; \
	else \
		echo "  未找到覆蓋率報告，請運行: make test-lambda"; \
	fi
	@echo ""