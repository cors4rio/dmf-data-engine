# Taskboard — Desacoplamento Central DMF x Automação de Horas

> **Regra de ouro:** o `run.bat` atual deve funcionar a cada ponto de verificação.
> Só avance para a próxima fase após marcar todos os checkpoints. ✅

---

## FASE 1 — Preparar a estrutura (sem alterar código)
> **Tempo:** ~30 min | **Risco:** Zero | **Branch:** `feat/desacoplamento`

### 1.1 — Git
- `[x]` Confirmar stage limpo: `git status`
- `[x]` Criar branch: `git checkout -b feat/desacoplamento`

### 1.2 — Criar estrutura de pastas
- `[x]` Criar `services\`
- `[x]` Criar `services\automacao_horas\`
- `[x]` Criar `services\automacao_horas\engine\`
- `[x]` Criar `services\automacao_horas\modulos\`
- `[x]` Criar `services\automacao_horas\modules\`
- `[x]` Criar `services\automacao_horas\core\`
- `[x]` Criar `services\automacao_horas\ui\`

### 1.3 — Copiar arquivos da Automação (cópia — original intocado)
- `[x]` Copiar `engine\*.py` → `services\automacao_horas\engine\`
- `[x]` Copiar `modulos\*.py` → `services\automacao_horas\modulos\`
- `[x]` Copiar `dmf_engine\modules\m_fiscal.py` → `services\automacao_horas\modules\`
- `[x]` Copiar `dmf_engine\modules\m_dp.py` → `services\automacao_horas\modules\`
- `[x]` Copiar `dmf_engine\modules\m_contabil.py` → `services\automacao_horas\modules\`
- `[x]` Copiar `dmf_engine\modules\base.py` → `services\automacao_horas\modules\`
- `[x]` Copiar `dmf_engine\modules\registry.py` → `services\automacao_horas\modules\`
- `[x]` Copiar `dmf_engine\core\event_bus.py` → `services\automacao_horas\core\`
- `[x]` Copiar `dmf_engine\core\thread_runner.py` → `services\automacao_horas\core\`
- `[x]` Copiar `dmf_engine\core\config.py` → `services\automacao_horas\core\`
- `[x]` Copiar `dmf_engine\auth.py` → `services\automacao_horas\`
- `[x]` Copiar `dmf_engine\config.json` → `services\automacao_horas\config_template.json`
- `[x]` Copiar `dmf_engine\supervisores.json` → `services\automacao_horas\`
- `[x]` Copiar `dmf_engine\ui\index.html` → `services\automacao_horas\ui\`
- `[x]` Copiar logos/imagens da `dmf_engine\ui\` → `services\automacao_horas\ui\`

### 1.4 — Criar `__init__.py` nas pastas necessárias
- `[x]` `services\__init__.py` (vazio)
- `[x]` `services\automacao_horas\__init__.py` (vazio)
- `[x]` `services\automacao_horas\engine\__init__.py` (vazio)
- `[x]` `services\automacao_horas\modulos\__init__.py` (vazio)
- `[x]` `services\automacao_horas\modules\__init__.py` (vazio)
- `[x]` `services\automacao_horas\core\__init__.py` (vazio)

### 1.5 — Commit
- `[x]` `git add services\`
- `[x]` `git commit -m "feat: estrutura services/automacao_horas criada (copias sem alterar original)"`

### CHECKPOINT 1 ✅
- `[x]` `run.bat` → app abre normalmente?
- `[x]` Login funciona?
- `[x]` Módulo Fiscal executa?
- `[ ]` **Se falhou:** `git stash` e investigar antes de continuar

---

## FASE 2 — Criar o main.py standalone da Automação
> **Tempo:** ~3h | **Risco:** Baixo | **Original continua intocado**

### 2.1 — Criar `services\automacao_horas\main.py`
- `[x]` Criar `services\automacao_horas\main.py` (criado do zero — não cópia direta)
- `[x]` Ajuste de `sys.path` no início (`_ROOT` inserido em `sys.path[0]`)
- `[x]` Imports locais: `from core.*`, `from modules.*`, `from api import Api`
- `[x]` `compat.py` criado como shim (expõe `db`, `estado_sh`, `PROJECT_ROOT`, `window`)
- `[x]` Função `_recuperar_sessao_via_token()` implementada
- `[x]` `_sessao_sso = _recuperar_sessao_via_token()` capturado antes de criar janela
- `[x]` `sessao_inicial=_sessao_sso` passado para a Api no construtor
- `[x]` Título: `"DMF — Automação de Horas"`
- `[x]` Guard 32-bit mantido
- `[x]` `compat.window = window` propagado após `create_window`

### 2.2 — Adaptar a Api da Automação para SSO
- `[x]` Copiar `dmf_engine\api.py` → `services\automacao_horas\api.py`
- `[x]` `sessao_inicial=None` adicionado ao `__init__`; `self._sessao = sessao_inicial`
- `[x]` `get_sessao()` criado
- `[x]` `from dmf_engine.core.event_bus import json_safe` → `from core.event_bus import json_safe`

### 2.3 — UI SSO
- `[x]` Verificado: `verificar_estado_login()` já retorna sessão SSO (pois `self._sessao`
  é definido no construtor) — o handler `pywebviewready` existente redireciona automaticamente

### 2.4 — Testar Automação standalone (sem SSO)
- `[x]` `copy config_template.json config.json` em `services\automacao_horas\`
- `[x]` `py -3-32 services\automacao_horas\main.py` → abre com tela de login?
- `[x]` Login manual funciona?
- `[x]` Módulos Fiscal, DP, Contábil executam?
- `[x]` `run.bat` ainda funciona? (original intocado)

### 2.5 — Testar SSO manualmente
- `[x]` Criar `scratch_test_token.py` na raiz e executar
  → Deve abrir **já logado como Carol** sem tela de login
- `[x]` Apagar `scratch_test_token.py`

### 2.6 — Commit
- `[x]` `git commit -m "feat: automacao_horas/main.py standalone com SSO por token"`

### CHECKPOINT 2 ✅
- `[x]` `run.bat` → app original abre normalmente?
- `[x]` `py -3-32 services\automacao_horas\main.py` → abre standalone com tela de login?
- `[x]` SSO com token válido → abre já autenticado?
- `[x]` Token inválido/ausente → tela de login aparece normalmente?

---

## FASE 3 — Adicionar o Launcher na Central DMF
> **Tempo:** ~2h | **Risco:** Baixo | **Original ainda funciona em paralelo**

### 3.1 — Identificar o Python 32-bit
- `[x]` Rodar: `py -3-32 -c "import sys; print(sys.executable)"`
- `[x]` Caminho: `C:\Users\DMF-AUTOMACAO\AppData\Local\Programs\Python\Python314-32\python.exe`
- `[x]` Adicionado ao `dmf_engine\config.json` como `automacao_horas_python`

### 3.2 — Criar `dmf_engine\modules\m_automacao_horas.py`
- `[x]` Criar o arquivo com o código do launcher SSO:
  ```python
  import os, json, secrets, subprocess, tempfile
  from datetime import datetime, timedelta
  from dmf_engine.modules.base import BaseModule, ModuleMeta

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

          token = secrets.token_hex(16)
          dados = {
              "usuario":   sessao["nome"],
              "label":     sessao.get("label", ""),
              "papel":     sessao["papel"],
              "maquina":   sessao.get("maquina", ""),
              "expira_em": (datetime.now() + timedelta(seconds=30)).isoformat(),
          }
          caminho_token = os.path.join(tempfile.gettempdir(), f"dmf_session_{token}.json")
          try:
              with open(caminho_token, "w", encoding="utf-8") as f:
                  json.dump(dados, f)
          except Exception as e:
              return {"ok": False, "erro": f"Erro ao criar token: {e}"}

          python_32 = self._config.get("automacao_horas_python")
          app_path = os.path.normpath(os.path.join(
              os.path.dirname(__file__), "..", "..", "services", "automacao_horas", "main.py"
          ))

          if not os.path.exists(app_path):
              os.remove(caminho_token)
              return {"ok": False, "erro": f"Automação não encontrada: {app_path}"}
          if not python_32 or not os.path.exists(python_32):
              os.remove(caminho_token)
              return {"ok": False, "erro": "Python 32-bit não configurado. Verifique 'automacao_horas_python' no config.json"}

          self.progress(10, "Abrindo Automação de Horas...")
          try:
              subprocess.Popen(
                  [python_32, app_path, "--session-token", token],
                  creationflags=(subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP),
              )
              self.progress(100, "Automação de Horas aberta.")
              return {"ok": True, "msg": "Automação de Horas aberta com sessão ativa."}
          except Exception as e:
              if os.path.exists(caminho_token):
                  os.remove(caminho_token)
              return {"ok": False, "erro": str(e)}
  ```

### 3.3 — Registrar o launcher na Central DMF
- `[x]` `from dmf_engine.modules.m_automacao_horas import AutomacaoHorasLauncher` adicionado
- `[x]` `_registry.register(AutomacaoHorasLauncher(_bus, _config, _sessao_fn))` adicionado

### 3.4 — Verificar o setor GESTÃO na UI da Central
- `[x]` `sector-block gestao` confirmado no HTML
- `[x]` Catálogo atualizado: `controle-horas` → `automacao_horas` com icon `ti-clock-play`
- `[x]` `pfAbrirModulo` atualizado: case `automacao_horas` chama `executar_modulo`

### 3.5 — Commit
- `[x]` `git commit -m "feat: launcher AutomacaoHoras com SSO adicionado na Central DMF"`

### CHECKPOINT 3 ✅
- `[x]` `run.bat` → Central DMF abre normalmente?
- `[x]` Login como `carol/admin` funciona?
- `[x]` Card "Automação de Horas" aparece no painel GESTÃO?
- `[x]` Clicar no card → janela da Automação abre?
- `[x]` Janela da Automação abre já logada (sem tela de login)?
- `[x]` Módulos Fiscal, DP, Contábil dentro da Automação funcionam?
- `[x]` Outros setores da Central ainda funcionam?

---

## FASE 4 — Limpar a Central DMF
> **Tempo:** ~3h | **Risco:** Médio | **Só após CHECKPOINT 3 aprovado**

> ⚠️ **Esta fase remove código. Faça commit antes de começar.**

### 4.1 — Remover registro dos módulos de automação
- `[x]` Em `dmf_engine\main.py`, remover os imports de:
  - `FiscalModule`, `DPModule`, `ContabilModule`
- `[x]` Remover os `_registry.register(...)` correspondentes

### 4.2 — Remover métodos de automação da api.py
- `[x]` Removidos: `executar_ciclo`, `listar_excecoes`, `importar_excecoes`, `abrir_pasta_excecoes`
- `[x]` Removidos: wrappers deprecated (`executar_fiscal_individual`, `importar_planilha_carol`, `injetar_dp_master`, `processar_horas_contabeis`, `injetar_horas_contabeis_master`)
- `[x]` Removidos imports órfãos: `traceback`, `threading`, `monthrange`
- `[x]` Mantidos: métodos de plataforma + dashboard (lêem master.xlsm via engine/)

### 4.3 — Remover o guard 32-bit da Central
- `[x]` Guard removido de `dmf_engine\main.py`
- `[x]` Título da janela corrigido para "Central DMF"

### 4.4 — Remover arquivos de módulo movidos para services/
- `[x]` Removido `dmf_engine\modules\m_fiscal.py`
- `[x]` Removido `dmf_engine\modules\m_dp.py`
- `[x]` Removido `dmf_engine\modules\m_contabil.py`

### 4.5 — Testar Central DMF limpa
- `[x]` `py dmf_engine\main.py` (sem 32-bit — deve funcionar em 64-bit)
- `[x]` Sem erros de import no console?
- `[x]` Login e navegação funcionam?
- `[x]` Card "Automação de Horas" lança com SSO?

### 4.6 — Commit
- `[x]` `git add -A`
- `[x]` `git commit -m "feat: Central DMF desacoplada - automacao_horas isolada em services/"`

### CHECKPOINT 4 ✅
- `[x]` `run.bat` → Central DMF abre normalmente?
- `[x]` Todos os setores navegáveis?
- `[x]` Automação de Horas lança com SSO a partir de GESTÃO?
- `[x]` Automação standalone funciona? `py -3-32 services\automacao_horas\main.py`
- `[x]` Nenhum erro de import nos dois apps?

---

## FASE 5 — Finalizar scripts e merge
> **Tempo:** ~1h | **Risco:** Baixo | **Só após CHECKPOINT 4 aprovado**

### 5.1 — Atualizar `run.bat`
- `[ ]` Atualizar para rodar a Central DMF sem forçar 32-bit:
  ```bat
  @echo off
  cd /d %~dp0
  py dmf_engine\main.py
  if errorlevel 1 pause
  ```

### 5.2 — Criar `run_automacao_horas.bat` (acesso direto para debug)
- `[ ]` Criar arquivo:
  ```bat
  @echo off
  cd /d %~dp0
  py -3-32 services\automacao_horas\main.py
  if errorlevel 1 pause
  ```

### 5.3 — Atualizar `.gitignore`
- `[ ]` Adicionar:
  ```
  services/automacao_horas/config.json
  services/automacao_horas/__pycache__/
  ```

### 5.4 — Commit final e merge
- `[ ]` `git add -A`
- `[ ]` `git commit -m "chore: scripts finalizados, desacoplamento concluido"`
- `[ ]` `git checkout main`
- `[ ]` `git merge feat/desacoplamento`
- `[ ]` `git push origin main`

### CHECKPOINT FINAL
- `[ ]` `run.bat` → Central DMF abre (processo 64-bit)?
- `[ ]` GESTÃO → Automação de Horas lança (processo 32-bit, SSO)?
- `[ ]` `run_automacao_horas.bat` → Automação abre standalone?
- `[ ]` Buscador XML pode ser integrado agora sem restrição de arquitetura?

---

## Resumo

| Fase | Descrição | Tempo | Risco |
|---|---|---|---|
| 1 | Estrutura de pastas + cópias | 30 min | Zero |
| 2 | main.py standalone + SSO | 3h | Baixo |
| 3 | Launcher na Central + SSO | 2h | Baixo |
| 4 | Limpeza da Central DMF | 3h | Médio |
| 5 | Scripts + merge | 1h | Baixo |
| **Total** | | **~9-10h** | |
