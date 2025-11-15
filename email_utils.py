# email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from bs4 import BeautifulSoup
from config_email import SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD, TO_EMAILS, STATUS_MONITOR_EMAILS

def send_email(subject: str, content: str, to_emails: list = None) -> bool:
    """
    发送邮件（HTML邮件，表情和分享图片URL自动改为完整URL）
    
    Args:
        subject: 邮件主题
        content: 邮件内容(HTML)
        to_emails: 收件人列表，如果为None则使用默认的TO_EMAILS
    """
    # 处理 HTML 中相对 URL
    soup = BeautifulSoup(content, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith("//"):
            img["src"] = "https:" + src

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
