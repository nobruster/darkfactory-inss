"""Resolução de espécie pelo código.

ADR 0003 · DF-INSS-001 · DF-INSS-002.

Estes testes protegem a decisão mais frágil do projeto: se alguém agrupar
por nome em vez de código, 34 de 65 espécies se fundem — e o total continua
batendo, então nada acusa o erro. Aqui ele acusa.
"""
import json
from pathlib import Path

import pytest

BASE = Path(__file__).resolve().parents[1]


def normaliza_codigo(bruto: str) -> str:
    """`'                  01'` → `'01'`.

    Dois passos, ambos necessários: strip tira o padding da fonte; zfill
    garante os 2 dígitos. Ler como int transformaria `01` em `1` e quebraria
    o join com o dicionário oficial.
    """
    return bruto.strip().zfill(2)


@pytest.fixture(scope="module")
def dicionario() -> dict[str, str]:
    caminho = BASE / "contracts" / "_especies.json"
    if not caminho.exists():
        pytest.skip("dicionário oficial ausente — rode a extração primeiro")
    return json.loads(caminho.read_text(encoding="utf-8"))


class TestNormalizacao:
    def test_remove_padding(self):
        assert normaliza_codigo("                  01") == "01"

    def test_preserva_zero_a_esquerda(self):
        """O erro clássico: int('01') vira 1 e o join quebra."""
        assert normaliza_codigo(" 1") == "01"
        assert normaliza_codigo("01") == "01"

    def test_dois_digitos_intactos(self):
        assert normaliza_codigo("  67") == "67"
        assert normaliza_codigo("41") == "41"


class TestDicionarioOficial:
    def test_tem_65_especies(self, dicionario):
        assert len(dicionario) == 65

    def test_todo_codigo_tem_dois_digitos(self, dicionario):
        assert all(len(c) == 2 and c.isdigit() for c in dicionario)

    def test_codigo_01_confere_com_a_fonte(self, dicionario):
        # a linha de exemplo da fonte traz 01 com Clientela=Rural
        assert dicionario["01"] == "Pensão por Morte de Trabalhador Rural"


class TestTruncamentoFundeCategorias:
    """DF-INSS-002 — a razão de existir do ADR 0003."""

    def test_truncar_em_20_perde_distincao(self, dicionario):
        truncados = {nome[:20] for nome in dicionario.values()}
        assert len(truncados) < len(dicionario), (
            "se isto falhar, o truncamento deixou de fundir nomes e o "
            "ADR 0003 pode ser revisado"
        )

    def test_impacto_medido(self, dicionario):
        """65 nomes viram 44 após truncar. Número do contrato."""
        truncados = {nome[:20] for nome in dicionario.values()}
        assert len(truncados) == 44

    def test_aposentadoria_invalidez_funde_seis(self, dicionario):
        """O pior caso: 6 políticas públicas distintas num nome só."""
        colidem = [c for c, n in dicionario.items() if n[:20] == "Aposentadoria Invali"]
        assert len(colidem) >= 2, "esperado colisão neste prefixo"
        assert "32" in colidem or "33" in colidem

    def test_codigo_e_unico_por_construcao(self, dicionario):
        """O código não colide — é por isso que o join é por ele."""
        assert len(set(dicionario)) == len(dicionario)


class TestRotulo:
    """`especie_rotulo` = código + nome oficial."""

    def test_rotulo_e_unico(self, dicionario):
        rotulos = {f"{c} · {n}" for c, n in dicionario.items()}
        assert len(rotulos) == len(dicionario)

    def test_rotulo_sobrevive_a_truncamento(self, dicionario):
        """Código vem primeiro: truncar em 20 num BI ainda distingue."""
        rotulos = {f"{c} · {n}"[:20] for c, n in dicionario.items()}
        truncados_so_nome = {n[:20] for n in dicionario.values()}
        assert len(rotulos) > len(truncados_so_nome)


class TestComplemento:
    """DF-INSS-003 — o código 67 e a regra de não sobrepor."""

    @pytest.fixture(scope="class")
    @classmethod
    def complemento(cls):
        import yaml
        caminho = BASE / "contracts" / "especies-complemento.yaml"
        if not caminho.exists():
            pytest.skip("complemento ausente")
        return yaml.safe_load(caminho.read_text(encoding="utf-8"))

    def test_67_esta_no_complemento(self, complemento):
        assert "67" in complemento["especies"]

    def test_origem_declarada_como_fonte(self, complemento):
        """Nunca 'dicionario_oficial' — o INSS não o documenta."""
        assert complemento["especies"]["67"]["origem"] == "fonte"

    def test_nao_sobrepoe_o_oficial(self, complemento, dicionario):
        """O gate do Silver reprova se sobrepuser. Aqui garantimos antes."""
        sobrepostos = set(complemento["especies"]) & set(dicionario)
        assert not sobrepostos, f"complemento sobrepõe o oficial em {sobrepostos}"

    def test_ambiguidade_continua_aberta(self, complemento):
        """O complemento documenta, não resolve."""
        assert complemento["classificacao"] == "CONTRACT_AMBIGUITY"
