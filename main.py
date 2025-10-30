# monitor
import asyncio
import json
import time
import os
import re
from pathlib import Path
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from config import (
    DYNAMIC_URLS, CHECK_INTERVAL, COOKIE_FILE, HISTORY_FILE,
    MAIL_SAVE_DIR, UP_NAME, BROWSER_CONFIG, BROWSER_RESTART_INTERVAL,
    HEALTH_CHECK_INTERVAL
)
from render_comment import CommentRenderer
from email_utils import send_email
from config_email import TO_EMAILS
from health_check import HealthChecker
from logger_config import logger
from retry_decorator import BROWSER_RETRY_CONFIG, async_retry
from performance_monitor import performance_monitor


class Monitor:
    """动态置顶评论监控类"""

    def __init__(self):
        self.check_interval = CHECK_INTERVAL
        self.cookie_file = COOKIE_FILE
        self.history_file = HISTORY_FILE
        self.mail_save_dir = MAIL_SAVE_DIR
        self.status_monitor = None  # 状态监控器实例
        self.comment_renderer = CommentRenderer()
        self.health_checker = HealthChecker()

        self.loop_count = 0
        self.is_running = True

        if os.path.exists(self.history_file):
            self.history_data = json.loads(Path(self.history_file).read_text(encoding="utf-8"))
        else:
            self.history_data = {}

        self.playwright = None
        self.browser = None
        self.context = None

    @async_retry(BROWSER_RETRY_CONFIG)
    async def initialize_browser(self):
        """初始化浏览器及上下文"""
        logger.info("🔄 初始化浏览器...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(**BROWSER_CONFIG)
        self.context = await self.browser.new_context()

        if not self.cookie_file.exists():
            raise FileNotFoundError("Cookie 文件不存在，请先运行获取cookie脚本")

        cookies = json.loads(self.cookie_file.read_text(encoding="utf-8"))
        await self.context.add_cookies(cookies)

        logger.info("✅ 浏览器初始化完成")

    async def safe_close_browser(self):
        """安全关闭浏览器及上下文"""
        try:
            if self.context:
                await self.context.close()
                self.context = None
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            logger.info("✅ 浏览器资源已释放")
        except Exception as e:
            logger.error(f"❌ 关闭浏览器失败: {e}")

    async def restart_browser_if_needed(self):
        """根据轮次定期重启浏览器或执行健康检查"""
        self.loop_count += 1
        restart_needed = False

        if self.loop_count % BROWSER_RESTART_INTERVAL == 0:
            logger.info("♻️ 达到重启阈值，执行浏览器重启")
            restart_needed = True
        elif self.loop_count % HEALTH_CHECK_INTERVAL == 0:
            logger.info("🔍 执行健康检查...")
            if self.context and self.browser and not await self.health_checker.comprehensive_check(await self.context.new_page()):
                logger.warning("⚠️ 健康检查失败，准备重启浏览器")
                restart_needed = True

        if restart_needed:
            await self.safe_close_browser()
            await asyncio.sleep(2)
            await self.initialize_browser()
            return True

        return False

    # ------------------ 辅助函数：去除表情 ------------------
    def _clean_html_emojis(self, html_text: str) -> str:
        """去除 HTML 中表情图片，保留文字"""
        if not html_text:
            return ""
        cleaned = re.sub(r'<img[^>]+class="[^"]*emoji[^"]*"[^>]*>', '', html_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'<img[^>]+alt="[^"]*"[^>]*>', '', cleaned, flags=re.IGNORECASE)
        return cleaned

    async def check_dynamic_changes(self, dynamic_id):
        """检查单个动态置顶评论变化（文字为主）"""
        try:
            if not self.context:
                logger.warning("⚠️ 浏览器上下文不存在，跳过本次检查")
                return

            page = await self.context.new_page()
            try:
                current_html, current_images = await asyncio.wait_for(
                    self.comment_renderer.get_pinned_comment(page, dynamic_id),
                    timeout=20
                )
            except (asyncio.TimeoutError, PlaywrightTimeoutError):
                logger.error(f"⏰ 动态 {dynamic_id} 获取置顶评论超时")
                await page.close()
                return

            await page.close()

            if not current_html or "未找到置顶评论" in current_html:
                logger.warning(f"⚠️ 动态 {dynamic_id} 未找到置顶评论")
                return

            last_record = self.history_data.get(dynamic_id, {"html": "", "images": []})
            last_html = last_record.get("html", "")
            last_images = last_record.get("images", [])

            current_html_cleaned = self._clean_html_emojis(current_html)
            last_html_cleaned = self._clean_html_emojis(last_html)

            current_text = self.comment_renderer.extract_text_from_html(current_html_cleaned)
            last_text = self.comment_renderer.extract_text_from_html(last_html_cleaned)

            logger.info(f"📝 当前文本: {current_text}")
            logger.info(f"📜 上次文本: {last_text if last_text else '无'}")

            # 仅文字变化触发通知
            if last_text and current_text != last_text:
                logger.info(f"🔔 动态 {dynamic_id} 置顶评论文字变化")
                await self._send_notification(dynamic_id, current_html, current_images, last_html, last_images)
                # 记录变化到状态监控器
                if self.status_monitor:
                    self.status_monitor.record_change()

            # 更新历史记录
            self.history_data[dynamic_id] = {"html": current_html, "images": current_images}
            self.health_checker.increment_success()

        except Exception as e:
            logger.error(f"❌ 检查动态 {dynamic_id} 出错: {e}")
            self.health_checker.increment_failure()

    async def _send_notification(self, dynamic_id, current_html, current_images, last_html, last_images):
        """发送邮件通知"""
        try:
            current_time = time.strftime("%Y-%m-%d %H:%M:%S")
            email_body = self.comment_renderer.render_email_content(
                dynamic_id, current_html, current_images, last_html, last_images, current_time
            )

            timestamp = time.strftime("%Y%m%d%H%M%S")
            file_name = f"{UP_NAME}-{timestamp}.html"
            file_path = os.path.join(self.mail_save_dir, file_name)
            Path(self.mail_save_dir).mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(email_body)
            logger.info(f"✅ 邮件内容已保存: {file_path}")

            success = await asyncio.to_thread(
                send_email,
                subject=f"【{UP_NAME}动态监控】置顶评论已更新",
                content=email_body
            )
            if success:
                logger.info("✅ 邮件发送成功")
            else:
                logger.error("❌ 邮件发送失败")

        except Exception as e:
            logger.error(f"❌ 发送通知出错: {e}")

    def _save_history(self):
        """保存历史记录到文件"""
        try:
            Path(self.history_file).write_text(
                json.dumps(self.history_data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"❌ 保存历史记录失败: {e}")

    async def run_monitoring_cycle(self):
        """执行一次完整监控循环"""
        # 这里修改了
        logger.info(f"🔍 第 {self.loop_count+1} 轮检查开始")
        self.health_checker.last_health_check = time.time()

        await self.restart_browser_if_needed()
        await performance_monitor.record_memory_usage()

        tasks = [self.check_dynamic_changes(url.split("/")[-1]) for url in DYNAMIC_URLS]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._save_history()
        # 将 loop_count 作为参数传入
        stats = self.health_checker.get_stats(total_loops=self.loop_count)
        logger.info(f"📊 本轮检查完成 - {stats}")
        # 记录状态信息到日志
        if self.status_monitor:
            status_info = self.status_monitor.get_status_info()
            logger.info(f"📈 状态监控: {status_info}")

    async def run(self):
        """运行监控主循环"""
        logger.info(f"=== {UP_NAME} 动态置顶评论监控启动 ===")
        logger.info(f"监控邮箱：{', '.join(TO_EMAILS)}")
        logger.info(f"检查间隔：{self.check_interval} 秒")
        for url in DYNAMIC_URLS:
            logger.info(f" - {url}")

        try:
            await self.initialize_browser()
            perf_task = asyncio.create_task(performance_monitor.periodic_report(interval_minutes=60))

            while self.is_running:
                try:
                    await self.run_monitoring_cycle()
                    next_check = time.strftime("%H:%M:%S", time.localtime(time.time() + self.check_interval))
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


# -------------------- 程序入口 --------------------
if __name__ == "__main__":
    monitor = Monitor()
    asyncio.run(monitor.run())
