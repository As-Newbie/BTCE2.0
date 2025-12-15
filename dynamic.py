# dynamic.py
# 存储要监控的B站动态链接列表
# 每次需要监控新的动态，可以手动在这里添加或删除链接

DYNAMIC_URLS = [
    # 添加要监控的动态链接，格式如下：
    # "https://t.bilibili.com/第一个动态ID",
    # "https://t.bilibili.com/另一个动态ID",
]

# 如果列表为空，添加一个提示
if not DYNAMIC_URLS:

    print("⚠️ 警告: DYNAMIC_URLS 列表为空，请添加要监控的动态链接")
