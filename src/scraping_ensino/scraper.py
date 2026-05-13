from .browser import open_browser
from .config import Settings


async def run(settings: Settings) -> None:
    async with open_browser(settings) as (_, _, page):
        await page.goto(settings.platform_base_url or "about:blank")
        print(f"Página carregada: {await page.title()}")
        # TODO: login + navegação + download de documentos e vídeos
