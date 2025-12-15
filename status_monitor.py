# status_monitor.py
import asyncio
import json
import time
# import os
from datetime import datetime,  timedelta
from pathlib import Path
from logger_config import logger
from email_utils import send_email
from config_email import STATUS_MONITOR_EMAILS  # 导入管理员邮箱
from config import UP_NAME, STATUS_MONITOR_INTERVAL, NO_UPDATE_ALERT_HOURS


class StatusMonitor:
    """状态监控器：检测长时间无更新情况"""

    def __init__(self):
        self.status_file = Path("monitor_status.json")
        self.no_update_alert_hours = NO_UPDATE_ALERT_HOURS
        self.monitor_interval = STATUS_MONITOR_INTERVAL

        # 加载状态数据
        self.status_data = self._load_status()

    def _load_status(self):
        """加载监控状态"""
        current_time = time.time()
        default_status = {
            "last_change_time": current_time,  # 使用当前时间
            "last_alert_time": current_time,  # 使用当前时间而不是0
            "total_changes": 0,
            "start_time": current_time
        }

        if self.status_file.exists():
            try:
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    # 确保所有必需的字段都存在
                    for key in default_status:
                        if key not in loaded_data:
                            loaded_data[key] = default_status[key]
                    return loaded_data
            except Exception as e:
                logger.error(f"❌❌ 加载状态文件失败: {e}")
                return default_status
        return default_status

    def _save_status(self):
        """保存监控状态"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"❌❌ 保存状态文件失败: {e}")

    def record_change(self):
        """记录检测到变化"""
        self.status_data["last_change_time"] = time.time()
        self.status_data["total_changes"] += 1
        self._save_status()
        logger.info("✅ 已记录变化时间戳")

    async def check_no_update_alert(self):
        """检查是否需要发送无更新提醒"""
        current_time = time.time()
        last_change_time = self.status_data["last_change_time"]
        last_alert_time = self.status_data["last_alert_time"]

        # 计算无更新时长（小时）
        hours_without_update = (current_time - last_change_time) / 3600

        # 如果超过设定小时且距离上次提醒也超过设定小时
        if (hours_without_update >= self.no_update_alert_hours and
                (current_time - last_alert_time) >= self.no_update_alert_hours * 3600):

            logger.warning(f"⚠️ 已 {hours_without_update:.1f} 小时未检测到更新，发送提醒邮件")

            # 发送提醒邮件
            success = await self._send_no_update_alert(hours_without_update)

            if success:
                self.status_data["last_alert_time"] = current_time
                self._save_status()
                return True

        return False

    async def _send_no_update_alert(self, hours_without_update):
        """发送无更新提醒邮件到管理员邮箱"""
        try:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            hours_int = int(hours_without_update)

            subject = f"【{UP_NAME}监控提醒】长时间未检测到置顶评论更新"

            content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>监控提醒</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .alert {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; }}
                    .info {{ background-color: #d1ecf1; border: 1px solid #bee5eb; padding: 10px; margin-top: 10px; border-radius: 5px; }}
                </style>
            </head>
            <body>
                <div class="alert">
                    <h2>⚠️ 监控系统提醒</h2>
                    <p>检测到监控系统已 <strong>{hours_int} 小时</strong> 未发现动态置顶评论更新。</p>
                    <p>这可能意味着：</p>
                    <ul>
                        <li>UP主长时间未更新动态</li>
                        <li>动态链接可能已失效或需要更新</li>
                        <li>监控系统可能出现异常</li>
                    </ul>
                </div>

                <div class="info">
                    <h3>📊📊 监控统计信息</h3>
                    <p>• 最后检测到更新时间: {datetime.fromtimestamp(self.status_data['last_change_time']).strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>• 总检测到变化次数: {self.status_data['total_changes']}</p>
                    <p>• 监控运行时长: {self._format_runtime()}</p>
                    <p>• 当前系统时间: {current_time}</p>
                </div>

                <div class="info">
                    <h3>🔍🔍 建议检查项</h3>
                    <ol>
                        <li>确认动态链接是否仍然有效</li>
                        <li>检查UP主是否有新动态发布</li>
                        <li>验证监控系统是否正常运行</li>
                        <li>如有必要，更新监控配置中的动态链接</li>
                    </ol>
                </div>
            </body>
            </html>
            """

            success = await asyncio.to_thread(
                send_email,
                subject=subject,
                content=content,
                to_emails=STATUS_MONITOR_EMAILS  # 发送到管理员邮箱
            )

            if success:
                logger.info("✅ 无更新提醒邮件发送成功（管理员邮箱）")
            else:
                logger.error("❌❌ 无更新提醒邮件发送失败")

            return success

        except Exception as e:
            logger.error(f"❌❌ 发送无更新提醒失败: {e}")
            return False

    def _format_runtime(self):
        """格式化运行时间"""
        runtime_seconds = time.time() - self.status_data["start_time"]
        days = int(runtime_seconds // 86400)
        hours = int((runtime_seconds % 86400) // 3600)
        return f"{days}天{hours}小时"

    def get_status_info(self):
        """获取状态信息"""
        current_time = time.time()
        hours_without_update = (current_time - self.status_data["last_change_time"]) / 3600
        hours_since_last_alert = (current_time - self.status_data["last_alert_time"]) / 3600

        # 格式化提醒时间显示
        if self.status_data["last_alert_time"] == self.status_data["start_time"]:
            alert_display = "从未提醒"
        else:
            alert_display = f"{hours_since_last_alert:.1f}小时前"

        return {
            "最后更新": datetime.fromtimestamp(self.status_data["last_change_time"]).strftime('%Y-%m-%d %H:%M:%S'),
            "无更新时长": f"{hours_without_update:.1f}小时",
            "总变化次数": self.status_data["total_changes"],
            "累计运行时长": self._format_runtime()
        }


# 全局实例
status_monitor = StatusMonitor()
