# performance_monitor.py
import asyncio
import psutil
import time
from datetime import datetime
from logger_config import logger


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self):
        self.metrics = {
            'memory_peak': 0,
            'task_durations': [],
            'error_count': 0,
            'start_time': time.time()
        }

    async def record_memory_usage(self):
        """记录内存使用情况"""
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024

        if memory_mb > self.metrics['memory_peak']:
            self.metrics['memory_peak'] = memory_mb

        return memory_mb

    def record_task_duration(self, task_name, duration):
        """记录任务执行时间"""
        self.metrics['task_durations'].append({
            'task': task_name,
            'duration': duration,
            'timestamp': datetime.now()
        })

        # 只保留最近100个记录
        if len(self.metrics['task_durations']) > 100:
            self.metrics['task_durations'] = self.metrics['task_durations'][-100:]

    def record_error(self, error_type):
        """记录错误"""
        self.metrics['error_count'] += 1
        logger.error(f"❌ 错误记录: {error_type}")

    def get_performance_report(self):
        """获取性能报告"""
        current_memory = psutil.Process().memory_info().rss / 1024 / 1024
        uptime_hours = (time.time() - self.metrics['start_time']) / 3600

        avg_duration = 0
        if self.metrics['task_durations']:
            avg_duration = sum(d['duration'] for d in self.metrics['task_durations']) / len(
                self.metrics['task_durations'])

        return {
            "运行时间": f"{uptime_hours:.1f} 小时",
            "当前内存": f"{current_memory:.1f} MB",
            "峰值内存": f"{self.metrics['memory_peak']:.1f} MB",
            "平均任务耗时": f"{avg_duration:.2f} 秒",
            "错误次数": self.metrics['error_count'],
            "总任务数": len(self.metrics['task_durations'])
        }

    async def periodic_report(self, interval_minutes=60):
        """定期生成性能报告"""
        while True:
            await asyncio.sleep(interval_minutes * 60)
            report = self.get_performance_report()
            logger.info("📊 性能报告: " + " | ".join(f"{k}: {v}" for k, v in report.items()))


# 全局性能监控实例
performance_monitor = PerformanceMonitor()
