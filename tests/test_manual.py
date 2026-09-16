"""O manual não pode mentir sobre a fábrica.

Documentação apodrece em silêncio: alguém renomeia um alvo do Makefile, o
manual continua ensinando o nome antigo, e quem seguir o manual bate numa
mensagem de erro que não explica nada.

Um manual errado é pior que nenhum — ele tem a autoridade de um documento
oficial e a precisão de um palpite.

Estes testes conferem só o que dá para conferir mecanicamente: que todo
comando ensinado existe. Se o manual está BOM é outra questão, e essa nenhum
teste responde.
"""
import re
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
MANUAL = BASE / "docs" / "MANUAL.md"


@pytest.fixture(scope="module")
def texto() -> str:
    if not MANUAL.exists():
        pytest.fail("docs/MANUAL.md não existe — a fábrica não tem manual")
    return MANUAL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def alvos() -> set[str]:
    """Alvos declarados no Makefile."""
    mk = (BASE / "Makefile").read_text(encoding="utf-8")
    return set(re.findall(r"^([a-z][a-z_-]*):", mk, re.M))


def test_manual_existe(texto):
    assert len(texto) > 2000, "manual curto demais para ensinar a fábrica"


def test_todo_alvo_citado_existe(texto, alvos):
    """`make foo` no manual, sem `foo:` no Makefile, é instrução quebrada."""
    citados = set(re.findall(r"make ([a-z][a-z_-]*)", texto))
    # `make` sozinho e variáveis não são alvos
    citados -= {"", "all"} if "all" not in alvos else {""}
    inexistentes = sorted(citados - alvos)
    assert not inexistentes, (
        f"MANUAL.md ensina alvos que não existem: {inexistentes}. "
        f"Alvos reais: {sorted(alvos)}"
    )


# Nomes que aparecem no manual como EXEMPLO, não como referência real:
# um ADR fictício num bloco de "faça assim", e um script que só existe nas
# fábricas geradas (o manual diz isso explicitamente).
EXEMPLOS = {
    "0007-minha-decisao.md",
    "scripts/estado_contrato.py",
}


def test_todo_script_citado_existe(texto):
    """Caminho de script no manual tem de apontar para arquivo real."""
    citados = set(re.findall(r"(?:scripts|ingestion)/[\w_]+\.(?:py|sh)", texto))
    faltando = sorted(c for c in citados - EXEMPLOS if not (BASE / c).exists())
    assert not faltando, f"MANUAL.md cita scripts inexistentes: {faltando}"


def test_todo_adr_citado_existe(texto):
    """Link para ADR que não existe quebra a trilha do 'por quê'."""
    citados = set(re.findall(r"adrs/(\d{4}-[\w-]+\.md)", texto)) - EXEMPLOS
    faltando = sorted(c for c in citados if not (BASE / "docs" / "adrs" / c).exists())
    assert not faltando, f"MANUAL.md cita ADRs inexistentes: {faltando}"


@pytest.mark.parametrize("assunto", [
    "ACEITO_SEM_ANCORA",   # o estado que parece sucesso e não é
    "make ancora",         # o passo que não se pode pular
    "ADR",                 # como se muda o congelado
    "classifique",         # a regra que resolve a maioria dos gates
])
def test_manual_cobre_o_essencial(texto, assunto):
    """Um manual que omite isto entrega uma fábrica que ninguém opera direito."""
    assert assunto.lower() in texto.lower(), (
        f"MANUAL.md não menciona {assunto!r}"
    )
