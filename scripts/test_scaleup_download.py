import re
import subprocess

import requests


def baixar_video_scaleup(hash_video: str, nome_saida: str = "aula.mp4") -> bool:
    """
    Dado o hash do vídeo (ex: 69f55165cf8e822a43ce69144542abe72fe88fe9),
    extrai a URL assinada e baixa o vídeo via yt-dlp.
    """
    embed_url = f"https://player.scaleup.com.br/embed/{hash_video}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://ucsonline.senior.com.br/",
    }

    print(f"[1/3] Baixando página embed: {embed_url}")
    r = requests.get(embed_url, headers=headers)
    r.raise_for_status()
    html = r.text

    # Padrão esperado:
    # stream.scaleup.com.br/player/v1/playlists/{HASH}?...&Signature=...&accessToken=...
    pattern = r'(https://stream\.scaleup\.com\.br/player/v1/playlists/[a-f0-9]+\?[^\s"\'<>]+)'
    matches = re.findall(pattern, html)

    if not matches:
        print("Não achei a URL no HTML. Salvando para debug em embed_debug.html")
        with open("embed_debug.html", "w", encoding="utf-8") as f:
            f.write(html)
        return False

    playlist_url = matches[0]
    print(f"[2/3] URL extraída: {playlist_url[:120]}...")

    print("[3/3] Baixando com yt-dlp...")
    cmd = [
        "yt-dlp",
        "--referer", "https://player.scaleup.com.br/",
        "--user-agent", headers["User-Agent"],
        "-o", nome_saida,
        playlist_url,
    ]
    result = subprocess.run(cmd)
    return result.returncode == 0


if __name__ == "__main__":
    hash_teste = "69f55165cf8e822a43ce69144542abe72fe88fe9"
    baixar_video_scaleup(hash_teste, "teste.mp4")
