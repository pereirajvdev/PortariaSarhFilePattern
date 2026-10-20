import argparse
from pathlib import Path

from extrator_ocr import analisar_portaria, identificar_tipo_portaria
from normalizador import normalizar_arquivo
from cache import (
    carregar_cache,
    arquivo_ja_processado,
    registrar_sucesso,
)

def listar_pdfs(caminho: Path, recursivo: bool = False) -> list[Path]:
    """Retorna os PDFs de um arquivo ou de uma pasta."""

    if caminho.is_file():
        if caminho.suffix.lower() == ".pdf":
            return [caminho]

        return []

    if not caminho.is_dir():
        print(f"[ERRO] Caminho não encontrado: {caminho}")
        return []

    if recursivo:
        arquivos = caminho.rglob("*")
    else:
        arquivos = caminho.iterdir()

    return sorted(
        (
            arquivo
            for arquivo in arquivos
            if arquivo.is_file() and arquivo.suffix.lower() == ".pdf"
        ),
        key=lambda arquivo: arquivo.name.lower(),
    )


def mover_nao_padronizado(arquivo: Path, pasta_destino: Path) -> Path:
    """Move um PDF não padronizado para a pasta de destino."""

    pasta_destino = pasta_destino.resolve()
    arquivo_resolvido = arquivo.resolve()

    # Evita mover um arquivo para a mesma pasta.
    if arquivo_resolvido.parent == pasta_destino:
        raise ValueError(
            "O arquivo já está na pasta de não padronizados."
        )

    pasta_destino.mkdir(parents=True, exist_ok=True)

    destino = pasta_destino / arquivo.name

    # Não sobrescreve arquivos existentes.
    if destino.exists():
        raise FileExistsError(
            f"Já existe um arquivo com esse nome no destino: {destino}"
        )

    arquivo.rename(destino)

    return destino


def testar_pdf(caminho: Path, mostrar_texto: bool = False) -> dict:
    """Analisa um PDF e exibe os dados extraídos."""

    dados = analisar_portaria(caminho)

    texto = dados.get("texto_extraido") or ""
    tipo = identificar_tipo_portaria(texto)

    print("\n" + "=" * 70)
    print(f"arquivo             : {dados.get('arquivo', caminho.name)}")
    print(f"metodo              : {dados.get('metodo')}")
    print(f"numero              : {dados.get('numero')}")
    print(f"ano                 : {dados.get('ano')}")
    print(f"tipo                : {tipo}")
    print(f"verbo               : {dados.get('verbo')}")
    print(f"servidor             : {dados.get('servidor')}")
    print(f"secretarias          : {dados.get('secretarias')}")
    print(f"resolve_encontrado   : {dados.get('resolve_encontrado')}")

    if mostrar_texto:
        print("\n--- TEXTO EXTRAÍDO ---")
        print(texto)

    return dados


def main():
    parser = argparse.ArgumentParser(
        description="Testa o OCR e renomeia portarias em PDF."
    )

    parser.add_argument(
        "caminho",
        type=Path,
        help="Caminho de um PDF ou de uma pasta com PDFs.",
    )

    parser.add_argument(
        "--texto",
        action="store_true",
        help="Exibe o texto completo extraído de cada PDF.",
    )

    parser.add_argument(
        "--recursivo",
        action="store_true",
        help="Percorre também as subpastas.",
    )

    parser.add_argument(
        "--notstd",
        type=Path,
        metavar="FOLDER",
        help="Move PDFs não padronizados para a pasta informada.",
    )

    args = parser.parse_args()

    arquivos = listar_pdfs(args.caminho, args.recursivo)

    if not arquivos:
        print("[INFO] Nenhum arquivo PDF encontrado.")
        return

    print(f"[INFO] Encontrados {len(arquivos)} arquivos PDF.")

    sucessos = 0
    falhas = 0
    ignorados = 0

    cache = carregar_cache()

    for indice, arquivo in enumerate(arquivos, start=1):
        print(
            f"\n[INFO] Processando "
            f"{indice}/{len(arquivos)}: {arquivo.name}"
        )

        try:
            if arquivo_ja_processado(arquivo, cache):
                print(f"[CACHE] Já processado com sucesso: {arquivo.name}")
                continue
            
            # Extrai e apresenta os dados encontrados.
            dados = testar_pdf(arquivo, args.texto)

            # Gera o nome padronizado conforme as regras do projeto.
            novo_nome = normalizar_arquivo(arquivo)

            if not novo_nome:
                if args.notstd:
                    try:
                        destino = mover_nao_padronizado(
                            arquivo,
                            args.notstd,
                        )

                        ignorados += 1

                        print(
                            "[AVISO] Não foi possível padronizar o arquivo."
                        )
                        print(
                            f"[OK] Movido para: {destino}"
                        )

                    except Exception as erro:
                        falhas += 1
                        print(
                            f"[ERRO] Não foi possível mover "
                            f"{arquivo.name}: {erro}"
                        )
                else:
                    ignorados += 1
                    print(
                        "[AVISO] Não foi possível gerar o nome. "
                        "Arquivo mantido."
                    )

                continue

            destino = arquivo.with_name(novo_nome)

            # Se o nome já estiver correto, registra o sucesso no cache.
            if destino == arquivo:
                registrar_sucesso(arquivo, cache)
                sucessos += 1
                print(f"[OK] Nome já padronizado: {arquivo.name}")
                continue

            # Não sobrescreve outro arquivo existente.
            if destino.exists():
                falhas += 1
                print(f"[ERRO] O destino já existe: {destino.name}")
                print("[INFO] Arquivo original mantido.")
                continue

            # Renomeia e registra no cache somente após o sucesso.
            arquivo.rename(destino)

            registrar_sucesso(destino, cache)

            sucessos += 1
            print(f"[OK] Renomeado para: {destino.name}")

        except Exception as erro:
            falhas += 1
            print(f"[ERRO] Falha em {arquivo.name}: {erro}")

    print("\n" + "=" * 70)
    print("RESUMO DO PROCESSAMENTO")
    print("=" * 70)
    print(f"PDFs encontrados: {len(arquivos)}")
    print(f"Renomeados ou já padronizados: {sucessos}")
    print(f"Não foi possível renomear: {falhas}")
    print(f"Ignorados por falta de dados: {ignorados}")


if __name__ == "__main__":
    main()