import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from config import LOG_DIR, MAX_LOG_SIZE_MB, LOG_BACKUP_COUNT


def setup_logging():
    """配置日志系统"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # 清除已有的handler
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 创建formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler - 按大小轮转
    log_file = LOG_DIR / "monitor.log"
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 错误日志单独记录
    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # 性能监控日志
    perf_handler = TimedRotatingFileHandler(
        LOG_DIR / "performance.log",
        when='D',
        interval=1,
        backupCount=7,
        encoding='utf-8'
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(formatter)
    logger.addHandler(perf_handler)

    logger.info("✅ 日志系统初始化完成")
    return logger


# 创建全局logger实例
logger = logging.getLogger('BiliMonitor')