# Workflow: defeito novo na fonte

Apareceu algo que o contrato não previa. Este é o fluxo mais delicado da
fábrica — é onde a tentação de "dar um jeitinho" é maior.

**Quando:** um gate reprova por conteúdo, ou surge valor fora do domínio.
**Duração:** horas a dias. Não tem pressa — tem rigor.

---

## Regra zero

> **Um defeito novo é um achado, não um obstáculo.**

O primeiro impulso é fazer o pipeline voltar a rodar. Resista: a informação mais
valiosa está no momento em que ele parou.

---

## O fluxo

```text
1. MEDIR       quantas linhas? qual valor? aparece em outras competências?
2. CLASSIFICAR fonte errou · nós erramos · o contrato não decide
3. DECIDIR     você — não o agente, não eu
4. REGISTRAR   contrato + ADR se for não-óbvio
5. IMPLEMENTAR com gate que prova
6. VERIFICAR   evals verdes, congelado intacto
```

---

## 1. Medir antes de opinar

```bash
# quantas linhas, que valor, em que competências
.venv/bin/python -c "
import duckdb
for comp in ['2026-01','2026-02','2026-03']:
    c = duckdb.connect(f'lakehouse/{comp}/inss.duckdb', read_only=True)
    print(comp, c.execute('select count(*), sum(vl_liquido) from silver where <CONDIÇÃO>').fetchone())
    c.close()
"
```

**Caso isolado ou padrão?** O código 67 parecia acaso em 2026-02 (3 linhas).
Março trouxe 6 — recorrente e crescendo. A decisão foi outra por causa disso.

---

## 2. Classificar

| Situação | Código | O que fazer |
|---|---|---|
| a fonte declara X, as linhas somam Y | `CONFIRMED_SOURCE_DEFECT` | preserva os dois, recusa o lote |
| nosso código produz número errado | `MODERN_DEFECT` | **conserta a fábrica, nunca a expectativa** |
| o contrato/dicionário não decide | `CONTRACT_AMBIGUITY` | escala — **não chuta** |
| não deu para classificar | `UNRESOLVED` | não pode ser servido |

A pergunta que separa: **quem errou?** Se a resposta for "não dá para saber", é
ambiguidade — e ambiguidade escala.

---

## 3. Decidir — e só você decide

Esta etapa não se delega. Um agente pode medir, classificar e propor. Escolher
entre preservar, complementar ou recusar é decisão de dono.

Se a decisão for não-óbvia **e** provável de ser re-litigada, ela merece ADR.

---

## 4. Registrar

No contrato (`contracts/layout.yaml`):

```yaml
- id: DF-INSS-00N
  campo: <onde>
  descricao: <o quê>
  ocorrencias_medidas:
    "2026-01": {linhas: 0}
    "2026-02": {linhas: 3, valor: "3243.00"}
  classificacao: CONTRACT_AMBIGUITY
  tratamento: |
    <o que a fábrica faz — e o que NÃO faz>
  escalar_para: <quem decide fora daqui>
```

⚠️ `contracts/` é congelado. Mexer exige ADR novo — e o CI bloqueia PR sem ele.

---

## 5. Implementar

Toda mudança traz um gate que **reprova se estiver errada**:

```python
# exemplo real: o complemento nunca sobrepõe o oficial
sobreposto = [c for c in do_complemento if c in especies]
if sobreposto:
    falhas.append(f"complemento sobrepôs o dicionário oficial em {sobreposto}")
```

Sem esse gate, o complemento poderia reescrever o juiz aos poucos.

---

## 6. Verificar

```bash
make qa                      # lint, testes, agentes
make evals COMP=AAAA-MM      # as 3 evals
git status --short contracts/ docs/adrs/
```

A `eval_doutrina` verifica B-7: pasta congelada intacta. Se você mexeu no
contrato **por decisão registrada**, ela vai reprovar até você commitar — e isso
está certo.

---

## O que nunca fazer

| | Por quê |
|---|---|
| adicionar tolerância | a mentira vira ruído aceitável |
| inventar descrição para órfão | é `CONTRACT_AMBIGUITY`, escala |
| editar `especies-oficial.xlsx` | deixa de ser o publicado pelo INSS |
| editar ADR aceito | revisão se faz com ADR novo que supersede |
| "resolver" e seguir sem registrar | o próximo encontra e não sabe por quê |

---

## O precedente

O código **67** (`Pecúlio Obrigatório`) percorreu este fluxo inteiro:

```
medido      0 · 3 · 6 linhas em jan/fev/mar — recorrente
classificado CONTRACT_AMBIGUITY (o INSS não o documenta)
decidido     complemento separado, XLSX oficial intocado
registrado   DF-INSS-003 + especies-complemento.yaml + ADR 0004
gate novo    complemento nunca sobrepõe o oficial
resultado    66 rótulos · ambiguidade continua ABERTA
```

Recusamos a saída fácil de adicionar uma linha no dicionário — seria destruir a
prova de que o INSS não o documenta.

Ver: [`prompts/`](../../prompts/) para os 4 passes quando a decisão for grande.
