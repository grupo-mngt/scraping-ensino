"""
Baixa vídeos e materiais de apoio dos seus cursos da UCS Online (Senior).
Uso pessoal, apenas para material ao qual você tem acesso legítimo.
"""
import os
import requests
import re
import subprocess
import json
import mimetypes
from pathlib import Path
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv
from static_ffmpeg import run as static_ffmpeg_run

# Carrega .env da raiz do projeto (um nível acima de scripts/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ============================================================
# CONFIGURAÇÃO
# ============================================================
BASE_HOST = "https://ucsonline.senior.com.br"
BASE_API = f"{BASE_HOST}/action/rest"
BASE_LMS = f"{BASE_API}/lms"
PASTA_DOWNLOADS = "downloads"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Token JWT (UCS_TOKEN) — capturado manualmente do navegador logado.
TOKEN = os.getenv("UCS_TOKEN", "").strip()

# Extensões de recurso a baixar. None = todas.
EXTENSOES_PERMITIDAS = None  # ex: {".pdf", ".docx", ".pptx", ".xlsx", ".zip"}

# Timeouts em segundos para chamadas HTTP (connect, read).
# Evita travar indefinidamente quando o servidor não responde.
HTTP_TIMEOUT = (15, 90)


# ============================================================
# AUTENTICAÇÃO
# ============================================================
def aplicar_token(session, token):
    """Injeta o JWT capturado do navegador no header Authorization."""
    if not token:
        raise RuntimeError(
            "UCS_TOKEN vazio no .env. Cole o valor do cookie 'JWT' do navegador logado."
        )
    if not token.startswith("K "):
        token = f"K {token}"
    session.headers["authorization"] = token
    print("✅ Token aplicado")
    return token


# ============================================================
# UTILS
# ============================================================
def sanitizar_nome(nome):
    if not nome:
        return "sem_nome"
    nome = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', nome).strip()
    nome = re.sub(r'\s+', ' ', nome)
    return nome[:150] or "sem_nome"


def detectar_extensao_da_resposta(r, nome_item):
    """Tenta descobrir a extensão pelo Content-Disposition, Content-Type ou URL."""
    cd = r.headers.get("content-disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^;"\']+)', cd, re.IGNORECASE)
    if m:
        fname = unquote(m.group(1))
        ext = Path(fname).suffix
        if ext:
            return ext.lower()

    url_path = urlparse(r.url).path
    ext = Path(url_path).suffix
    if ext and ext.lower() not in (".php", ".jsp", ".aspx"):
        return ext.lower()

    ct = r.headers.get("content-type", "").split(";")[0].strip()
    if ct:
        ext = mimetypes.guess_extension(ct)
        if ext:
            return ext.lower()

    ext = Path(nome_item).suffix
    return ext.lower() if ext else ".bin"


# ============================================================
# API SENIOR
# ============================================================
def listar_matriculas(session, page_size=200):
    matriculas = []
    start = 0
    while True:
        r = session.post(
            f"{BASE_LMS}/matriculas",
            params={"s": start, "m": page_size},
            json={"statusMatricula": ["MATRICULADO"]},
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        items = data if isinstance(data, list) else data.get("content", data.get("data", []))
        if not items:
            break
        matriculas.extend(items)
        if len(items) < page_size:
            break
        start += page_size
    return matriculas


def pegar_conteudo(session, id_matricula):
    r = session.get(
        f"{BASE_LMS}/matriculas/{id_matricula}/conteudo",
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()


# ============================================================
# EXTRAÇÃO DA ÁRVORE
# ============================================================
def extrair_itens(conteudo, caminho=()):
    """Devolve dois arrays: (videos, recursos)."""
    videos, recursos = [], []
    for item in conteudo:
        nome = (item.get("nome") or "sem_nome").strip()
        tipo = item.get("tipo")
        data = item.get("data") or {}
        href = data.get("href") or ""

        # vídeo Scaleup
        m = re.search(r"player\.scaleup\.com\.br/embed/([a-f0-9]+)", href)
        if m:
            videos.append({"nome": nome, "hash": m.group(1), "caminho": caminho})

        # recurso (PDF, apostila, etc.)
        elif tipo == "RECURSO":
            recursos.append({
                "nome": nome,
                "id": item.get("id"),
                "idFile": data.get("idFile"),
                "subtipo": item.get("subtipo"),
                "caminho": caminho,
            })

        children = item.get("children") or []
        if children:
            v2, r2 = extrair_itens(children, caminho + (nome,))
            videos.extend(v2)
            recursos.extend(r2)

    return videos, recursos


# ============================================================
# DOWNLOAD VÍDEO (Scaleup HLS)
# ============================================================
def extrair_url_playlist(hash_video):
    embed_url = f"https://player.scaleup.com.br/embed/{hash_video}"
    r = requests.get(
        embed_url,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": f"{BASE_HOST}/",
        },
        timeout=HTTP_TIMEOUT,
    )
    r.raise_for_status()
    matches = re.findall(
        r'(https://stream\.scaleup\.com\.br/player/v1/playlists/[a-f0-9]+\?[^\s"\'<>]+)',
        r.text,
    )
    if not matches:
        raise RuntimeError(f"URL playlist não achada no embed {hash_video}")
    return matches[0]


_FFMPEG_DIR: str | None = None


def _ffmpeg_dir() -> str:
    """Garante que ffmpeg/ffprobe estáticos existem e devolve o diretório."""
    global _FFMPEG_DIR
    if _FFMPEG_DIR is None:
        ffmpeg_path, _ = static_ffmpeg_run.get_or_fetch_platform_executables_else_raise()
        _FFMPEG_DIR = str(Path(ffmpeg_path).parent)
    return _FFMPEG_DIR


def baixar_video(hash_video, caminho_saida):
    if caminho_saida.exists() and caminho_saida.stat().st_size > 0:
        print(f"   ⏭️  já existe: {caminho_saida.name}")
        return True

    print(f"   🎬 {caminho_saida.name}")
    try:
        playlist_url = extrair_url_playlist(hash_video)
    except Exception as e:
        print(f"   ❌ extrair URL: {e}")
        return False

    cmd = [
        "yt-dlp", "--no-warnings",
        "--ffmpeg-location", _ffmpeg_dir(),
        "--referer", "https://player.scaleup.com.br/",
        "--user-agent", USER_AGENT,
        "--merge-output-format", "mp4",
        "-o", str(caminho_saida),
        playlist_url,
    ]
    return subprocess.run(cmd).returncode == 0


# ============================================================
# DOWNLOAD RECURSO (PDF, apostila, etc.)
# ============================================================
def baixar_recurso(session, id_matricula, recurso, pasta):
    nome_base = sanitizar_nome(recurso["nome"])

    # se já existe arquivo com qualquer extensão começando por esse nome, pula
    existentes = list(pasta.glob(f"{nome_base}.*"))
    if any(e.stat().st_size > 0 for e in existentes):
        print(f"   ⏭️  já existe: {nome_base}.*")
        return True

    url = f"{BASE_LMS}/matriculas/{id_matricula}/conteudo/{recurso['id']}"
    params = {"curlanguage": "pt", "registrarAcesso": "true", "loadby": "matricula"}

    try:
        r = session.get(
            url, params=params, allow_redirects=True, stream=True,
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()
    except Exception as e:
        print(f"   ❌ pegar recurso '{recurso.get('nome')}': {e}")
        return False

    ct = r.headers.get("content-type", "")

    # CASO A: resposta é JSON com URL pra baixar de fato
    if "json" in ct.lower():
        try:
            payload = r.json()
        except Exception:
            payload = None

        url_arquivo = None
        if isinstance(payload, dict):
            data = payload.get("data") or {}
            for key in ("href", "url", "downloadUrl", "fileUrl"):
                if data.get(key):
                    url_arquivo = data[key]
                    break
                if payload.get(key):
                    url_arquivo = payload[key]
                    break

        if not url_arquivo:
            print("   ⚠️  JSON sem URL clara. Salvando metadata.")
            (pasta / f"{nome_base}.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return False

        r = requests.get(
            url_arquivo,
            headers={"User-Agent": USER_AGENT},
            stream=True,
            timeout=HTTP_TIMEOUT,
        )
        r.raise_for_status()

    # CASO B (já estamos aqui): resposta tem o arquivo (depois de redirect ou direto)
    ext = detectar_extensao_da_resposta(r, recurso["nome"])
    if EXTENSOES_PERMITIDAS and ext not in EXTENSOES_PERMITIDAS:
        print(f"   ⏭️  extensão {ext} ignorada: {nome_base}")
        return True

    saida = pasta / f"{nome_base}{ext}"
    print(f"   📎 {saida.name}")

    with open(saida, "wb") as f:
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if chunk:
                f.write(chunk)

    return True


# ============================================================
# MAIN
# ============================================================
def main():
    session = requests.Session()
    session.headers.update({
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "referer": f"{BASE_HOST}/lms/",
        "user-agent": USER_AGENT,
    })

    aplicar_token(session, TOKEN)

    print("\n🔍 Listando matrículas...")
    matriculas = listar_matriculas(session)
    print(f"   {len(matriculas)} matrícula(s)")

    Path(PASTA_DOWNLOADS).mkdir(exist_ok=True)

    # Índice das matrículas (id, curso, andamento) — útil pra conferência.
    idx = [
        {
            "id": m["id"],
            "curso": m.get("turma", {}).get("curso", {}).get("nome", "?"),
            "andamento": m.get("andamento", 0),
        }
        for m in matriculas
    ]
    with open(f"{PASTA_DOWNLOADS}/_indice.json", "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)

    total = {"videos_ok": 0, "videos_total": 0, "recursos_ok": 0, "recursos_total": 0}

    for m in matriculas:
        id_mat = m["id"]
        nome_curso = m.get("turma", {}).get("curso", {}).get("nome", f"curso_{id_mat}")
        nome_curso_safe = sanitizar_nome(nome_curso)

        print(f"\n📚 [{id_mat}] {nome_curso}")

        try:
            conteudo = pegar_conteudo(session, id_mat)
        except Exception as e:
            print(f"   ❌ conteúdo: {e}")
            continue

        videos, recursos = extrair_itens(conteudo)
        if not videos and not recursos:
            print("   (sem itens)")
            continue

        print(f"   {len(videos)} vídeo(s), {len(recursos)} recurso(s)")
        total["videos_total"] += len(videos)
        total["recursos_total"] += len(recursos)

        for i, v in enumerate(videos, 1):
            partes = [PASTA_DOWNLOADS, nome_curso_safe]
            for p in v["caminho"]:
                partes.append(sanitizar_nome(p))

            pasta = Path(*partes)
            pasta.mkdir(parents=True, exist_ok=True)

            nome_arquivo = f"{i:02d} - {sanitizar_nome(v['nome'])}.mp4"
            arquivo = pasta / nome_arquivo

            if baixar_video(v["hash"], arquivo):
                total["videos_ok"] += 1

        for rec in recursos:
            partes = [PASTA_DOWNLOADS, nome_curso_safe]
            for p in rec["caminho"]:
                partes.append(sanitizar_nome(p))

            pasta = Path(*partes)
            pasta.mkdir(parents=True, exist_ok=True)

            try:
                if baixar_recurso(session, id_mat, rec, pasta):
                    total["recursos_ok"] += 1
            except Exception as e:
                print(f"   ❌ recurso '{rec.get('nome')}' falhou: {e}")

    print(
        f"\n✅ Concluído! "
        f"{total['videos_ok']}/{total['videos_total']} vídeos, "
        f"{total['recursos_ok']}/{total['recursos_total']} recursos."
    )


if __name__ == "__main__":
    main()
