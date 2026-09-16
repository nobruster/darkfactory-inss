"""Parse de valor monetário pt-BR.

ADR 0002 — decimal, nunca float. Estes testes existem porque a soma de
41,5 milhões de valores precisa bater centavo a centavo com o contrato;
com float ela erraria e o erro seria pequeno o bastante para passar
despercebido.
"""
from decimal import Decimal

import pytest


def parse_valor(texto: str) -> Decimal:
    """Converte o formato da fonte para Decimal exato.

    A fonte traz pt-BR com padding: `"        1.621,00"` — ponto de milhar,
    vírgula decimal, largura 16. Mesma transformação usada em
    ingest_bronze.py e totais_controle.py.
    """
    return Decimal(texto.strip().replace(".", "").replace(",", "."))


class TestParseValor:
    def test_valor_simples(self):
        assert parse_valor("1.621,00") == Decimal("1621.00")

    def test_padding_da_fonte(self):
        # a fonte preenche até 16 caracteres
        assert parse_valor("        1.621,00") == Decimal("1621.00")

    def test_sem_milhar(self):
        assert parse_valor("173,45") == Decimal("173.45")

    def test_milhar_multiplo(self):
        assert parse_valor("183.725,76") == Decimal("183725.76")

    def test_zero(self):
        # existe na fonte: benefício consumido por consignado
        assert parse_valor("0,00") == Decimal("0.00")

    def test_maximo_observado(self):
        assert parse_valor("      183.725,76") == Decimal("183725.76")


class TestExatidao:
    """O motivo de existir do ADR 0002."""

    def test_soma_de_centavos_e_exata(self):
        # 3 × 0,10 == 0,30 em Decimal; em float dá 0.30000000000000004
        valores = [parse_valor("0,10") for _ in range(3)]
        assert sum(valores) == Decimal("0.30")

    def test_float_erraria_aqui(self):
        """Documenta o defeito que Decimal evita — não é teste do nosso código."""
        assert 0.1 + 0.1 + 0.1 != 0.3          # float erra
        soma = sum(parse_valor("0,10") for _ in range(3))
        assert soma == Decimal("0.30")          # Decimal acerta

    def test_soma_grande_mantem_centavo(self):
        # ordem de grandeza do total real: R$ 78,5 bilhões
        base = parse_valor("78.521.752.562,12")
        assert base + Decimal("0.01") == Decimal("78521752562.13")

    def test_comparacao_sem_tolerancia(self):
        """Tolerância zero: ou é igual, ou o gate reprova."""
        a = parse_valor("173,45")
        b = parse_valor("173,44")
        assert a != b
        assert a - b == Decimal("0.01")   # o centavo do caso Northwind


class TestEntradaInvalida:
    @pytest.mark.parametrize("texto", ["", "   ", "abc", "1,2,3"])
    def test_texto_ilegivel_levanta(self, texto):
        """Falhar alto é o comportamento certo: ingest_bronze conta como rejeição."""
        from decimal import InvalidOperation
        with pytest.raises((InvalidOperation, ValueError)):
            parse_valor(texto)
