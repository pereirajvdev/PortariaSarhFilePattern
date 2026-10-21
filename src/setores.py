import re
import unicodedata


SETORES = {
    "SEMS",
    "SEDUC",
    "SEMOSP",
    "SEFIN",
    "SARH",
    "SECOM",
    "SEDEC",
    "SEMAP",
    "SEMOB",
    "SESP",
    "SEMCI",
    "SEDESO",
    "SEGOV",
    "PGM",
    "SEMMADA",
    "SEPLAN",
    "SESMT",
    "SELTC",
}


# Nomes completos e variações conhecidas das secretarias.
# Acrescente novas variações conforme forem identificadas nos PDFs.
NOMES_SETORES = {
    "SEMS": [
        "Secretaria Municipal de Saúde",
    ],
    "SEDUC": [
        "Secretaria Municipal de Educação",
    ],
    "SEMOSP": [
        "Secretaria Municipal de Obras e Serviços Públicos",
        "Secretaria Municipal de Obras",
        "Secretaria Municipal de Serviços Públicos",
    ],
    "SEFIN": [
        "Secretaria Municipal de Fazenda",
        "Secretaria Municipal de Finanças",
    ],
    "SARH": [
        "Secretaria Municipal de Administração e Recursos Humanos",
        "Secretaria Municipal de Administração",
    ],
    "SECOM": [
        "Secretaria Municipal de Comunicação",
        "Secretaria Municipal de Comunicação Social",
    ],
    "SEDEC": [
        "Secretaria Municipal de Desenvolvimento Econômico",
    ],
    "SEMAP": [
        "Secretaria Municipal de Agricultura e Pecuária",
    ],
    "SEMOB": [
        "Secretaria Municipal de Mobilidade Urbana",
    ],
    "SESP": [
        "Secretaria Municipal de Esportes",
    ],
    "SEMCI": [
        "Secretaria Municipal de Controle Interno",
    ],
    "SEDESO": [
        "Secretaria Municipal de Desenvolvimento Social",
    ],
    "SEGOV": [
        "Secretaria Municipal de Governo",
    ],
    "PGM": [
        "Procuradoria-Geral do Município",
        "Procuradoria Geral do Município",
    ],
    "SEMMADA": [
        "Secretaria Municipal de Meio Ambiente e Defesa Animal",
        "Secretaria Municipal de Meio Ambiente",
    ],
    "SEPLAN": [
        "Secretaria Municipal de Planejamento",
    ],
    "SELTC": [
        "Secretaria Municipal de Lazer, Turismo e Cultura",
    ],
}


def _normalizar_texto(texto: str) -> str:
    """Padroniza acentos, espaços e letras para facilitar a comparação."""
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caractere
        for caractere in texto
        if unicodedata.category(caractere) != "Mn"
    )
    return re.sub(r"\s+", " ", texto).strip().upper()


def identificar_secretarias(texto: str) -> list[str]:
    """
    Identifica todas as secretarias mencionadas no texto.

    Retorna as siglas sem repetição, na ordem da primeira ocorrência.
    Reconhece tanto siglas quanto nomes completos.
    """
    texto_normalizado = _normalizar_texto(texto)
    ocorrencias = []

    # Procura as siglas escritas diretamente no documento.
    for sigla in SETORES:
        padrao = rf"(?<![A-Z0-9]){re.escape(sigla)}(?![A-Z0-9])"

        for resultado in re.finditer(padrao, texto_normalizado):
            ocorrencias.append((resultado.start(), sigla))

    # Procura os nomes completos e suas variações.
    for sigla, nomes in NOMES_SETORES.items():
        for nome in nomes:
            nome_normalizado = _normalizar_texto(nome)
            padrao = re.escape(nome_normalizado).replace(r"\ ", r"\s+")

            for resultado in re.finditer(padrao, texto_normalizado):
                ocorrencias.append((resultado.start(), sigla))

    # Ordena pela primeira posição encontrada no texto.
    ocorrencias.sort(key=lambda item: item[0])

    secretarias = []
    for _, sigla in ocorrencias:
        if sigla not in secretarias:
            secretarias.append(sigla)

    return secretarias


def identificar_setor(partes: list[str]):
    """
    Mantém a função original para compatibilidade com o renomeador.
    """
    for i in range(len(partes) - 1, -1, -1):
        parte = partes[i].upper().strip()

        if parte in SETORES:
            nome = " ".join(partes[:i])

            if not nome:
                return None

            return nome, parte

    texto = " ".join(partes).strip()
    texto_upper = texto.upper()

    for setor in sorted(SETORES, key=len, reverse=True):
        if texto_upper.endswith(setor):
            nome = texto[:-len(setor)].strip()

            if nome:
                return nome, setor

    return None