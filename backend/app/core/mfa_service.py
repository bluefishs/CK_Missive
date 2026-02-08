"""
MFA (Multi-Factor Authentication) 服務

提供 TOTP 雙因素認證功能，支援 Google Authenticator / Microsoft Authenticator。

遵循 RFC 6238 (TOTP) 標準。

@version 1.0.0
@date 2026-02-08
"""
import json
import hashlib
import secrets
import logging
from typing import Tuple, List

import pyotp

logger = logging.getLogger(__name__)

# MFA 臨時 token 過期時間（秒）
MFA_TOKEN_EXPIRE_SECONDS = 300  # 5 分鐘


class MFAService:
    """TOTP 雙因素認證服務"""

    ISSUER = "CK_Missive"
    BACKUP_CODES_COUNT = 10

    @staticmethod
    def generate_secret() -> str:
        """生成 TOTP secret (base32 encoded)"""
        return pyotp.random_base32()

    @staticmethod
    def get_totp_uri(secret: str, email: str) -> str:
        """
        生成 TOTP URI（供 QR code 掃描使用）

        Args:
            secret: base32 encoded TOTP secret
            email: 使用者 email（顯示在驗證器 App 中）

        Returns:
            otpauth:// URI 字串
        """
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=MFAService.ISSUER)

    @staticmethod
    def generate_qr_code_base64(uri: str) -> str:
        """
        將 TOTP URI 生成 QR code 並返回 base64 編碼的 PNG 圖片

        Args:
            uri: otpauth:// URI

        Returns:
            base64 encoded PNG image string (不含 data:image/png;base64, 前綴)
        """
        import qrcode
        import io
        import base64

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=6,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        return base64.b64encode(buffer.read()).decode("utf-8")

    @staticmethod
    def verify_totp(secret: str, code: str) -> bool:
        """
        驗證 TOTP code

        允許前後各 1 個時間窗口（30 秒），容錯使用者裝置時鐘偏差。

        Args:
            secret: base32 encoded TOTP secret
            code: 6 位數驗證碼

        Returns:
            True 表示驗證通過
        """
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)

    @staticmethod
    def generate_backup_codes() -> Tuple[List[str], str]:
        """
        生成備用碼

        Returns:
            tuple: (明文碼列表, SHA-256 hashed JSON 字串)
            明文碼僅在設定時顯示一次，後端只儲存 hash
        """
        codes = [
            secrets.token_hex(4).upper()
            for _ in range(MFAService.BACKUP_CODES_COUNT)
        ]
        hashed = [
            hashlib.sha256(c.encode()).hexdigest()
            for c in codes
        ]
        return codes, json.dumps(hashed)

    @staticmethod
    def verify_backup_code(code: str, hashed_codes_json: str) -> Tuple[bool, str]:
        """
        驗證備用碼

        驗證成功後會從列表中移除已使用的備用碼（一次性使用）。

        Args:
            code: 使用者輸入的備用碼
            hashed_codes_json: JSON 格式的 hashed 備用碼列表

        Returns:
            tuple: (是否有效, 更新後的 hashed JSON)
        """
        hashed_input = hashlib.sha256(code.upper().strip().encode()).hexdigest()
        try:
            codes = json.loads(hashed_codes_json)
        except (json.JSONDecodeError, TypeError):
            return False, hashed_codes_json or "[]"

        if hashed_input in codes:
            codes.remove(hashed_input)
            logger.info(f"[MFA] 備用碼已使用，剩餘 {len(codes)} 組")
            return True, json.dumps(codes)

        return False, hashed_codes_json

    @staticmethod
    def get_remaining_backup_codes_count(hashed_codes_json: str) -> int:
        """
        取得剩餘備用碼數量

        Args:
            hashed_codes_json: JSON 格式的 hashed 備用碼列表

        Returns:
            剩餘備用碼數量
        """
        try:
            codes = json.loads(hashed_codes_json)
            return len(codes)
        except (json.JSONDecodeError, TypeError):
            return 0
