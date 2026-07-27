# config_custom.example.py
# 复制为 config_custom.py 并填入个性化文案（覆盖通用默认值）
# 此文件已在 .gitignore 中，不会被提交到 Git 也不会被部署覆盖

# ---- QQ推送文案个性化 ----
# 新动态单条通知
QQ_SINGLE_LINK_LABEL = "🔗"      # 链接前缀
QQ_SINGLE_TIME_LABEL = "📅"     # 时间前缀

# 新动态批量通知
QQ_BATCH_LINK_LABEL = "🔗"      # 链接前缀
QQ_BATCH_TIME_LABEL = "📅"     # 时间前缀

# ---- 邮件标题个性化 ----
# 置顶评论更新邮件标题
EMAIL_PINNED_SUBJECT = "置顶评论更新"

# ---- 配置值个性化 ----
# 如需要也可覆盖 config.py 中的值
# UP_NAME = "你的UP主昵称"
# PINNED_DYNAMIC_ID = "你的置顶动态ID"
