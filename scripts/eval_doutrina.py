#!/usr/bin/env python3
"""eval-3 — a doutrina foi respeitada.

Verifica B-4 (espécie pelo código) e B-4b (o Gold não agrega por nome),
B-5 (sentinelas fora do ranking), B-6 (27 UFs, grão único) e
B-7/b/c (congelados intactos: git, sha256 da fonte e permissão).

Executa contra o lakehouse real, não contra o packet. Se alguém reintroduzir
o agrupamento por nome, o número de rótulos cai e esta eval reprova.
"""
from __future__ import annotations

import argparse
import hashlib
import stat
import subprocess
import sys
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parents[1]
CONGELADOS = ["_raw/", "contracts/", "docs/adrs/"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--competencia", default="2026-01")
    args = ap.parse_args()

    db = BASE / "lakehouse" / args.competencia / "inss.duckdb"
    if not db.exists():
        print(f"eval-3 FALHOU · sem lakehouse para {args.competencia}")
        return 1

    con = duckdb.connect(str(db), read_only=True)
    q = lambda s: con.execute(s).fetchone()[0]
    erros: list[str] = []

    # B-4 — espécie resolvida pelo código, não pelo nome truncado.
    #
    # ⚠ A versão anterior comparava especie_rotulo com especie_nome_fonte, duas
    # colunas que o PRÓPRIO Silver constrói na mesma query. Elas não podem
    # divergir: a eval validava a si mesma e passaria mesmo com o Gold inteiro
    # agregando por nome. Auditoria de 16/09/2026, objeção #7.
    #
    # O teste que importa é OBSERVAR a fonte: contar quantas espécies distintas
    # existem de verdade (por código) e quantas sobrariam se alguém agrupasse
    # pelo nome truncado. Se os dois números forem iguais, ou o truncamento
    # deixou de fundir — ou a resolução por código deixou de acontecer.
    por_codigo = q("select count(distinct especie_codigo) from silver")
    por_nome_fonte = q("select count(distinct especie_nome_fonte) from silver")
    if por_codigo <= por_nome_fonte:
        erros.append(f"B-4: códigos {por_codigo} <= nomes truncados "
                     f"{por_nome_fonte} — o truncamento deixou de fundir, ou a "
                     f"espécie deixou de ser resolvida pelo código")
    rotulos = q("select count(distinct especie_rotulo) from silver where not especie_orfa")
    truncados = por_nome_fonte

    # B-4b — o Gold é quem publica. Se alguém trocar a chave de agregação de
    # código para nome, a soma continua batendo e nada acusa, exceto isto.
    bancos_cod = q("select count(distinct banco_codigo) from gold_concentracao_bancaria")
    bancos_nome = q("select count(distinct banco_nome) from gold_concentracao_bancaria")
    if bancos_cod <= bancos_nome:
        erros.append(f"B-4b: Gold com códigos {bancos_cod} <= nomes "
                     f"{bancos_nome} — agregação por nome? (DF-INSS-002: "
                     f"748/756 e 037/047 colidem)")
    # O grão do Gold é (competencia, banco_codigo, uf_residencia). A prova de
    # que ele agrega por CÓDIGO é que um mesmo código nunca se parte em duas
    # linhas da mesma UF.
    #
    # ⚠ Não confundir com o inverso. Um par (nome, UF) cobrindo dois códigos é
    # EXATAMENTE o comportamento correto: 748 e 756 compartilham o nome
    # truncado 'Banco Cooperativ' e têm de continuar em linhas separadas. Uma
    # primeira versão desta eval acusava esses 36 pares como fusão — estava
    # chamando de defeito a própria defesa contra o defeito (DF-INSS-002).
    partido = q("""select count(*) from (
                     select banco_codigo, uf_residencia
                     from gold_concentracao_bancaria
                     group by 1,2 having count(*) > 1)""")
    if partido:
        erros.append(f"B-4b: {partido} pares (código, UF) em mais de uma linha "
                     f"— o grão do Gold não é por código")

    # B-5 — o banco 998 é o INSS pagando direto, não instituição financeira
    ranqueado = q("""select count(*) from gold_concentracao_bancaria
                     where e_inss_direto and posicao_na_uf is not null""")
    if ranqueado:
        erros.append(f"B-5: banco 998 ranqueado em {ranqueado} UFs")
    if not q("select count(*) from gold_concentracao_bancaria where e_inss_direto"):
        erros.append("B-5: banco 998 ausente — deveria ter linha própria")

    # B-6 — cobertura nacional e grão único
    ufs = q("select count(distinct uf_residencia) from gold_concentracao_bancaria")
    if ufs != 27:
        erros.append(f"B-6: {ufs} UFs, esperado 27")
    dup = q("""select count(*) from (
                 select 1 from gold_concentracao_bancaria
                 group by competencia, banco_codigo, uf_residencia
                 having count(*) > 1)""")
    if dup:
        erros.append(f"B-6: grão duplicado em {dup} combinações")

    con.close()

    # B-7 — nada foi escrito nas pastas congeladas.
    #
    # ⚠ `git status` sozinho é cego para dois casos, e os dois importam:
    #   1. _raw/*.zip está no .gitignore — a FONTE, o artefato mais congelado
    #      da fábrica, era exatamente o que o git não olhava.
    #   2. uma alteração já commitada some do status: fica limpa por definição.
    # A cadeia de custódia se prova por sha256 e por permissão, não por git.
    # Auditoria de 16/09/2026, objeção #8.
    sujo = subprocess.run(
        ["git", "-C", str(BASE), "status", "--short", "--ignored=no", *CONGELADOS],
        capture_output=True, text=True,
    ).stdout.strip()
    if sujo:
        erros.append("B-7: pasta congelada alterada:\n      "
                     + sujo.replace("\n", "\n      "))

    # B-7b — a fonte confere com o sha256 registrado no download
    for zipf in sorted((BASE / "_raw").glob("fonte-*.zip")):
        registro = zipf.with_suffix(".zip.sha256")
        if not registro.exists():
            erros.append(f"B-7b: {zipf.name} sem sha256 registrado — "
                         f"sem cadeia de custódia")
            continue
        esperado = registro.read_text(encoding="utf-8").split()[0]
        h = hashlib.sha256()
        with zipf.open("rb") as f:
            for bloco in iter(lambda: f.read(1 << 20), b""):
                h.update(bloco)
        if h.hexdigest() != esperado:
            erros.append(f"B-7b: {zipf.name} NÃO confere com o sha256 do "
                         f"download — a fonte foi alterada")

    # B-7c — congelado é chmod 444. Um arquivo gravável não está congelado:
    # está apenas intocado até agora, o que é sorte, não garantia.
    gravaveis = []
    for pasta in ("_raw", "contracts"):
        for arq in sorted((BASE / pasta).rglob("*")):
            if arq.is_file() and not arq.name.startswith("_") and \
                    arq.stat().st_mode & stat.S_IWUSR:
                gravaveis.append(str(arq.relative_to(BASE)))
    if gravaveis:
        erros.append("B-7c: congelado mas gravável (chmod 444 pendente):\n      "
                     + "\n      ".join(gravaveis))

    if erros:
        print("eval-3 FALHOU")
        for e in erros:
            print(f"  - {e}")
        return 1

    print(f"eval-3 OK · {rotulos} rótulos > {truncados} truncados · "
          f"998 fora do ranking · {ufs} UFs · congelados intactos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
