{
  "_comentario": [
    "Esta deny-list espelha protected_paths de .cvg/gate.yaml.",
    "Duas cercas, uma doutrina: se divergirem, a divergência é defeito.",
    "scripts/verificar_cercas.py confere que continuam de acordo — rode",
    "com `make cercas`, e o CI roda a cada PR.",
    "",
    "Gerada por nova-fabrica em {{DATA}} para {{DISPLAY_NAME}}."
  ],
  "permissions": {
    "deny": [
      "Write(_raw/**)",
      "Edit(_raw/**)",
      "Write(contracts/**)",
      "Edit(contracts/**)",
      "Write(docs/adrs/**)",
      "Edit(docs/adrs/**)",
      "Write(evidence/**)",
      "Edit(evidence/**)",
      "Write(.cvg/gate.yaml)",
      "Edit(.cvg/gate.yaml)",
      "Write(.github/workflows/**)",
      "Edit(.github/workflows/**)",
      "Bash(sed -i *)",
      "Bash(tee _raw/*)",
      "Bash(tee contracts/*)",
      "Bash(tee docs/adrs/*)",
      "Bash(tee evidence/*)",
      "Bash(rm -rf _raw*)",
      "Bash(chmod *contracts/*)",
      "Bash(chmod *_raw/*)"
    ]
  }
}
