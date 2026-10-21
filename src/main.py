import argparse
import re
from pathlib import Path

from processamento import processar_pasta


PADRAO_NOME = re.compile(
    r"^Portaria nº \d{3,5}-20\d{2}"
    r" - .+"
    r" - .+"
    r" - [A-Z0-9]+"
    r"(?: - [A-Z0-9]+)*"
    r"(?: - .+)?"
    r"\.pdf$",
    flags=re.IGNORECASE,
)

BASE_NOME = re.compile(
    r"^Portaria nº \d{3,5}-20\d{2}\.pdf$",
    flags=re.IGNORECASE,
)


def verificar_nomes(pasta: Path, padrao: re.Pattern) -> None:
    """Verifica os nomes dos PDFs sem usar OCR ou alterar arquivos."""

    arquivos = sorted(
        (
            arquivo
            for arquivo in pasta.iterdir()
            if arquivo.is_file()
            and arquivo.suffix.lower() == ".pdf"
        ),
        key=lambda arquivo: arquivo.name.lower(),
    )

    if not arquivos:
        print("[INFO] Nenhum arquivo PDF encontrado.")
        return

    fora_padrao = []

    print(f"[INFO] Encontrados {len(arquivos)} arquivos PDF.\n")

    for arquivo in arquivos:
        if padrao.fullmatch(arquivo.name):
            print(f"[OK] {arquivo.name}")
        else:
            print(f"[FORA DO PADRÃO] {arquivo.name}")
            fora_padrao.append(arquivo.name)

    print("\n" + "=" * 60)
    print("RESUMO DA VERIFICAÇÃO")
    print("=" * 60)
    print(f"Arquivos analisados: {len(arquivos)}")
    print(f"Dentro do padrão:   {len(arquivos) - len(fora_padrao)}")
    print(f"Fora do padrão:     {len(fora_padrao)}")
    print("=" * 60)

    if fora_padrao:
        print("\nArquivos que precisam de atenção:")
        for nome in fora_padrao:
            print(f" - {nome}")


def main():
    parser = argparse.ArgumentParser(
        description="Verifica ou normaliza nomes de portarias em PDF."
    )

    parser.add_argument(
        "entrada",
        help="Pasta contendo os arquivos PDF.",
    )

    parser.add_argument(
        "--out",
        help="Pasta onde os arquivos normalizados serão salvos (modo OCR).",
    )

    parser.add_argument(
        "--ignorados",
        help="Pasta onde os arquivos não processados serão salvos (modo OCR).",
    )

    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Ativa o processamento por OCR e a normalização dos arquivos.",
    )

    parser.add_argument(
        "--base",
        action="store_true",
        help="Verifica os arquivos usando o padrão básico de nomes.",
    )

    args = parser.parse_args()

    pasta_entrada = Path(args.entrada)

    if not pasta_entrada.is_dir():
        print(
            f"[ERRO] Pasta de entrada não encontrada "
            f"ou inválida: {pasta_entrada}"
        )
        return

    # Modo --base: verifica somente o padrão básico.
    if args.base:
        verificar_nomes(pasta_entrada, BASE_NOME)
        return

    # Modo de verificação normal: usa o padrão original.
    if not args.ocr:
        verificar_nomes(pasta_entrada, PADRAO_NOME)
        return

    if not args.out or not args.ignorados:
        parser.error(
            "O modo --ocr exige os argumentos --out e --ignorados."
        )

    pasta_saida = Path(args.out)
    pasta_ignorados = Path(args.ignorados)

    processar_pasta(
        pasta_entrada,
        pasta_saida,
        pasta_ignorados,
    )


if __name__ == "__main__":
    main()