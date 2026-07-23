# BTCE 4.11 — B站动态/直播监控系统

基于 Python + Playwright 的 Bilibili UP 主动态和直播自动化监控系统，支持多通道实时通知及自动发布动态。

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/Playwright-1.40%2B-45ba4b)](https://playwright.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

![BTCE 架构图](mermaid-diagram.png)

## 版本演进

| 版本 | 主要变更 |
|------|---------|
| **v4.11** | B站动态发布末尾附加评论纯文本+MD5去重标记，避免重复动态被B站拿下 |
| **v4.10** | 直播标题更新同步B站话题：封面图+新标题+时间+链接+房间状态标签（加密/锁定/隐藏/付费） |
| **v4.9** | B站推送评论直达链接：rpid穿透Shadow DOM + `#reply{rpid}` 双链接 + `@机器人 测试` 显示当前置顶 |
| **v4.8** | 性能优化：Playwright页面复用（3-4s/轮）+ 滚动优化（5→3次）+ 检查间隔缩短（8→6s）+ 浏览器重启间隔延长（10→100轮） |
| **v4.7** | 管理群独立 + Cookie远程更新（@机器人指令→邮箱二维码→扫码→自动保存）+ 测试指令增强（轮次/成功率展示） |
| **v4.6** | 直播通知附加房间状态标签：room_init API 补充 encrypted/锁房/隐藏/付费/拜年纪，消息中标记 🔒密码保护 等 |
| **v4.5** | 修复 B站旧版 API 下线（404），更换 polymer 新版接口；API 独立健康统计+P1/P2告警+日报双通道 |
| **v4.4** | QQ群 @机器人 指令实时更换置顶动态ID：NapCat HTTP回调 + 权限校验 + 持久化+内存即时生效 |
| v4.3 | 三通道推送模式可配置：QQ/邮件/B站各自可选 text/screenshot 模式，截图延迟到B站发布不阻塞通知 |
| v4.2 | 自动发布B站动态：置顶评论变更时自动发图文动态（话题+截图+跳转链接），config开关控制 |
| v4.1 | 置顶评论截图推送：高DPI `#comment` 元素截图，替换文字+表情+图片，失败兜底旧格式 |
| v4.0 | 架构升级：API 动态列表 + 手动配置置顶 ID + 新动态卡片截图 + 双通道推送 |
| v3.0 | 本地重构版 |
| v2.0 | 云端部署版（BTCE2.0） |
| v1.0 | 初始版本：Playwright 抓取置顶评论 + 邮件/QQ 通知 |

## 核心功能

1. **置顶评论监控** — Playwright 打开置顶动态，抓取置顶评论文字+图片，变化时推送邮件/QQ/B站；推送模式三通道可配；支持 QQ 群 @机器人 实时更换置顶动态ID
2. **新动态检测** — API 定时获取动态列表，差集比对发现新动态，卡片截图 QQ 推送
3. **直播监控** — 轮询 B站直播 API，开播/下播/标题变化即时通知；标题更新自动发布B站动态（封面+链接+房间状态标签）
4. **多通道通知** — 邮件（HTML 格式）+ QQ 群（文字/CQ码图片/卡片截图）+ B站动态话题
5. **系统运维** — 健康检查、性能监控、日志轮转、浏览器自动重启、P1/P2 告警

## 项目结构

```
BTCE/
├── main.py                    # 程序入口
├── monitor.py                 # 核心监控逻辑
├── auto_publish.py            # B站动态自动发布模块（v4.2）
├── bili_api.py                # B站动态列表 API 客户端
├── live_monitor.py            # 直播状态监控
├── monitor_scheduler.py       # 直播监控调度器
├── render_comment.py          # 评论渲染与变化检测
├── email_renderer.py          # 邮件 HTML 模板
├── email_utils.py             # SMTP 邮件发送
├── qq_message_generator.py    # QQ 消息生成
├── qq_utils.py                # QQ 机器人推送
├── qq_callback_server.py      # QQ回调服务器（v4.4+: @机器人指令）
├── cookie_renewer.py           # Cookie远程更新（v4.7: 邮件二维码→扫码→自动保存）
├── color_config.py            # 邮件渐变色配置
├── config.py                  # 主配置（含 PINNED_DYNAMIC_ID）
├── config_email.example.py    # 邮箱配置模板
├── config_qq.example.py       # QQ配置模板
├── dynamic.py                 # 监控目标列表
├── health_check.py            # 健康检查
├── performance_monitor.py     # 性能监控
├── status_monitor.py          # 状态监控
├── self_monitor.py            # 直播失败计数
├── retry_decorator.py         # 重试装饰器
├── logger_config.py           # 日志配置
├── get_cookies.py             # Cookie 获取工具
├── requirements.txt           # Python 依赖
├── LICENSE                    # MIT 开源协议
├── mermaid-diagram.png        # 架构流程图
└── .gitignore                 # Git 忽略规则
```

## 快速开始

### 1. 环境准备
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 获取 Cookie
```bash
python get_cookies.py
```
或手动从浏览器导出 Cookie 保存为 `cookies.json`。

### 3. 配置
```bash
cp config_email.example.py config_email.py
cp config_qq.example.py config_qq.py
```
编辑配置文件，填入真实 SMTP 和 QQ 机器人信息。

在 `config.py` 中设置：
- `UP_NAME` / `UP_UID`：监控的 UP 主
- `PINNED_DYNAMIC_ID`：要监测评论的置顶动态 ID

### 4. 运行
```bash
python main.py
```

后台运行（Linux）：
```bash
pm2 start main.py --name bili-monitor --interpreter python3
```

## 配置说明

| 配置项 | 位置 | 说明 |
|--------|------|------|
| 监控目标 | `dynamic.py` `MONITOR_LIST` | UID + 名称 |
| 置顶动态 ID | `config.py` `PINNED_DYNAMIC_ID` | 手动配置，换置顶时修改 |
| 推送模式 | `config.py` `QQ_MODE`/`EMAIL_MODE`/`BILI_MODE` | text=文字+图片, screenshot=截图 |
| 检查间隔 | `config.py` `CHECK_INTERVAL` | 默认 6 秒（v4.8页面复用优化后缩短） |
| 邮箱 | `config_email.py` | SMTP + 收发人 |
| QQ 推送 | `config_qq.py` | 机器人 API + 群号 |
| 浏览器参数 | `config.py` `BROWSER_CONFIG` | headless 模式 |

## 注意事项

- Cookie 约 7 天失效，需定期更新
- 置顶动态更换时需手动更新 `PINNED_DYNAMIC_ID`
- 请勿将 `config_email.py`、`config_qq.py`、`cookies.json` 提交到公开仓库

## 免责声明

本项目仅供学习交流使用。使用者应遵守 Bilibili 平台的相关服务条款，不得用于任何违法违规用途。因使用本项目产生的任何后果由使用者自行承担，开发者不承担任何责任。
