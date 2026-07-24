# Changelog

BTCE 各版本详细变更记录。简表见 [README.md](README.md#版本演进)。

## v4.12 — 邮件HTML统一备份 (2026-07)

- **`send_email()` 内统一备份**：所有邮件发送前自动保存HTML到 `sent_emails/` 目录，覆盖此前遗漏的直播通知和告警邮件
- **移除冗余保存点**：`monitor.py` 中新动态批量通知和置顶评论更新两处手动写文件移除，统一走 `send_email()` 备份
- **备份格式**：`sent_emails/{YYYYMMDD_HHMMSS}_{主题}.html`，SMTP发送前写入确保即使发送失败也有留档

### XTong 的贡献
- **需求与设计**：提出邮件备份需求，便于后续数据分析

### Claude (AI Assistant) 的贡献
- **编码实现**：`email_utils.py` 新增 `_save_email_backup()` 函数；`monitor.py` 冗余保存点清理；文档更新与部署

## v4.11 — B站发布附加评论纯文本+去重标记 (2026-07)

- **动态末尾附加评论纯文本**：B站置顶评论更新动态自动附上评论纯文本（与QQ推送一致：emoji img替换为alt文字）
- **MD5去重标记**：`MD5(评论文本+时间戳)` 取前16位追加到动态末尾，避免B站判重拦截
- **仅影响置顶评论发布**：`publish_dynamic()` 新增 `comment_text` 参数，直播间标题发布 (`publish_live_update`) 不变
- **monitor.py 联动**：`_send_notification()` 从 `cur_html` 提取纯文本，传入B站发布流程

### XTong 的贡献
- **需求与设计**：提出B站动态附加评论纯文本+MD5去重标记需求

### Claude (AI Assistant) 的贡献
- **编码实现**：`publish_dynamic()` 新增 `comment_text` 参数与MD5去重逻辑；`monitor.py` 纯文本提取与传递；文档更新与部署

## v4.10 — 直播标题更新同步B站话题 (2026-07)

- **直播标题更新自动发布B站动态**：标题变化时同步发布图文动态到B站话题
- **动态内容**：封面图 + 新标题 + 更新时间 + 直播间链接 + 房间状态标签（加密/锁定/隐藏/付费/拜年纪）
- **容错降级**：封面下载/上传失败自动降级为纯文本动态，不阻塞QQ/邮件通知
- **可配置开关**：`LIVE_BILI_PUBLISH_ENABLED` 独立控制，复用已有话题配置
- **新增 `auto_publish.py` 函数**：`_download_cover_image()` 下载封面到本地、`publish_live_update()` 完整发布流程
- **`monitor_scheduler.py` 扩展**：`send_live_notification()` 新增B站动态发布通道，fire-and-forget 不阻塞

### XTong 的贡献
- **需求与设计**：提出直播标题更新同步B站话题需求，指定动态内容格式（封面+标题+时间+链接+状态标签）

### Claude (AI Assistant) 的贡献
- **编码实现**：新增 `_download_cover_image()`、`publish_live_update()` 函数；扩展 `monitor_scheduler.py` B站发布通道；容错降级逻辑；文档更新与部署

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

---

## 待优化

### rpid 改用 B站公开 API 获取

**现状**（v4.9 fix）：从 Web Component 内部属性 `__data.rpid` 获取，依赖 Playwright 打开的页面。

**方案**：通过 B站公开 API 直接获取，无需登录、无需打开页面。

```python
# 1. 获取评论线程ID（oid）
async def get_comment_oid(dynamic_id: str) -> str:
    url = f"https://api.bilibili.com/x/polymer/web-dynamic/v1/detail?id={dynamic_id}"
    async with aiohttp.ClientSession() as s:
        r = await s.get(url)
        data = await r.json()
        return data["data"]["item"]["basic"]["comment_id_str"]

# 2. 用 oid 获取置顶评论rpid
async def get_rpid(dynamic_id: str) -> str | None:
    oid = await get_comment_oid(dynamic_id)
    url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={oid}&type=11&mode=3"
    async with aiohttp.ClientSession() as s:
        r = await s.get(url)
        data = await r.json()
        top = data["data"].get("top_replies")
        return top[0]["rpid_str"] if top else None
```

**优点**：
- 不需要 Playwright、不需要 cookies
- API 响应始终包含 `rpid_str`，与评论是否带 emoji 无关
- 可并行调用（API 拿 rpid + Playwright 拿文字截图），互不阻塞

**代价**：
- 需要 WBI 签名（B站 API 防爬机制，已有实现可复用）
- 多 2 个 HTTP 请求（~1s）
- 仍需 Playwright 拿评论文字和截图（不能完全替代）
