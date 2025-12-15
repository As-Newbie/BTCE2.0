import logging
import sys
# import os
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
# from pathlib import Path
# import glob
import time
from config import LOG_DIR, MAX_LOG_SIZE_MB, LOG_BACKUP_COUNT


def cleanup_old_logs():
    """清理过期的日志文件"""
    try:
        # 定义要清理的日志文件模式
        log_patterns = [
            "monitor.log.*",
            "error.log.*",
            "performance.log.*",
            "performance.log.????-??-??",
            "combined.log",
            "out.log",
            "err.log"
        ]

        deleted_files = []

        for pattern in log_patterns:
            # 在日志目录中查找匹配的文件
            for log_file in LOG_DIR.glob(pattern):
                try:
                    # 检查文件修改时间，删除3天前的文件
                    file_age = time.time() - log_file.stat().st_mtime
                    if file_age > 3 * 24 * 3600:  # 30天
                        log_file.unlink()
                        deleted_files.append(log_file.name)
                except Exception as e:
                    print(f"清理日志文件 {log_file} 失败: {e}")

        if deleted_files:
            print(f"✅ 已清理 {len(deleted_files)} 个旧日志文件: {', '.join(deleted_files)}")

    except Exception as e:
        print(f"❌ 日志清理过程出错: {e}")


def setup_logging():
    """配置日志系统"""
    # 先清理旧日志
    cleanup_old_logs()

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

    # 确保日志目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 主日志文件 - 按大小轮转
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

    # 错误日志单独记录 - 按大小轮转
    error_handler = RotatingFileHandler(
        LOG_DIR / "error.log",
        maxBytes=MAX_LOG_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)

    # 性能监控日志 - 按时间轮转（每天），并设置备份数量
    perf_handler = TimedRotatingFileHandler(
        LOG_DIR / "performance.log",
        when='midnight',  # 每天午夜轮转
        interval=1,
        backupCount=3,  # 保留3天
        encoding='utf-8'
    )
    perf_handler.setLevel(logging.INFO)
    perf_handler.setFormatter(formatter)

    # 设置后缀为日期格式
    perf_handler.suffix = "%Y-%m-%d"
    logger.addHandler(perf_handler)

    # 添加PM2相关日志的处理器（如果存在）
    pm2_logs = [
        LOG_DIR / "combined.log",
        LOG_DIR / "out.log",
        LOG_DIR / "err.log"
    ]

    for pm2_log in pm2_logs:
        try:
            pm2_handler = RotatingFileHandler(
                pm2_log,
                maxBytes=10 * 1024 * 1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            pm2_handler.setLevel(logging.INFO)
            pm2_handler.setFormatter(formatter)
            logger.addHandler(pm2_handler)
        except Exception as e:
            print(f"配置PM2日志 {pm2_log} 失败: {e}")

    logger.info("✅ 日志系统初始化完成")
    logger.info(f"📁 日志目录: {LOG_DIR}")
    logger.info(f"📏 日志文件大小限制: {MAX_LOG_SIZE_MB}MB")
    logger.info(f"💾 日志备份数量: {LOG_BACKUP_COUNT}")

    return logger


# 创建全局logger实例
logger = logging.getLogger('BiliMonitor')
