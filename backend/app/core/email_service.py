"""
Email 發送服務

提供簡易的 Email 發送功能，支援：
- SMTP 實際發送（生產環境）
- 日誌模擬發送（開發環境，SMTP 未設定時）

@version 1.0.0
@date 2026-02-08
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email 發送服務"""

    @staticmethod
    async def send_email(to: str, subject: str, html_body: str) -> bool:
        """
        發送 Email

        Args:
            to: 收件人地址
            subject: 郵件主旨
            html_body: HTML 格式內容

        Returns:
            True 表示發送成功（或模擬成功），False 表示發送失敗
        """
        smtp_host = settings.SMTP_HOST
        if not smtp_host:
            logger.warning(
                f"[EMAIL] SMTP 未設定，模擬發送: to={to}, subject={subject}"
            )
            logger.info(f"[EMAIL] 內容: {html_body[:500]}")
            return True  # 開發模式模擬成功

        try:
            smtp_port = settings.SMTP_PORT
            smtp_user = settings.SMTP_USER or ""
            smtp_pass = settings.SMTP_PASSWORD or ""
            from_email = settings.EMAIL_FROM or smtp_user

            msg = MIMEMultipart("alternative")
            msg["From"] = from_email
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)

            logger.info(f"[EMAIL] 已發送: to={to}, subject={subject}")
            return True
        except Exception as e:
            logger.error(f"[EMAIL] 發送失敗: {e}")
            return False

    @staticmethod
    async def send_verification_email(
        email: str, token: str, base_url: str
    ) -> bool:
        """
        發送 Email 驗證信

        Args:
            email: 收件人地址
            token: 驗證 token（明文）
            base_url: 前端基礎 URL（如 http://localhost:3000）

        Returns:
            True 表示發送成功
        """
        verify_url = f"{base_url}/verify-email?token={token}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1890ff;">CK_Missive 公文管理系統 - Email 驗證</h2>
            <p>您好，</p>
            <p>請點擊下方連結驗證您的電子郵件：</p>
            <p style="margin: 24px 0;">
                <a href="{verify_url}"
                   style="background-color: #1890ff; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    驗證我的 Email
                </a>
            </p>
            <p style="color: #666;">此連結將在 24 小時後失效。</p>
            <p style="color: #999; font-size: 12px;">
                如果您未註冊此系統，請忽略此信件。
            </p>
        </div>
        """
        return await EmailService.send_email(
            email, "CK_Missive - 電子郵件驗證", html
        )

    @staticmethod
    async def send_password_reset_email(
        email: str, token: str, base_url: str
    ) -> bool:
        """
        發送密碼重設 Email

        Args:
            email: 收件人地址
            token: 重設 token（明文）
            base_url: 前端基礎 URL

        Returns:
            True 表示發送成功
        """
        reset_url = f"{base_url}/reset-password?token={token}"
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1890ff;">CK_Missive 公文管理系統 - 密碼重設</h2>
            <p>您好，</p>
            <p>請點擊下方連結重設您的密碼：</p>
            <p style="margin: 24px 0;">
                <a href="{reset_url}"
                   style="background-color: #1890ff; color: white; padding: 12px 24px;
                          text-decoration: none; border-radius: 4px; display: inline-block;">
                    重設密碼
                </a>
            </p>
            <p style="color: #666;">此連結將在 15 分鐘後失效。</p>
            <p style="color: #999; font-size: 12px;">
                如果您未請求重設密碼，請忽略此信件。
            </p>
        </div>
        """
        return await EmailService.send_email(
            email, "CK_Missive - 密碼重設", html
        )
