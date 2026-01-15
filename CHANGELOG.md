# Changelog

所有重要變更都會記錄在此文件中。

格式基於 [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)，
版本號遵循 [Semantic Versioning](https://semver.org/spec/v2.0.0.html)。

---

## [Unreleased]

### Changed
- Major refactoring: Complete naming overhaul
- All components renamed for clarity and consistency

---

## [0.9.0] - 2026-01-15

### Added
- **Complete Naming Overhaul**: Renamed all components and Stacks for clarity
  - `telegram-agentcore-bot` → `ai-processor` (Channel-agnostic AI Processor)
  - `telegram-lambda` → `telegram-adapter` (Telegram Channel Adapter)
  - `web-channel` → `web-adapter` (Web Channel Adapter)
- **Unified Stack Naming**: All CloudFormation Stacks now use `agentcore-` prefix
  - `telegram-lambda-receiver` → `agentcore-telegram-adapter`
  - `telegram-unified-bot` → `agentcore-ai-processor`
  - `agentcore-web-channel` → `agentcore-web-adapter`
- **Test Structure Unified**: Consistent test directory structure across components
  - ai-processor/tests/
  - telegram-adapter/tests/integration/ (renamed from e2e/)
  - web-adapter/tests/ (unified structure)
- **Professional Documentation**:
  - LICENSE (MIT)
  - CONTRIBUTING.md
  - CHANGELOG.md (this file)
  - SECURITY.md
- **Real AWS E2E Testing**: Established dual testing strategy
  - Mock E2E for fast iteration
  - Real AWS E2E for deployment validation
  - 100% pass rate on both
- **.clinerules Expansion**: Added refactoring and naming standards
  - rules/naming-standards.md
  - rules/refactoring-protocol.md
  - workflows/backup-restore.md

### Changed
- **Architecture Documentation**: Corrected terminology
  - Clarified "Universal" refers to EventBridge + Message Schema
  - Explained why multiple Adapters (not single Universal Adapter)
  - Updated all architecture diagrams
- **Documentation v2.0**: Complete overhaul
  - Added prerequisites, cost estimates, security features
  - Added limitations and known issues section
  - Complete frontend technology stack documentation
- **Makefile**: Updated all paths and Stack names
- **Testing**: Verified 100% test pass rate (391 tests)

### Fixed
- Web E2E test timing issues
- Mock testing limitations identified and documented

---

## [0.8.0-web-mvp] - 2026-01-14

### Added
- **Web Channel MVP**: 85% complete
  - Authentication system (Email + JWT + Bcrypt)
  - WebSocket real-time messaging
  - React PWA frontend
  - Conversation history (90-day retention)
  - Cross-channel binding
  - Export functionality (JSON/Markdown)
  - CloudFront + S3 hosting
  - Complete deployment scripts

### Changed
- **Phase 5 Progress**: From 50% to 78%
- **Documentation**: Enhanced with Web Channel details

---

## [0.5.0-phase3] - 2026-01-12

### Added
- **EventBridge Integration**: Event-driven architecture
- **Universal Message Schema**: Channel-agnostic message format
- **Response Router**: Channel-specific response delivery
- **Dual-track Operation**: EventBridge + SQS parallel operation

### Changed
- Migrated from SQS-only to EventBridge-first architecture
- Updated testing to include EventBridge integration tests

---

## [Earlier Versions]

（詳細歷史記錄在 dev-reports/）

---

## Version Scheme

- **Major** (X.0.0): Breaking changes, major architecture updates
- **Minor** (0.X.0): New features, backwards compatible
- **Patch** (0.0.X): Bug fixes, documentation updates