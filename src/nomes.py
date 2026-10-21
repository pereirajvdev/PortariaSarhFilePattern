import re


def normalizar_nome(nome: str) -> str:
    """
    Normaliza o nome da pessoa, mantendo preposições
    em minúsculas.
    """
    nome = re.sub(r"\s+", " ", nome).strip().lower().title()

    preposicoes = r"\b(De|Da|Do|Das|Dos|E|Em|Na|No|Nas|Nos)\b"

    nome = re.sub(
        preposicoes,
        lambda m: m.group(1).lower(),
        nome,
    )

    return nome