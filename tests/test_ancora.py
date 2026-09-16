"""A âncora é por competência, e gate desligado não passa por gate aprovado.

ADR 0006 · auditoria de 16/09/2026, objeção #28.

O defeito que estes testes travam não era um bug: era uma linha de código
razoável — `if comp == contrato["competencia"]` — que desligava o juiz sem
avisar ninguém. Nada quebrava. O packet dizia ACEITO. 82 milhões de linhas
foram publicadas assim.

Não há teste unitário que "detecte" isso rodando o pipeline: o pipeline
passava. O que se testa aqui é a ESTRUTURA — que a âncora exista para cada
competência processada, e que nenhum packet publicado diga ACEITO com um
gate de âncora falso.
"""
import json
from pathlib import Path

import pytest
import yaml

BASE = Path(__file__).resolve().parents[1]

# Gates que provam conferência real. Um `false` aqui, sob status ACEITO,
# é a mentira por omissão que a objeção #28 descreve.
GATES_DE_ANCORA = {
    "count_confere", "soma_confere",
    "count_confere_ancora", "soma_confere_ancora", "qtd_confere_ancora",
    "count_confere_bronze", "soma_confere_bronze",
    "soma_confere_silver", "qtd_confere_silver",
    "rejeicoes_zero", "grao_unico",
}


@pytest.fixture(scope="module")
def contrato():
    return yaml.safe_load(
        (BASE / "contracts" / "layout.yaml").read_text(encoding="utf-8")
    )


CAMADAS = ("bronze", "silver", "gold")


def packets():
    """Os packets de camada publicados, como (nome, conteúdo).

    Só bronze/silver/gold: `_totais-*.json` é medição da fonte e
    `*-conferencia.json` é auditoria retroativa — nenhum dos dois tem status.
    """
    for p in sorted((BASE / "evidence").glob("*-20*.json")):
        if p.name.endswith("-conferencia.json"):
            continue
        if not p.name.startswith(CAMADAS):
            continue
        yield p.name, json.loads(p.read_text(encoding="utf-8"))


def test_contrato_tem_ancora_por_competencia(contrato):
    """O bloco existe e não está vazio."""
    ancoras = contrato.get("controle_por_competencia")
    assert ancoras, "contrato sem controle_por_competencia — ver ADR 0006"


def test_toda_ancora_tem_count_e_soma(contrato):
    """Âncora sem os dois números não ancora nada."""
    for comp, a in contrato["controle_por_competencia"].items():
        assert "count_linhas" in a, f"{comp}: âncora sem count_linhas"
        assert "sum_vl_liquido" in a, f"{comp}: âncora sem sum_vl_liquido"
        assert isinstance(a["sum_vl_liquido"], str), (
            f"{comp}: soma deve ser string — float perde centavo (ADR 0002)"
        )


def test_toda_ancora_aponta_para_evidencia(contrato):
    """Número no contrato sem evidência reproduzível é palpite, não âncora."""
    for comp, a in contrato["controle_por_competencia"].items():
        assert a.get("evidencia"), f"{comp}: âncora sem arquivo de evidência"
        assert a.get("medido_em"), f"{comp}: âncora sem data de medição"


@pytest.mark.parametrize("nome,packet", list(packets()))
def test_packet_aceito_nao_tem_gate_de_ancora_falso(nome, packet):
    """ACEITO com gate de âncora false é exatamente a objeção #28."""
    if packet.get("status") != "ACEITO":
        return
    gates = packet.get("gates") or {}
    desligados = sorted(k for k in GATES_DE_ANCORA if gates.get(k) is False)
    assert not desligados, (
        f"{nome}: diz ACEITO mas {desligados} está(ão) false. "
        f"Gate que não rodou não é gate que passou — use ACEITO_SEM_ANCORA."
    )


@pytest.mark.parametrize("nome,packet", list(packets()))
def test_packet_declara_status_conhecido(nome, packet):
    """Um status novo e não documentado esconde estado, como o ACEITO fazia."""
    assert packet.get("status") in {
        "ACEITO", "ACEITO_SEM_ANCORA", "REJEITADO"
    }, f"{nome}: status desconhecido {packet.get('status')!r}"


def test_competencia_processada_tem_ancora(contrato):
    """Toda competência com packet publicado precisa de âncora no contrato.

    É este teste que impede a regressão: processar uma competência nova sem
    medir a fonte volta a produzir publicação sem juiz.
    """
    ancoras = set(contrato.get("controle_por_competencia") or {})
    processadas = {
        f"{p.stem.split('-')[1][:4]}-{p.stem.split('-')[1][4:]}"
        for p in (BASE / "evidence").glob("bronze-20*.json")
        if not p.name.endswith("-conferencia.json")
    }
    sem_ancora = sorted(processadas - ancoras)
    assert not sem_ancora, (
        f"competências processadas sem âncora: {sem_ancora}. "
        f"Rode: make ancora COMP=<AAAA-MM>"
    )
