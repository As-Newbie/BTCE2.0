# email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from bs4 import BeautifulSoup
from logger_config import logger
from config_email import SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD, TO_EMAILS

def send_email(subject: str, content: str, to_emails: list = None) -> bool:
    """
    发送 HTML 邮件（阻塞函数，外层应通过 asyncio.to_thread 调用）表情和分享图片URL自动改为完整URL

    Args:
        subject:邮件主题
        content：邮件内容(HTML)
        to_emails:收件人列表，如果为None则使用默认的TO_EMAILS
    """

    try:
        # 处理 HTML 中相对 URL（保留你的设计）
        soup = BeautifulSoup(content, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if src.startswith("//"):
                img["src"] = "https:" + src

        content_fixed = str(soup)

        msg = MIMEText(content_fixed, "html", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = EMAIL_USER

        # 使用指定的收件人列表，如果为None则使用默认的TO_EMAILS
        recipients = to_emails if to_emails is not None else TO_EMAILS
        msg["To"] = ", ".join(recipients)

        # 建立 SMTP 连接
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, recipients, msg.as_string())

        logger.info(f"📧 邮件发送成功: {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("❌ 邮件认证失败（账号或密码错误）")
        return False
    except Exception as e:
        logger.error(f"❌ 邮件发送失败: {e}")
        return False
