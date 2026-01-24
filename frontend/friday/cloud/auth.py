import json
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass

import httpx

from friday.config import get_config
from friday.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenInfo:
    access_token: str
    token_type: str
    expires_at: datetime | None = None


class AuthManager:
    def __init__(self, token_file: str | Path | None = None):
        self.config = get_config()
        self.token_file = Path(token_file) if token_file else Path.home() / ".friday" / "token.json"
        self._token: TokenInfo | None = None
        self._load_token()

    def _load_token(self):
        if self.token_file.exists():
            try:
                with open(self.token_file, "r") as f:
                    data = json.load(f)
                    expires_at = None
                    if data.get("expires_at"):
                        expires_at = datetime.fromisoformat(data["expires_at"])
                    self._token = TokenInfo(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "bearer"),
                        expires_at=expires_at,
                    )
                    logger.debug("Loaded existing token")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                self._token = None

    def _save_token(self):
        if self._token is None:
            return

        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, "w") as f:
            data = {
                "access_token": self._token.access_token,
                "token_type": self._token.token_type,
            }
            if self._token.expires_at:
                data["expires_at"] = self._token.expires_at.isoformat()
            json.dump(data, f)
        logger.debug("Saved token to file")

    @property
    def is_authenticated(self) -> bool:
        if self._token is None:
            return False
        if self._token.expires_at and datetime.utcnow() >= self._token.expires_at:
            return False
        return True

    @property
    def access_token(self) -> str | None:
        if self.is_authenticated:
            return self._token.access_token
        return None

    def get_auth_header(self) -> dict[str, str]:
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    async def login(self, username: str | None = None, password: str | None = None) -> bool:
        username = username or self.config.cloud.username
        password = password or self.config.cloud.password

        if not username or not password:
            logger.error("Username and password required for login")
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.cloud.server_url}/auth/login",
                    json={"username": username, "password": password},
                )

                if response.status_code == 200:
                    data = response.json()
                    self._token = TokenInfo(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "bearer"),
                        expires_at=datetime.utcnow() + timedelta(days=7),  # Assume 7-day expiry
                    )
                    self._save_token()
                    logger.info("Successfully logged in")
                    return True
                else:
                    logger.error(f"Login failed: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Login error: {e}")
            return False

    async def register(self, username: str, email: str, password: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.cloud.server_url}/auth/register",
                    json={"username": username, "email": email, "password": password},
                )

                if response.status_code == 201:
                    logger.info("Successfully registered")
                    # Auto-login after registration
                    return await self.login(username, password)
                else:
                    logger.error(f"Registration failed: {response.status_code} - {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False

    async def refresh_token(self) -> bool:
        if not self.access_token:
            return False

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.config.cloud.server_url}/auth/refresh",
                    headers=self.get_auth_header(),
                )

                if response.status_code == 200:
                    data = response.json()
                    self._token = TokenInfo(
                        access_token=data["access_token"],
                        token_type=data.get("token_type", "bearer"),
                        expires_at=datetime.utcnow() + timedelta(days=7),
                    )
                    self._save_token()
                    logger.debug("Token refreshed")
                    return True
                else:
                    logger.warning("Token refresh failed")
                    return False

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False

    def logout(self):
        self._token = None
        if self.token_file.exists():
            self.token_file.unlink()
        logger.info("Logged out")
