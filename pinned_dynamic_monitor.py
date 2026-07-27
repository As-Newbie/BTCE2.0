# pinned_dynamic_monitor.py
# 通过 API 自动发现置顶动态，监测置顶更换并邮件通知管理邮箱
# 可独立运行，也可被 monitor.py 导入调用
import json
import time
import asyncio
from pathlib import Path
from typing import Optional

from config import UP_UID, UP_NAME, COOKIE_FILE
from config_email import STATUS_MONITOR_EMAILS
from email_utils import send_email
from logger_config import logger

STATE_FILE = Path(__file__).parent / "pinned_dynamic_state.json"


def _load_state() -> dict:
    """加载本地状态文件"""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    """保存状态到本地"""
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_pinned(raw_items: list[dict]) -> Optional[dict]:
    """从 API 原始 items 列表中找出置顶动态（检查 modules.module_tag.text）"""
    for item in raw_items:
        modules = item.get("modules", {})
        tag = modules.get("module_tag") or {}
        if tag.get("text") == "置顶":
            return item
    return None


def _extract_info(item: dict) -> dict:
    """从一条 raw item 中提取置顶通知所需的关键信息"""
    modules = item.get("modules", {})
    author = modules.get("module_author", {})
    mod_dyn = modules.get("module_dynamic", {})
    mod_stat = modules.get("module_stat", {})

    # 文本内容
    desc = mod_dyn.get("desc")
    text = (desc.get("text", "") if desc else "")[:200]

    # 图片列表
    major = mod_dyn.get("major") or {}
    draw = major.get("draw") or {}
    images = [di.get("src", "") for di in draw.get("items", [])]

    # 动态类型
    dyn_type = item.get("type", "")

    # 发布时间
    pub_ts_str = author.get("pub_ts", "")
    pub_time_label = author.get("pub_time", "")

    return {
        "dynamic_id": item.get("id_str", ""),
        "type": dyn_type,
        "text": text,
        "images": images,
        "pub_ts": pub_ts_str,
        "pub_time": pub_time_label,
        "like_count": mod_stat.get("like", {}).get("count", 0),
        "comment_count": mod_stat.get("comment", {}).get("count", 0),
    }


def _build_email_html(info: dict, is_new: bool, previous_info: Optional[dict] = None) -> str:
    """生成置顶动态变更通知的 HTML 邮件"""
    dyn_id = info["dynamic_id"]
    url = f"https://t.bilibili.com/{dyn_id}"
    ct = time.strftime("%Y-%m-%d %H:%M:%S")

    if is_new:
        title = f"[{UP_NAME}] 首次记录置顶动态"
        change_desc = "系统首次发现置顶动态并记录。"
    else:
        title = f"[{UP_NAME}] 置顶动态已更换"
        prev_id = (previous_info or {}).get("dynamic_id", "?")
        change_desc = f"置顶动态 ID 已从 {prev_id} 更换为 {dyn_id}。"

    # 图片 HTML
    img_html = ""
    for src in info["images"][:3]:
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("http://"):
            src = src.replace("http://", "https://")
        img_html += f'<img src="{src}" style="max-width:600px;margin:4px 0;display:block;" />'

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head><body>
<h2>{title}</h2>
<p><strong>变更时间:</strong> {ct}</p>
<p><strong>变更说明:</strong> {change_desc}</p>
<hr>
<h3>新置顶动态信息</h3>
<table style="border-collapse:collapse;width:100%;max-width:700px">
  <tr><td style="padding:6px;border:1px solid #ddd;background:#f5f5f5;width:100px"><strong>动态ID</strong></td>
      <td style="padding:6px;border:1px solid #ddd">{dyn_id}</td></tr>
  <tr><td style="padding:6px;border:1px solid #ddd;background:#f5f5f5"><strong>纯数字ID</strong></td>
      <td style="padding:6px;border:1px solid #ddd;font-family:monospace">{dyn_id}</td></tr>
  <tr><td style="padding:6px;border:1px solid #ddd;background:#f5f5f5"><strong>类型</strong></td>
      <td style="padding:6px;border:1px solid #ddd">{info['type']}</td></tr>
  <tr><td style="padding:6px;border:1px solid #ddd;background:#f5f5f5"><strong>发布时间</strong></td>
      <td style="padding:6px;border:1px solid #ddd">{info['pub_time']}</td></tr>
  <tr><td style="padding:6px;border:1px solid #ddd;background:#f5f5f5"><strong>点赞/评论</strong></td>
      <td style="padding:6px;border:1px solid #ddd">点赞 {info['like_count']} / 评论 {info['comment_count']}</td></tr>
  <tr><td style="padding:6px;border:1px solid #ddd;background:#f5f5f5"><strong>链接</strong></td>
      <td style="padding:6px;border:1px solid #ddd"><a href="{url}">{url}</a></td></tr>
</table>
<br>
<p><strong>内容:</strong> {info['text'] or '(无文字)'}</p>
{img_html}
<hr>
<p style="color:#999;font-size:12px">此邮件由 BTCE 置顶动态监测模块自动发送</p>
</body></html>"""


async def check_pinned_dynamic(uid: str = None) -> Optional[str]:
    """
    通过 API 发现当前置顶动态，检测是否更换，更换时发邮件通知。
    返回当前置顶动态 ID，无置顶则返回 None。

    Args:
        uid: B站 UID，默认用 config.UP_UID
    Returns:
        当前置顶动态 ID 字符串，或 None
    """
    from bili_api import BiliAPI

    uid = uid or UP_UID
    cookie_file = COOKIE_FILE

    if not cookie_file.exists():
        logger.warning("置顶监测: Cookie 文件不存在，跳过")
        return None

    bili = BiliAPI(cookie_file)
    raw_items, ok = await bili._fetch_raw(uid)
    await bili.close()

    if not ok:
        logger.warning("置顶监测: API 请求失败，跳过本轮")
        return None

    pinned = _find_pinned(raw_items)
    current_pinned_id = pinned.get("id_str") if pinned else None
    state = _load_state()
    last_pinned_id = state.get("pinned_dynamic_id")

    # 无变化
    if current_pinned_id and current_pinned_id == last_pinned_id:
        return current_pinned_id

    # 有变化（首次 / 更换 / 消失）
    if current_pinned_id is None:
        if last_pinned_id:
            logger.info(f"置顶监测: 置顶动态已消失 (上次: {last_pinned_id})")
            state["pinned_dynamic_id"] = None
            state["last_change"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save_state(state)
        return None

    # 有置顶，但 ID 变了
    info = _extract_info(pinned)
    is_new = (last_pinned_id is None)

    logger.info(f"置顶监测: {'首次发现' if is_new else '已更换'} 置顶动态 -> {current_pinned_id}")

    # 构建并发送邮件
    previous_info = None
    if not is_new:
        previous_info = state.get("last_pinned_info", {})
        # 尝试补全上次信息：如果之前只有 ID 没有详情，补一个简单 dict
        if not previous_info or not previous_info.get("dynamic_id"):
            previous_info = {"dynamic_id": last_pinned_id}

    html = _build_email_html(info, is_new, previous_info)
    subject = f"[{UP_NAME}] 置顶动态{'首次记录' if is_new else '已更换'}"
    try:
        # send_email 在 asyncio.to_thread 中调用以不阻塞事件循环
        await asyncio.to_thread(send_email, subject=subject, content=html,
                                to_emails=STATUS_MONITOR_EMAILS)
        logger.info(f"置顶监测: 通知邮件已发送 -> {STATUS_MONITOR_EMAILS}")
    except Exception as e:
        logger.error(f"置顶监测: 发送邮件失败: {e}")

    # 更新状态
    state["pinned_dynamic_id"] = current_pinned_id
    state["last_change"] = time.strftime("%Y-%m-%d %H:%M:%S")
    state["last_pinned_info"] = {
        "dynamic_id": info["dynamic_id"],
        "type": info["type"],
        "pub_time": info["pub_time"],
        "text": info["text"][:100],
    }
    _save_state(state)

    return current_pinned_id


# ---- 独立运行入口 ----
if __name__ == "__main__":
    async def main():
        print(f"置顶动态监测 - {UP_NAME} (UID={UP_UID})")
        result = await check_pinned_dynamic()
        if result:
            state = _load_state()
            print(f"当前置顶动态 ID: {result}")
            print(f"上次变更: {state.get('last_change', '未知')}")
            info = state.get("last_pinned_info", {})
            if info:
                print(f"  类型: {info.get('type')}")
                print(f"  时间: {info.get('pub_time')}")
                print(f"  内容: {info.get('text', '')[:80]}")
        else:
            print("当前无置顶动态")

    asyncio.run(main())
