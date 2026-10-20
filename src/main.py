import argparse
from pathlib import Path

from processamento import processar_pasta

def main():
    parser = argparse.ArgumentParser(
        description="Normaliza nomes de arquivos PDF."
    )

    parser.add_argument(
        "entrada",
        help="Pasta contendo os arquivos PDF."
    )

    parser.add_argument(
        "--out",
        required=True,
        help="Pasta onde os arquivos normalizados serão salvos."
    )

    parser.add_argument(
        "--ignorados",
        required=True,
        help="Pasta onde os arquivos que não puderam ser processados serão salvos."
    )

    args = parser.parse_args()

    pasta_entrada = Path(args.entrada)
    pasta_saida = Path(args.out)
    pasta_ignorados = Path(args.ignorados)

    if not pasta_entrada.exists():
        print(f"[ERRO] Pasta de entrada não encontrada: {pasta_entrada}")
        return

    if not pasta_entrada.is_dir():
        print(f"[ERRO] A entrada não é uma pasta: {pasta_entrada}")
        return

    processar_pasta(pasta_entrada, pasta_saida, pasta_ignorados)

if __name__ == "__main__":
    main()