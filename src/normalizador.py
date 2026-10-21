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
    "L Luto",
    "LP",
    "LC",
    "LTS",
    "LG",
    "L Pat",
    "L CAT",
    "AP",
    "Readapt",
    "Relot",
    "FR",
    "Anular",
    "Prorrogar",
    "Revog",
    "Prom Vert",
    "Enqua",
    "Adic Tit",
    "Av Area Afim",
}

def normalizar_secretarias(secretarias: list[str], tipo: str) -> list[str]:
    """Normaliza as secretarias e remove setores que não são secretarias."""

    setores = list(dict.fromkeys(
        setor.upper().strip()
        for setor in secretarias
        if setor
        and setor.strip()
        and setor.upper().strip() != "SESMT"
    ))

    tipo_normalizado = tipo.casefold().strip()
    limite = 2 if tipo_normalizado == "relot" else 1

    if len(setores) > limite and "SARH" in setores:
        setores.remove("SARH")

    return setores[:limite]


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
    setores = normalizar_secretarias(secretarias, tipo)

    if not setores:
        log_warning(
            f"Nenhuma secretaria identificada no OCR: {caminho.name}"
        )
        return None

    portaria = f"Portaria nº {numero}-{ano}"
    setores_texto = " - ".join(setores)

    return f"{portaria} - {tipo} - {nome} - {setores_texto}.pdf"


def normalizar_base(caminho: Path) -> str | None:
    """
    Gera o nome básico da portaria, mantendo apenas número e ano.
    Não utiliza OCR.
    """

    nome_original = caminho.stem

    resultado = re.search(
        r"Portaria\s+n[ºo°]?\s*(\d{1,5})\s*[-_/]\s*(20\d{2})",
        nome_original,
        flags=re.IGNORECASE,
    )

    # Caso o nome não contenha a palavra Portaria, procura número e ano.
    if resultado is None:
        resultado = re.search(
            r"(?<!\d)(\d{1,5})\s*[-_/]\s*(20\d{2})(?!\d)",
            nome_original,
        )

    if resultado is None:
        log_warning(
            f"Número e ano não identificados: {caminho.name}"
        )
        return None

    numero = resultado.group(1).zfill(3)
    ano = resultado.group(2)

    return f"Portaria nº {numero}-{ano}.pdf"


def normalizar_arquivo(caminho: Path) -> str | None:
    """
    Recebe o caminho de um PDF e tenta gerar o novo nome.

    Arquivos numéricos ou com nome descritivo sem sigla de tipo
    são normalizados usando OCR.
    Arquivos que já possuem a sigla seguem o fluxo atual.
    """

    nome_original = caminho.stem

    # Extrai número e ano mesmo quando o nome contém texto descritivo.
    nome_numerico = re.sub(r"[^\d\s/_-]", "", nome_original)

    resultado_numero = re.search(
        r"(?<!\d)(\d{1,5})\s*[-_/]\s*(20\d{2})(?!\d)",
        nome_numerico,
    )

    if resultado_numero is None:
        log_warning(f"Portaria não identificada: {caminho.name}")
        return None

    # Arquivos somente numéricos usam OCR.
    if re.fullmatch(
        r"\s*\d{1,5}\s*[-_/]\s*20\d{2}\s*",
        nome_numerico,
    ):
        return normalizar_portaria_ocr(caminho)

    # Identifica o prefixo da portaria.
    resultado_portaria = re.match(
        r"^\s*(Portaria\s+n[ºo°]?\s*\d+\s*-\s*\d{4})\s*-\s*(.*)$",
        nome_original,
        flags=re.IGNORECASE,
    )

    if resultado_portaria is None:
        # Nome descritivo em formato diferente: tenta normalizar pelo OCR.
        return normalizar_portaria_ocr(caminho)

    portaria = resultado_portaria.group(1).strip()
    texto = resultado_portaria.group(2).strip()

    # Portarias de prorrogação podem trazer o tipo do benefício
    # separado do nome da servidora. Nesses casos, usar o OCR.
    if re.match(r"^\s*Prorrogar\b", texto, flags=re.IGNORECASE):
        return normalizar_portaria_ocr(caminho)

    tipo_encontrado = None
    texto_restante = None

    for tipo in sorted(TIPOS_PORTARIA, key=len, reverse=True):
        if tipo == "AP":
            padrao_tipo = r"A\s*P"
        else:
            partes_tipo = tipo.split()
            padrao_tipo = r"\s+".join(
                map(re.escape, partes_tipo)
            )

        resultado_tipo = re.match(
            rf"^\s*{padrao_tipo}(?=\s|$|-)",
            texto,
            flags=re.IGNORECASE,
        )

        if resultado_tipo:
            tipo_encontrado = tipo
            texto_restante = texto[resultado_tipo.end():].lstrip(" -")

            # Remove a sigla repetida no começo, se houver.
            padrao_tipo_repetido = re.match(
                r"^\s*" + re.escape(tipo_encontrado) + r"(?=\s|$|-)",
                texto_restante,
                flags=re.IGNORECASE,
            )

            if padrao_tipo_repetido:
                texto_restante = texto_restante[
                    padrao_tipo_repetido.end():
                ].lstrip(" -")

            break

    # Sem sigla reconhecida: o OCR identifica o tipo e os demais dados.
    if tipo_encontrado is None:
        return normalizar_portaria_ocr(caminho)

    tipo = tipo_encontrado.upper()

    # Substitui underscore por hífen.
    texto = texto_restante.replace("_", "-")

    # Identifica a marcação de contrato.
    eh_contrato = bool(
        re.search(r"\s+(?:CONT|CONTRATO)\s+(?=-)", texto, re.IGNORECASE)
    )

    if eh_contrato:
        texto = re.sub(
            r"\s+(?:CONT|CONTRATO)\s+(?=-)",
            " ",
            texto,
            flags=re.IGNORECASE,
        )

    texto = re.sub(r"\s+", " ", texto).strip()

    resultado_periodo = extrair_periodo(texto)

    if resultado_periodo is None:
        inicio = None
        fim = None
        texto_sem_periodo = texto
    else:
        inicio, fim, inicio_pos, fim_pos = resultado_periodo
        texto_sem_periodo = texto[:inicio_pos] + texto[fim_pos:]

    texto_sem_periodo = re.sub(
        r"\s*[-–—]\s*",
        " - ",
        texto_sem_periodo,
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
            f"Não foi possível identificar nome/setor pelo nome "
            f"do arquivo: {caminho.name}. Tentando OCR."
        )
        return normalizar_portaria_ocr(caminho)

    nome, setor = resultado_nome_setor

    nome = normalizar_nome(nome)
    setor = setor.upper().strip()

    if inicio is not None:
        inicio, fim = completar_periodo(inicio, fim)
        periodo = formatar_periodo(inicio, fim)

        if eh_contrato:
            return (
                f"{portaria} - {tipo} - {nome} - {setor} "
                f"- {periodo} - CONTRATO.pdf"
            )

        return f"{portaria} - {tipo} - {nome} - {setor} - {periodo}.pdf"

    if eh_contrato:
        return f"{portaria} - {tipo} - {nome} - {setor} - CONTRATO.pdf"

    return f"{portaria} - {tipo} - {nome} - {setor}.pdf"