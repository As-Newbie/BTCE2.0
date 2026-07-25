# email_utils.py
import smtplib
import re
import time
from email.mime.text import MIMEText
from email.header import Header
from bs4 import BeautifulSoup
from config_email import SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD, TO_EMAILS, STATUS_MONITOR_EMAILS
from config import MAIL_SAVE_DIR
from logger_config import logger


def _save_email_backup(subject: str, content: str):
    """保存邮件HTML备份到本地"""
    try:
        MAIL_SAVE_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        # 清理主题中的非法文件名字符，截断避免路径过长
        safe_subject = re.sub(r'[\\/*?:"<>|]', '', subject)[:60]
        filename = f"{ts}_{safe_subject}.html"
        filepath = MAIL_SAVE_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"邮件已备份: {filename}")
    except Exception as e:
        logger.warning(f"邮件备份失败: {e}")


def send_email(subject: str, content: str, to_emails: list = None) -> bool:
    """
    发送邮件（HTML邮件，表情和分享图片URL自动改为完整URL）

    Args:
        subject: 邮件主题
        content: 邮件内容(HTML)
        to_emails: 收件人列表，如果为None则使用默认的TO_EMAILS
    """
    # 保存邮件备份（SMTP发送前，确保即使发送失败也有备份）
    _save_email_backup(subject, content)

    # 处理 HTML 中图片 URL：补全协议头 + 剥掉B站CDN处理后缀
    soup = BeautifulSoup(content, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if not src:
            continue
        # 补全协议头：// → https://
        if src.startswith("//"):
            src = "https:" + src
        # 剥掉 B站 CDN 图片处理后缀（如 @100w_100h.avif）
        # 否则 CDN 返回 AVIF/WebP 格式，手机邮箱客户端无法渲染
        if 'hdslb.com' in src:
            src = re.sub(r'@[^/?#]+', '', src)
        img["src"] = src

    content_fixed = str(soup)

    msg = MIMEText(content_fixed, "html", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = EMAIL_USER

    # 使用指定的收件人列表，如果没有指定则使用默认的TO_EMAILS
    recipients = to_emails if to_emails is not None else TO_EMAILS
    msg["To"] = ", ".join(recipients)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, recipients, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        return False
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False
