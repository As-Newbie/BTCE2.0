#!/usr/bin/env python3
import asyncio
import signal
import sys
from monitor import Monitor
from logger_config import setup_logging


class Application:
    """应用程序管理器"""

    def __init__(self):
        self.monitor = None
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
        sys.exit(0)

    async def run(self):
        """运行应用程序"""
        setup_logging()

        try:
            self.monitor = Monitor()
            await self.monitor.run()
        except Exception as e:
            print(f"❌ 应用程序错误: {e}")
            sys.exit(1)


if __name__ == "__main__":
    app = Application()
    asyncio.run(app.run())