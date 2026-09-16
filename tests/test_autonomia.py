"""O degrau de autonomia do agente só pode estar escrito em um lugar por vez.

Até 16/09/2026 o `docs/OPERADOR.md` declarava degrau 2 ("executa e reporta")
enquanto o SOUL em produção dizia degrau 1 ("NUNCA PROCESSA POR CONTA
PRÓPRIA"). Os dois documentos existiam há meses; ninguém tinha lido os dois
lado a lado.

Não houve consequência porque o Hermes lê o SOUL, não o OPERADOR.md. Mas a
próxima pessoa a configurar um agente leria o documento do repositório — e
configuraria um agente que processa sozinho, contra a regra explícita do
dono.

Este teste não sabe qual degrau é o certo. Ele sabe que **um número que
aparece em dois lugares vai divergir**, e cobra que os lugares concordem.
"""
import re
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]
OPERADOR = BASE / "docs" / "OPERADOR.md"
MANUAL = BASE / "docs" / "MANUAL.md"
CLAUDE = BASE / "CLAUDE.md"


def le(p: Path) -> str:
    if not p.exists():
        pytest.skip(f"{p.name} não existe")
    return p.read_text(encoding="utf-8")


def test_operador_declara_um_degrau_so():
    """O título de nível não pode dizer um número e a tabela outro."""
    txt = le(OPERADOR)
    m = re.search(r"Nível de autonomia:\s*degrau\s*(\d)", txt)
    assert m, "OPERADOR.md não declara o degrau no título"
    declarado = m.group(1)

    # a linha em negrito da tabela é o degrau em vigor
    negritos = re.findall(r"^\|\s*\*\*(\d)\*\*\s*\|", txt, re.M)
    assert negritos, "a tabela de degraus não marca nenhum em negrito"
    assert declarado in negritos, (
        f"OPERADOR.md diz 'degrau {declarado}' no título mas a tabela "
        f"destaca {negritos}"
    )


def test_degrau_1_significa_nao_processar_sozinho():
    """Degrau 1 sem a proibição explícita é degrau 2 com outro nome."""
    txt = le(OPERADOR)
    if not re.search(r"Nível de autonomia:\s*degrau\s*1", txt):
        pytest.skip("não está em degrau 1")
    alvo = txt.upper()
    assert "NUNCA PROCESSA POR CONTA PRÓPRIA" in alvo, (
        "OPERADOR.md declara degrau 1 mas não diz, em letras claras, que o "
        "agente nunca processa sozinho. Sem essa frase o SOUL gerado a partir "
        "daqui autoriza o que o degrau 1 proíbe."
    )
    assert "AUTORIZAÇÃO" in alvo, (
        "degrau 1 exige autorização explícita — a palavra não aparece"
    )


def test_rotina_do_soul_nao_processa():
    """A ROTINA é o que o agente faz sem ser mandado. Não pode processar."""
    txt = le(OPERADOR)
    m = re.search(r"ROTINA.*?(?=\n[A-ZÇÃÕ]{4,}|\n```)", txt, re.S)
    if not m:
        pytest.skip("bloco ROTINA não encontrado")
    rotina = m.group(0)
    # "NÃO processe" é permitido; "rode processar" não é
    assert not re.search(r"rode\s+\"?processar", rotina, re.I), (
        "a ROTINA manda o agente processar sem ser mandado — isso é degrau 2"
    )


@pytest.mark.parametrize("doc", [OPERADOR, MANUAL, CLAUDE])
def test_nenhum_doc_promete_degrau_maior(doc):
    """Nenhum documento pode afirmar um degrau acima do declarado."""
    txt = le(doc)
    oper = le(OPERADOR)
    m = re.search(r"Nível de autonomia:\s*degrau\s*(\d)", oper)
    if not m:
        pytest.skip("degrau não declarado")
    vigente = int(m.group(1))

    # frases que AFIRMAM o degrau atual, não que o descrevem como futuro
    for achado in re.findall(r"(?:está no |em |Nível de autonomia:\s*)degrau\s*(\d)", txt):
        assert int(achado) <= vigente, (
            f"{doc.name} afirma degrau {achado}, acima do vigente ({vigente})"
        )
