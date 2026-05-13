import asyncio

from src.scraping_ensino.config import load_settings
from src.scraping_ensino.scraper import run


def main() -> None:
    settings = load_settings()
    asyncio.run(run(settings))


if __name__ == "__main__":
    main()
