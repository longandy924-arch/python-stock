import os
import sys
import smtplib
from pathlib import Path
from email.mime.text import MIMEText

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / "config" / "private" / "qq_mail.env"


def load_env():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()


def main():
    load_env()

    sender = os.environ["QQ_MAIL_USER"]
    password = os.environ["QQ_MAIL_AUTH_CODE"]
    receiver = os.environ["QQ_MAIL_TO"]

    subject = sys.argv[1] if len(sys.argv) > 1 else "V52选股提醒"
    body = sys.stdin.read().strip()

    if not body:
        body = "V52今日运行完成，无详细候选信息。"

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject

    with smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=20) as server:
        server.login(sender, password)
        server.sendmail(sender, [receiver], msg.as_string())

    print("QQ邮件通知已发送")


if __name__ == "__main__":
    main()
