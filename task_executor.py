import asyncio
import time  
from typing import Any, Callable, List
from logger_config import logger
from config import TASK_TIMEOUT
from performance_monitor import performance_monitor


class TaskExecutor:
    """安全的任务执行器"""

    @staticmethod
    async def execute_with_timeout(coro, timeout: int = TASK_TIMEOUT, task_name: str = "未知任务"):
        """带超时和异常处理的任务执行"""
        start_time = time.time()

        try:
            result = await asyncio.wait_for(coro, timeout=timeout)
            duration = time.time() - start_time

            # 记录性能数据
            performance_monitor.record_task_duration(task_name, duration)

            if duration > timeout / 2:  # 如果耗时超过超时时间的一半，记录警告
                logger.warning(f"⚠️ 任务 {task_name} 执行较慢: {duration:.2f}秒")

            return result

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.error(f"⏰ 任务 {task_name} 超时 (限制: {timeout}秒, 实际: {duration:.2f}秒)")
            performance_monitor.record_error("任务超时")
            raise

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"❌ 任务 {task_name} 执行失败: {e} (耗时: {duration:.2f}秒)")
            performance_monitor.record_error(type(e).__name__)
            raise

    @staticmethod
    async def execute_parallel(tasks: List[Callable], max_concurrent: int = 3):
        """并行执行任务，控制并发数量"""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def bounded_task(task):
            async with semaphore:
                return await task

        # 使用return_exceptions=True防止单个任务异常影响其他任务
        results = await asyncio.gather(
            *(bounded_task(task) for task in tasks),
            return_exceptions=True
        )

        # 处理异常结果
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"并行任务 {i} 执行失败: {result}")
                performance_monitor.record_error("并行任务失败")
            else:
                successful_results.append(result)


        return successful_results
