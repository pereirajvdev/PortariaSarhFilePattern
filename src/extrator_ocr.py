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
    Tenta extrair texto diretamente do PDF.
    Se não houver texto suficiente, utiliza OCR.
    """

    with fitz.open(caminho_pdf) as documento:
        paginas = list(documento)

        texto_direto = "\n".join(
            pagina.get_text("text")
            for pagina in paginas
        ).strip()

        if len(texto_direto) >= 100:
            return texto_direto, "TEXTO DIRETO"

        configurar_tesseract()

        textos_ocr = []

        for pagina in paginas:
            pix = pagina.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False,
            )

            imagem = Image.frombytes(
                "RGB",
                [pix.width, pix.height],
                pix.samples,
            )

            texto = pytesseract.image_to_string(
                imagem,
                lang="por",
                config="--psm 3",
            )

            textos_ocr.append(texto)

        return "\n".join(textos_ocr), "TESSERACT OCR"


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
    """
    Extrai somente o primeiro artigo após RESOLVE.
    Exemplo: Art. 1º RELOTAR a servidora ...
    """
    resultado_resolve = re.search(
        r"\bRESOLVE\s*[:;]?\s*",
        texto,
        flags=re.IGNORECASE,
    )

    if not resultado_resolve:
        return None

    texto_posterior = texto[resultado_resolve.end():]

    resultado_artigo = re.search(
        r"\bArt(?:igo)?\.?\s*1\s*[º°oª.]?\s*(.*?)"
        r"(?=\bArt(?:igo)?\.?\s*2\b|$)",
        texto_posterior,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not resultado_artigo:
        return None

    return resultado_artigo.group(1).strip()


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
    """
    Extrai o nome do servidor em diferentes formatos de portaria.

    Exemplos:
    - a servidora MARIA APARECIDA, matrícula 123
    - à servidora MARIA APARECIDA, matrícula 123
    - ao servidor JOÃO DA SILVA, matrícula 456
    - ao sr. ROMULO RAIMUNDO DE ANDRADE ROTONDARO, matrícula 2290
    - à Sra. MARIA APARECIDA, matrícula 789
    - READAPTAR o servidor JOÃO DA SILVA, matrícula 321
    """

    texto = re.sub(r"\s+", " ", texto).strip()

    padrao = (
        r"\b(?:"
        r"ao\s+servidor"
        r"|a\s+servidora"
        r"|à\s+servidora"
        r"|à?\s+servidor"
        r"|o\s+servidor"
        r"|a\s+servidor"
        r"|ao\s+(?:sr|senhor)\.?"
        r"|à\s+(?:sra|senhora)\.?"
        r"|a\s+(?:sra|senhora)\.?"
        r"|(?:sr|sra|senhor|senhora)\.?"
        r")\s+"
        r"(.+?)"
        r"(?=\s*,?\s*matr[ií]cula\b"
        r"|\s*,\s*cargo\b"
        r"|\s+ocupante\s+do\s+cargo\b"
        r"|\s+lotad[oa]\b"
        r"|\s+no\s+per[ií]odo\b"
        r"|\s+por\s+um\s+per[ií]odo\b"
        r"|\s+a\s+contar\b"
        r"|$)"
    )

    resultado = re.search(
        padrao,
        texto,
        flags=re.IGNORECASE,
    )

    if not resultado:
        return None

    nome = resultado.group(1).strip(" ,.;:-")
    nome = re.sub(r"\s+", " ", nome)

    # Exige pelo menos nome e sobrenome.
    if len(nome.split()) < 2:
        return None

    return nome.upper()


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

    secretarias = identificar_secretarias(texto)

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
            "LDPF",
            r"LICENCA\s+POR\s+MOTIVO\s+DE\s+DOENCA\s+EM\s+PESSOA\s+DA\s+FAMILIA",
        ),
        (
            "L Luto",
            r"LICENCA\s+ESPECIAL\s+POR\s+LUTO",
        ),
        (
            "LP",
            r"LICENCA\s+PREMIO\s+POR\s+ASSIDUIDADE",
        ),
        (
            "LC",
            r"LICENCA\s+(?:PARA\s+)?CASAMENTO",
        ),
        (
            "LTS",
            r"LICENCA\s+PARA\s+TRATAMENTO\s+DE\s+(?:SUA\s+)?SAUDE",
        ),
        (
            "LG",
            r"LICENCA\s+(?:A|A\s+GESTANTE|MATERNIDADE)",
        ),
        (
            "AP",
            r"ABONO\s+(?:DE\s+)?PERMANENCIA",
        ),
        (
            "Readapt",
            r"\bREADAPTAR\b",
        ),
        (
            "Relot",
            r"\bRELOTAR\b",
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
            "L Pat",
            r"\bLICENCA\s+PATERNIDADE\b",
        ),
    ]

    for tipo, padrao in tipos:
        if re.search(padrao, texto):
            return tipo

    return None