"""Cyber-Shield — Prompt Injection protection + Code Safety + encrypted logging"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings
from core.safety.injection import InjectionGuard

logger = logging.getLogger("vrav.shield")


class PromptInjectionShield:
    @classmethod
    def sanitize(cls, prompt: str) -> str:
        return InjectionGuard.check(prompt)


class CodeSafetyFilter:
    DANGEROUS = [
        "os.system", "subprocess.call", "subprocess.Popen", "subprocess.run",
        "eval(", "exec(", "__import__", "rm -rf", "shutil.rmtree",
        "os.remove", "os.unlink", "ctypes.windll", "socket.connect",
        "reverse shell", "bind shell", "meterpreter", "msfvenom",
        "powershell -enc", "base64.b64decode", "pickle.loads",
    ]
    CODE_HINTS = ["```python", "```bash", "```sh", "def ", "import ", "#!/bin", "function "]

    @classmethod
    def looks_like_code(cls, text: str) -> bool:
        return any(h in text for h in cls.CODE_HINTS)

    @classmethod
    def validate(cls, code: str) -> bool:
        if not settings.enable_code_safety_filter:
            return True
        lower = code.lower()
        return not any(kw.lower() in lower for kw in cls.DANGEROUS)


class EncryptedAppendOnlyLogger:
    def __init__(self):
        key = settings.log_encryption_key
        if not key:
            key = Fernet.generate_key().decode()
            logger.info("Generated ephemeral log encryption key")
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        self.path = Path(settings.encrypted_log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, message: str) -> None:
        try:
            encrypted = self.cipher.encrypt(message.encode("utf-8"))
            with open(self.path, "ab") as f:
                f.write(encrypted + b"\n")
        except Exception as e:
            logger.error(f"Failed to write encrypted log: {e}")


_secure_logger: Optional[EncryptedAppendOnlyLogger] = None


def get_secure_logger() -> EncryptedAppendOnlyLogger:
    global _secure_logger
    if _secure_logger is None:
        _secure_logger = EncryptedAppendOnlyLogger()
    return _secure_logger


class ShieldMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            get_secure_logger().log(
                f"{request.method} {request.url.path} → {response.status_code}"
            )
        except Exception:
            pass
        return response
