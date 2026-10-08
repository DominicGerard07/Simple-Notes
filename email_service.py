import os
import smtplib
from email.message import EmailMessage
from typing import Tuple, Optional

# In-memory store for testing and local development fallback
_last_sent_codes = {}

def get_last_dev_code(email: str) -> Optional[str]:
    """Retrieve the most recently dispatched reset code for an email (for testing/dev)."""
    return _last_sent_codes.get(email.lower().strip())

def send_password_reset_email(to_email: str, code: str) -> Tuple[bool, str]:
    """
    Sends a 6-digit password reset verification code to user's email address.
    If SMTP server is configured via environment variables, sends via real SMTP.
    Otherwise, logs the code to console and stores it in dev cache for offline/local usage.
    """
    clean_email = to_email.lower().strip()
    _last_sent_codes[clean_email] = code

    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = int(os.environ.get("SMTP_PORT", 587))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    smtp_from = os.environ.get("SMTP_FROM", "SimpleNotes <noreply@simplenotes.local>")
    smtp_tls = os.environ.get("SMTP_TLS", "true").lower() in ("true", "1", "yes")

    subject = f"SimpleNotes: Your Password Reset Code [{code}]"
    body = f"""Hello,

You requested a password reset for your SimpleNotes account.

Your 6-digit verification code is:
----------------------------------------
                {code}
----------------------------------------

This code will expire in 15 minutes.
If you did not request this reset, you can safely ignore this email.

Best regards,
The SimpleNotes Team
"""

    if smtp_host:
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = clean_email
            msg.set_content(body)

            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                if smtp_tls:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            print(f"📧 [Email Service] Dispatched reset code to {clean_email} via SMTP ({smtp_host}:{smtp_port})")
            return True, "Email sent via SMTP successfully"
        except Exception as e:
            print(f"⚠️ [Email Service] SMTP send failed: {e}. Falling back to dev logger.")

    # Local development / test / offline mode
    print(f"\n========================================================")
    print(f"📧 [SimpleNotes Mailer] Password Reset Code for {clean_email}: {code}")
    print(f"========================================================\n")
    return True, "Reset code generated and dispatched"

