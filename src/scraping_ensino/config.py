import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    platform_base_url: str
    platform_username: str
    platform_password: str
    download_dir: Path
    headless: bool


def load_settings() -> Settings:
    download_dir = Path(os.getenv("DOWNLOAD_DIR", "./downloads")).resolve()
    download_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        platform_base_url=os.getenv("PLATFORM_BASE_URL", ""),
        platform_username=os.getenv("PLATFORM_USERNAME", ""),
        platform_password=os.getenv("PLATFORM_PASSWORD", ""),
        download_dir=download_dir,
        headless=os.getenv("HEADLESS", "true").lower() == "true",
    )
