# dynamic.py
# 监控目标配置：以 UID 为主键，系统自动从空间页发现置顶动态
# 添加新 UP 主只需新增一条字典即可

MONITOR_LIST = [
    {"uid": "", "name": ""},  # 需自行配置 UID 和昵称
]

# 从 MONITOR_LIST 提取动态链接列表（兼容旧代码）
DYNAMIC_URLS = []
