# Changelog

Todas as mudanças relevantes da Central DMF são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/). Versões seguem [Semantic Versioning](https://semver.org/lang/pt-BR/) — `MAJOR.MINOR.PATCH`.

---

## [Unreleased]

*Mudanças em desenvolvimento no momento.*

---

## [0.3.1] — 2026-05-29

### Simplificação Arquitetural — Relatório de Rendimentos

Identificado e corrigido over-engineering: `relatorio_rendimentos` foi migrado de subprocess+janela própria para módulo inline (Padrão 0), o padrão correto para código Python puro sem necessidade de janela separada.

**Removido:**
- `services/relatorio_rendimentos/main.py`, `auth.py`, `api.py`, `compat.py`, `core/`, `modules/`, `ui/` — infraestrutura desnecessária (janela PyWebView própria, tela de login separada, SSO token, duplicações de EventBus/ThreadRunner/auth)

**Alterado:**
- `dmf_engine/modules/m_relatorio_rendimentos.py` — reescrito de `RelatorioRendimentosLauncher` (subprocess) para `RelatorioRendimentosModule` (BaseModule inline, Padrão 0)
- `dmf_engine/api.py` — adicionados `abrir_seletor_pasta()` e `abrir_arquivo()` para uso pelo modal inline
- `dmf_engine/ui/index.html` — `pfAbrirModulo('relatorio_rendimentos')` abre modal inline na Central DMF (sem nova janela); adicionado bloco `rfAbrirModal / rfEscolherPasta / rfGerarRelatorio`
- `docs/design-patterns.md` — adicionado **Padrão 0 (Módulo Inline)** como padrão default; árvore de decisão revisada
- `CLAUDE.md` — regra de integração corrigida: Padrão 0 por default, não A/B/C

---

## [0.3.0] — 2026-05-29

### Novo Serviço: Relatório de Rendimentos

Segundo serviço acoplado à Central DMF. Integra o projeto externo `efd_contabil` como serviço independente com UI própria.

**Adicionado:**
- `services/relatorio_rendimentos/` — novo serviço Python 32-bit com stack completa (core, modules, api, ui)
- `modulos/relatorio_rendimentos_isentos.py` — extrai EFD-Reinf rendimentos isentos do Domínio via ODBC e gera Excel formatado
- `modules/m_rendimentos_isentos.py` — adaptador BaseModule com contrato `{ok, arquivo, total}`
- `dmf_engine/modules/m_relatorio_rendimentos.py` — launcher SSO na Central DMF (setor CONTABIL)
- UI com seletor de pasta de saída (`webview.FOLDER_DIALOG`), progress bar EventBus e botão "Abrir arquivo"
- SSO por token idêntico ao padrão da Automação de Horas (30s, uso único)

**Modificado:**
- `dmf_engine/main.py` — registro do `RelatorioRendimentosLauncher`
- `docs/modulos.md` — catálogo atualizado com Serviço 2

---

## [0.2.0] — 2026-05-28

### Desacoplamento Central ↔ Automação de Horas

Esta release implementou a separação arquitetural da Central DMF (plataforma) e da Automação de Horas (primeiro serviço). O objetivo foi remover a restrição de Python 32-bit da plataforma principal, permitindo que futuros módulos usem bibliotecas 64-bit.

### Adicionado

- **Central DMF como plataforma**: `dmf_engine/` reposicionada como plataforma de plugins agnóstica de serviços setoriais.
- **Serviço Automação de Horas isolado**: `services/automacao_horas/` com cópias independentes de `engine/`, `modulos/` e `modules/`.
- **SSO por token temporário**: módulo `AutomacaoHorasLauncher` gera token JSON em `temp/` (validade 30s) e passa ao processo filho via `--session-token`.
- **Launcher `AutomacaoHorasLauncher`**: `dmf_engine/modules/m_automacao_horas.py` lança `services/automacao_horas/main.py` como subprocess Python 32-bit.
- **Guard de arquitetura**: `services/automacao_horas/main.py` avisa se executado com Python 64-bit (conexões ODBC falharão).
- **`compat.py`**: camada de compatibilidade que exporta `db`, `estado_sh` e `PROJECT_ROOT` para os adaptadores de módulo da Automação.

### Alterado

- **Automação de Horas** passa a consumir suas próprias cópias de `engine/` e `modulos/` em `services/automacao_horas/` em vez das da raiz.
- **`dmf_engine/main.py`** removidos os registros diretos de `FiscalModule`, `DPModule` e `ContabilModule` — esses módulos agora pertencem à Automação de Horas.
- **Dependências residuais da Central** em `engine/` da raiz documentadas explicitamente: `database.py`, `estado_compartilhado.py`, `lock_master.py`, `excel_parser.py` ainda são importados pela Central para dashboard e diagnóstico — limpeza registrada no [ROADMAP](ROADMAP.md).
- **Documentação técnica** reestruturada: 10 documentos consolidados em `docs/`, histórico preservado em `docs/legacy/`.

### Removido

- Módulos `FiscalModule`, `DPModule` e `ContabilModule` removidos do registro da Central DMF (permanecem ativos em `services/automacao_horas/modules/`).
- Guard de 32-bit da Central DMF removido — a Central não tem mais dependência direta de ODBC.
- 7 arquivos `.md` técnicos movidos da raiz para `docs/legacy/`.

---

## [0.1.0] — 2026-03-11

### Versão Inicial — Piloto em Produção

Esta versão consolidou o sistema a partir dos scripts ETL iniciais, introduziu a interface desktop e estabeleceu as fundações da arquitetura de plugins.

> Detalhes históricos desta versão estão em [`docs/legacy/TASKBOARD.md`](legacy/TASKBOARD.md) (seção "Concluído") e [`docs/legacy/task-REFATORACAO.md`](legacy/task-REFATORACAO.md).

### Adicionado (resumo)

- **Interface PyWebView**: substituiu o Flet, unificou o frontend em `dmf_engine/ui/index.html`.
- **Plugin System**: `BaseModule`, `ModuleMeta`, `ModuleRegistry` — módulo novo = 1 arquivo + 1 linha de registro.
- **5 usuários fixos**: Carol (admin), James (contábil), Nayane (fiscal), Jailton (DP), Adriele (legalização).
- **Autenticação PBKDF2-SHA256** com machine binding.
- **Lock cooperativo** via `.dmflock` atômico no OneDrive.
- **Módulos operacionais**: FiscalModule (coluna O + adicional 80%), DPModule (coluna Q, fórmula cascata), ContabilModule (3 fases).
- **EventBus**: canal único Python → JS via `window.__onEvent`.
- **Build PyInstaller** (`build.bat` + `dmf_engine.spec`) e instalador `Instalar DMF Engine.bat`.
- **Specs de negócio** em `Specs_Definitivos/`: Planilha Master, Fiscal, DP, Contábil.

---

*Para histórico anterior à v0.1.0 (fase de scripts ETL), consultar [`docs/legacy/`](legacy/).*
