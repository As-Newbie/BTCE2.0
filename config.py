# config.py
# import os
from pathlib import Path

# ===== 导入动态链接 =====
try:
    from dynamic import DYNAMIC_URLS
except ImportError:
    # 如果导入失败，使用默认的空列表
    DYNAMIC_URLS = []
    print("⚠️ 警告: 无法从 dynamic.py 导入 DYNAMIC_URLS，使用空列表")

# ===== 基础配置 =====
UP_NAME = "星瞳_Official"
CHECK_INTERVAL = 8  # 秒
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # 秒

# ===== 文件路径配置 =====
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
HEALTH_CHECK_INTERVAL = 15  # 每15次循环进行健康检查
TASK_TIMEOUT = 30  # 单个任务超时时间(秒)

# ===== 状态监控配置 =====
STATUS_MONITOR_INTERVAL = 7200  # 状态检查间隔（秒），2小时
NO_UPDATE_ALERT_HOURS = 26      # 无更新提醒阈值（小时）

# ===== 性能监控配置 =====
MEMORY_THRESHOLD_MB = 500  # 内存阈值(MB)
MAX_LOG_SIZE_MB = 10  # 单个日志文件最大大小(MB)
LOG_BACKUP_COUNT = 5  # 保留的日志备份数量

# ===== 性能报告配置（基于轮次）=====
PERFORMANCE_REPORT_CYCLE_INTERVAL = 40  # 每8000轮发送一次报告
P2_WINDOW_CYCLES = 20  # P2告警窗口轮次数（最近100轮）
P2_DURATION_CYCLES = 10  # P2告警持续时间（连续10轮低成功率）

# ===== 告警阈值配置 =====
P1_CONTINUOUS_FAILURE = 5  # 连续失败次数阈值（P1告警）
P2_SUCCESS_RATE_THRESHOLD = 0.99  # 成功率阈值（99%）
