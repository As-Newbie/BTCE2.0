import asyncio
import json
import time  
import os
from pathlib import Path
from playwright.async_api import async_playwright

from config import (
    DYNAMIC_URLS, CHECK_INTERVAL, COOKIE_FILE, HISTORY_FILE,
    MAIL_SAVE_DIR, UP_NAME, BROWSER_CONFIG, BROWSER_RESTART_INTERVAL,
    HEALTH_CHECK_INTERVAL, TASK_TIMEOUT
)
from render_comment import CommentRenderer
from email_utils import send_email
from config_email import TO_EMAILS
from health_check import HealthChecker
from logger_config import logger
from retry_decorator import BROWSER_RETRY_CONFIG, async_retry
from performance_monitor import performance_monitor
from task_executor import TaskExecutor


class Monitor:
    def __init__(self):
        self.check_interval = CHECK_INTERVAL
        self.cookie_file = COOKIE_FILE
        self.history_file = HISTORY_FILE
        self.mail_save_dir = MAIL_SAVE_DIR

        self.comment_renderer = CommentRenderer()
        self.health_checker = HealthChecker()
        self.task_executor = TaskExecutor()

        self.loop_count = 0
        self.is_running = True

        # 初始化历史记录
        if os.path.exists(self.history_file):
            self.history_data = json.loads(Path(self.history_file).read_text(encoding="utf-8"))
        else:
            self.history_data = {}

    @async_retry(BROWSER_RETRY_CONFIG)
    async def initialize_browser(self):
        """安全地初始化浏览器"""
        logger.info("🔄 初始化浏览器...")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(**BROWSER_CONFIG)
        self.context = await self.browser.new_context()

        # 检查cookie文件
        if not self.cookie_file.exists():
            logger.error("❌ Cookie文件不存在，请先运行获取cookie脚本")
            raise FileNotFoundError("Cookie文件不存在")

        # 加载cookies
        cookies = json.loads(self.cookie_file.read_text(encoding="utf-8"))
        await self.context.add_cookies(cookies)

        self.page = await self.context.new_page()

        # 设置页面默认超时
        self.page.set_default_timeout(15000)

        # 健康检查
        if not await self.health_checker.comprehensive_check(self.page):
            logger.error("❌ 浏览器健康检查失败")
            raise Exception("浏览器健康检查失败")

        logger.info("✅ 浏览器初始化完成")

    async def safe_close_browser(self):
        """安全关闭浏览器"""
        try:
            if hasattr(self, 'page') and self.page:
                await self.page.close()
            if hasattr(self, 'context') and self.context:
                await self.context.close()
            if hasattr(self, 'browser') and self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright') and self.playwright:
                await self.playwright.stop()

            logger.info("✅ 浏览器资源已清理")
        except Exception as e:
            logger.error(f"❌ 关闭浏览器时出错: {e}")

    async def restart_browser_if_needed(self):
        """根据需要重启浏览器"""
        self.loop_count += 1

        # 定期重启浏览器
        if self.loop_count % BROWSER_RESTART_INTERVAL == 0:
            logger.info("🔄 执行定期浏览器重启...")
            await self.safe_close_browser()
            await asyncio.sleep(2)  # 等待资源释放
            await self.initialize_browser()
            return True

        # 定期健康检查
        if self.loop_count % HEALTH_CHECK_INTERVAL == 0:
            logger.info("🔍 执行定期健康检查...")
            if not await self.health_checker.comprehensive_check(self.page):
                logger.warning("⚠️ 健康检查失败，尝试重启浏览器...")
                await self.safe_close_browser()
                await asyncio.sleep(2)
                await self.initialize_browser()
                return True

        return False

    async def check_dynamic_changes(self, dynamic_id):
        """检查单个动态的变化"""
        try:
            # 直接调用方法，而不是通过任务执行器
            current_comment_html, current_comment_images = await self.comment_renderer.get_pinned_comment(
                self.page, dynamic_id
            )

            if current_comment_html is None:
                logger.warning(f"⚠️ 动态 {dynamic_id} 未找到置顶评论")
                return

            # 获取历史记录
            last_record = self.history_data.get(dynamic_id, {"html": "", "images": []})
            if isinstance(last_record, str):
                last_record = {"html": last_record, "images": []}

            last_comment_html = last_record.get("html", "")
            last_comment_images = last_record.get("images", [])

            # 检测变化
            if await self.comment_renderer.detect_comment_change(
                    current_comment_html, current_comment_images,
                    last_comment_html, last_comment_images
            ):
                await self._send_notification(
                    dynamic_id, current_comment_html, current_comment_images,
                    last_comment_html, last_comment_images
                )

            # 更新历史记录
            self.history_data[dynamic_id] = {
                "html": current_comment_html,
                "images": current_comment_images
            }

            self.health_checker.increment_success()

        except Exception as e:
            logger.error(f"❌ 检查动态 {dynamic_id} 时出错: {e}")
            self.health_checker.increment_failure()

    async def _send_notification(self, dynamic_id, current_html, current_images, last_html, last_images):
        """发送通知邮件"""
        try:
            # 生成时间字符串
            current_time = time.strftime('%Y-%m-%d %H:%M:%S')

            email_body = self.comment_renderer.render_email_content(
                dynamic_id, current_html, current_images, last_html, last_images, current_time
            )

            # 保存HTML文件
            timestamp = time.strftime("%Y%m%d%H%M%S")
            file_name = f"{UP_NAME}-{timestamp}.html"
            file_path = os.path.join(self.mail_save_dir, file_name)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(email_body)
            logger.info(f"✅ 邮件内容已保存: {file_path}")

            # 发送邮件
            success = await asyncio.to_thread(
                send_email,
                subject=f"【{UP_NAME}动态监控】置顶评论已更新",
                content=email_body,
            )

            if success:
                logger.info("✅ 邮件发送成功")
            else:
                logger.error("❌ 邮件发送失败")

        except Exception as e:
            logger.error(f"❌ 发送通知时出错: {e}")

    def _save_history(self):
        """保存历史记录到文件"""
        try:
            Path(self.history_file).write_text(
                json.dumps(self.history_data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"❌ 保存历史记录失败: {e}")

    async def run_monitoring_cycle(self):
        """执行一次完整的监控循环"""
        logger.info(f"🔍 第 {self.loop_count} 轮检查开始")

        # 检查是否需要重启浏览器
        await self.restart_browser_if_needed()

        # 记录内存使用
        await performance_monitor.record_memory_usage()

        # 并行检查所有动态
        tasks = [
            self.check_dynamic_changes(url.split("/")[-1])
            for url in DYNAMIC_URLS
        ]

        # 使用安全的任务执行器
        await asyncio.gather(*tasks, return_exceptions=True)

        # 保存历史记录
        self._save_history()

        # 记录统计信息
        stats = self.health_checker.get_stats()
        logger.info(f"📊 本轮检查完成 - {stats}")

    async def run(self):
        """运行监控主循环"""
        logger.info(f"=== {UP_NAME} 动态置顶评论监控启动 ===")
        logger.info(f"监控邮箱：{', '.join(TO_EMAILS)}")
        logger.info(f"检查间隔：{self.check_interval} 秒")

        logger.info("监控动态列表：")
        for url in DYNAMIC_URLS:
            logger.info(f" - {url}")

        try:
            await self.initialize_browser()

            # 启动性能监控报告
            perf_task = asyncio.create_task(
                performance_monitor.periodic_report(interval_minutes=60)
            )

            while self.is_running:
                try:
                    await self.run_monitoring_cycle()

                    next_check = time.strftime(
                        "%H:%M:%S", time.localtime(time.time() + self.check_interval)
                    )
                    logger.info(f"⏰ 下次检查时间: {next_check}")
                    await asyncio.sleep(self.check_interval)

                except KeyboardInterrupt:
                    logger.info("⛔ 收到中断信号，准备退出...")
                    break
                except Exception as e:
                    logger.error(f"❌ 监控循环出错: {e}")
                    logger.info("🔄 5秒后重试...")
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"❌ 监控程序严重错误: {e}")
        finally:
            self.is_running = False
            if 'perf_task' in locals():
                perf_task.cancel()
            await self.safe_close_browser()

            logger.info("✅ 监控程序已安全退出")
