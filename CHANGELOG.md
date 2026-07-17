# Changelog

BTCE 各版本详细变更记录。简表见 [README.md](README.md#版本演进)。

## v4.9 — 评论直达链接 (2026-07)

- **评论直达链接**：穿透 B站 Web Component 三层 Shadow DOM 提取 `rpid`（评论ID），B站推送新增 `#reply{rpid}` 直达链接
- **双链接推送**：`💻跳转链接`（评论直达）+ `📱跳转链接`（动态页），替代原来被 B站 自动转"网页链接"卡片的方式
- **状态显示当前置顶**：`@机器人 测试` 回复新增 `🔗 当前置顶: https://t.bilibili.com/{ID}`

## v4.8 — 性能优化 (2026-07)

- **页面复用**：`check_dynamic_changes` 持久化复用 Playwright 页面，不再每轮 `new_page()` + `close()`，省 ~1s/轮
- **滚动优化**：触发懒加载的滚动从 5次×1s 降为 3次×0.5s，省 ~3.5s/轮
- **检查间隔缩短**：`CHECK_INTERVAL` 8→6s，配合页面复用后 3s 工作耗时留足缓冲
- **浏览器重启间隔**：`BROWSER_RESTART_INTERVAL` 10→100 轮，减少重启开销
- **综合效果**：单轮总周期 8s→6s，8000 轮从 19.4h→13.3h（-31%）

## v4.7 — Cookie 远程更新 (2026-06)

- **管理群独立**：新增 `QQ_MANAGEMENT_GROUP_IDS` 配置，管理群只接收 `@机器人` 指令，不接收监控推送
- **Cookie 远程更新**：`@机器人 更新凭证` → B站 QR 登录 API 生成二维码 → 邮件内嵌二维码 → 管理员扫码 → 自动保存 `cookies.json` + 热重启浏览器
- **测试指令增强**：`@机器人 测试/状态` 回复增加当前轮次、运行时间、抓取成功率、API 成功率、凭证更新时间
- **新增 `cookie_renewer.py`**：独立模块，B站 `generate`/`poll` 双 API + `qrcode` 库 + MIME 邮件内嵌图片
- **`monitor.py` 新增 `restart_browser()`**：无条件重启浏览器，凭证更新后热加载新 cookie
- **`qq_callback_server.py` 扩展**：`更新凭证/测试/状态` 三条指令 + 推送群+管理群联合白名单

## v4.6 — 直播房间状态标签 (2026-05)

- **直播通知附加房间状态标签**：新增调用 `room_init` API，获取 `encrypted`/`is_locked`/`is_hidden`/`special_type` 四个字段
- **状态标签展示**：加密 → 🔒密码保护、锁定 → 🔐房间已锁定、隐藏 → 👻房间已隐藏、付费 → 💰付费直播、拜年纪 → 🎊拜年纪
- **纯展示不触发通知**：标签仅作为已触发通知的附加信息（路线A），不产生独立的变更事件
- **失败无感兜底**：`room_init` 请求失败时字段默认为 `false`/`0`，不影响开播/下播检测主流程

## v4.5 — API 接口迁移 (2026-04)

- **API 接口迁移**：B站旧版 `api.vc.bilibili.com` 已下线（HTTP 404），更换为 `api.bilibili.com/x/polymer/web-dynamic/v1/feed/space`
- **仅需 Cookie**：新版 polymer 接口无需 WBI 签名
- **响应结构适配**：新版返回 `items[]` 结构（含 `id_str` / `modules.module_dynamic`）
- **API 独立健康统计**：API 动态列表与置顶评论（Playwright）分开计数
- **API 独立 P1/P2 告警**：P1 连续失败 ≥10 次，P2 成功率 <90%
- **日报双通道**：性能报告分「置顶评论监控 (Playwright)」和「API 动态列表 (urllib)」两块

## v4.4 — QQ 群 @机器人 指令 (2026-03)

- **QQ群指令更换置顶**：在群里 `@Bot 更换置顶 <动态ID>` 实时更换，无需登录服务器改 config
- **qq_callback_server.py**：aiohttp HTTP 服务器，接收 NapCat 事件回调
- **权限校验**：`QQ_ADMIN_USERS` 白名单控制
- **双重更新**：写入 config.py 持久化 + 内存即时生效

## v4.3 — 三通道推送模式可配置 (2026-02)

- **三通道推送模式**：`QQ_MODE` / `EMAIL_MODE` / `BILI_MODE` 各可选 `"text"` 或 `"screenshot"`
  - `text`：纯文本+图片（快速不阻塞）
  - `screenshot`：截图内嵌（B站截图发布）
- **推送顺序优化**：默认 text 模式，QQ+邮件先推不等待截图
- **截图逻辑提取**：`_take_pinned_comment_screenshot` 独立方法

## v4.2 — 自动发布B站动态 (2026-01)

- **自动发布B站动态**：置顶评论变更时上传截图+发布带 `#TAG` 话题的图文动态
- **auto_publish.py**：独立模块，B站图床上传 + 动态发布 API，异步调用不阻塞通知
- **config 开关**：`AUTO_PUBLISH_ENABLED` 控制功能启用/关闭

## v4.1 — 置顶评论截图推送 (2025-12)

- **置顶评论截图推送**：高DPI context（`device_scale_factor=2`）截图 `#comment` 元素
- **截图替换旧格式**：QQ/邮件通知中用截图替换文字+表情+图片，失败自动兜底旧文字格式

## v4.0 — 架构升级

- **架构重构**：从单一 URL 硬编码升级为 API 动态列表 + 手动置顶 ID 的混合架构
- **bili_api.py**：B站新版 polymer API 客户端，带 Cookie 获取动态列表
- **monitor.py 全重写**：分离新动态检测和置顶评论监控两条独立线路
- **历史记录按 dynamic_id 追踪**：消除置顶动态更换时的误报
- **卡片截图推送**：Playwright 截取动态卡片 → QQ 群图片推送
- **新动态批量通知**：API 差集检测 → 邮件/QQ 合并推送，冷启动静默记录

## v3.0 — 本地重构版

## v2.0 — 云端部署版（BTCE2.0）

## v1.0 — 初始版本

Playwright 抓取置顶评论 + 邮件/QQ 通知。
