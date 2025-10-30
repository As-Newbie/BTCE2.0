#!/usr/bin/env python3
# main.py
import asyncio
import signal
import sys
from monitor import Monitor
from status_monitor import status_monitor  # 导入状态监控器
from logger_config import setup_logging


class Application:
    """应用程序管理器"""

    def __init__(self):
        self.monitor = None
        self.status_check_task = None
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """信号处理函数"""
        print(f"\n📡 收到信号 {signum}，正在优雅退出...")
        if self.monitor:
            self.monitor.is_running = False
        if self.status_check_task:
            self.status_check_task.cancel()
        sys.exit(0)

    async def periodic_status_check(self):
        """定期状态检查任务"""
        try:
            while True:
                # 每小时检查一次状态
                await asyncio.sleep(3600)  # 1小时

                # 检查是否需要发送无更新提醒
                await status_monitor.check_no_update_alert()

                # 记录状态信息
                status_info = status_monitor.get_status_info()
                print(f"📈 状态监控: {status_info}")

        except asyncio.CancelledError:
            print("⏹️ 状态监控任务已取消")
        except Exception as e:
            print(f"❌ 状态监控任务异常: {e}")

    async def run(self):
        """运行应用程序"""
        setup_logging()

        try:
            # 启动状态监控任务
            self.status_check_task = asyncio.create_task(self.periodic_status_check())

            # 启动主监控
            self.monitor = Monitor()

            # 将状态监控器传递给Monitor实例
            self.monitor.status_monitor = status_monitor

            await self.monitor.run()

        except Exception as e:
            print(f"❌ 应用程序错误: {e}")
            sys.exit(1)
        finally:
            # 确保状态监控任务被取消
            if self.status_check_task and not self.status_check_task.done():
                self.status_check_task.cancel()
                try:
                    await self.status_check_task
                except asyncio.CancelledError:
                    pass


if __name__ == "__main__":
    app = Application()
    asyncio.run(app.run())
