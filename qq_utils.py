# qq_utils.py
import aiohttp
import asyncio
from typing import List
from logger_config import logger
from config_qq import QQ_BOT_API_URL, QQ_BOT_ACCESS_TOKEN, QQ_GROUP_IDS, QQ_PUSH_ENABLED, MAX_MESSAGE_LENGTH


class QQMessageSender:
    """QQ群消息发送器"""

    def __init__(self):
        self.api_url = QQ_BOT_API_URL
        self.access_token = QQ_BOT_ACCESS_TOKEN
        self.headers = {}

        if self.access_token:
            self.headers = {"Authorization": f"Bearer {self.access_token}"}

    async def send_group_message(self, group_id: str, message: str) -> bool:
        """发送群消息"""
        if not QQ_PUSH_ENABLED:
            logger.info("QQ推送已禁用，跳过发送")
            return True

        # 截断过长的消息
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH - 3] + "..."

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "group_id": group_id,
                    "message": message,
                    "auto_escape": False  # 允许CQ码
                }

                async with session.post(
                        f"{self.api_url}/send_group_msg",
                        json=payload,
                        headers=self.headers,
                        timeout=10
                ) as response:

                    if response.status == 200:
                        result = await response.json()
                        if result.get("status") == "ok":
                            logger.info(f"✅ QQ群 {group_id} 消息发送成功")
                            return True
                        else:
                            logger.error(f"❌ QQ群 {group_id} 消息发送失败: {result}")
                            return False
                    else:
                        logger.error(f"❌ QQ群 {group_id} API请求失败: {response.status}")
                        return False

        except asyncio.TimeoutError:
            logger.error(f"❌ QQ群 {group_id} 消息发送超时")
            return False
        except Exception as e:
            logger.error(f"❌ QQ群 {group_id} 消息发送异常: {e}")
            return False

    async def send_to_all_groups(self, message: str) -> List[bool]:
        """向所有配置的QQ群发送消息"""
        tasks = [self.send_group_message(group_id, message) for group_id in QQ_GROUP_IDS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        success_count = sum(1 for r in results if r is True)
        total_count = len(QQ_GROUP_IDS)

        if success_count == total_count:
            logger.info(f"✅ 所有QQ群消息发送成功 ({success_count}/{total_count})")
        else:
            logger.warning(f"⚠️ QQ群消息发送结果: {success_count}成功, {total_count - success_count}失败")

        return results


# 全局实例
qq_sender = QQMessageSender()


async def send_qq_message(message: str) -> List[bool]:
    """发送QQ群消息（便捷函数）"""
    return await qq_sender.send_to_all_groups(message)