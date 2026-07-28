import os
import smtplib
import sys
from pathlib import Path
from email.mime.text import MIMEText

BASE_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BASE_DIR / "config" / "private" / "qq_mail.env"

def load_env_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"未找到邮件配置文件: {path}")

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip()

def main() -> None:
    load_env_file(ENV_FILE)

    sender = os.environ["QQ_MAIL_USER"]
    password = os.environ["QQ_MAIL_AUTH_CODE"]
    receiver = os.environ["QQ_MAIL_TO"]

    subject = sys.argv[1] if len(sys.argv) > 1 else "V52选股提醒"
    body = sys.stdin.read().strip()

    if not body:
        body = "V52有候选，但邮件正文为空，请检查脚本日志。"

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
