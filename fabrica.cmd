@echo off
REM Ponte Windows -> fabrica INSS no WSL.
REM O Hermes roda no Windows; a fabrica roda no Ubuntu-24.04.
REM
REM Uso:
REM   fabrica.cmd pendentes
REM   fabrica.cmd processar 2026-03
REM   fabrica.cmd relatorio 2026-02
REM
REM Devolve JSON. O campo "mensagem" e o texto para o humano;
REM "escalar_para_humano" e o que o agente NAO decide.

wsl.exe -d Ubuntu-24.04 -- bash -c "cd /home/nobru/darkfactory-inss && .venv/bin/python scripts/operador.py %*"
