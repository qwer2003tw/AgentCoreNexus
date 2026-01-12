"""
Updated Info Handler - 顯示所有 3 個 stacks 的資訊

整合說明：
將此代碼合併到 telegram-lambda/src/commands/handlers/info_handler.py
"""


def _get_deployment_info(self) -> str:
    """
    取得所有 stacks 的部署資訊

    Returns:
        格式化的部署資訊文字
    """
    stack_names = {
        "telegram-lambda-receiver": "【接收層】Telegram",
        "telegram-unified-bot": "【處理層】AI Processor",
        "agentcore-web-channel": "【Web 層】Web Channel",
    }

    info_lines = ["📊 AgentCoreNexus 系統資訊", ""]

    latest_time = None
    all_healthy = True

    for stack_name, display_name in stack_names.items():
        try:
            response = self.cfn_client.describe_stacks(StackName=stack_name)

            if not response.get("Stacks"):
                info_lines.append(f"{display_name}")
                info_lines.append("  ⚠️  Stack 不存在")
                info_lines.append("")
                all_healthy = False
                continue

            stack = response["Stacks"][0]
            last_updated = stack.get("LastUpdatedTime") or stack.get("CreationTime")
            stack_status = stack.get("StackStatus", "UNKNOWN")

            # 格式化時間
            if last_updated:
                time_str = last_updated.strftime("%Y-%m-%d %H:%M UTC")

                # 追蹤最新時間
                if not latest_time or last_updated > latest_time:
                    latest_time = last_updated
            else:
                time_str = "Unknown"

            # 狀態 emoji
            if "COMPLETE" in stack_status:
                status_emoji = "✅"
            elif "IN_PROGRESS" in stack_status:
                status_emoji = "🔄"
            elif "FAILED" in stack_status or "ROLLBACK" in stack_status:
                status_emoji = "❌"
                all_healthy = False
            else:
                status_emoji = "⚠️"
                all_healthy = False

            # 添加 stack 資訊
            info_lines.append(f"{display_name}")
            info_lines.append(f"  🚀 更新：{time_str}")
            info_lines.append(f"  {status_emoji} 狀態：{stack_status}")

            # 特殊處理：Web stack 顯示前端 URL
            if stack_name == "agentcore-web-channel":
                outputs = stack.get("Outputs", [])
                frontend_url = next(
                    (o["OutputValue"] for o in outputs if o["OutputKey"] == "FrontendUrl"), None
                )
                if frontend_url:
                    info_lines.append(f"  🌐 前端：{frontend_url}")

            info_lines.append("")

        except self.cfn_client.exceptions.ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")

            if error_code == "ValidationError":
                # Stack 不存在
                info_lines.append(f"{display_name}")
                info_lines.append("  ⚠️  Stack 未部署")
                info_lines.append("")
                all_healthy = False
            else:
                logger.error(f"Error querying {stack_name}: {error_code}")
                info_lines.append(f"{display_name}")
                info_lines.append(f"  ❌ 查詢錯誤：{error_code}")
                info_lines.append("")
                all_healthy = False

        except Exception as e:
            logger.error(f"Unexpected error querying {stack_name}: {str(e)}")
            info_lines.append(f"{display_name}")
            info_lines.append("  ❌ 未知錯誤")
            info_lines.append("")
            all_healthy = False

    # 添加總結
    info_lines.append("━━━━━━━━━━━━━━━━━━━")
    info_lines.append(f"🌍 Region：{self.region}")

    if latest_time:
        latest_str = latest_time.strftime("%Y-%m-%d %H:%M UTC")
        info_lines.append(f"📅 最後更新：{latest_str}")

    if all_healthy:
        info_lines.append("✅ 系統運作正常")
    else:
        info_lines.append("⚠️  部分組件異常")

    return "\n".join(info_lines)
