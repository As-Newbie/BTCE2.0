# config.py
import os
from pathlib import Path

# ===== 导入动态链接 =====
try:
    from dynamic import DYNAMIC_URLS
except ImportError:
    # 如果导入失败，使用默认的空列表
    DYNAMIC_URLS = []
    print("⚠️ 警告: 无法从 dynamic.py 导入 DYNAMIC_URLS，使用空列表")

# ===== 基础配置 =====
UP_NAME = "User name"  # 修改为您要监控的UP主名字
CHECK_INTERVAL = 3  # 秒
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # 秒

# ===== 文件路径配置 =====
# 使用相对路径，项目根目录
BASE_DIR = Path(__file__).parent

COOKIE_FILE = BASE_DIR / "cookies.json"
HISTORY_FILE = BASE_DIR / "bili_pinned_comment.json"
MAIL_SAVE_DIR = BASE_DIR / "sent_emails"
LOG_DIR = BASE_DIR / "logs"

# 创建必要目录
for dir_path in [MAIL_SAVE_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# ===== 浏览器配置 =====
BROWSER_CONFIG = {
    "headless": True,
    "args": [
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-gpu",
        "--disable-software-rasterizer",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        "--memory-pressure-off",
        "--max_old_space_size=4096"
    ]
}

# ===== 监控配置 =====
BROWSER_RESTART_INTERVAL = 10  # 每10次循环重启浏览器
HEALTH_CHECK_INTERVAL = 5  # 每5次循环进行健康检查
TASK_TIMEOUT = 30  # 单个任务超时时间(秒)

# ===== 性能监控配置 =====
MEMORY_THRESHOLD_MB = 500  # 内存阈值(MB)
MAX_LOG_SIZE_MB = 10  # 单个日志文件最大大小(MB)
LOG_BACKUP_COUNT = 5  # 保留的日志备份数量