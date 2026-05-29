# Plano de Desacoplamento — Central DMF × Automação de Horas
> Status: ✅ decisões confirmadas — aguardando aprovação para executar  
> Data: 28/05/2026

## Decisões Confirmadas

| Questão | Decisão |
|---|---|
| Login da Automação | **SSO via token** — usuário logado na Central não loga de novo |
| Janela da Automação | **PyWebView próprio** — abre como janela separada, sem embutir na Central |

---

## O Problema Confirmado

O `dmf_engine/main.py` atual **é a Automação de Horas disfarçada de app principal**.

Ela nasceu como a ferramenta de controle de horas, evoluiu para incluir a shell da Central DMF (telas de setor, login, módulos), mas nunca separou os dois papéis. O resultado:

- A Central DMF **obrigatoriamente roda em Python 32-bit** por causa do driver ODBC do Domínio — que é uma restrição exclusiva da Automação de Horas.
- Qualquer novo módulo que precise de bibliotecas 64-bit não pode conviver no mesmo processo.
- A plataforma está presa às limitações de um de seus serviços.

**O `index.html` já sabe a diferença.** Ele tem `screen-sector`, `screen-login`, `screen-module` (Central DMF) e os painéis de fiscal/dp/contabil (Automação de Horas). A divisão existe na UI — falta existe no backend.

---

## Divisão de Responsabilidade

### O que é Central DMF (plataforma)
| Componente | Arquivo atual | Destino |
|---|---|---|
| Telas de setor, login, shell | `ui/index.html` linhas 591–734 | Fica na Central DMF |
| Autenticação por papel | `auth.py` | Fica — é da plataforma |
| Plugin system | `modules/base.py`, `registry.py` | Fica — é da plataforma |
| EventBus, ThreadRunner, Config | `core/` | Fica — é da plataforma |
| Bridge JS ↔ Python (api.py) | `api.py` linhas 1–190 | Fica — métodos de plataforma |

### O que é Automação de Horas (serviço dentro de GESTÃO)
| Componente | Arquivo atual | Destino |
|---|---|---|
| ODBC Domínio, Excel, lock | `engine/` inteiro | Vai para a Automação |
| Lógica fiscal, dp, contabil | `modulos/` inteiro | Vai para a Automação |
| Adaptadores de módulo | `modules/m_fiscal.py`, `m_dp.py`, `m_contabil.py` | Vão para a Automação |
| Config de banco, planilha master | `config.json` (chaves db_*, master_path) | Ficam na Automação |
| Métodos específicos da automação | `api.py` linhas 196–731 | Vão para a Automação |
| A janela PyWebView completa atual | `main.py` | Bifurca em dois |

---

## Arquitetura Alvo

```
N8N automacao/
│
├── central_dmf/                    ← NOVO — app da plataforma
│   ├── main.py                     ← Python 64-bit, sem restrição ODBC
│   ├── auth.py                     ← idêntico ao atual
│   ├── config.json                 ← só configs da plataforma
│   ├── supervisores.json           ← idêntico ao atual
│   ├── core/                       ← idêntico ao atual
│   │   ├── event_bus.py
│   │   ├── thread_runner.py
│   │   └── config.py
│   ├── modules/
│   │   ├── base.py                 ← idêntico ao atual
│   │   ├── registry.py             ← idêntico ao atual
│   │   └── m_automacao_horas.py    ← NOVO launcher (Padrão B)
│   └── ui/
│       └── index.html              ← só as telas da plataforma (sem painéis de horas)
│
└── services/
    └── automacao_horas/            ← o app atual movido para cá
        ├── main.py                 ← o main.py atual, 32-bit, intocado
        ├── auth.py                 ← cópia própria ou referência
        ├── config.json             ← configs específicas (db, master_path)
        ├── engine/                 ← o engine/ atual, movido
        ├── modulos/                ← o modulos/ atual, movido
        └── modules/                ← m_fiscal, m_dp, m_contabil
```

**Comunicação entre eles:**
```
Central DMF (64-bit, PyWebView)
  └── GESTÃO → card "Automação de Horas"
        └── m_automacao_horas.py (Padrão B)
              └── subprocess.Popen([python_32bit, services/automacao_horas/main.py])
                    └── Abre janela própria do app atual — intocado
```

---

## Plano de Migração — 4 Fases

### ⚠️ Regra de ouro durante a migração
> Em nenhum momento o app atual para de funcionar.  
> Cada fase é independente e reversível via `git revert`.  
> A Automação de Horas continua rodando pelo `run.bat` atual durante todo o processo.

---

### Fase 1 — Separar a estrutura de pastas (sem mudar código)
**Tempo estimado: 30 minutos**  
**Risco: zero**

```
Criar:
  services/automacao_horas/

Mover (git mv — preserva histórico):
  engine/           → services/automacao_horas/engine/
  modulos/          → services/automacao_horas/modulos/
  dmf_engine/modules/m_fiscal.py   → services/automacao_horas/modules/m_fiscal.py
  dmf_engine/modules/m_dp.py       → services/automacao_horas/modules/m_dp.py
  dmf_engine/modules/m_contabil.py → services/automacao_horas/modules/m_contabil.py
```

Atualizar os imports nos arquivos movidos para apontar para os novos caminhos.  
Testar: `run.bat` ainda funciona? Se sim, commit. Se não, revert.

---

### Fase 2 — Dar à Automação de Horas seu próprio main.py com SSO
**Tempo estimado: 3 horas**  
**Risco: baixo**

Criar `services/automacao_horas/main.py` baseado no `dmf_engine/main.py` atual, com:
- A restrição 32-bit permanece aqui — onde pertence
- Suporte ao token de sessão passado pela Central (SSO)
- Remove as telas da plataforma (seleção de setor, login da Central)
- Mantém os painéis de fiscal/dp/contabil intactos

```python
# services/automacao_horas/main.py — adição do SSO no boot
import sys, os, json, tempfile

def _recuperar_sessao_via_token() -> dict | None:
    """Lê o token passado pela Central DMF e reconstrói a sessão."""
    token = None
    for i, arg in enumerate(sys.argv):
        if arg == "--session-token" and i + 1 < len(sys.argv):
            token = sys.argv[i + 1]
            break
    if not token:
        return None

    caminho = os.path.join(tempfile.gettempdir(), f"dmf_session_{token}.json")
    if not os.path.exists(caminho):
        return None

    try:
        with open(caminho, encoding="utf-8") as f:
            dados = json.load(f)
        os.remove(caminho)  # uso único — apaga imediatamente

        from datetime import datetime
        expira = datetime.fromisoformat(dados["expira_em"])
        if datetime.now() > expira:
            return None  # token expirado

        return {
            "nome": dados["usuario"],
            "label": dados.get("label", dados["usuario"].title()),
            "papel": dados["papel"],
            "maquina": dados.get("maquina"),
        }
    except Exception:
        return None

# No boot, antes de criar a janela:
_sessao_inicial = _recuperar_sessao_via_token()
# Se _sessao_inicial não for None, a Api inicia já autenticada
# e a UI pula a tela de login
```

O `dmf_engine/main.py` atual continua funcionando como está durante essa fase.

---

### Fase 3 — Limpar a Central DMF e adicionar o Launcher com SSO
**Tempo estimado: 3 horas**  
**Risco: médio**

Remover do `dmf_engine/main.py` e `api.py`:
- Registro de `FiscalModule`, `DPModule`, `ContabilModule`
- Métodos específicos da automação em `api.py` (linhas 196–731)
- Imports de `engine/` e `modulos/`
- O guard 32-bit (não é mais responsabilidade da Central)

Adicionar `dmf_engine/modules/m_automacao_horas.py`:

```python
# dmf_engine/modules/m_automacao_horas.py
import os, sys, json, secrets, subprocess, tempfile
from datetime import datetime, timedelta
from dmf_engine.modules.base import BaseModule, ModuleMeta

# Caminho para o Python 32-bit da Automação de Horas.
# Pode ser o mesmo venv 32-bit que era usado antes, ou um novo.
# Configurável em config.json como "automacao_horas_python".
PYTHON_32_PADRAO = r"C:\Python32\python.exe"  # ajustar após migração

class AutomacaoHorasLauncher(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="automacao_horas",
            nome="Automação de Horas",
            desc="Apuração e lançamento de horas via ERP Domínio.",
            setor="GESTAO",
            icon="ti-clock-play",
            color="#2B65B5",
            papeis=["admin", "contabil", "fiscal", "dp"],
        )

    def execute(self, opcoes: dict) -> dict:
        sessao = self.sessao()
        if not sessao:
            return {"ok": False, "erro": "Sessão não autenticada."}

        # 1. Gerar token de sessão único (30 segundos de validade)
        token = secrets.token_hex(16)
        dados_sessao = {
            "usuario": sessao["nome"],
            "label":   sessao.get("label", ""),
            "papel":   sessao["papel"],
            "maquina": sessao.get("maquina", ""),
            "expira_em": (datetime.now() + timedelta(seconds=30)).isoformat(),
        }
        caminho_token = os.path.join(
            tempfile.gettempdir(), f"dmf_session_{token}.json"
        )
        try:
            with open(caminho_token, "w", encoding="utf-8") as f:
                json.dump(dados_sessao, f)
        except Exception as e:
            return {"ok": False, "erro": f"Falha ao criar token de sessão: {e}"}

        # 2. Resolver o caminho do Python 32-bit e do app
        python_32 = self.cfg("automacao_horas_python", PYTHON_32_PADRAO)
        app_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__),
            "..", "..", "services", "automacao_horas", "main.py"
        ))

        if not os.path.exists(app_path):
            return {"ok": False, "erro": f"Automação não encontrada: {app_path}"}
        if not os.path.exists(python_32):
            return {"ok": False, "erro": f"Python 32-bit não encontrado: {python_32}"}

        # 3. Lançar como processo separado — janela PyWebView própria
        self.progress(10, "Abrindo Automação de Horas...")
        try:
            subprocess.Popen(
                [python_32, app_path, "--session-token", token],
                creationflags=(
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                ),
            )
            self.progress(100, "Automação de Horas aberta.")
            return {"ok": True, "msg": "Automação de Horas aberta com sessão ativa."}
        except Exception as e:
            os.remove(caminho_token)  # limpa o token se o lançamento falhar
            return {"ok": False, "erro": str(e)}
```

Registrar em `dmf_engine/main.py`:
```python
from dmf_engine.modules.m_automacao_horas import AutomacaoHorasLauncher
_registry.register(AutomacaoHorasLauncher(_bus, _config, _sessao_fn))
```

A Central DMF passa a ser processo 64-bit limpo. A Automação abre como janela separada já autenticada.

---

### Fase 4 — Renomear e finalizar
**Tempo estimado: 1 hora**

```
dmf_engine/ → central_dmf/     (ou manter dmf_engine — é só nome)
run.bat     → dois scripts:
  run_central.bat               ← abre a Central DMF (64-bit)
  run_automacao_horas.bat       ← abre direto a Automação (32-bit, para debug)
```

Atualizar `Instalar DMF Engine.bat` para refletir a nova estrutura.

---

## O que NÃO muda

| Item | Por quê |
|---|---|
| `auth.py` — lógica de autenticação | É correto e funciona. Pode ser compartilhado ou duplicado. |
| `core/event_bus.py`, `thread_runner.py` | Corretos. Cada app tem a sua cópia. |
| `modules/base.py`, `registry.py` | Contrato correto. Cada app tem a sua cópia. |
| `ui/index.html` — telas da Central | As telas de setor/login/shell permanecem. Os painéis de horas vão para a Automação. |
| A lógica da Automação de Horas | **Zero mudança.** A Automação continua funcionando exatamente como hoje. |

---

## Decisões Fechadas ✅

| # | Questão | Decisão |
|---|---|---|
| 1 | Login na Automação | **SSO por token** — arquivo temporário em `%TEMP%`, validade 30s, apagado na leitura |
| 2 | Janela da Automação | **PyWebView próprio** — janela separada, zero reescrita de UI |
| 3 | Nome da pasta | Manter `dmf_engine/` por ora — renomear na Fase 4 após tudo funcionar |

---

## Verificação por Fase

| Fase | Como verificar que funcionou |
|---|---|
| 1 | `run.bat` abre o app atual sem erro |
| 2 | `python services/automacao_horas/main.py` abre a janela de automação standalone |
| 3 | `python central_dmf/main.py` abre a Central sem erro, sem módulos de horas, com card "Automação de Horas" em GESTÃO |
| 4 | `run_central.bat` funciona; clicar no card abre a Automação de Horas |
