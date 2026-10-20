import re
from pathlib import Path

from extrator_ocr import analisar_portaria, identificar_tipo_portaria
from setores import identificar_setor
from nomes import normalizar_nome
from logger import log_warning
from datas import (
    completar_periodo,
    formatar_periodo,
    extrair_periodo,
)

TIPOS_PORTARIA = {
    "LDPF",
    "LTS",
    "LP",
    "AP",
    "L Luto",
    "READAPT",
    "L CAT",
    "LG"
}

def normalizar_portaria_ocr(caminho: Path) -> str | None:
    """Gera o nome padronizado usando os dados extraídos por OCR."""

    dados = analisar_portaria(caminho)

    numero = dados.get("numero")
    ano = dados.get("ano")
    servidor = dados.get("servidor")
    secretarias = dados.get("secretarias") or []
    texto = dados.get("texto_extraido") or ""

    tipo = identificar_tipo_portaria(texto)

    if not numero or not ano or not tipo or not servidor:
        log_warning(
            f"Dados insuficientes no OCR para renomear: {caminho.name}"
        )
        return None

    nome = normalizar_nome(servidor)

    # Remove siglas repetidas sem alterar a ordem.
    setores = list(dict.fromkeys(
        setor.upper().strip()
        for setor in secretarias
        if setor and setor.strip()
    ))

    if not setores:
        log_warning(
            f"Nenhuma secretaria identificada no OCR: {caminho.name}"
        )
        return None

    portaria = f"Portaria nº {numero}-{ano}"
    setores_texto = " - ".join(setores)

    return f"{portaria} - {tipo} - {nome} - {setores_texto}.pdf"

def normalizar_arquivo(caminho: Path) -> str | None:
    """
    Recebe o caminho de um PDF e tenta gerar o novo nome.
    """

    nome_original = caminho.stem

    # Remove as letras do nome antes de verificar o padrão numérico.
    nome_numerico = re.sub(r"[^\d\s/_-]", "", nome_original)

    # PDFs com nome numérico, inclusive "Portaria nº 003-2026",
    # utilizam OCR para identificar os dados da portaria.
    if re.fullmatch(r"\s*\d{1,5}\s*[-_/]\s*20\d{2}\s*", nome_numerico):
        return normalizar_portaria_ocr(caminho)
    
    # Identifica e remove o prefixo do arquivo
    resultado_portaria = re.match(
        r"^\s*(Portaria\s+n[ºo°]?\s*\d+\s*-\s*\d{4})\s*-\s*(.*)$",
        nome_original,
        flags=re.IGNORECASE
    )

    if resultado_portaria is None:
        log_warning(f"Portaria não identificada: {caminho.name}")
        return None

    portaria = resultado_portaria.group(1).strip()
    texto = resultado_portaria.group(2).strip()

    tipo_encontrado = None
    texto_restante = None

    for tipo in sorted(TIPOS_PORTARIA, key=len, reverse=True):

        # Permite variações de espaços no tipo.
        # Ex.: "AP" e "A P" são equivalentes.
        if tipo == "AP":
            padrao_tipo = r"A\s*P"
        else:
            partes_tipo = tipo.split()
            padrao_tipo = r"\s*".join(map(re.escape, partes_tipo))

        resultado_tipo = re.match(
            rf"^\s*{padrao_tipo}(?=\s|$|-)",
            texto,
            flags=re.IGNORECASE
        )

        if resultado_tipo:
            tipo_encontrado = tipo
            texto_restante = texto[resultado_tipo.end():].lstrip(" -")

            # Remove o tipo caso ele apareça novamente no início do texto.
            padrao_tipo_repetido = re.match(
                r"^\s*" + re.escape(tipo_encontrado) + r"(?=\s|$|-)",
                texto_restante,
                flags=re.IGNORECASE
            )

            if padrao_tipo_repetido:
                texto_restante = texto_restante[padrao_tipo_repetido.end():].lstrip(" -")
            break

    if tipo_encontrado is None:
        log_warning(
            f"Tipo de portaria não identificado: {caminho.name}"
        )
        return None

    tipo = tipo_encontrado.upper()

    # Substitui underscore por hífen    
    texto = texto_restante.replace("_", "-")

    # Identifica a marcação de contrato
    eh_contrato = bool(
        re.search(r"\s+(?:CONT|CONTRATO)\s+(?=-)", texto, re.IGNORECASE)
    )

    # Remove a marcação do texto para facilitar a identificação do nome
    if eh_contrato:
        texto = re.sub(
            r"\s+(?:CONT|CONTRATO)\s+(?=-)",
            " ",
            texto,
            flags=re.IGNORECASE
        )

    # converte espaços multiplicados em único
    texto = re.sub(r"\s+", " ", texto).strip()

    resultado_periodo = extrair_periodo(texto)

    if resultado_periodo is None:
        inicio = None
        fim = None
        texto_sem_periodo = texto
    else:
        inicio, fim, inicio_pos, fim_pos = resultado_periodo

        # Remove exatamente o período encontrado
        texto_sem_periodo = texto[:inicio_pos] + texto[fim_pos:]

    # Limpa separadores duplicados
    texto_sem_periodo = re.sub(
        r"\s*[-–—]\s*",
        " - ",
        texto_sem_periodo
    )

    partes = [
        parte.strip()
        for parte in texto_sem_periodo.split(" - ")
        if parte.strip()
    ]

    if not partes:
        log_warning(
            f"Não foi possível identificar nome/setor: {caminho.name}"
        )
        return None

    resultado_nome_setor = identificar_setor(partes)

    if resultado_nome_setor is None:
        log_warning(
            f"Não foi possível identificar nome/setor: {caminho.name}"
        )
        return None

    nome, setor = resultado_nome_setor

    nome = normalizar_nome(nome)
    setor = setor.upper().strip()
    
    if inicio is not None:
        inicio, fim = completar_periodo(inicio, fim)
        periodo = formatar_periodo(inicio, fim)

        if eh_contrato:
            return f"{portaria} - {tipo} - {nome} - {setor} - {periodo} - CONTRATO.pdf"

        return f"{portaria} - {tipo} - {nome} - {setor} - {periodo}.pdf"

    if eh_contrato:
        return f"{portaria} - {tipo} - {nome} - {setor} - CONTRATO.pdf"

    return f"{portaria} - {tipo} - {nome} - {setor}.pdf"