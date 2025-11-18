# config_qq.py
# QQ群推送配置文件

"""
QQ群推送配置模块 (config_qq.py)

此文件包含推送消息到QQ群所需的配置信息。
请根据您的QQ机器人服务修改以下配置参数。
"""

# ===== QQ机器人配置 =====
# QQ机器人API地址（根据您使用的QQ机器人框架配置）
# 例如：CoolQ HTTP API、Go-CQHTTP等
QQ_BOT_API_URL = "ws://127.0.0.1:8080/onebot/v11/ws"

# API访问令牌（如果您的机器人需要认证）
QQ_BOT_ACCESS_TOKEN = "<;UBllNdGKc7%>6D"

# ===== 推送配置 =====
# 要推送的QQ群号列表
QQ_GROUP_IDS = [
    "865320052",  # 第一个QQ群

    # 可继续添加更多QQ群
]

# ===== 消息格式配置 =====
# 消息最大长度（避免消息过长被截断）
MAX_MESSAGE_LENGTH = 500

# 是否启用推送（可以临时关闭）
QQ_PUSH_ENABLED = True

"""
使用说明：
1. 修改 QQ_BOT_API_URL
   - 根据您的QQ机器人实际部署地址修改
   - 默认使用Go-CQHTTP的默认端口5700

2. 设置QQ群号
   - 在 QQ_GROUP_IDS 列表中添加要推送的QQ群号
   - 每个群号用字符串形式表示

3. 配置访问令牌（如果需要）
   - 如果您的QQ机器人设置了访问令牌，请填写QQ_BOT_ACCESS_TOKEN

4. 保存文件后重启监控程序使配置生效

重要提示：
1. 请确保QQ机器人服务正常运行
2. 确保监控程序可以访问QQ机器人API地址
3. 请勿将此文件提交到公开的代码仓库
"""