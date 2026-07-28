# qq_message_generator.py
from bs4 import BeautifulSoup
from logger_config import logger
from config import QQ_PINNED_UPDATE_TEXT, QQ_SINGLE_LINK_LABEL, QQ_SINGLE_TIME_LABEL


class QQMessageGenerator:
    """QQ消息生成类"""

    def generate_qq_message(self, up_name: str, dynamic_id: str, current_html: str, current_time: str,
                            current_images: list, screenshot_path: str = None) -> str:
        """生成QQ群推送消息（优先用截图，失败兜底文字+表情+评论区图片）"""
        try:
            qq_message = f"【{up_name}】{QQ_PINNED_UPDATE_TEXT}\n"

            if screenshot_path:
                # 截图模式：只用截图替换文字+表情+评论区图片
                qq_message += f"[CQ:image,file=file:///{screenshot_path.replace(chr(92), '/')}]\n"
            else:
                # 兜底模式：旧版文字+表情alt+评论区图片
                soup = BeautifulSoup(current_html, "html.parser")
                for img in soup.find_all("img"):
                    alt_text = img.get("alt", "")
                    if alt_text:
                        img.replace_with(alt_text)
                    else:
                        img.decompose()
                text_content = soup.get_text(strip=True)
                qq_message += f"{text_content}\n"

                if current_images:
                    qq_message += "📸 图片：\n"
                    for i, img_url in enumerate(current_images[:9]):
                        qq_message += f"[CQ:image,file={img_url}]\n"
                    if len(current_images) > 9:
                        qq_message += f"... 还有 {len(current_images) - 9} 张图片\n"

            qq_message += "----------------\n"
            qq_message += f"检测时间: {current_time}\n"
            qq_message += f"监测动态: https://t.bilibili.com/{dynamic_id}\n"
            qq_message += "----------------"

            return qq_message

        except Exception as e:
            logger.error(f" 生成QQ消息失败: {e}")
            # 备用消息格式
            backup_msg = f"【{up_name}】置顶评论更新通知\n动态: {dynamic_id}\n时间: {current_time}"
            if current_images:
                backup_msg += f"\n包含 {len(current_images)} 张图片"
            return backup_msg

    def generate_degraded_message(self, up_name: str, dynamic_id: str, current_html: str, current_time: str,
                                  current_images: list, original_failed: bool = False) -> str:
        """生成降级消息（不含图片CQ码，仅文字提示）"""
        try:
            # 使用BeautifulSoup处理HTML，将表情图片替换为alt文字
            soup = BeautifulSoup(current_html, "html.parser")

            # 找到所有表情图片，替换为alt属性中的文字
            for img in soup.find_all("img"):
                alt_text = img.get("alt", "")
                if alt_text:
                    img.replace_with(alt_text)
                else:
                    img.decompose()

            # 提取纯文本内容
            text_content = soup.get_text(strip=True)

            # 生成降级消息
            degraded_message = f"【{up_name}】{QQ_PINNED_UPDATE_TEXT}\n"
            degraded_message += f"{text_content}\n"

            # 添加图片提示（不含CQ码）
            if current_images:
                if original_failed:
                    degraded_message += "⚠️ 图片推送超时，已启用降级模式\n"
                degraded_message += f"📸 包含 {len(current_images)} 张图片，请自行查看动态\n"

            degraded_message += "----------------\n"
            degraded_message += f"检测时间: {current_time}\n"
            degraded_message += f"监测动态: https://t.bilibili.com/{dynamic_id}\n"

            if original_failed:
                degraded_message += "🚨 消息已降级（图片推送超时）\n"

            degraded_message += "----------------"

            return degraded_message

        except Exception as e:
            logger.error(f"❌ 生成降级消息失败: {e}")
            # 最终的备用消息
            return f"【{up_name}】动态更新通知\n动态ID: {dynamic_id}\n时间: {current_time}\n⚠️ 包含图片，请查看原动态"

    def generate_new_dynamic_qq_message(self, up_name: str, dynamic_id: str, dynamic_url: str,
                                        current_time: str, content_text: str = "",
                                        screenshot_path: str = None) -> str:
        """生成新动态 QQ 群推送消息（支持截图）"""
        parts = [f"【{up_name}】发布了新动态~"]
        if screenshot_path:
            parts.append(f"[CQ:image,file=file:///{screenshot_path.replace(chr(92), '/')}]")
        if content_text:
            parts.append(content_text[:300])
        parts.append(f"{QQ_SINGLE_LINK_LABEL} {dynamic_url}")
        parts.append(f"{QQ_SINGLE_TIME_LABEL} {current_time}")
        return '\n'.join(parts)


# 全局实例
qq_message_generator = QQMessageGenerator()