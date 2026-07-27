# pinned_dynamic_monitor.py
# 通过 API 自动发现置顶动态，检测置顶是否更换
# 纯检测模块：不发送邮件、不截图，只返回变更信息，由调用方（monitor.py）处理通知
import json
import time
import asyncio
from pathlib import Path
from typing import Optional

from config import UP_UID, UP_NAME, COOKIE_FILE
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


async def check_pinned_dynamic(uid: str = None) -> dict:
    """
    通过 API 发现当前置顶动态，检测是否更换。
    只检测和记录状态，不发送邮件。

    Args:
        uid: B站 UID，默认用 config.UP_UID
    Returns:
        {"changed": bool, "current_id": str|None, "previous_id": str|None, "is_new": bool}
    """
    from bili_api import BiliAPI

    uid = uid or UP_UID
    cookie_file = COOKIE_FILE

    result = {"changed": False, "current_id": None, "previous_id": None, "is_new": False, "api_id": None}

    if not cookie_file.exists():
        logger.warning("置顶监测: Cookie 文件不存在，跳过")
        return result

    bili = BiliAPI(cookie_file)
    raw_items, ok = await bili._fetch_raw(uid)
    await bili.close()

    if not ok:
        logger.warning("置顶监测: API 请求失败，跳过本轮")
        return result

    pinned = _find_pinned(raw_items)
    api_pinned_id = pinned.get("id_str") if pinned else None
    state = _load_state()
    monitored_id = state.get("pinned_dynamic_id")  # 系统正在监控的ID

    result["api_id"] = api_pinned_id
    result["current_id"] = monitored_id or api_pinned_id
    result["previous_id"] = monitored_id

    # 手动模式：API照查，但不自动切换，只上报差异
    if state.get("mode") == "manual":
        if api_pinned_id and api_pinned_id != monitored_id:
            logger.info(f"置顶监测: 手动模式，B站置顶={api_pinned_id}，监控中={monitored_id}，不自动切换")
        else:
            logger.info(f"置顶监测: 手动模式，B站置顶={api_pinned_id} (一致)")
        return result

    # 自动模式 -------------------------------------------------
    if api_pinned_id is None:
        if monitored_id:
            logger.info(f"置顶监测: 置顶动态已消失 (上次: {monitored_id})")
            state["pinned_dynamic_id"] = None
            state["last_change"] = time.strftime("%Y-%m-%d %H:%M:%S")
            _save_state(state)
            result["changed"] = True
        return result

    # 无变化
    if api_pinned_id == monitored_id:
        return result

    # 有变化（首次发现 或 自动更换）
    is_new = (monitored_id is None)
    logger.info(f"置顶监测: {'首次发现' if is_new else '已更换'} 置顶动态 -> {api_pinned_id}")

    # 更新状态文件
    state["pinned_dynamic_id"] = api_pinned_id
    state["last_change"] = time.strftime("%Y-%m-%d %H:%M:%S")
    mod_dyn = (pinned.get("modules", {}).get("module_dynamic") or {})
    desc = mod_dyn.get("desc")
    state["last_pinned_info"] = {
        "dynamic_id": api_pinned_id,
        "type": pinned.get("type", ""),
        "pub_time": (pinned.get("modules", {}).get("module_author", {}).get("pub_time", "")),
        "text": (desc.get("text", "") if desc else "")[:100],
    }
    _save_state(state)

    result["changed"] = True
    result["is_new"] = is_new
    result["current_id"] = api_pinned_id
    return result


def set_mode_manual(dynamic_id: str = None):
    """
    切换到手动模式，可同时指定置顶ID。
    API 自动检测暂停，监控目标保持不变。
    """
    state = _load_state()
    state["mode"] = "manual"
    if dynamic_id:
        state["pinned_dynamic_id"] = dynamic_id
    state["last_change"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_state(state)
    current = state.get("pinned_dynamic_id", "?")
    logger.info(f"置顶监测: 已切换为手动模式 (当前ID={current})")


def set_mode_auto():
    """
    切换到自动模式，API 检测恢复，下次循环自动同步 B站置顶。
    """
    state = _load_state()
    state["mode"] = "auto"
    state["last_change"] = time.strftime("%Y-%m-%d %H:%M:%S")
    _save_state(state)
    logger.info(f"置顶监测: 已切换为自动模式，下次API检测将同步B站置顶")


def get_mode() -> str:
    """返回当前模式 'auto' 或 'manual'"""
    state = _load_state()
    return state.get("mode", "auto")


# ---- 独立运行入口 ----
if __name__ == "__main__":
    async def main():
        print(f"pinned check - {UP_NAME} (UID={UP_UID})")
        result = await check_pinned_dynamic()
        if result["changed"]:
            print(f"Changed! new={result['current_id']} old={result['previous_id']} is_new={result['is_new']}")
        else:
            print(f"No change, current={result['current_id']}")

    asyncio.run(main())
