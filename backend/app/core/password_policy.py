"""
密碼策略模組

@version 1.0.0
@date 2026-02-02

提供密碼強度驗證功能:
- 最小長度要求 (預設 12 字元)
- 複雜度要求 (大小寫、數字、特殊字元)
- 常見密碼檢查
- 用戶名相似度檢查

使用方式:
    from app.core.password_policy import PasswordPolicy, validate_password

    # 使用預設策略
    is_valid, message = validate_password("MyP@ssw0rd123")

    # 自訂策略
    policy = PasswordPolicy(min_length=16, require_special=True)
    is_valid, message = policy.validate("CustomPassword")
"""

import re
from typing import Tuple, Optional
from dataclasses import dataclass, field


# 常見弱密碼列表 (部分)
COMMON_PASSWORDS = {
    "password", "123456", "12345678", "qwerty", "abc123",
    "monkey", "1234567", "letmein", "trustno1", "dragon",
    "baseball", "iloveyou", "master", "sunshine", "ashley",
    "foobar", "passw0rd", "shadow", "123123", "654321",
    "password1", "password123", "admin", "admin123", "root",
    "toor", "pass", "test", "guest", "master", "changeme",
}


@dataclass
class PasswordPolicy:
    """密碼策略配置"""

    min_length: int = 12
    max_length: int = 128
    require_uppercase: bool = True
    require_lowercase: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_characters: str = "!@#$%^&*(),.?\":{}|<>-_=+[]\\';/`~"
    check_common_passwords: bool = True
    check_username_similarity: bool = True

    def validate(
        self,
        password: str,
        username: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        驗證密碼是否符合策略

        Args:
            password: 要驗證的密碼
            username: 可選的用戶名，用於檢查相似度

        Returns:
            Tuple[bool, str]: (是否有效, 訊息)
        """
        # 長度檢查
        if len(password) < self.min_length:
            return False, f"密碼長度至少需要 {self.min_length} 個字元"

        if len(password) > self.max_length:
            return False, f"密碼長度不能超過 {self.max_length} 個字元"

        # 大寫字母檢查
        if self.require_uppercase and not re.search(r'[A-Z]', password):
            return False, "密碼必須包含至少一個大寫字母"

        # 小寫字母檢查
        if self.require_lowercase and not re.search(r'[a-z]', password):
            return False, "密碼必須包含至少一個小寫字母"

        # 數字檢查
        if self.require_digit and not re.search(r'\d', password):
            return False, "密碼必須包含至少一個數字"

        # 特殊字元檢查
        if self.require_special:
            special_pattern = f'[{re.escape(self.special_characters)}]'
            if not re.search(special_pattern, password):
                return False, "密碼必須包含至少一個特殊字元 (!@#$%^&* 等)"

        # 常見密碼檢查
        if self.check_common_passwords:
            if password.lower() in COMMON_PASSWORDS:
                return False, "密碼過於常見，請使用更複雜的密碼"

        # 用戶名相似度檢查
        if self.check_username_similarity and username:
            username_lower = username.lower()
            password_lower = password.lower()
            if username_lower in password_lower:
                return False, "密碼不能包含用戶名"
            if password_lower in username_lower:
                return False, "密碼不能是用戶名的一部分"

        return True, "密碼強度符合要求"

    def get_strength_score(self, password: str) -> int:
        """
        計算密碼強度分數 (0-100)

        Args:
            password: 要評估的密碼

        Returns:
            int: 強度分數 (0-100)
        """
        score = 0

        # 長度分數 (最高 25 分)
        length_score = min(len(password) * 2, 25)
        score += length_score

        # 字元類型分數 (每種 15 分，最高 60 分)
        if re.search(r'[a-z]', password):
            score += 15
        if re.search(r'[A-Z]', password):
            score += 15
        if re.search(r'\d', password):
            score += 15
        if re.search(f'[{re.escape(self.special_characters)}]', password):
            score += 15

        # 混合度分數 (最高 15 分)
        unique_chars = len(set(password))
        if unique_chars >= 10:
            score += 15
        elif unique_chars >= 7:
            score += 10
        elif unique_chars >= 5:
            score += 5

        return min(score, 100)

    def get_strength_label(self, password: str) -> str:
        """
        取得密碼強度標籤

        Args:
            password: 要評估的密碼

        Returns:
            str: 強度標籤 (弱/中/強/非常強)
        """
        score = self.get_strength_score(password)
        if score < 40:
            return "弱"
        elif score < 60:
            return "中"
        elif score < 80:
            return "強"
        else:
            return "非常強"


# 預設密碼策略實例
default_policy = PasswordPolicy()


def validate_password(
    password: str,
    username: Optional[str] = None,
    policy: Optional[PasswordPolicy] = None
) -> Tuple[bool, str]:
    """
    使用指定策略驗證密碼

    Args:
        password: 要驗證的密碼
        username: 可選的用戶名
        policy: 可選的密碼策略，預設使用 default_policy

    Returns:
        Tuple[bool, str]: (是否有效, 訊息)
    """
    if policy is None:
        policy = default_policy
    return policy.validate(password, username)


def get_password_strength(password: str) -> dict:
    """
    取得密碼強度資訊

    Args:
        password: 要評估的密碼

    Returns:
        dict: 包含 score 和 label 的字典
    """
    return {
        "score": default_policy.get_strength_score(password),
        "label": default_policy.get_strength_label(password)
    }
