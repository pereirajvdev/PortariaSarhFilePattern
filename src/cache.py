import json
from pathlib import Path


PASTA_PROJETO = Path(__file__).resolve().parent.parent
ARQUIVO_CACHE = PASTA_PROJETO / ".cache_sucesso.json"


def carregar_cache() -> dict:
    if not ARQUIVO_CACHE.exists():
        return {}

    try:
        with ARQUIVO_CACHE.open("r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
            return dados if isinstance(dados, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def salvar_cache(cache: dict) -> None:
    with ARQUIVO_CACHE.open("w", encoding="utf-8") as arquivo:
        json.dump(cache, arquivo, ensure_ascii=False, indent=4)


def arquivo_ja_processado(caminho: Path, cache: dict) -> bool:
    registro = cache.get(caminho.name)

    if not isinstance(registro, dict) or not caminho.is_file():
        return False

    stat = caminho.stat()

    return (
        registro.get("tamanho") == stat.st_size
        and registro.get("modificado") == stat.st_mtime_ns
    )


def registrar_sucesso(caminho: Path, cache: dict) -> None:
    stat = caminho.stat()

    cache[caminho.name] = {
        "tamanho": stat.st_size,
        "modificado": stat.st_mtime_ns,
    }

    salvar_cache(cache)