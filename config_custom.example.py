# config_custom.example.py
# 复制为 config_custom.py 并填入个性化值（覆盖 config.py 的默认值）
# 此文件已在 .gitignore 中，不会被 Git 提交，也不会被部署覆盖
#
# 用法：在此文件中定义任何变量，部署后自动覆盖 config.py 同名默认值

# ---- 基础配置覆盖（示例）----
# UP_NAME = "你的UP主昵称"
# PINNED_DYNAMIC_ID = "你的置顶动态ID"
# CHECK_INTERVAL = 4  # 如果要改检查间隔

# ---- QQ推送文案个性化 ----
# QQ_SINGLE_LINK_LABEL = "动态链接"    # 单条通知链接前缀（默认: 🔗）
# QQ_SINGLE_TIME_LABEL = "检测时间"    # 单条通知时间前缀（默认: 📅）
# QQ_BATCH_LINK_LABEL = "动态链接"    # 批量通知链接前缀（默认: 🔗）
# QQ_BATCH_TIME_LABEL = "监测时间"    # 批量通知时间前缀（默认: 📅）

# ---- 邮件标题个性化 ----
# EMAIL_PINNED_SUBJECT = "置顶评论更新"  # 邮件主题格式: 【UP_NAME】{此值}
