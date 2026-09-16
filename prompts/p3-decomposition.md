# P3 — Decomposition

**Onde:** Claude Code, **na mesma sessão do P2** (o contexto está carregado).
**Emite arquivo?** Sim — Task-Specs em `tasks/`.

---

## Cole isto

```
Transformar a estrutura do P2 em tarefas atômicas com eval executável.

REGRAS DE DECOMPOSIÇÃO

1. Uma tarefa = um artefato. Se produz dois arquivos independentes, são duas.
2. Toda tarefa tem eval que RODA — não "verificar se existe", mas executar
   e reprovar quando errado.
3. Toda tarefa declara creates_paths e touches_paths. Se o raio de mudança
   for maior que o declarado, a aceitação reprova (BLAST_RADIUS).
4. Tarefa que toca pasta congelada NÃO EXISTE. Se for necessária, ela é uma
   decisão do dono — vira ADR, não tarefa.
5. Se a tarefa cria mais de 3 caminhos, provavelmente são várias tarefas.

FORMATO — use tasks/T-20260915-processar-competencia.md como modelo

Frontmatter: id, title, effort, budget_iterations, creates_paths,
touches_paths, severity, owner, signed_off: false

Corpo:
  ## Goal            o que fica pronto, em um parágrafo
  ## Context         o que o executor precisa saber, com link para ADR
  ## Behavior        B-1, B-2... comportamentos verificáveis
  ## Success Criteria  eval_1(), eval_2()... funções bash que retornam 0/≠0
  ## Validation Card   YAML mapeando cada eval aos B-N que ela prova
  ## Exit Check      eval_1 && eval_2 && eval_3
  ## Rollback Plan   como desfazer
  ## Anti-Patterns   a saída fácil que alguém vai tentar
  ## Do-Not-Touch    _raw/ contracts/ docs/adrs/

CADA EVAL PRECISA
- rodar por comando, sem interação
- ser determinística: mesma entrada, mesmo resultado
- reprovar pelo motivo certo — não só "deu erro"
- terminar rápido: eval que reprocessa 41M de linhas não serve de gate

DEPOIS DE ESCREVER, VALIDE
  bash task-spec/bin/taskspec validate tasks/<arquivo>.md

REGRAS
- Não implemente nada. Este passe só decompõe.
- Se uma tarefa não tiver eval possível, ela não está pronta — diga isso.
- Toda referência a ADR ou contrato cita o caminho.

SAÍDA
- os arquivos em tasks/
- uma tabela: | Tarefa | Cria | Eval prova | Depende de |
```

---

## O que separa tarefa de desejo

| Desejo | Tarefa |
|---|---|
| "melhorar o tratamento de espécie" | cria `especie_rotulo`; eval: `count(distinct rotulo) > count(distinct nome_truncado)` |
| "garantir qualidade dos dados" | eval: `sum(silver) == sum(bronze)`, tolerância zero |
| "documentar melhor" | cria `docs/adrs/0006-x.md`; eval: o ADR existe e tem as 4 seções |

**Se você não consegue escrever a eval, a tarefa não está definida.**
