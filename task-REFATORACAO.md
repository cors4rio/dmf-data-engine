# Taskboard — Desacoplamento Central DMF x Automação de Horas

> **Regra de ouro:** o `run.bat` atual deve funcionar a cada ponto de verificação.
> Só avance para a próxima fase após marcar todos os checkpoints. ✅

---

## FASE 1 — Preparar a estrutura (sem alterar código)
> **Tempo:** ~30 min | **Risco:** Zero | **Branch:** `feat/desacoplamento`

### 1.1 — Git
- `[ ]` Confirmar stage limpo: `git status`
- `[ ]` Criar branch: `git checkout -b feat/desacoplamento`

### 1.2 — Criar estrutura de pastas
- `[ ]` Criar `services\`
- `[ ]` Criar `services\automacao_horas\`
- `[ ]` Criar `services\automacao_horas\engine\`
- `[ ]` Criar `services\automacao_horas\modulos\`
- `[ ]` Criar `services\automacao_horas\modules\`
- `[ ]` Criar `services\automacao_horas\core\`
- `[ ]` Criar `services\automacao_horas\ui\`

### 1.3 — Copiar arquivos da Automação (cópia — original intocado)
- `[ ]` Copiar `engine\*.py` → `services\automacao_horas\engine\`
- `[ ]` Copiar `modulos\*.py` → `services\automacao_horas\modulos\`
- `[ ]` Copiar `dmf_engine\modules\m_fiscal.py` → `services\automacao_horas\modules\`
- `[ ]` Copiar `dmf_engine\modules\m_dp.py` → `services\automacao_horas\modules\`
- `[ ]` Copiar `dmf_engine\modules\m_contabil.py` → `services\automacao_horas\modules\`
- `[ ]` Copiar `dmf_engine\modules\base.py` → `services\automacao_horas\modules\`
- `[ ]` Copiar `dmf_engine\modules\registry.py` → `services\automacao_horas\modules\`
- `[ ]` Copiar `dmf_engine\core\event_bus.py` → `services\automacao_horas\core\`
- `[ ]` Copiar `dmf_engine\core\thread_runner.py` → `services\automacao_horas\core\`
- `[ ]` Copiar `dmf_engine\core\config.py` → `services\automacao_horas\core\`
- `[ ]` Copiar `dmf_engine\auth.py` → `services\automacao_horas\`
- `[ ]` Copiar `dmf_engine\config.json` → `services\automacao_horas\config_template.json`
- `[ ]` Copiar `dmf_engine\supervisores.json` → `services\automacao_horas\`
- `[ ]` Copiar `dmf_engine\ui\index.html` → `services\automacao_horas\ui\`
- `[ ]` Copiar logos/imagens da `dmf_engine\ui\` → `services\automacao_horas\ui\`

### 1.4 — Criar `__init__.py` nas pastas necessárias
- `[ ]` `services\__init__.py` (vazio)
- `[ ]` `services\automacao_horas\__init__.py` (vazio)
- `[ ]` `services\automacao_horas\engine\__init__.py` (vazio)
- `[ ]` `services\automacao_horas\modulos\__init__.py` (vazio)
- `[ ]` `services\automacao_horas\modules\__init__.py` (vazio)
- `[ ]` `services\automacao_horas\core\__init__.py` (vazio)

### 1.5 — Commit
- `[ ]` `git add services\`
- `[ ]` `git commit -m "feat: estrutura services/automacao_horas criada (copias sem alterar original)"`

### CHECKPOINT 1
- `[ ]` `run.bat` → app abre normalmente?
- `[ ]` Login funciona?
- `[ ]` Módulo Fiscal executa?
- `[ ]` **Se falhou:** `git stash` e investigar antes de continuar

---

## FASE 2 — Criar o main.py standalone da Automação
> **Tempo:** ~3h | **Risco:** Baixo | **Original continua intocado**

### 2.1 — Criar `services\automacao_horas\main.py`
- `[ ]` Copiar `dmf_engine\main.py` → `services\automacao_horas\main.py`
- `[ ]` Adicionar no início do arquivo o ajuste de `sys.path`:
  ```python
  import sys, os
  _ROOT = os.path.dirname(os.path.abspath(__file__))
  sys.path.insert(0, _ROOT)
  sys.path.insert(0, os.path.dirname(_ROOT))
  sys.path.insert(0, os.path.dirname(os.path.dirname(_ROOT)))
  ```
- `[ ]` Atualizar imports para usar módulos locais (`from modules.registry import ModuleRegistry`)
- `[ ]` Adicionar função `_recuperar_sessao_via_token()` após os imports:
  ```python
  def _recuperar_sessao_via_token():
      token = None
      for i, arg in enumerate(sys.argv):
          if arg == "--session-token" and i + 1 < len(sys.argv):
              token = sys.argv[i + 1]
              break
      if not token:
          return None
      import json, tempfile
      from datetime import datetime
      caminho = os.path.join(tempfile.gettempdir(), f"dmf_session_{token}.json")
      if not os.path.exists(caminho):
          return None
      try:
          with open(caminho, encoding="utf-8") as f:
              dados = json.load(f)
          os.remove(caminho)
          if datetime.now() > datetime.fromisoformat(dados["expira_em"]):
              return None
          return {"nome": dados["usuario"], "label": dados.get("label", ""), "papel": dados["papel"]}
      except Exception:
          return None
  ```
- `[ ]` Capturar sessão SSO antes de criar a janela: `_sessao_sso = _recuperar_sessao_via_token()`
- `[ ]` Passar `_sessao_sso` para a `Api` no construtor
- `[ ]` Alterar título da janela para `"DMF — Automação de Horas"`
- `[ ]` Manter o guard 32-bit — ele pertence aqui

### 2.2 — Adaptar a Api da Automação para SSO
- `[ ]` Copiar `dmf_engine\api.py` → `services\automacao_horas\api.py`
- `[ ]` No `__init__` da Api, aceitar `sessao_inicial=None`
- `[ ]` Se `sessao_inicial` não for None, popular `self._sessao` direto (pula login)
- `[ ]` Verificar se `get_sessao()` existe na Api — se não, criar:
  ```python
  def get_sessao(self):
      return self._sessao
  ```

### 2.3 — Adaptar a UI para pular login quando SSO está ativo
- `[ ]` Em `services\automacao_horas\ui\index.html`, no `DOMContentLoaded`, adicionar verificação:
  ```javascript
  async function _verificarSessaoSSO() {
      try {
          const s = await window.pywebview.api.get_sessao();
          if (s && s.nome) {
              pfEntrarNoApp(s);  // pula setor e login, vai direto para módulos
              return true;
          }
      } catch(e) {}
      return false;
  }
  // Chamar no início: await _verificarSessaoSSO();
  ```

### 2.4 — Testar Automação standalone (sem SSO)
- `[ ]` `py -3-32 services\automacao_horas\main.py`
  → Deve abrir com tela de login
- `[ ]` Login manual funciona?
- `[ ]` Módulos Fiscal, DP, Contábil executam?
- `[ ]` `run.bat` ainda funciona? (original intocado)

### 2.5 — Testar SSO manualmente
- `[ ]` Criar `scratch_test_token.py` na raiz:
  ```python
  import json, os, tempfile, secrets
  from datetime import datetime, timedelta
  token = secrets.token_hex(16)
  dados = {
      "usuario": "***", "label": "***", "papel": "admin",
      "expira_em": (datetime.now() + timedelta(seconds=30)).isoformat()
  }
  caminho = os.path.join(tempfile.gettempdir(), f"dmf_session_{token}.json")
  with open(caminho, "w") as f:
      json.dump(dados, f)
  print(f"py -3-32 services\\automacao_horas\\main.py --session-token {token}")
  ```
- `[ ]` Rodar o script e executar o comando impresso
  → Deve abrir **já logado como Carol** sem tela de login
- `[ ]` Apagar `scratch_test_token.py`

### 2.6 — Commit
- `[ ]` `git add services\automacao_horas\`
- `[ ]` `git commit -m "feat: automacao_horas/main.py standalone com SSO por token"`

### CHECKPOINT 2
- `[ ]` `run.bat` → app original abre normalmente?
- `[ ]` `py -3-32 services\automacao_horas\main.py` → abre standalone com tela de login?
- `[ ]` SSO com token válido → abre já autenticado?
- `[ ]` Token inválido/ausente → tela de login aparece normalmente?

---

## FASE 3 — Adicionar o Launcher na Central DMF
> **Tempo:** ~2h | **Risco:** Baixo | **Original ainda funciona em paralelo**

### 3.1 — Identificar o Python 32-bit
- `[ ]` Rodar: `py -3-32 -c "import sys; print(sys.executable)"`
- `[ ]` Anotar o caminho completo (ex: `C:\Python312-32\python.exe`)
- `[ ]` Adicionar ao `dmf_engine\config.json`:
  ```json
  "automacao_horas_python": "C:\\caminho\\completo\\python.exe"
  ```

### 3.2 — Criar `dmf_engine\modules\m_automacao_horas.py`
- `[ ]` Criar o arquivo com o código do launcher SSO:
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
- `[ ]` Em `dmf_engine\main.py`, adicionar no bloco de imports de módulos:
  ```python
  from dmf_engine.modules.m_automacao_horas import AutomacaoHorasLauncher
  ```
- `[ ]` Na seção de registro, adicionar:
  ```python
  _registry.register(AutomacaoHorasLauncher(_bus, _config, _sessao_fn))
  ```

### 3.4 — Verificar o setor GESTÃO na UI da Central
- `[ ]` Confirmar que `index.html` tem `sector-block gestao` definido
- `[ ]` Confirmar que o catálogo (`get_catalog()`) filtra por setor corretamente
- `[ ]` O card "Automação de Horas" deve aparecer quando o usuário acessar GESTÃO

### 3.5 — Commit
- `[ ]` `git add dmf_engine\modules\m_automacao_horas.py dmf_engine\main.py dmf_engine\config.json`
- `[ ]` `git commit -m "feat: launcher AutomacaoHoras com SSO adicionado na Central DMF"`

### CHECKPOINT 3
- `[ ]` `run.bat` → Central DMF abre normalmente?
- `[ ]` Login como `carol/admin` funciona?
- `[ ]` Card "Automação de Horas" aparece no painel GESTÃO?
- `[ ]` Clicar no card → janela da Automação abre?
- `[ ]` Janela da Automação abre já logada (sem tela de login)?
- `[ ]` Módulos Fiscal, DP, Contábil dentro da Automação funcionam?
- `[ ]` Outros setores da Central ainda funcionam?

---

## FASE 4 — Limpar a Central DMF
> **Tempo:** ~3h | **Risco:** Médio | **Só após CHECKPOINT 3 aprovado**

> ⚠️ **Esta fase remove código. Faça commit antes de começar.**

### 4.1 — Remover registro dos módulos de automação
- `[ ]` Em `dmf_engine\main.py`, remover os imports de:
  - `FiscalModule`, `DPModule`, `ContabilModule`
- `[ ]` Remover os `_registry.register(...)` correspondentes

### 4.2 — Remover métodos de automação da api.py
- `[ ]` Buscar métodos que importam de `engine/` ou `modulos/`:
  `grep -n "from engine\|from modulos" dmf_engine\api.py`
- `[ ]` Remover esses métodos e seus imports do topo
- `[ ]` Manter apenas métodos de plataforma: login, logout, sessão, catálogo, perfil, configurações

### 4.3 — Remover o guard 32-bit da Central
- `[ ]` Em `dmf_engine\main.py`, localizar e remover:
  ```python
  PYTHON_BITS = platform.architecture()[0]
  if PYTHON_BITS != "32bit":
      logging.warning(...)
  ```

### 4.4 — Remover arquivos de módulo movidos para services/
- `[ ]` Remover `dmf_engine\modules\m_fiscal.py`
- `[ ]` Remover `dmf_engine\modules\m_dp.py`
- `[ ]` Remover `dmf_engine\modules\m_contabil.py`

### 4.5 — Testar Central DMF limpa
- `[ ]` `py dmf_engine\main.py` (sem 32-bit — deve funcionar em 64-bit)
- `[ ]` Sem erros de import no console?
- `[ ]` Login e navegação funcionam?
- `[ ]` Card "Automação de Horas" lança com SSO?

### 4.6 — Commit
- `[ ]` `git add -A`
- `[ ]` `git commit -m "feat: Central DMF desacoplada - automacao_horas isolada em services/"`

### CHECKPOINT 4
- `[ ]` `run.bat` → Central DMF abre normalmente?
- `[ ]` Todos os setores navegáveis?
- `[ ]` Automação de Horas lança com SSO a partir de GESTÃO?
- `[ ]` Automação standalone funciona? `py -3-32 services\automacao_horas\main.py`
- `[ ]` Nenhum erro de import nos dois apps?

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
