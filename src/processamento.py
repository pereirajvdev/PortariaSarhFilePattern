import shutil
from pathlib import Path
from tqdm import tqdm

from logger import log_ok, log_warning
from normalizador import normalizar_arquivo, normalizar_base

def processar_pasta(pasta_entrada: Path, pasta_saida: Path, pasta_ignorados: Path):
    """
    Processa todos os PDFs da pasta de entrada.
    """

    pasta_saida.mkdir(parents=True, exist_ok=True)
    pasta_ignorados.mkdir(parents=True, exist_ok=True)

    arquivos = list(pasta_entrada.glob("*.pdf"))

    if not arquivos:
        print("[INFO] Nenhum arquivo PDF encontrado.")
        return

    print(f"[INFO] Encontrados {len(arquivos)} arquivos.\n")

    processados = 0
    ignorados = 0

    for arquivo in tqdm(
        arquivos,
        desc="Processando",
        unit="arquivo",
        dynamic_ncols=True
    ):

        novo_nome = normalizar_arquivo(arquivo)

        if novo_nome is None:
            destino_ignorado = pasta_ignorados / arquivo.name

            shutil.copy2(
                arquivo,
                destino_ignorado
            )

            log_warning(
                f"Arquivo ignorado: {arquivo.name}"
            )

            ignorados += 1
            continue

        destino = pasta_saida / novo_nome

        shutil.copy2(arquivo, destino)

        log_ok(
            f"Arquivo processado: {arquivo.name} -> {novo_nome}"
        )

        processados += 1

    print()
    print("─" * 50)
    print("Processamento concluído")
    print("─" * 50)
    print(f"✓ Processados: {processados}")
    print(f"! Ignorados:   {ignorados}")
    print("─" * 50)

def processar_base(pasta: Path) -> None:
    """
    Renomeia os PDFs na própria pasta para o padrão básico.
    Não utiliza OCR nem altera o conteúdo dos arquivos.
    """

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

    processados = 0
    ignorados = 0

    print(f"[INFO] Encontrados {len(arquivos)} arquivos PDF.\n")

    for arquivo in arquivos:
        novo_nome = normalizar_base(arquivo)

        if novo_nome is None:
            ignorados += 1
            continue

        destino = arquivo.with_name(novo_nome)

        if destino == arquivo:
            print(f"[OK] Já está no padrão: {arquivo.name}")
            ignorados += 1
            continue

        if destino.exists():
            print(
                f"[AVISO] Destino já existe; arquivo não renomeado: "
                f"{arquivo.name} -> {novo_nome}"
            )
            ignorados += 1
            continue

        arquivo.rename(destino)

        print(f"[RENOMEADO] {arquivo.name} -> {novo_nome}")
        processados += 1

    print("\n" + "=" * 50)
    print("NORMALIZAÇÃO BASE CONCLUÍDA")
    print("=" * 50)
    print(f"Renomeados: {processados}")
    print(f"Não alterados: {ignorados}")
    print("=" * 50)