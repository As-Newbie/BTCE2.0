# email_utils.py
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from bs4 import BeautifulSoup
from config_email import SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD, TO_EMAILS

def send_email(subject: str, content: str) -> bool:
    """
    群发邮件（HTML邮件，表情和分享图片URL自动改为完整URL）
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
    msg["To"] = ", ".join(TO_EMAILS)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, TO_EMAILS, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        return False
    except:
        return False
