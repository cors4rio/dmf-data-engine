# Central DMF — Guia para Claude Code

Este arquivo é lido automaticamente pelo Claude Code em toda sessão. Define as regras obrigatórias antes de qualquer implementação neste projeto.

---

## Leitura Obrigatória por Tipo de Tarefa

Antes de escrever qualquer código, leia os documentos abaixo conforme o escopo da tarefa. Não pule esta etapa.

| Tarefa | Documentos obrigatórios |
|---|---|
| Qualquer alteração no código | `docs/arquitetura.md` + `docs/design-patterns.md` |
| Novo módulo ou alteração em módulo existente | + `docs/modulos.md` |
| Regras de negócio (fiscal, dp, contábil) | + `docs/regras-de-negocio.md` |
| Build, deploy, segurança, observabilidade | + `docs/operacoes.md` |
| Primeiro contato com o projeto | `docs/onboarding.md` (leitura completa) |
| Integrar um novo módulo | `docs/design-patterns.md` Padrão 0 (default) + `docs/modulos.md` |

---

## Arquitetura — Princípios Inegociáveis

- **Central DMF é a plataforma.** Automação de Horas é o *primeiro serviço*, não o produto principal. Qualquer referência ao produto principal deve ser à Central DMF.
- **Novos módulos usam Padrão 0 (inline) por default.** Padrão A/B/C apenas quando há razão explícita para processo separado. Ver `docs/design-patterns.md` — Árvore de Decisão.
- **Todo `execute()` retorna `{"ok": bool}`.** Nenhuma exceção não tratada pode chegar ao JS. Ver Seção 10 de `design-patterns.md`.
- **Lock cooperativo é obrigatório** antes de qualquer escrita na planilha master. Liberar sempre no `finally`.
- **Imports de bibliotecas pesadas** (`openpyxl`, `pyodbc`, drivers) ficam dentro de `execute()`, nunca no topo do módulo.
- **`main.py` da Central** é tocado apenas para adicionar uma linha de `registry.register(...)`. Lógica de negócio nunca entra no `main.py`.

---

## Comandos do Projeto

```
# Rodar Central DMF (dev) — 64-bit (banco via DSN-less, ver docs/legacy/migracao-64bit.md)
py -3-64 dmf_engine/main.py

# Rodar Automação de Horas (dev)
py -3-64 services/automacao_horas/main.py

# Build do executável
build.bat
```

---

## O Que Nunca Fazer

- Não versionar `config.json`, `supervisores.json`, logs, planilhas ou qualquer dado de cliente.
- Não reintroduzir conexão via `DSN=` ao banco — usar sempre DSN-less (DRIVER+host+porta). O banco é SQL Anywhere 17 com driver 64-bit; a antiga amarra 32-bit foi removida (ver docs/legacy/migracao-64bit.md).
- Não escrever lógica de negócio em `main.py` da Central.
- Não usar `print()` em produção — usar `logging.getLogger("NomeDoModulo")`.
- Não hardcodar caminhos de máquina — usar `config.json`.
- Não pular o lock cooperativo em módulos que escrevem na master.
- Não tratar Automação de Horas como o produto principal em documentação ou código.

---

## Onde Encontrar o Quê

| O que preciso | Onde está |
|---|---|
| Como funciona a plataforma (visão geral) | `docs/arquitetura.md` |
| Qual padrão usar para integração | `docs/design-patterns.md` — Árvore de Decisão |
| Contratos de entrada/saída dos módulos | `docs/modulos.md` |
| Regras de cálculo fiscal/DP/contábil | `docs/regras-de-negocio.md` |
| Como fazer build e deploy | `docs/operacoes.md` |
| Setup local do ambiente | `docs/onboarding.md` |
| Termos de domínio (GELOGUSER, planilha master, etc.) | `docs/glossario.md` |
| Próximas tarefas e serviços planejados | `docs/ROADMAP.md` |
