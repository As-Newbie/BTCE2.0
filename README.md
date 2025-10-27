# B站动态置顶评论监控系统

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-playwright%20%7C%20beautifulsoup4-orange)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20linux%20%7C%20macOS-lightgrey)
![Python](https://img.shields.io/badge/Python-Learning-blue?logo=python)


一个自动监控B站动态置顶评论变化的Python程序，当检测到置顶评论更新时自动发送邮件通知。

## 项目完全非原创且主要依赖AI辅助开发！！！

## 功能特点

- 🔍 实时监控B站动态置顶评论变化
- 📧 自动发送邮件通知
- 🖼️ 支持评论图片监控
- ⏰ 可配置检查间隔
- 📊 完善的日志和性能监控
- 🔄 自动重试和错误恢复

## 安装要求

- Python 3.8+
- 支持的操作系统：Windows/Linux/macOS

## 快速开始

### 1. 克隆项目
```bash
git clone <项目地址>
cd bili-dynamic-monitor
```
### 2. 安装依赖
```bash
pip install -r requirements.txt
```
### 3. 安装Playwright浏览器
```bash
playwright install chromium
```
### 4. 配置邮箱（重要！）

编辑 `config_email.py` 文件：**最好是两个不同的邮箱 没试过同一个邮箱**
```
python

发件邮箱配置
EMAIL_USER = "your_email@qq.com" # 您的QQ邮箱
EMAIL_PASSWORD = "your_smtp_password" # QQ邮箱SMTP授权码
接收邮箱
TO_EMAILS = [
"receiver@qq.com", # 接收通知的邮箱
]
```
**获取QQ邮箱SMTP授权码：**
1. 登录QQ邮箱 → 设置 → 账户
2. 开启"POP3/SMTP服务"
3. 生成授权码

### 5. 配置监控目标

编辑 `dynamic.py` 文件，添加要监控的动态链接：
```
python

DYNAMIC_URLS = [
"https://t.bilibili.com/动态ID1",
"https://t.bilibili.com/动态ID2",
]
```
**如何获取动态ID：**
- 打开B站动态页面
- 复制地址栏中的动态ID，如：`https://t.bilibili.com/1128150856256978944`

### 6. 获取B站登录Cookie

运行获取Cookie脚本：
```bash
python get_cookies.py
```
按提示扫码登录B站，登录成功后会自动保存cookies。
**隐私安全说明**：
- Cookie文件仅保存在您的本地电脑，不会被传输到任何服务器
- 项目作者无法获取您的登录信息
- Cookie包含您的B站身份凭证，请妥善保管，不要分享给他人
- 如需彻底删除登录信息，直接删除项目目录下的`cookies.json`文件即可

### 7. 运行监控程序
```bash
python main.py
```
## 文件结构
```text
bili-dynamic-monitor/
├── main.py # 主程序入口
├── config.py # 主配置文件
├── config_email.py # 邮箱配置文件
├── dynamic.py # 监控动态列表
├── get_cookies.py # 获取Cookie脚本
├── cookies.json # 登录Cookie（自动生成）
├── requirements.txt # 依赖包列表
├── README.md # 说明文档
├── monitor.py # 监控主逻辑
├── render_comment.py # 评论渲染和检测
├── email_utils.py # 邮件发送工具
├── health_check.py # 健康检查
├── logger_config.py # 日志配置
├── performance_monitor.py # 性能监控
├── retry_decorator.py # 重试装饰器
├── task_executor.py # 任务执行器
├── logs/ # 日志目录（自动生成）
│   ├── monitor.log
│   ├── error.log
│   └── performance.log
├── sent_emails/ # 邮件备份（自动生成）
└── bili_pinned_comment.json # 历史记录（自动生成）
```
## 配置说明

### 主要配置项（config.py）
```
python

UP_NAME = "user name" # UP主名字（仅用于邮件标题）
CHECK_INTERVAL = 3 # 检查间隔（秒）
```
### 邮箱配置（config_email.py）

支持主流邮箱服务商：
- QQ邮箱：smtp.qq.com:465
- 163邮箱：smtp.163.com:465
- Gmail：smtp.gmail.com:587

### 动态监控配置（dynamic.py）

添加要监控的动态链接到 `DYNAMIC_URLS` 列表。

## 使用说明

### 启动监控
```bash
python main.py
```
### 停止监控
按 `Ctrl + C` 优雅停止程序

### 查看日志
程序运行日志保存在 `logs/` 目录：
- `monitor.log` - 运行日志
- `error.log` - 错误日志
- `performance.log` - 性能日志

## 常见问题

### 1. 无法获取Cookie
- 确保已安装Chromium浏览器：`playwright install chromium`
- 检查网络连接，确保可以访问B站

### 2. 邮件发送失败但实际收到邮件
**这是一个已知问题**：有时程序会报告"邮件发送失败"，但您实际上能收到邮件。

**原因**：SMTP服务器在处理邮件时可能出现异步响应，程序在等待确认时超时，但邮件实际上已经进入发送队列。

**解决方法**：
- 如果能看到邮件正常接收，可以忽略这个错误提示
- 可以适当增加`email_utils.py`中的超时时间
- 检查`sent_emails/`目录中是否有邮件备份，如果有备份说明邮件内容已生成

### 3. 邮件完全发送失败
- 检查邮箱配置是否正确
- 确认SMTP授权码已正确设置
- 检查防火墙设置
- 确认发件邮箱已开启SMTP服务

### 4. 监控不到变化
- 确认动态链接格式正确
- 检查Cookie是否过期（需重新获取）
- 查看日志文件排查问题

### 5. 内存占用过高
程序会自动重启浏览器释放内存，可在config.py中调整：
```
python

MEMORY_THRESHOLD_MB = 500 # 内存阈值
BROWSER_RESTART_INTERVAL = 10 # 重启间隔
```
## 注意事项

1. **隐私安全**：不要泄露 `cookies.json` 和 `config_email.py` 文件
2. **遵守规则**：合理设置检查间隔，避免对B站服务器造成压力
3. **定期维护**：Cookie会过期，需要定期重新获取
4. **合法使用**：请遵守B站用户协议和相关法律法规

## 更新日志

### v2.0.0

- 支持置顶评论文字和图片监控
- 支持邮件通知
- 完善的错误处理和日志系统

## 技术支持

### 项目开发说明
本项目是在AI助手（包括ChatGPT、腾讯元宝等）的协助下完成的。项目代码和功能实现得到了AI技术的大力支持。

### 技术支持政策
由于项目完全非原创且主要依赖AI辅助开发，技术支持将按以下优先级提供：

1. **优先建议**：遇到问题时，请先询问AI助手（如ChatGPT、腾讯元宝等）
2. **查阅文档**：仔细阅读本README和代码中的注释
3. **社区互助**：在相关技术社区寻求帮助
4. **有限支持**：开发者仅提供有限的技术支持

### 推荐的问题解决路径：
1. 将错误信息复制到AI助手中询问解决方案
2. 检查配置文件是否正确设置
3. 查看logs目录下的日志文件排查问题
4. 在GitHub Issues中查看是否有类似问题

### 注意事项
- 本项目适合有一定Python基础的用户使用
- 复杂的定制化需求建议自行修改或寻求AI助手帮助
- 不保证在所有环境下都能完美运行








