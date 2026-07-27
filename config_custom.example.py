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
# QQ_SINGLE_LINK_LABEL = "动态链接"
# QQ_SINGLE_TIME_LABEL = "检测时间"
# QQ_BATCH_LINK_LABEL = "动态链接"
# QQ_BATCH_TIME_LABEL = "监测时间"
# QQ_PINNED_UPDATE_TEXT = "置顶评论更新"

# ---- 邮件标题个性化 ----
# EMAIL_PINNED_SUBJECT = "置顶评论更新"
# EMAIL_HEADER_TITLE = "动态置顶评论更新通知"

# ---- B站发布文案个性化 ----
# BILI_PUBLISH_TEXT = "置顶评论更新~"
# BILI_PC_LINK_LABEL = "电脑链接"
# BILI_MOBILE_LINK_LABEL = "手机链接"
