# Arquitetura — Central DMF

> Documento técnico-executivo da plataforma. Descreve contexto, componentes, comunicação, deployment e decisões arquiteturais.

---

## Sumário

1. [Visão de Contexto](#1-visão-de-contexto)
2. [Componentes](#2-componentes)
3. [Comunicação entre Processos — SSO](#3-comunicação-entre-processos--sso)
4. [Deployment](#4-deployment)
5. [Fluxo de Dados — Automação de Horas (Serviço 1)](#5-fluxo-de-dados--automação-de-horas-serviço-1)
6. [Estado de Transição da Central](#6-estado-de-transição-da-central)
7. [Decisões Arquiteturais](#7-decisões-arquiteturais)

---

## 1. Visão de Contexto

A **Central DMF** é uma plataforma desktop interna que fornece autenticação, plugin system extensível e infraestrutura para serviços de back-office do escritório DMF. Cada serviço acoplado à plataforma opera de forma independente, integrando sistemas externos — como o ERP Domínio e o OneDrive — conforme sua própria lógica, sem impactar o núcleo da plataforma.

O diagrama abaixo representa a Central DMF como plataforma extensível com seus componentes internos e os serviços que hospeda. A Automação de Horas é o Serviço 1; novos serviços se integram pelo mesmo mecanismo de launcher + SSO sem modificar a plataforma.

```mermaid
graph TD
    USR["Supervisores\n(usuários internos)"]

    subgraph PLATAFORMA["Central DMF — Plataforma (dmf_engine/)"]
        AUTH["Autenticação\nPBKDF2 · Machine Binding"]
        PLUGINS["Plugin System\nBaseModule · Registry"]
        UI["Interface\nPyWebView · Vanilla JS"]
        BUS["EventBus\nPython ↔ JS"]
    end

    subgraph S1["Serviço 1 — Automação de Horas (32-bit)"]
        FISCAL["FiscalModule"]
        DP["DPModule"]
        CONTABIL["ContabilModule"]
    end

    S2["Serviço 2\n(futuro)"]
    SN["Serviço N\n(futuro)"]

    ODBC["ERP Domínio\n(Sybase · ODBC 32-bit)"]
    MASTER["Planilha Master\n(.xlsm · OneDrive)"]

    USR --> PLATAFORMA
    PLATAFORMA -->|"SSO + subprocess"| S1
    PLATAFORMA -. "futuro" .-> S2
    PLATAFORMA -. "futuro" .-> SN
    S1 --> ODBC
    S1 --> MASTER
```
![diagrama](img/arquitetura_1.svg)


---

## 2. Componentes

### Central DMF

A Central DMF é a **camada de plataforma**: interface gráfica, autenticação, plugin system e orquestração. Não contém lógica de negócio setorial.

| Diretório | Responsabilidade |
|---|---|
| `dmf_engine/main.py` | Bootstrap: carrega componentes, registra módulos, abre janela PyWebView |
| `dmf_engine/api.py` | Bridge JS ↔ Python: dispatcher genérico de chamadas do frontend |
| `dmf_engine/auth.py` | Autenticação: PBKDF2-SHA256, machine binding, sessão por papel |
| `dmf_engine/core/` | EventBus, ThreadRunner, ConfigManager — infraestrutura da plataforma |
| `dmf_engine/modules/` | Plugin system: BaseModule, ModuleRegistry e adaptadores de módulo |
| `dmf_engine/ui/index.html` | SPA frontend: dashboard, telas de setor, execução de módulos |

### Automação de Horas

A Automação de Horas é o **primeiro serviço acoplado à plataforma**. Opera como processo 32-bit independente, obrigatório pelo driver ODBC do Sybase.

| Diretório | Responsabilidade |
|---|---|
| `services/automacao_horas/main.py` | Bootstrap standalone com suporte a SSO por token |
| `services/automacao_horas/engine/` | ODBC, planilha master, lock cooperativo, estado compartilhado |
| `services/automacao_horas/modules/` | Adaptadores Fiscal, DP e Contábil (herdam BaseModule) |
| `services/automacao_horas/modulos/` | Lógica de negócio pura por setor (sem UI, sem threading) |

### Separação de Responsabilidades

| Camada | Diretório | O que faz | Pode importar de |
|---|---|---|---|
| Plataforma | `dmf_engine/core/` | EventBus, threads, config | — (base) |
| Bridge | `dmf_engine/api.py` | Dispatcher JS ↔ Python | `core/`, `modules/` |
| Plugin System | `dmf_engine/modules/` | Contrato, registro, dispatch | `core/`, regras |
| Regras | `modulos/` | Lógica de negócio pura | `engine/` apenas |
| Infraestrutura | `engine/` | Banco, arquivo, lock, estado | — (base) |

**Regra crítica:** `modulos/` jamais importa de `dmf_engine/`. A lógica de negócio deve funcionar sem a janela PyWebView.

---

## 3. Comunicação entre Processos — SSO

A Central DMF e a Automação de Horas são processos separados. Para evitar que o usuário faça login duas vezes, o sistema implementa SSO via arquivo de token temporário.

O diagrama abaixo descreve o fluxo completo desde a ação do usuário até a abertura da janela da Automação.

```mermaid
sequenceDiagram
    participant U as Usuário
    participant C as Central DMF
    participant FS as Sistema de Arquivos (temp/)
    participant A as Automação de Horas

    U->>C: Clica em "Automação de Horas"
    C->>C: Gera token aleatório (secrets.token_hex)
    C->>FS: Cria dmf_session_<token>.json<br/>(usuario, papel, máquina, expira_em: +30s)
    C->>A: subprocess.Popen(py -3-32 main.py --session-token <token>)
    A->>FS: Lê dmf_session_<token>.json
    A->>A: Valida: token não expirado?
    A->>FS: Deleta arquivo de token
    A->>A: Carrega sessão (usuario, papel, maquina)
    A->>U: Abre janela com usuário já autenticado
    C-->>U: Retorna {"ok": true} (launcher concluído)
```
![diagrama](img/arquitetura_2.svg)


O token expira em 30 segundos e é deletado após consumo. Se o prazo expirar antes do processo filho iniciá-lo, a Automação exige login manual.

---

## 4. Deployment

O sistema opera em duas configurações: **desenvolvimento** (repositório clonado, Python direto) e **produção** (binário compilado com PyInstaller, distribuído pela rede corporativa).

```mermaid
graph TD
    DEV["Máquina do Desenvolvedor\n(Python 64-bit + Python 32-bit)"]
    BUILD["build.bat\n(PyInstaller — empacota dmf_engine/)"]
    NET["Pasta de Rede\n(dist/dmf_engine/ copiado)"]
    U1["Máquina Usuário 1\n(Instalar DMF Engine.bat)"]
    U2["Máquina Usuário 2"]
    U3["Máquina Usuário 3"]

    DEV -->|"py -3-32 dmf_engine/main.py (dev)"| DEV
    DEV -->|"build.bat"| BUILD
    BUILD -->|"Copia para rede"| NET
    NET -->|"Instalação local"| U1
    NET -->|"Instalação local"| U2
    NET -->|"Instalação local"| U3
```
![diagrama](img/arquitetura_3.svg)


### Frozen Mode

Em produção (binário compilado), o PyInstaller altera a estrutura de diretórios. O código distingue as duas situações:

| Variável | Desenvolvimento | Produção (frozen) |
|---|---|---|
| `BASE_DIR` | Diretório do `main.py` | Diretório do `.exe` |
| `RESOURCES_DIR` | Idem `BASE_DIR` | `sys._MEIPASS/dmf_engine/` (assets empacotados) |
| `PROJECT_ROOT` | Raiz do repositório | Diretório do `.exe` |

`BASE_DIR` é usado para **escrita** (logs, config.json). `RESOURCES_DIR` é usado para **leitura de assets** (HTML, ícone). Essa distinção é obrigatória — assets em `_MEIPASS` são somente-leitura.

---

## 5. Fluxo de Dados — Automação de Horas (Serviço 1)

> Este fluxo é específico do primeiro serviço acoplado à plataforma. Cada serviço futuro implementará seu próprio pipeline de dados.

O usuário interage com a Central DMF, seleciona o módulo Automação de Horas e dispara a execução. A Central lança o processo de Automação de Horas (32-bit) via SSO, que então extrai dados do ERP, processa as regras de negócio por setor e escreve na planilha master. O sistema garante acesso exclusivo à planilha durante a escrita via lock cooperativo.

```mermaid
graph TD
    UI["Interface\n(Usuário seleciona módulo e competência)"]
    LOCK["Lock Cooperativo\n(adquire .dmflock no OneDrive)"]
    ODBC["Extração ODBC\n(Consulta Sybase — logs de uso, folha, faturamento)"]
    CALC["Processamento\n(Regras de negócio por setor)"]
    WRITE["Escrita na Master\n(MasterWriter — xlsm sem quebrar fórmulas)"]
    UNLOCK["Libera Lock"]
    DONE["Resultado exibido na UI"]

    UI --> LOCK
    LOCK -->|"Lock adquirido"| ODBC
    LOCK -->|"Lock negado"| DONE
    ODBC --> CALC
    CALC --> WRITE
    WRITE --> UNLOCK
    UNLOCK --> DONE
```
![diagrama](img/arquitetura_4.svg)


---

## 6. Estado de Transição da Central

A Central DMF foi desacoplada da execução Fiscal/DP/Contábil (v0.2.0), mas **mantém dependências residuais** em `engine/` para as seguintes funcionalidades:

| Funcionalidade | Dependência residual | Justificativa |
|---|---|---|
| Dashboard de estado | `engine/estado_compartilhado.py` | Lê o JSON de estado multi-usuário |
| Diagnóstico ODBC | `engine/database.py` | Testa conectividade |
| Lock status | `engine/lock_master.py` | Verifica se a master está ocupada |
| Leitura da master | `engine/excel_parser.py` | Exibe informações na tela principal |

Essas dependências **não são o design final**. A limpeza está registrada em [`ROADMAP.md`](ROADMAP.md) como evolução futura — a Central deve expor essas informações via API REST da Automação, sem importar `engine/` diretamente.

Enquanto as dependências residuais existirem, a Central obrigatoriamente roda em **Python 32-bit** — a mesma restrição que motivou o desacoplamento. A eliminação dessas dependências libertará a Central para Python 64-bit.

---

## 7. Decisões Arquiteturais

| Decisão | Alternativas descartadas | Justificativa |
|---|---|---|
| **PyWebView** como UI | Electron, Flet | Electron: +150MB de overhead para app sem internet. Flet: travava com PyInstaller + driver ODBC. |
| **Vanilla JS** (sem framework) | React, Vue | PyInstaller empacota `index.html` estático; frameworks exigem `npm build` e `node_modules` a cada deploy. |
| **Python 32-bit obrigatório** | Python 64-bit | Driver ODBC do Sybase SQL Anywhere (Domínio) não tem versão 64-bit. Python 64-bit lança erro IM014. |
| **Plugin Module System** | Monolito | `main.py` atingiu 1.771 linhas. Novo módulo = 1 arquivo + 1 linha de registro. `main.py` não é editado para novas funcionalidades. |
| **Lock via `.dmflock`** | SQLite, banco | OneDrive sincroniza arquivos; `open(path, 'x')` é atômico no Windows. Sem dependência extra. |
| **config.json** | Banco de dados | Volume pequeno, fácil de inspecionar, backup manual trivial, zero dependência extra. |
| **Mesmo repositório** | Repos separados | Todos os componentes são deployados juntos; um único `build.bat` gera tudo. |

---

*Última atualização: 2026-05-29*
