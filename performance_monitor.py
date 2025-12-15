# performance_monitor.py
import asyncio
import psutil
import time
from datetime import datetime
from collections import deque
from logger_config import logger
from email_utils import send_email
from config_email import STATUS_MONITOR_EMAILS
from config import (
    P1_CONTINUOUS_FAILURE,
    P2_SUCCESS_RATE_THRESHOLD,
    PERFORMANCE_REPORT_CYCLE_INTERVAL,
    P2_WINDOW_CYCLES,
    P2_DURATION_CYCLES
)


class PerformanceMonitor:
    """简化版性能监控器，确保稳定运行"""

    def __init__(self):
        # 轮次统计
        self.total_cycles = 0
        self.cycle_success_count = 0
        self.cycle_failure_count = 0
        self.continuous_failures = 0
        self.cycle_history = deque(maxlen=1000)

        # 性能指标
        self.memory_peak = 0
        self.cycle_durations = deque(maxlen=100)
        self.error_count = 0
        self.start_time = time.time()
        self.last_alert_time = 0
        self.last_report_cycle = 0
        self.low_success_rate_start_cycle = None
        self.p1_alert_sent = False
        self.p2_alert_sent = False
        self.report_sent = False

        logger.info("📊 性能监控器初始化完成")
        logger.info(f"  - 报告间隔: 每{PERFORMANCE_REPORT_CYCLE_INTERVAL}轮")
        logger.info(f"  - P1告警: 连续失败{P1_CONTINUOUS_FAILURE}次")
        logger.info(
            f"  - P2告警: 最近{P2_WINDOW_CYCLES}轮成功率低于{P2_SUCCESS_RATE_THRESHOLD * 100:.0f}%持续{P2_DURATION_CYCLES}轮")

    async def record_memory_usage(self):
        """记录内存使用情况"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024

            if memory_mb > self.memory_peak:
                self.memory_peak = memory_mb

            return memory_mb
        except Exception as e:
            logger.error(f"❌ 记录内存使用失败: {e}")
            return 0

    def record_cycle(self, cycle_number, success, duration=None):
        """记录一轮检查的结果（快速返回，不阻塞）"""
        try:
            # 记录到轮次历史
            cycle_record = {
                'cycle_number': cycle_number,
                'timestamp': time.time(),
                'success': success,
                'duration': duration if duration else 0
            }
            self.cycle_history.append(cycle_record)

            # 更新统计
            self.total_cycles += 1

            if success:
                self.cycle_success_count += 1
                self.continuous_failures = 0

                # 如果之前有低成功率告警，现在重置
                if self.low_success_rate_start_cycle is not None:
                    logger.info("✅ 成功率恢复，重置低成功率计时器")
                    self.low_success_rate_start_cycle = None
                    self.p2_alert_sent = False
            else:
                self.cycle_failure_count += 1
                self.continuous_failures += 1
                self.error_count += 1

            if duration:
                self.cycle_durations.append({
                    'cycle': cycle_number,
                    'duration': duration,
                    'timestamp': datetime.now(),
                    'success': success
                })

            # 每100轮记录一次状态
            if cycle_number % 100 == 0:
                try:
                    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                    logger.info(
                        f"📊 第{cycle_number}轮统计: 成功={success}, 耗时={duration:.2f}s, 连续失败={self.continuous_failures}, 内存={memory_mb:.1f}MB")
                except:
                    pass

            # 快速检查告警和报告条件（不发送邮件，避免阻塞）
            self._check_conditions_quickly(cycle_number)

        except Exception as e:
            logger.error(f"❌ 记录轮次结果失败: {e}")

    def _check_conditions_quickly(self, current_cycle):
        """快速检查条件（不发送邮件，避免阻塞）"""
        try:
            # P1告警：连续失败检查
            if self.continuous_failures >= P1_CONTINUOUS_FAILURE and not self.p1_alert_sent:
                logger.error(f"🚨 P1告警条件满足: 连续失败{self.continuous_failures}次 (阈值: {P1_CONTINUOUS_FAILURE})")
                # 异步发送邮件
                asyncio.create_task(self._send_p1_alert(current_cycle))
                self.p1_alert_sent = True
                self.last_alert_time = time.time()

            # P2告警：低成功率检查
            recent_success_rate = self._get_recent_success_rate()
            if recent_success_rate < P2_SUCCESS_RATE_THRESHOLD:
                if self.low_success_rate_start_cycle is None:
                    self.low_success_rate_start_cycle = current_cycle
                    logger.warning(
                        f"⚠️ 检测到低成功率 {recent_success_rate:.2%} (阈值: {P2_SUCCESS_RATE_THRESHOLD:.0%})，开始计时...")

                duration_cycles = current_cycle - self.low_success_rate_start_cycle
                if duration_cycles >= P2_DURATION_CYCLES and not self.p2_alert_sent:
                    logger.error(f"🚨 P2告警条件满足: 低成功率持续{duration_cycles}轮 (阈值: {P2_DURATION_CYCLES}轮)")
                    # 异步发送邮件
                    asyncio.create_task(self._send_p2_alert(current_cycle, recent_success_rate, duration_cycles))
                    self.p2_alert_sent = True
                    self.last_alert_time = time.time()
            else:
                if self.low_success_rate_start_cycle is not None:
                    logger.info(f"✅ 成功率恢复至 {recent_success_rate:.2%}，重置告警状态")
                    self.low_success_rate_start_cycle = None
                self.p2_alert_sent = False

            # 检查是否需要发送报告
            cycles_since_last_report = current_cycle - self.last_report_cycle
            if cycles_since_last_report >= PERFORMANCE_REPORT_CYCLE_INTERVAL and not self.report_sent:
                logger.info(f"📧 满足报告发送条件: 第{current_cycle}轮")
                # 异步发送邮件
                asyncio.create_task(self._send_report(current_cycle))
                self.report_sent = True
                self.last_report_cycle = current_cycle

        except Exception as e:
            logger.error(f"❌ 检查条件失败: {e}")

    def _get_recent_success_rate(self):
        """获取最近指定轮次的成功率"""
        if len(self.cycle_history) < P2_WINDOW_CYCLES:
            return 1.0

        # 获取最近P2_WINDOW_CYCLES轮
        recent_cycles = list(self.cycle_history)[-P2_WINDOW_CYCLES:]
        successful_cycles = sum(1 for cycle in recent_cycles if cycle['success'])
        return successful_cycles / len(recent_cycles)

    async def _send_p1_alert(self, current_cycle):
        """发送P1告警邮件"""
        try:
            subject = f"🚨 P1告警: 连续失败{self.continuous_failures}次 (第{current_cycle}轮)"
            content = self._generate_p1_alert_content(current_cycle)

            success = await asyncio.to_thread(
                send_email,
                subject=subject,
                content=content,
                to_emails=STATUS_MONITOR_EMAILS
            )
            if success:
                logger.info("✅ P1告警邮件发送成功")
            else:
                logger.error("❌ P1告警邮件发送失败")
        except Exception as e:
            logger.error(f"❌ 发送P1告警邮件异常: {e}")

    async def _send_p2_alert(self, current_cycle, success_rate, duration_cycles):
        """发送P2告警邮件"""
        try:
            subject = f"⚠️ P2告警: 成功率过低 {success_rate:.1%} (第{current_cycle}轮)"
            content = self._generate_p2_alert_content(current_cycle, success_rate, duration_cycles)

            success = await asyncio.to_thread(
                send_email,
                subject=subject,
                content=content,
                to_emails=STATUS_MONITOR_EMAILS
            )
            if success:
                logger.info("✅ P2告警邮件发送成功")
            else:
                logger.error("❌ P2告警邮件发送失败")
        except Exception as e:
            logger.error(f"❌ 发送P2告警邮件异常: {e}")

    async def _send_report(self, current_cycle):
        """发送性能报告邮件"""
        try:
            subject = f"📊 性能报告 - 第{current_cycle}轮"
            content = self._generate_report_content(current_cycle)

            success = await asyncio.to_thread(
                send_email,
                subject=subject,
                content=content,
                to_emails=STATUS_MONITOR_EMAILS
            )
            if success:
                logger.info("✅ 性能报告邮件发送成功")
                self.report_sent = False  # 重置报告发送状态
            else:
                logger.error("❌ 性能报告邮件发送失败")
        except Exception as e:
            logger.error(f"❌ 发送性能报告邮件异常: {e}")

    def _generate_p1_alert_content(self, current_cycle):
        """生成P1告警内容"""
        return f"""
        <html>
        <head><style>body {{ font-family: Arial, sans-serif; margin: 20px; }}</style></head>
        <body>
            <h2 style="color: #dc3545;">🚨 P1告警 - 连续失败</h2>
            <p><strong>连续失败次数:</strong> {self.continuous_failures} (阈值: {P1_CONTINUOUS_FAILURE})</p>
            <p><strong>当前轮次:</strong> {current_cycle}</p>
            <p><strong>告警时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <h3>📊 系统状态</h3>
            <p>总轮次数: {self.total_cycles}</p>
            <p>成功轮次: {self.cycle_success_count}</p>
            <p>失败轮次: {self.cycle_failure_count}</p>
            <p>成功率: {(self.cycle_success_count / self.total_cycles * 100) if self.total_cycles else 0:.1f}%</p>
            <p><strong>⚠️ 请立即检查监控系统状态！</strong></p>
        </body>
        </html>
        """

    def _generate_p2_alert_content(self, current_cycle, success_rate, duration_cycles):
        """生成P2告警内容"""
        return f"""
        <html>
        <head><style>body {{ font-family: Arial, sans-serif; margin: 20px; }}</style></head>
        <body>
            <h2 style="color: #ffc107;">⚠️ P2告警 - 成功率过低</h2>
            <p><strong>成功率:</strong> {success_rate:.2%} (阈值: {P2_SUCCESS_RATE_THRESHOLD:.0%})</p>
            <p><strong>持续时间:</strong> {duration_cycles} 轮</p>
            <p><strong>当前轮次:</strong> {current_cycle}</p>
            <p><strong>告警时间:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            <h3>📊 性能详情</h3>
            <p>总轮次数: {self.total_cycles}</p>
            <p>成功轮次: {self.cycle_success_count}</p>
            <p>失败轮次: {self.cycle_failure_count}</p>
            <p>连续失败: {self.continuous_failures}</p>
            <p><strong>💡 建议：检查网络连接或目标页面是否正常</strong></p>
        </body>
        </html>
        """

    def _generate_report_content(self, current_cycle):
        """生成报告内容"""
        uptime_seconds = time.time() - self.start_time
        uptime_hours = uptime_seconds / 3600
        success_rate = self.cycle_success_count / self.total_cycles if self.total_cycles > 0 else 0

        return f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                .alert {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 10px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <h2>📊 性能报告 - 第{current_cycle}轮</h2>
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>系统运行时间: {uptime_hours:.1f} 小时</p>

            <h3>📈 核心指标</h3>
            <table>
                <tr><th>指标</th><th>数值</th></tr>
                <tr><td>成功率</td><td>{success_rate:.2%}</td></tr>
                <tr><td>总轮次数</td><td>{self.total_cycles}</td></tr>
                <tr><td>成功轮次</td><td>{self.cycle_success_count}</td></tr>
                <tr><td>失败轮次</td><td>{self.cycle_failure_count}</td></tr>
                <tr><td>连续失败</td><td>{self.continuous_failures}</td></tr>
                <tr><td>运行频率</td><td>{self.total_cycles / uptime_hours:.1f} 轮/小时</td></tr>
            </table>

            <div class="alert">
                <strong>💡 告警状态:</strong><br>
                P1告警: {'🚨 已触发' if self.p1_alert_sent else '✅ 正常'}<br>
                P2告警: {'⚠️ 已触发' if self.p2_alert_sent else '✅ 正常'}
            </div>

            <p><em>报告间隔: 每{PERFORMANCE_REPORT_CYCLE_INTERVAL}轮发送一次</em></p>
        </body>
        </html>
        """

    async def periodic_report(self, interval_minutes=60):
        """定期生成性能报告（按时间间隔）"""
        while True:
            try:
                await asyncio.sleep(interval_minutes * 60)

                # 获取当前内存
                memory_mb = 0
                try:
                    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                except:
                    pass

                uptime_hours = (time.time() - self.start_time) / 3600

                logger.info(
                    f"📊 定期性能报告: 运行{uptime_hours:.1f}小时, 轮次{self.total_cycles}, 成功率{(self.cycle_success_count / self.total_cycles * 100) if self.total_cycles else 0:.1f}%, 内存{memory_mb:.1f}MB")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 定期报告异常: {e}")


# 全局性能监控实例
performance_monitor = PerformanceMonitor()
