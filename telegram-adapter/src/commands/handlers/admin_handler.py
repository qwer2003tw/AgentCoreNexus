"""
Admin Command Handler - 完整的管理員指令處理器
支持用戶管理、權限控制、統計信息和廣播功能
"""

import allowlist
import telegram_client
from commands.base import CommandHandler
from commands.decorators import require_admin
from telegram import Update

from utils.logger import get_logger

logger = get_logger(__name__)


@require_admin
class AdminCommandHandler(CommandHandler):
    """
    管理員指令處理器

    支持的子指令：
    - add <chat_id> [username] - 添加用戶/群組
    - remove <chat_id> - 移除用戶/群組
    - list [page] - 列出所有用戶（分頁）
    - info <chat_id> - 查看用戶詳情
    - enable <chat_id> - 啟用用戶
    - disable <chat_id> - 禁用用戶
    - promote <chat_id> - 升級為管理員
    - demote <chat_id> - 降級為普通用戶
    - stats - 查看系統統計
    - broadcast <message> - 廣播消息給所有用戶
    - help - 顯示幫助信息

    權限：需要管理員權限 (ADMIN)
    """

    def can_handle(self, text: str) -> bool:
        """判斷是否為 /admin 指令"""
        if not text:
            return False
        stripped = text.strip()
        return stripped == "/admin" or stripped.startswith("/admin ")

    def handle(self, update: Update, event: dict) -> bool:
        """處理 /admin 指令"""
        message = update.message or update.edited_message
        if not message:
            return False

        chat_id = message.chat_id
        username = message.from_user.username if message.from_user else "Unknown"
        command_text = (message.text or message.caption or "").strip()

        # 解析子指令
        parts = command_text.split(maxsplit=2)
        subcommand = parts[1] if len(parts) > 1 else "help"
        args = parts[2] if len(parts) > 2 else ""

        logger.info(
            f"Admin command: {subcommand}",
            extra={
                "chat_id": chat_id,
                "username": username,
                "subcommand": subcommand,
                "event_type": "admin_command",
            },
        )

        # 路由到對應的處理函數
        handlers = {
            "add": self._handle_add,
            "remove": self._handle_remove,
            "list": self._handle_list,
            "info": self._handle_info,
            "enable": self._handle_enable,
            "disable": self._handle_disable,
            "promote": self._handle_promote,
            "demote": self._handle_demote,
            "grant_file": self._handle_grant_file,
            "revoke_file": self._handle_revoke_file,
            "stats": self._handle_stats,
            "broadcast": self._handle_broadcast,
            "help": self._handle_help,
        }

        handler_func = handlers.get(subcommand, self._handle_help)
        return handler_func(chat_id, args)

    def _handle_add(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin add 指令"""
        parts = args.split()
        if not parts:
            return self._send_error(admin_chat_id, "用法：`/admin add <chat_id> [username]`")

        try:
            target_chat_id = int(parts[0])
            target_username = parts[1] if len(parts) > 1 else f"user_{abs(target_chat_id)}"

            # 添加到允許名單
            success = allowlist.add_to_allowlist(
                chat_id=target_chat_id, username=target_username, enabled=True
            )

            if success:
                chat_type = "👥 群組" if target_chat_id < 0 else "👤 私聊"
                message = f"✅ 已添加到允許名單\n\n{chat_type}\nID: `{target_chat_id}`\n用戶名: @{target_username}\n狀態: 已啟用\n角色: user"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "添加失敗，請檢查日誌")

        except ValueError:
            return self._send_error(admin_chat_id, "無效的 chat_id，必須是數字")

    def _handle_remove(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin remove 指令"""
        try:
            target_chat_id = int(args.strip())

            # 檢查是否存在
            user_info = allowlist.get_user_info(target_chat_id)
            if not user_info:
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            # 防止刪除自己
            if target_chat_id == admin_chat_id:
                return self._send_error(admin_chat_id, "⚠️ 無法移除自己")

            # 移除
            success = allowlist.remove_from_allowlist(target_chat_id)

            if success:
                username = user_info.get("username", "Unknown")
                message = f"✅ 已從允許名單移除\n\nID: `{target_chat_id}`\n用戶名: @{username}"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "移除失敗，請檢查日誌")

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin remove <chat_id>`")

    def _handle_list(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin list 指令"""
        users = allowlist.list_all_users(limit=100)

        if not users:
            return telegram_client.send_message(admin_chat_id, "📋 允許名單為空", parse_mode=None)

        # 格式化用戶列表
        lines = ["📋 允許名單\n"]

        for user in users:
            chat_id = user.get("chat_id", 0)
            username = user.get("username", "Unknown")
            enabled = user.get("enabled", False)
            role = user.get("role", "user")

            # 圖標
            chat_icon = "👥" if chat_id < 0 else "👤"
            status_icon = "✅" if enabled else "❌"
            role_icon = "👑" if role == "admin" else "👤"

            lines.append(f"{chat_icon} {status_icon} {role_icon} @{username}")
            lines.append(f"   ID: `{chat_id}` | 角色: {role}\n")

        lines.append(f"\n總計: {len(users)} 個用戶/群組")
        message = "\n".join(lines)

        return telegram_client.send_message(admin_chat_id, message, parse_mode=None)

    def _handle_info(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin info 指令"""
        try:
            target_chat_id = int(args.strip())

            user_info = allowlist.get_user_info(target_chat_id)
            if not user_info:
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            # 格式化用戶信息
            chat_type = "👥 群組" if target_chat_id < 0 else "👤 私聊"
            username = user_info.get("username", "Unknown")
            enabled = user_info.get("enabled", False)
            role = user_info.get("role", "user")

            status = "✅ 已啟用" if enabled else "❌ 已禁用"
            role_display = "👑 管理員" if role == "admin" else "👤 普通用戶"

            lines = [
                "ℹ️ 用戶詳細信息\n",
                f"類型: {chat_type}",
                f"ID: `{target_chat_id}`",
                f"用戶名: @{username}",
                f"狀態: {status}",
                f"角色: {role_display}",
            ]

            # 顯示額外信息
            if "added_at" in user_info:
                lines.append(f"加入時間: {user_info['added_at']}")
            if "added_by" in user_info:
                lines.append(f"添加者: {user_info['added_by']}")

            message = "\n".join(lines)
            return telegram_client.send_message(admin_chat_id, message, parse_mode=None)

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin info <chat_id>`")

    def _handle_enable(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin enable 指令"""
        try:
            target_chat_id = int(args.strip())

            # 檢查是否存在
            if not allowlist.get_user_info(target_chat_id):
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            success = allowlist.update_user_enabled(target_chat_id, True)

            if success:
                message = f"✅ 已啟用用戶\n\nID: `{target_chat_id}`"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "啟用失敗")

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin enable <chat_id>`")

    def _handle_disable(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin disable 指令"""
        try:
            target_chat_id = int(args.strip())

            # 防止禁用自己
            if target_chat_id == admin_chat_id:
                return self._send_error(admin_chat_id, "⚠️ 無法禁用自己")

            # 檢查是否存在
            if not allowlist.get_user_info(target_chat_id):
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            success = allowlist.update_user_enabled(target_chat_id, False)

            if success:
                message = f"✅ 已禁用用戶\n\nID: `{target_chat_id}`"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "禁用失敗")

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin disable <chat_id>`")

    def _handle_promote(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin promote 指令"""
        try:
            target_chat_id = int(args.strip())

            # 檢查是否存在
            user_info = allowlist.get_user_info(target_chat_id)
            if not user_info:
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            # 檢查是否已是管理員
            if user_info.get("role") == "admin":
                return self._send_error(admin_chat_id, "該用戶已經是管理員")

            success = allowlist.update_user_role(target_chat_id, "admin")

            if success:
                username = user_info.get("username", "Unknown")
                message = f"👑 已升級為管理員\n\nID: `{target_chat_id}`\n用戶名: @{username}"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "升級失敗")

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin promote <chat_id>`")

    def _handle_demote(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin demote 指令"""
        try:
            target_chat_id = int(args.strip())

            # 防止降級自己
            if target_chat_id == admin_chat_id:
                return self._send_error(admin_chat_id, "⚠️ 無法降級自己")

            # 檢查是否存在
            user_info = allowlist.get_user_info(target_chat_id)
            if not user_info:
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            # 檢查是否已是普通用戶
            if user_info.get("role") == "user":
                return self._send_error(admin_chat_id, "該用戶已經是普通用戶")

            success = allowlist.update_user_role(target_chat_id, "user")

            if success:
                username = user_info.get("username", "Unknown")
                message = f"👤 已降級為普通用戶\n\nID: `{target_chat_id}`\n用戶名: @{username}"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "降級失敗")

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin demote <chat_id>`")

    def _handle_grant_file(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin grant_file 指令"""
        try:
            target_chat_id = int(args.strip())

            # 檢查是否存在
            user_info = allowlist.get_user_info(target_chat_id)
            if not user_info:
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            # 檢查是否已有權限
            permissions = user_info.get("permissions", {})
            if permissions.get("file_reader", False):
                return self._send_error(admin_chat_id, "該用戶已有檔案讀取權限")

            success = allowlist.update_file_permission(target_chat_id, True)

            if success:
                username = user_info.get("username", "Unknown")
                chat_type = "👥 群組" if target_chat_id < 0 else "👤 用戶"
                message = f"📁 已授予檔案讀取權限\n\n{chat_type}\nID: `{target_chat_id}`\n用戶名: @{username}\n\n✅ 現在可以處理圖片、文件等附件"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "授予權限失敗")

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin grant_file <chat_id>`")

    def _handle_revoke_file(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin revoke_file 指令"""
        try:
            target_chat_id = int(args.strip())

            # 檢查是否存在
            user_info = allowlist.get_user_info(target_chat_id)
            if not user_info:
                return self._send_error(admin_chat_id, f"用戶 {target_chat_id} 不在名單中")

            # 檢查是否沒有權限
            permissions = user_info.get("permissions", {})
            if not permissions.get("file_reader", False):
                return self._send_error(admin_chat_id, "該用戶沒有檔案讀取權限")

            success = allowlist.update_file_permission(target_chat_id, False)

            if success:
                username = user_info.get("username", "Unknown")
                chat_type = "👥 群組" if target_chat_id < 0 else "👤 用戶"
                message = f"📁 已撤銷檔案讀取權限\n\n{chat_type}\nID: `{target_chat_id}`\n用戶名: @{username}\n\n⚠️ 將無法處理圖片、文件等附件"
                return telegram_client.send_message(admin_chat_id, message, parse_mode=None)
            else:
                return self._send_error(admin_chat_id, "撤銷權限失敗")

        except ValueError:
            return self._send_error(admin_chat_id, "用法：`/admin revoke_file <chat_id>`")

    def _handle_stats(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin stats 指令"""
        stats = allowlist.get_stats()

        if not stats:
            return self._send_error(admin_chat_id, "無法獲取統計信息")

        lines = [
            "📊 系統統計信息\n",
            f"總用戶數: {stats.get('total_users', 0)}",
            f"  ├─ 👤 私聊: {stats.get('private_count', 0)}",
            f"  └─ 👥 群組: {stats.get('group_count', 0)}\n",
            "啟用狀態:",
            f"  ├─ ✅ 已啟用: {stats.get('enabled_users', 0)}",
            f"  └─ ❌ 已禁用: {stats.get('disabled_users', 0)}\n",
            "權限分布:",
            f"  ├─ 👑 管理員: {stats.get('admin_count', 0)}",
            f"  └─ 👤 普通用戶: {stats.get('user_count', 0)}",
        ]

        message = "\n".join(lines)
        return telegram_client.send_message(admin_chat_id, message, parse_mode=None)

    def _handle_broadcast(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin broadcast 指令"""
        if not args.strip():
            return self._send_error(admin_chat_id, "用法：`/admin broadcast <message>`")

        # 獲取所有啟用的用戶
        all_users = allowlist.list_all_users(limit=1000)
        enabled_users = [u for u in all_users if u.get("enabled", False)]

        if not enabled_users:
            return self._send_error(admin_chat_id, "沒有啟用的用戶")

        # 發送確認
        confirm_msg = f"📢 準備廣播給 {len(enabled_users)} 個用戶/群組\n\n預覽：\n{args[:100]}...\n\n發送中..."
        telegram_client.send_message(admin_chat_id, confirm_msg, parse_mode=None)

        # 廣播消息
        success_count = 0
        fail_count = 0

        broadcast_message = f"📢 系統廣播\n\n{args}"

        for user in enabled_users:
            target_chat_id = user.get("chat_id")
            if target_chat_id and target_chat_id != admin_chat_id:
                if telegram_client.send_message(target_chat_id, broadcast_message, parse_mode=None):
                    success_count += 1
                else:
                    fail_count += 1

        # 發送結果
        result_msg = (
            f"✅ 廣播完成\n\n成功: {success_count}\n失敗: {fail_count}\n總計: {len(enabled_users)}"
        )
        return telegram_client.send_message(admin_chat_id, result_msg, parse_mode=None)

    def _handle_help(self, admin_chat_id: int, args: str) -> bool:
        """處理 /admin help 或顯示幫助"""
        help_text = """🔧 管理員指令幫助

**用戶管理：**
/admin add <chat_id> [username]
  添加用戶/群組到允許名單

/admin remove <chat_id>
  移除用戶/群組

/admin list
  列出所有用戶/群組

/admin info <chat_id>
  查看用戶詳細信息

**狀態控制：**
/admin enable <chat_id>
  啟用用戶（軟啟用）

/admin disable <chat_id>
  禁用用戶（軟刪除）

**權限管理：**
/admin promote <chat_id>
  升級為管理員

/admin demote <chat_id>
  降級為普通用戶

/admin grant_file <chat_id>
  授予檔案讀取權限（圖片、文件等）

/admin revoke_file <chat_id>
  撤銷檔案讀取權限

**系統管理：**
/admin stats
  查看系統統計信息

/admin broadcast <message>
  廣播消息給所有用戶

**說明：**
• chat_id 為正數：私聊 👤
• chat_id 為負數：群組 👥
• 所有操作需要管理員權限 👑
• 檔案權限控制圖片/文件處理功能"""

        return telegram_client.send_message(admin_chat_id, help_text, parse_mode=None)

    def _send_error(self, chat_id: int, error_message: str) -> bool:
        """發送錯誤消息"""
        message = f"❌ {error_message}"
        return telegram_client.send_message(chat_id, message, parse_mode=None)

    def get_command_name(self) -> str:
        """取得指令名稱"""
        return "AdminCommand"

    def get_description(self) -> str:
        """取得指令描述"""
        return "管理員指令（用戶管理、權限控制、系統統計）"
