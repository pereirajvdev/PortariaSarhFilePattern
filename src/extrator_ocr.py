import re
import shutil
from pathlib import Path

import pymupdf as fitz
import pytesseract
from PIL import Image

from setores import identificar_secretarias


PASTA_PROJETO = Path(__file__).resolve().parent
PASTA_TESSERACT = (
    PASTA_PROJETO
    / "tesseract"
)

if not PASTA_TESSERACT.exists():
    PASTA_TESSERACT = (
        PASTA_PROJETO.parent
        / "tesseract"
    )

CAMINHOS_TESSERACT = [
    PASTA_TESSERACT / "tesseract.exe",
    PASTA_TESSERACT / "bin" / "tesseract.exe",
    PASTA_TESSERACT / "tesseract" / "tesseract.exe",
]


def configurar_tesseract() -> None:
    """Localiza e configura o executável do Tesseract."""

    for caminho in CAMINHOS_TESSERACT:
        if caminho.is_file():
            pytesseract.pytesseract.tesseract_cmd = str(caminho)
            return

    executavel = shutil.which("tesseract")

    if executavel:
        pytesseract.pytesseract.tesseract_cmd = executavel
        return

    raise FileNotFoundError(
        "Tesseract não encontrado. Verifique o caminho: "
        f"{PASTA_TESSERACT}"
    )


def extrair_texto_pdf(caminho_pdf: Path) -> tuple[str, str]:
    """
    Extrai o texto de todas as páginas do PDF.
    Usa texto direto quando suficiente e Tesseract como alternativa.
    """

    textos = []
    metodos = set()

    with fitz.open(caminho_pdf) as documento:
        if len(documento) == 0:
            return "", "PDF VAZIO"

        for pagina in documento:
            texto_direto = pagina.get_text("text").strip()

            if len(texto_direto) >= 100:
                textos.append(texto_direto)
                metodos.add("TEXTO DIRETO")
                continue

            configurar_tesseract()

            pix = pagina.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False,
            )

            imagem = Image.frombytes(
                "RGB",
                [pix.width, pix.height],
                pix.samples,
            )

            texto_ocr = pytesseract.image_to_string(
                imagem,
                lang="por",
                config="--psm 3",
            ).strip()

            textos.append(texto_ocr)
            metodos.add("TESSERACT OCR")

    texto_completo = "\n\n".join(
        texto for texto in textos if texto
    )

    if metodos == {"TEXTO DIRETO"}:
        metodo = "TEXTO DIRETO"
    elif metodos == {"TESSERACT OCR"}:
        metodo = "TESSERACT OCR"
    else:
        metodo = "TEXTO DIRETO + TESSERACT OCR"

    return texto_completo, metodo


def extrair_numero_ano(nome_arquivo: str) -> tuple[str, str] | None:
    """
    Remove as letras do nome e extrai o número e o ano.
    Exemplo: 'Portaria nº 001-2026' -> '  001-2026'
    """

    nome_numerico = re.sub(r"[^\d\s/_-]", "", nome_arquivo)

    print(f"Nome original: {nome_arquivo}")
    print(f"Nome sem letras: {nome_numerico}")

    resultado = re.search(
        r"(?<!\d)(\d{1,5})\s*[-_/]\s*(20\d{2})(?!\d)",
        nome_numerico,
    )

    if not resultado:
        return None

    return resultado.group(1), resultado.group(2)


def extrair_artigo_resolve(texto: str) -> str | None:
    """Extrai o primeiro artigo após RESOLVE."""

    resultado_resolve = re.search(
        r"\bRESOLVE\b\s*[:;.]?\s*",
        texto,
        flags=re.IGNORECASE,
    )

    if not resultado_resolve:
        return None

    texto_posterior = texto[resultado_resolve.end():]

    resultado_artigo = re.search(
        r"\bArt(?:igo)?[.,]?\s*"
        r"1\s*(?:[º°oª])?\s*\.?\s*"
        r"(.*?)"
        r"(?=\bArt(?:igo)?[.,]?\s*"
        r"2\s*(?:[º°oª])?\s*\.?\s*|$)",
        texto_posterior,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not resultado_artigo:
        return None

    artigo = resultado_artigo.group(1).strip()

    return artigo or None


def extrair_verbo_e_artigo(texto_artigo: str) -> tuple[str | None, str]:
    """
    Identifica o verbo no início do primeiro artigo.
    """
    texto = re.sub(r"\s+", " ", texto_artigo).strip()

    resultado = re.match(
        r"([A-Za-zÀ-ÿ]+)",
        texto,
    )

    if not resultado:
        return None, texto

    verbo = resultado.group(1).upper()

    return verbo, texto






def extrair_servidor(texto: str) -> str | None:
    """Extrai o nome do servidor, tolerando falhas comuns de OCR."""

    texto = re.sub(r"\s+", " ", texto).strip()

    padrao = (
        r"\b(?:"
        r"a\s+servidora|"
        r"o\s+servidor|"
        r"ao\s+servidor|"
        r"à\s+servidora|"
        r"a\s+servidor|"
        r"à\s+Sra\.?|"
        r"a\s+Sra\.?|"
        r"ao\s+Sr\.?|"
        r"o\s+Sr\.?|"
        r"à\s+senhora|"
        r"ao\s+senhor|"
        r"Sra\.?|"
        r"Sr\.?"
        r")\s+"
        r"([A-ZÀ-Ü][A-ZÀ-Ü'-]+"
        r"(?:\s+[A-ZÀ-Ü][A-ZÀ-Ü'-]+){1,11})"
    )

    for resultado in re.finditer(
        padrao,
        texto,
        flags=re.IGNORECASE,
    ):
        nome = resultado.group(1).strip(" ,.;:-")
        palavras = nome.split()

        if not 2 <= len(palavras) <= 12:
            continue

        if any(
            termo in nome.casefold()
            for termo in (
                "considerando",
                "resolve",
                "o direito",
                "licença",
                "portaria",
            )
        ):
            continue

        trecho_posterior = texto[
            resultado.end():resultado.end() + 150
        ]

        if re.search(
            r"\bmatr[ií]|matr[ií]cula|ocupante\b|lotad[oa]\b|"
            r"\bm[aá]tr[ií]",
            trecho_posterior,
            flags=re.IGNORECASE,
        ):
            return nome.upper()

    return None



def extrair_secretaria(texto: str) -> str | None:
    from setores import SETORES

    # Uniformiza espaços e quebras de linha do OCR.
    texto = re.sub(r"\s+", " ", texto).strip()

    aliases = {
        "SEMS": [
            "Secretaria Municipal de Saúde",
        ],
        "SELTC": [
            "Secretaria Municipal de Lazer, Turismo e Cultura",
        ],
    }

    # Em relotação, prioriza exclusivamente a secretaria de destino.
    destino = re.search(
        r"\bpara\s+(?:a|o)\s+(Secretaria Municipal de .+?)"
        r"(?=,|\.|;|$)",
        texto,
        flags=re.IGNORECASE,
    )

    if destino:
        nome_destino = destino.group(1).strip().casefold()

        for sigla, nomes in aliases.items():
            for nome in nomes:
                if nome_destino == nome.casefold():
                    return sigla

        # Se encontramos um destino, não devemos retornar a secretaria
        # de origem por engano.
        return None

    # Para portarias que não são de relotação, procura os nomes completos.
    for sigla, nomes in aliases.items():
        for nome in nomes:
            if re.search(re.escape(nome), texto, flags=re.IGNORECASE):
                return sigla

    # Alternativa: siglas escritas literalmente no texto.
    setores_ordenados = sorted(SETORES, key=len, reverse=True)
    padrao = (
        r"(?<![A-Z0-9])("
        + "|".join(re.escape(setor) for setor in setores_ordenados)
        + r")(?![A-Z0-9])"
    )

    resultado = re.search(padrao, texto, flags=re.IGNORECASE)

    if resultado:
        return resultado.group(1).upper()

    return None


def analisar_portaria(caminho_pdf: Path) -> dict:
    texto, metodo = extrair_texto_pdf(caminho_pdf)

    numero_ano = extrair_numero_ano(caminho_pdf.stem)
    texto_resolve = extrair_artigo_resolve(texto)

    tipo = identificar_tipo_portaria(
        texto_resolve if texto_resolve else texto
    )

    verbo = None
    servidor = None

    if texto_resolve:
        verbo, artigo = extrair_verbo_e_artigo(texto_resolve)
        servidor = extrair_servidor(artigo)

        if servidor is None:
            servidor = extrair_servidor(texto_resolve)

        if servidor is None:
            servidor = extrair_servidor(texto)

    if tipo in ("RELOT", "Relot") and texto_resolve:
        secretarias = [
            secretaria
            for secretaria in extrair_secretarias_relot(texto_resolve)
            if secretaria.strip().upper() != "SESMT"
        ]
    else:
        secretarias = [
            secretaria
            for secretaria in identificar_secretarias(texto)
            if secretaria.strip().upper() != "SESMT"
        ]

    # Em portarias de relotação, remover SARH quando
    # houver duas ou mais outras secretarias diferentes.
    if tipo == "RELOT":
        secretarias_sem_sarh = [
            secretaria
            for secretaria in secretarias
            if secretaria.upper() != "SARH"
        ]

        if len(set(secretarias_sem_sarh)) >= 2:
            secretarias = secretarias_sem_sarh

    if tipo in ("Anula", "Anular", "Revoga", "Revog"):
        verbo_referencia = (
            "ANULAR"
            if tipo in ("Anula", "Anular")
            else "REVOGAR"
        )

        portaria_referenciada = extrair_portaria_referenciada(
            texto,
            verbo_referencia,
        )

        if portaria_referenciada:
            tipo = f"{verbo_referencia.title()} {portaria_referenciada}"

    return {
        "arquivo": caminho_pdf.name,
        "metodo": metodo,
        "numero": numero_ano[0] if numero_ano else None,
        "ano": numero_ano[1] if numero_ano else None,
        "verbo": verbo,
        "tipo": tipo,
        "servidor": servidor,
        "secretarias": secretarias,
        "resolve_encontrado": texto_resolve is not None,
        "texto_extraido": texto,
    }


def extrair_secretarias_relot(texto_artigo: str) -> list[str]:
    """Extrai as secretarias de origem e destino de uma relotação."""

    from setores import identificar_secretarias

    texto_artigo = re.sub(r"\s+", " ", texto_artigo).strip()

    resultado = re.search(
        r"\bda\s+(Secretaria Municipal de .+?)\s+"
        r"para\s+a\s+(Secretaria Municipal de .+?)"
        r"(?=,\s*a partir de\b|[.;]|$)",
        texto_artigo,
        flags=re.IGNORECASE,
    )

    if not resultado:
        return identificar_secretarias(texto_artigo)

    origem = resultado.group(1).strip()
    destino = resultado.group(2).strip()

    # Identifica as siglas a partir dos nomes completos.
    secretarias = identificar_secretarias(
        f"{origem}. {destino}."
    )

    return secretarias


def extrair_portaria_referenciada(
    texto: str,
    verbo: str,
) -> str | None:
    """
    Extrai o número e o ano da portaria anulada ou revogada.

    Exemplos:
    ANULAR a Portaria nº 629/2025 -> 629-2025
    REVOGAR a Portaria 727/2025 -> 727-2025
    """

    padrao = re.compile(
        rf"\b{re.escape(verbo)}\b"
        rf"[\s\S]{{0,300}}?"
        rf"\bPortaria\s*(?:n[º°.]?\s*)?"
        rf"(\d{{1,4}})\s*[/\-]\s*(\d{{4}})",
        re.IGNORECASE,
    )

    resultado = padrao.search(texto)

    if resultado:
        numero, ano = resultado.groups()
        return f"{numero}-{ano}"

    return None


def extrair_portaria_anulada(texto: str) -> str | None:
    """Mantém compatibilidade com a extração de portarias anuladas."""

    return extrair_portaria_referenciada(texto, "ANULAR")


def identificar_tipo_portaria(texto: str) -> str | None:
    """Identifica o tipo da portaria pelo texto extraído."""

    import unicodedata

    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    texto = re.sub(r"\s+", " ", texto).upper()

    tipos = [
        (
            "Anula",
            r"ANULAR"
        ),
        (
            "Revoga",
            r"REVOGAR"
        ),
        (
            "L CAT",
            r"LICENCA\s+EM\s+DECORRENCIA\s+DE\s+ACIDENTE\s+DE\s+TRABALHO"
            r"|LICENCA\s+(?:POR\s+)?CAT\b",
        ),
        (
            "LDPF",
            r"LICENCA\s+POR\s+MOTIVO\s+DE\s+DOENCA\s+EM\s+PESSOA\s+DA\s+FAMILIA",
        ),
        (
            "L Luto",
            r"LICENCA\s+(?:ESPECIAL\s+POR\s+)?LUTO",
        ),
        (
            "LP",
            r"LICENCA\s+PREMIO(?:\s+POR\s+ASSIDUIDADE)?",
        ),
        (
            "LC",
            r"LICENCA\s+(?:PARA\s+)?CASAMENTO",
        ),
        (
            "LTS",
            r"LICENCA\s+(?:PARA\s+TRATAMENTO\s+DE\s+(?:SUA\s+)?SAUDE|SAUDE)",
        ),
        (
            "L Mat",
            r"LICENCA\s+(?:GESTANTE|MATERNIDADE|A\s+GESTANTE)",
        ),
        (
            "L Pat",
            r"LICENCA\s+PATERNIDADE",
        ),
        (
            "AP",
            r"ABONO\s+(?:DE\s+)?PERMANENCIA",
        ),
        (
            "Readapt",
            r"\bREADAPT(?:AR|ACAO|ACAO\s+DE)?\b",
        ),
        (
            "Relot",
            r"\bRELOT(?:AR|ACAO)\b",
        ),
        (
            "FR",
            r"\bFERIAS\s+REGULAMENTARES\b",
        ),
        (
            "Anular",
            r"\bANULAR\b",
        ),
        (
            "Prorrogar",
            r"\bPRORROGAR\b",
        ),
        (
            "Revog",
            r"\bREVOGAR\b|\bREVOGACAO\b",
        ),
        (
            "Prom Vert",
            r"\bPROMOCAO\s+VERTICAL\b|\bPROGRESSAO\s+VERTICAL\b",
        ),
        (
            "Enqua",
            r"\bENQUADRA(?:R|MENTO)\b",
        ),
        (
            "Adic Tit",
            r"\bADICIONAL\s+DE\s+TITULACAO\b",
        ),
        (
            "Av Area Afim",
            r"\bAVALIACAO\s+DE\s+AREA\s+AFIM\b",
        ),
    ]

    for tipo, padrao in tipos:
        if re.search(padrao, texto):
            return tipo

    return None