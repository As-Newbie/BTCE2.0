# monitor.py
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
    HEALTH_CHECK_INTERVAL,
    P1_CONTINUOUS_FAILURE, P2_SUCCESS_RATE_THRESHOLD,
    PERFORMANCE_REPORT_CYCLE_INTERVAL, P2_WINDOW_CYCLES, P2_DURATION_CYCLES
)
from render_comment import CommentRenderer
from email_utils import send_email
from config_email import TO_EMAILS, STATUS_MONITOR_EMAILS, EMAIL_USER
from health_check import HealthChecker
from logger_config import logger
from retry_decorator import BROWSER_RETRY_CONFIG, async_retry
from performance_monitor import performance_monitor
from qq_utils import send_qq_message
from config_qq import QQ_GROUP_IDS


class Monitor:
    """动态置顶评论监控类"""

    def __init__(self):
        self.check_interval = CHECK_INTERVAL
        self.cookie_file = COOKIE_FILE
        self.history_file = HISTORY_FILE
        self.mail_save_dir = MAIL_SAVE_DIR
        self.status_monitor = None
        self.comment_renderer = CommentRenderer()
        self.health_checker = HealthChecker()

        self.loop_count = 0
        self.is_running = True

        # 修改：按照UP_NAME存储历史记录，而不是动态ID
        if os.path.exists(self.history_file):
            self.history_data = json.loads(Path(self.history_file).read_text(encoding="utf-8"))
            # 兼容旧格式：如果存在动态ID格式的数据，转换为UP_NAME格式
            self._migrate_old_history_format()
        else:
            self.history_data = {}

        self.playwright = None
        self.browser = None
        self.context = None

    def _migrate_old_history_format(self):
        """迁移旧的历史记录格式（动态ID为键 -> UP_NAME为键）"""
        # 检查是否包含动态ID格式的键（长的数字字符串）
        dynamic_id_keys = [key for key in self.history_data.keys() if key.isdigit() and len(key) > 10]

        if dynamic_id_keys and UP_NAME not in self.history_data:
            # 使用第一个动态ID的数据作为初始UP_NAME数据
            first_dynamic_id = dynamic_id_keys[0]
            self.history_data[UP_NAME] = self.history_data[first_dynamic_id]
            logger.info(f"✅ 已迁移历史记录格式: {first_dynamic_id} -> {UP_NAME}")

            # 清理旧的动态ID数据
            for dynamic_id in dynamic_id_keys:
                if dynamic_id in self.history_data:
                    del self.history_data[dynamic_id]

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
            if self.context and self.browser and not await self.health_checker.comprehensive_check(
                    await self.context.new_page()):
                logger.warning("⚠️ 健康检查失败，准备重启浏览器")
                restart_needed = True

        if restart_needed:
            await self.safe_close_browser()
            await asyncio.sleep(2)
            await self.initialize_browser()
            return True

        return False


    def _clean_html_emojis(self, html_text: str) -> str:
        """
        将 HTML 中的表情图片替换为 alt 属性中的文本，而不是直接删除。
        例如：<img alt="[doge]" ...> 会被替换为文本 [doge]
        """
        if not html_text:
            return ""

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_text, 'html.parser')

            # 查找所有的图片标签
            for img in soup.find_all('img'):
                alt_text = img.get('alt', '')  # 获取alt属性
                if alt_text:
                    # 用方括号包裹alt文本，如[doge]，替换掉原图片标签
                    img.replace_with(f"{alt_text}")
                else:
                    # 如果没有alt文本，统一用[表情]代替，避免空标签
                    img.replace_with("[表情]")

            # 返回处理后的HTML字符串
            return str(soup)
        except Exception as e:
            logger.error(f"❌ 使用BeautifulSoup处理表情时失败，将回退至正则表达式清理: {e}")
            # 如果BeautifulSoup处理失败，则回退到原来的正则表达式清理逻辑（作为保底）
            cleaned = re.sub(r'<img[^>]*class="[^"]*emoji[^"]*"[^>]*>', '', html_text, flags=re.IGNORECASE)
            cleaned = re.sub(r'<img[^>]*alt="[^"]*"[^>]*>', '', cleaned, flags=re.IGNORECASE)
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

            # 修改：使用UP_NAME作为键，而不是dynamic_id
            last_record = self.history_data.get(UP_NAME, {"html": "", "images": []})
            last_html = last_record.get("html", "")
            last_images = last_record.get("images", [])

            current_html_cleaned = self._clean_html_emojis(current_html)
            last_html_cleaned = self._clean_html_emojis(last_html)

            current_text = self.comment_renderer.extract_text_from_html(current_html_cleaned)
            last_text = self.comment_renderer.extract_text_from_html(last_html_cleaned)

            logger.info(f"📝 当前文本: {current_text}")
            logger.info(f"📜 上次文本: {last_text if last_text else '无'}")

            # 仅文字变化触发通知
            if not last_text or current_text != last_text:
                logger.info(f"🔔 动态 {dynamic_id} 置顶评论文字变化")
                await self._send_notification(dynamic_id, current_html, current_images, last_html, last_images)
                # 记录变化到状态监控器
                if self.status_monitor:
                    self.status_monitor.record_change()

            # 修改：使用UP_NAME更新历史记录
            self.history_data[UP_NAME] = {"html": current_html, "images": current_images}
            self.health_checker.increment_success()

        except Exception as e:
            logger.error(f"❌ 检查动态 {dynamic_id} 出错: {e}")
            self.health_checker.increment_failure()

    async def _send_notification(self, dynamic_id, current_html, current_images, last_html, last_images):
        """发送邮件和QQ通知"""
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

            # 发送邮件
            email_success = await asyncio.to_thread(
                send_email,
                subject=f"【{UP_NAME}动态监控】瞳瞳空间更新啦",
                content=email_body
            )
            if email_success:
                logger.info("✅ 邮件发送成功")
            else:
                logger.error("❌❌ 邮件发送失败")

            # 修改：传入 current_images 参数
            qq_message = self.comment_renderer.generate_qq_message(
                UP_NAME, dynamic_id, current_html, current_time, current_images  # 添加 current_images
            )
            qq_results = await send_qq_message(qq_message)

            qq_success_count = sum(1 for r in qq_results if r is True)
            if qq_results:
                logger.info(f"✅ QQ消息发送结果: {qq_success_count}/{len(qq_results)} 成功")

        except Exception as e:
            logger.error(f"❌❌ 发送通知出错: {e}")

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
        logger.info(f"🔍 第 {self.loop_count + 1} 轮检查开始")
        self.health_checker.last_health_check = time.time()

        await self.restart_browser_if_needed()
        await performance_monitor.record_memory_usage()

        # 记录循环开始时间
        cycle_start_time = time.time()

        tasks = [self.check_dynamic_changes(url.split("/")[-1]) for url in DYNAMIC_URLS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 计算本轮是否成功（只要有一个任务成功，就认为本轮成功）
        success = any(not isinstance(result, Exception) for result in results)
        duration = time.time() - cycle_start_time

        # 记录本轮结果到性能监控器
        performance_monitor.record_cycle(
            cycle_number=self.loop_count + 1,
            success=success,
            duration=duration
        )

        self._save_history()
        # 将 loop_count 作为参数传入
        stats = self.health_checker.get_stats(total_loops=self.loop_count)
        logger.info(f"📊 本轮检查完成 - {stats}")
        # 记录状态信息到日志
        if self.status_monitor:
            status_info = self.status_monitor.get_status_info()
            logger.info(f"📈 状态监控: {status_info}")

        return success, duration

    async def run(self):
        """运行监控主循环"""
        logger.info(f"=== {UP_NAME} 动态置顶评论监控启动 ===")
        logger.info(f"动态地址：{', '.join(DYNAMIC_URLS)}")
        logger.info(f"监控发件邮箱：{EMAIL_USER}")
        logger.info(f"监控收件邮箱：{', '.join(TO_EMAILS)}")
        logger.info(f"检查间隔：{self.check_interval} 秒")
        logger.info(f"状态提醒邮箱：{', '.join(STATUS_MONITOR_EMAILS)}")
        logger.info(f"推送群聊：{', '.join(QQ_GROUP_IDS)}")

        try:
            await self.initialize_browser()

            # 启动定期性能报告任务
            perf_task = asyncio.create_task(performance_monitor.periodic_report(interval_minutes=60))
            logger.info("📊 定期性能报告任务已启动")

            while self.is_running:
                cycle_start = time.time()
                try:
                    success, duration = await self.run_monitoring_cycle()

                    # 计算需要等待的时间，确保精确间隔
                    elapsed = time.time() - cycle_start
                    wait_time = max(0, self.check_interval - elapsed)

                    if wait_time > 0:
                        next_check = time.strftime("%H:%M:%S", time.localtime(time.time() + wait_time))
                        logger.info(f"⏰ 下次检查时间: {next_check} (等待{wait_time:.1f}秒)")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.warning(f"⏱️ 检查耗时({elapsed:.1f}秒)超过间隔，立即开始下一轮")

                except KeyboardInterrupt:
                    logger.info("⛔ 收到中断信号，准备退出...")
                    break
                except Exception as e:
                    logger.error(f"❌ 监控循环出错: {e}")
                    await asyncio.sleep(5)  # 出错时等待5秒

        except Exception as e:
            logger.error(f"❌ 监控程序严重错误: {e}")
        finally:
            self.is_running = False
            # 取消定期性能报告任务
            if 'perf_task' in locals():
                perf_task.cancel()
                try:
                    await perf_task
                except asyncio.CancelledError:
                    logger.info("✅ 定期性能报告任务已取消")
            await self.safe_close_browser()
            logger.info("✅ 监控程序已安全退出")


# -------------------- 程序入口 --------------------
if __name__ == "__main__":
    monitor = Monitor()
    asyncio.run(monitor.run())
