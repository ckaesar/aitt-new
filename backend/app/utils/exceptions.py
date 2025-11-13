"""
统一异常类型定义
"""
from typing import Optional


class CustomException(Exception):
    def __init__(self, message: str, code: str = "CUSTOM_ERROR", status_code: int = 400, details: Optional[dict] = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationException(CustomException):
    def __init__(self, message: str = "参数验证失败", details: Optional[dict] = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=422, details=details)


class AuthenticationException(CustomException):
    def __init__(self, message: str = "认证失败", details: Optional[dict] = None):
        super().__init__(message=message, code="AUTH_ERROR", status_code=401, details=details)