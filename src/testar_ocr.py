import argparse
from pathlib import Path

from extrator_ocr import analisar_portaria, identificar_tipo_portaria


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
        description="Testa a extração OCR de portarias em PDF."
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

    args = parser.parse_args()

    arquivos = listar_pdfs(args.caminho, args.recursivo)

    if not arquivos:
        print("[INFO] Nenhum arquivo PDF encontrado.")
        return

    print(f"[INFO] Encontrados {len(arquivos)} arquivos PDF.")

    sucessos = 0
    falhas = 0

    for indice, arquivo in enumerate(arquivos, start=1):
        print(f"\n[INFO] Analisando {indice}/{len(arquivos)}: {arquivo.name}")

        try:
            dados = testar_pdf(arquivo, args.texto)

            if (
                dados.get("numero")
                and dados.get("ano")
                and dados.get("servidor")
                and identificar_tipo_portaria(
                    dados.get("texto_extraido") or ""
                )
            ):
                sucessos += 1
            else:
                falhas += 1

        except Exception as erro:
            falhas += 1
            print(f"[ERRO] Falha ao analisar {arquivo.name}: {erro}")

    print("\n" + "=" * 70)
    print("RESUMO DOS TESTES")
    print("=" * 70)
    print(f"PDFs encontrados: {len(arquivos)}")
    print(f"Extrações completas: {sucessos}")
    print(f"Extrações incompletas ou com erro: {falhas}")
    print("[INFO] Nenhum arquivo foi alterado.")


if __name__ == "__main__":
    main()