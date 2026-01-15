# AgentCore Web Frontend

React + TypeScript + Vite 前端應用，提供 Web 通道聊天界面。

## 🚀 快速開始

### 1. 安裝依賴

```bash
npm install
```

### 2. 配置環境變數

複製 `.env.example` 並更新 API endpoints：

```bash
cp .env.example .env
```

編輯 `.env`：
```
VITE_API_ENDPOINT=https://YOUR_API_ID.execute-api.us-west-2.amazonaws.com/prod
VITE_WS_ENDPOINT=wss://YOUR_WS_API_ID.execute-api.us-west-2.amazonaws.com/prod
```

### 3. 啟動開發伺服器

```bash
npm run dev
```

應用將在 http://localhost:5173 啟動

### 4. 建構生產版本

```bash
npm run build
```

輸出在 `dist/` 目錄

---

## 📁 專案結構

```
src/
├── main.tsx              # 應用入口
├── App.tsx               # 主路由組件
├── index.css             # 全域樣式
├── config/
│   └── env.ts            # 環境配置
├── services/
│   ├── api.ts            # REST API client
│   └── websocket.ts      # WebSocket client
├── stores/
│   ├── authStore.ts      # 認證狀態
│   └── chatStore.ts      # 聊天狀態
├── pages/
│   ├── LoginPage.tsx
│   ├── ChangePasswordPage.tsx
│   └── ChatPage.tsx
└── components/
    └── Chat/
        ├── ChatWindow.tsx
        ├── MessageList.tsx
        └── Sidebar.tsx
```

---

## 🎨 技術棧

- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand
- **Data Fetching**: TanStack Query
- **Icons**: Lucide React
- **PWA**: vite-plugin-pwa

---

## 🔧 開發

### 可用腳本

- `npm run dev` - 啟動開發伺服器
- `npm run build` - 建構生產版本
- `npm run preview` - 預覽生產建構
- `npm run lint` - 執行 ESLint

### PWA 測試

PWA 功能僅在生產建構中啟用：

```bash
npm run build
npm run preview
```

---

## 🌐 部署到 S3 + CloudFront

### 1. 建構應用

```bash
npm run build
```

### 2. 上傳到 S3

```bash
aws s3 sync dist/ s3://your-bucket-name/ --delete
```

### 3. 設置 CloudFront

CloudFormation 或手動創建 Distribution，指向 S3 bucket。

---

## 🔑 首次使用

1. **創建帳號**（需要管理員）
   - 聯絡管理員創建帳號
   - 獲得臨時密碼

2. **首次登入**
   - 使用 email 和臨時密碼登入
   - 系統會要求修改密碼

3. **開始使用**
   - 修改密碼後即可開始對話
   - 可選：綁定 Telegram 帳號

---

## 🔗 綁定 Telegram

1. 在設定頁面點擊「綁定 Telegram」
2. 獲得 6 位數驗證碼
3. 在 Telegram 發送：`/bind 123456`
4. 綁定成功後兩邊共享對話記錄

---

## 🐛 Troubleshooting

### WebSocket 無法連接

1. 檢查 `.env` 中的 `VITE_WS_ENDPOINT` 是否正確
2. 檢查 JWT token 是否有效（重新登入）
3. 查看瀏覽器 Console 錯誤

### API 請求失敗

1. 檢查 `.env` 中的 `VITE_API_ENDPOINT` 是否正確
2. 檢查網絡連接
3. 查看 Network tab 中的請求詳情

---

## 📚 相關文檔

- [ARCHITECTURE.md](../ARCHITECTURE.md) - 系統架構
- [INTEGRATION_GUIDE.md](../INTEGRATION_GUIDE.md) - 整合指南
- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - 實施總結

---

**版本**: 0.1.0  
**狀態**: Development  
**最後更新**: 2026-01-08