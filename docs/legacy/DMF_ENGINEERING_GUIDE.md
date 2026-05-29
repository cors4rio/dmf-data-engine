# DMF Engine — Guia de Integração e Crescimento

> **Leia este documento antes de qualquer nova integração.**
> Ele define o que é o projeto, como ele cresce e como cada nova funcionalidade
> se conecta sem quebrar o que está em produção.

---

## O que é o DMF Engine

O DMF Engine é o **app interno do escritório** — um lugar único onde automações de
todos os setores rodam sob uma interface visual consistente. Fiscal, Contábil, DP e
qualquer setor futuro aparecem para o usuário na mesma janela, com o mesmo visual.

Por baixo, cada funcionalidade pode ser escrita em qualquer linguagem.
O que une tudo é uma arquitetura simples:

```
PyWebView (janela nativa Windows)
  └─ index.html  ←  HTML + CSS + JS  (o visual que o usuário vê)
        │
        ├─ pywebview.api.executar_modulo("fiscal", opcoes)
        │        └─ Python  →  Domínio ODBC, Excel, OneDrive
        │
        └─ fetch("http://localhost:8080/api/relatorio")
                 └─ qualquer serviço HTTP — Java, Go, Node, C#, Rust
```

O frontend HTML não sabe (e não precisa saber) o que roda no backend.
Para o usuário, é sempre a mesma janela DMF.

---

## Índice

1. [Decisão: mesmo repo ou projeto separado?](#1-decisão-mesmo-repo-ou-projeto-separado)
2. [Como não quebrar produção — estratégia de branches](#2-como-não-quebrar-produção--estratégia-de-branches)
3. [Árvore de decisão: qual padrão de integração usar?](#3-árvore-de-decisão-qual-padrão-de-integração-usar)
4. [Padrão A — Projeto Python externo](#4-padrão-a--projeto-python-externo)
5. [Padrão B — Binário compilado (Go, Java, Rust, C#)](#5-padrão-b--binário-compilado-go-java-rust-c)
6. [Padrão C — Serviço HTTP local (daemon em qualquer linguagem)](#6-padrão-c--serviço-http-local-daemon-em-qualquer-linguagem)
7. [Apps com UI própria — iframe ou janela separada](#7-apps-com-ui-própria--iframe-ou-janela-separada)
8. [Subindo serviços no boot do app](#8-subindo-serviços-no-boot-do-app)
9. [Flutter e outras stacks com janela própria](#9-flutter-e-outras-stacks-com-janela-própria)
10. [Padrões de qualidade obrigatórios](#10-padrões-de-qualidade-obrigatórios)
11. [Pipeline de desenvolvimento — do zero à produção](#11-pipeline-de-desenvolvimento--do-zero-à-produção)
12. [Mapa do projeto e decisões arquiteturais](#12-mapa-do-projeto-e-decisões-arquiteturais)

---

## 1. Decisão: mesmo repo ou projeto separado?

Antes de escrever uma linha de código, defina onde o novo projeto vai viver.

| Situação | Recomendação |
|---|---|
| Novo módulo dentro do DMF (horas, conferências, documentos) | **Mesmo repo** — branch `feat/nome` |
| App Python com lógica própria (como o buscador_xml) | Mesmo repo **ou** repo separado — adaptador via `sys.path` |
| Ferramenta compilada em Go / Java / Rust | **Repo separado** — integração via subprocess (Padrão B) |
| Serviço com ciclo de vida próprio (daemon, API REST) | **Repo separado** — integração via HTTP (Padrão C) |
| App com interface visual própria (Flask, Streamlit) | **Repo separado** — DMF sobe via subprocess no boot |
| Serviço usado por outras equipes além do DMF | **Sempre repo separado** — API REST independente |

**Regra de ouro:**
- Vai ser deployado junto com o DMF? → mesmo repo.
- Tem ciclo de vida independente (outra equipe cuida, versiona separado)? → repo separado.

---

## 2. Como não quebrar produção — estratégia de branches

Nunca desenvolva diretamente na `main`. A `main` é o que o usuário está usando agora.

```
main                ← produção estável
  └── feat/clientes      ← desenvolvimento do módulo clientes
  └── feat/documentos    ← outro módulo em paralelo, se necessário
```

**Regras durante o desenvolvimento:**

- Módulo novo cria **arquivos novos** — nunca edita `m_fiscal.py`, `m_dp.py` ou qualquer módulo existente
- Só encosta no `main.py` quando for conectar: uma linha `registry.register(MeuModulo(...))`
- `engine/` é somente leitura — se precisar de algo novo lá, abre branch específica só para isso
- Merge na `main` apenas após o smoke test completo (ver Seção 11, Passo 6)
- Usuários em produção continuam usando a `main` sem saber do que está sendo desenvolvido

---

## 3. Árvore de decisão: qual padrão de integração usar?

```
Tenho código novo para integrar. Qual padrão?

É Python puro (script, lib, projeto)?
  └─ Sim → Padrão A  (sys.path + adaptador BaseModule)

  └─ Não → Já tem servidor HTTP rodando?
              └─ Sim → Padrão C  (fetch() no JS ou requests no Python)

              └─ Não → É um executável (CLI, .exe, .jar, binário)?
                          └─ Sim → Padrão B  (subprocess + stdout JSON)

                          └─ Não → Empacotar como serviço HTTP primeiro → Padrão C
```

Os três padrões são mutuamente exclusivos. Escolha um e siga até o fim.

---

## 4. Padrão A — Projeto Python externo

**Quando usar:** código Python com arquitetura própria que não faz sentido reescrever.
O buscador_xml usa este padrão.

**Como funciona:**
1. O adaptador injeta o caminho do projeto externo no `sys.path`
2. Importa o serviço principal do projeto externo
3. Passa um callback `_ev` para o serviço — quando o serviço emite eventos internos, o callback os traduz para o EventBus do DMF
4. A UI não sabe que o código é externo — recebe os mesmos eventos de qualquer módulo interno

```python
# dmf_engine/modules/m_meu_projeto.py
import os, logging
from dmf_engine.modules.base import BaseModule, ModuleMeta

_EXT_PATH = r"C:\Projetos\meu_projeto"   # mover para config.json em produção
log = logging.getLogger("MeuProjeto")

class MeuProjetoModule(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="meu-projeto", nome="Meu Projeto",
            desc="Descrição curta do que faz.",
            setor="FISCAL",                # FISCAL | CONTABIL | DP | GESTAO
            icon="ti-file", color="#B06A00",
            papeis=["admin", "fiscal"],
        )

    def _get_service(self):
        import sys
        if _EXT_PATH not in sys.path:
            sys.path.insert(0, _EXT_PATH)
        try:
            from meu_projeto.service import MeuService
            def _ev(evento, dados):
                self._bus.emit(self.meta.id, evento, dados)
            return MeuService(base_dir=_EXT_PATH, callback=_ev)
        except ImportError as e:
            log.warning(f"[MEU-PROJETO] Não disponível: {e}")
            return None

    def execute(self, opcoes: dict) -> dict:
        s = self._get_service()
        if s is None:
            return {"ok": False, "erro": "Projeto não disponível neste ambiente."}
        try:
            return s.executar(opcoes)
        except Exception as e:
            log.error(f"[MEU-PROJETO] {e}")
            return {"ok": False, "erro": str(e)}
```

**Registrar em `main.py`** (uma linha):
```python
from dmf_engine.modules.m_meu_projeto import MeuProjetoModule
_registry.register(MeuProjetoModule(_bus, _config, _sessao_fn))
```

---

## 5. Padrão B — Binário compilado (Go, Java, Rust, C#)

**Quando usar:** ferramenta compilada que você quer chamar como processo e ler o resultado.

**Contrato obrigatório do binário** (qualquer linguagem deve seguir):
```
stdout linha 1: {"event": "progress", "pct": 10, "msg": "Iniciando..."}
stdout linha 2: {"event": "progress", "pct": 50, "msg": "Processando..."}
stdout linha 3: {"event": "progress", "pct": 100, "msg": "Concluído."}
exit code 0 = sucesso
exit code != 0 = erro
```

**Implementação em Go:**
```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
)

func emit(pct int, msg string) {
    b, _ := json.Marshal(map[string]interface{}{
        "event": "progress", "pct": pct, "msg": msg,
    })
    fmt.Println(string(b))
}

func main() {
    emit(10, "Iniciando...")
    // lógica aqui
    emit(100, "Concluído.")
    os.Exit(0)
}
```

**Adaptador Python:**
```python
# dmf_engine/modules/m_ferramenta_go.py
import subprocess, json, logging
from dmf_engine.modules.base import BaseModule, ModuleMeta

_BINARIO = r"C:\Projetos\ferramenta\ferramenta.exe"
log = logging.getLogger("FerramentaGo")

class FerramentaGoModule(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="ferramenta-go", nome="Ferramenta Go",
            desc="Processamento via binário Go.", setor="FISCAL",
            icon="ti-brand-golang", color="#B06A00",
            papeis=["admin", "fiscal"],
        )

    def execute(self, opcoes: dict) -> dict:
        self.progress(5, "Iniciando processo externo...")
        args = [_BINARIO, "--param", opcoes.get("valor", "")]
        try:
            proc = subprocess.Popen(args, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, text=True)
            for linha in proc.stdout:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    ev = json.loads(linha)
                    if ev.get("event") == "progress":
                        self.progress(ev.get("pct", 0), ev.get("msg", ""))
                except json.JSONDecodeError:
                    pass
            proc.wait()
            if proc.returncode != 0:
                stderr = proc.stderr.read()
                log.error(f"[FERRAMENTA-GO] Exit {proc.returncode}: {stderr}")
                return {"ok": False, "erro": f"Processo falhou (código {proc.returncode})"}
            return {"ok": True}
        except FileNotFoundError:
            return {"ok": False, "erro": f"Binário não encontrado: {_BINARIO}"}
        except Exception as e:
            log.error(f"[FERRAMENTA-GO] {e}")
            return {"ok": False, "erro": str(e)}
```

---

## 6. Padrão C — Serviço HTTP local (daemon em qualquer linguagem)

**Quando usar:** serviço que fica rodando em background com sua própria API.
Pode ser Java, Node, Python (Flask), Go com servidor HTTP, qualquer coisa.

O frontend JavaScript pode chamar **diretamente**, sem passar pelo Python:

```javascript
// index.html — chama API Java/Go/Node diretamente
async function executarRelatorio(params) {
    const r = await fetch("http://localhost:8080/api/relatorio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(params),
    });
    const data = await r.json();
    if (data.ok) mostrarResultado(data);
    else toast(data.erro, "error");
}
```

Ou via adaptador Python (quando o DMF precisa controlar o fluxo e emitir progress):

```python
# dmf_engine/modules/m_servico_local.py
import requests, logging
from dmf_engine.modules.base import BaseModule, ModuleMeta

_BASE_URL = "http://localhost:8080"
log = logging.getLogger("ServicoLocal")

class ServicoLocalModule(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="servico-local", nome="Serviço Local",
            desc="Integração com serviço HTTP.", setor="GESTAO",
            icon="ti-server-2", color="#2B65B5",
            papeis=["admin"],
        )

    def execute(self, opcoes: dict) -> dict:
        self.progress(10, "Chamando serviço...")
        try:
            r = requests.post(f"{_BASE_URL}/executar", json=opcoes, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.Timeout:
            return {"ok": False, "erro": "Serviço não respondeu em 30s."}
        except requests.ConnectionError:
            return {"ok": False, "erro": f"Serviço indisponível em {_BASE_URL}."}
        except Exception as e:
            log.error(f"[SERVICO-LOCAL] {e}")
            return {"ok": False, "erro": str(e)}
```

---

## 7. Apps com UI própria — iframe ou janela separada

Para apps que já têm interface visual (Flask + templates, Streamlit, outro app Python):

### Opção A — iframe dentro do DMF (experiência unificada)

O usuário vê o app externo dentro da janela DMF, sem perceber que são dois processos.

```html
<!-- index.html -->
<div class="app-container" id="app-container-meuapp" style="display:none">
    <iframe src="http://localhost:5000"
            style="width:100%;height:100%;border:none;border-radius:8px;"></iframe>
</div>
```

```python
# main.py — sobe o serviço antes de webview.start()
import subprocess, atexit
_flask = subprocess.Popen(
    ["python", r"C:\Projetos\meuapp\app.py"],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)
atexit.register(lambda: _flask.terminate())
```

**Use quando:** o app tem uma tela que faz sentido encaixar no visual do DMF.

### Opção B — janela separada (UX independente)

```python
# m_meuapp.py
def execute(self, opcoes: dict) -> dict:
    import subprocess
    subprocess.Popen(["python", r"C:\Projetos\meuapp\app.py"])
    return {"ok": True, "msg": "Aplicativo aberto em janela separada."}
```

**Use quando:** o app tem um fluxo próprio que não faz sentido dentro da janela DMF
(ex: fluxo guiado, wizard com muitas etapas, app de assinatura de documentos).

---

## 8. Subindo serviços no boot do app

Para daemons que precisam estar rodando antes de qualquer chamada do frontend:

```python
# dmf_engine/main.py — antes de webview.start()
import subprocess, atexit

_daemon = subprocess.Popen(
    [r"C:\Projetos\meu_servico\meu_servico.exe"],
    # alternativas:
    # ["java", "-jar", r"C:\Projetos\servico.jar"]
    # ["node", r"C:\Projetos\servico\index.js"]
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
atexit.register(lambda: _daemon.terminate())  # encerra junto com o DMF
```

O frontend chama `http://localhost:PORTA/api` normalmente.
Para o usuário, parece que é tudo parte do mesmo app.

**Atenção:** adicionar processos no boot aumenta o tempo de abertura do app.
Use apenas para serviços que precisam estar prontos antes do usuário interagir.

---

## 9. Flutter e outras stacks com janela própria

Flutter tem engine gráfica e janela nativa própria — não roda dentro do PyWebView.

| Opção | Como funciona | Quando usar |
|---|---|---|
| Flutter expõe API REST | DMF chama via Padrão C; resultados aparecem na UI HTML | Flutter processa, DMF exibe |
| Dois processos paralelos | DMF sobe o Flutter com `subprocess.Popen`; cada um tem sua janela | Flutter tem UX própria que vale manter |

Para automações internas, a **API REST é mais simples**: Flutter processa no background,
DMF exibe o resultado na interface unificada sem abrir outra janela.

O mesmo vale para apps React Native, WPF, WinForms ou qualquer outra coisa com
janela própria — a forma de integrar é sempre via HTTP.

---

## 10. Padrões de qualidade obrigatórios

Todo módulo — independente do padrão de integração — deve seguir:

### Contrato de retorno

```python
# Mínimo obrigatório
return {"ok": True}

# Em caso de erro (mensagem legível por não-técnicos)
return {"ok": False, "erro": "Arquivo master está aberto no Excel. Feche e tente novamente."}

# Com dados extras (opcionais, para o JS usar)
return {"ok": True, "total": 42, "competencia": "2026-04"}
```

Nunca deixar uma exceção não tratada chegar ao JS. Sempre capturar e retornar `ok: False`.

### Progress reporting

```python
def execute(self, opcoes: dict) -> dict:
    self.progress(0,  "Iniciando...")
    self.progress(15, "Verificando parâmetros...")
    self.progress(40, "Conectando ao Domínio...")
    # ... lógica pesada ...
    self.progress(80, "Gravando resultados...")
    self.progress(100, "Concluído.")
    return {"ok": True}
```

Emitir pelo menos 4 pontos intermediários. Uma barra estática por 30 segundos parece travada.

### Tratamento de exceção

```python
import traceback

def execute(self, opcoes: dict) -> dict:
    try:
        resultado = self._fazer_algo(opcoes)
        return {"ok": True, **resultado}
    except Exception as e:
        log.error(f"[NOME-MODULO] {traceback.format_exc()}")
        return {"ok": False, "erro": str(e)}
```

### Imports lazy

```python
# ERRADO — importado no boot do app, mesmo quando o módulo não é usado
import openpyxl
from engine.database import db

# CERTO — importado só quando o módulo executa
def execute(self, opcoes: dict) -> dict:
    import openpyxl
    from engine.database import db
    ...
```

### Lock antes de escrever na master

```python
from engine.lock_master import adquirir_lock, liberar_lock

def execute(self, opcoes: dict) -> dict:
    ok_lock, info = adquirir_lock(master_path, usuario, host, "Descrição")
    if not ok_lock:
        return {"ok": False, "tipo": "lock",
                "erro": f"Master em uso por {info.get('usuario', '?')}."}
    try:
        # escrever na master
        return {"ok": True}
    finally:
        liberar_lock(master_path, usuario, host)  # sempre no finally
```

---

## 11. Pipeline de desenvolvimento — do zero à produção

### Passo 1 — Spec (antes de escrever código)

Criar arquivo em `Specs_Definitivos/` com:
- Query SQL (se houver Domínio ODBC)
- Regra de negócio: entrada → processamento → saída esperada
- Campos do objeto `opcoes` e do retorno

### Passo 2 — Lógica de negócio em `modulos/`

```python
# modulos/estagiarios.py — sem UI, sem threading, sem dmf_engine
def calcular_horas(planilha_path: str, inicio: str, fim: str) -> dict:
    """Retorna {"ok": bool, "total": int, "por_estagiario": dict}"""
    ...
```

Testar isoladamente com `python modulos/estagiarios.py` antes de integrar.

### Passo 3 — Adaptador `dmf_engine/modules/m_{nome}.py`

Usar o Padrão A, B ou C conforme a Seção 3. Herdar `BaseModule`, preencher `ModuleMeta`, implementar `execute()`.

### Passo 4 — Registrar em `dmf_engine/main.py`

```python
from dmf_engine.modules.m_estagiarios import EstagiariosModule
_registry.register(EstagiariosModule(_bus, _config, _sessao_fn))
```

### Passo 5 — UI em `index.html`

1. Adicionar container `<div class="app-container" id="app-container-estagiarios" style="display:none">`
2. Criar função `bootAppEstagiarios()` com `registerModuleHandlers`
3. Adicionar `document.getElementById('app-container-estagiarios').style.display = 'none'` em `pfVoltarParaModulos()`

### Passo 6 — Smoke test

```bash
py -3-32 dmf_engine/main.py
```

- [ ] App abre sem erros
- [ ] Login funciona
- [ ] Módulo aparece no catálogo no setor correto
- [ ] Apenas usuários com papel correto veem o card
- [ ] Botão executa e eventos `progress` → `done` chegam via `window.__onEvent`
- [ ] `← Módulos` volta sem erros

### Passo 7 — Build e teste do `.exe`

```bash
build.bat
```

Testar o `.exe` em `dist/dmf_engine/dmf_engine.exe` como usuário leigo
(sem Python no PATH, sem o repositório aberto).

### Passo 8 — Deploy

Copiar `dist/dmf_engine/` para a pasta de rede. Usuários rodam `Instalar DMF Engine.bat`.

### Checklist antes de ir à produção

```
Código:
  [ ] Imports lazy dentro de execute()
  [ ] try/except cobrindo todo execute() com log.error + traceback
  [ ] self.progress() em pelo menos 4 pontos
  [ ] adquirir_lock() + liberar_lock() no finally se escrever na master
  [ ] Retorno {"ok": bool} em todos os caminhos de código

UI:
  [ ] Prefix de IDs único (ex: est-) em todos os elementos HTML
  [ ] registerModuleHandlers chamado no boot do módulo
  [ ] pfVoltarParaModulos() esconde o container corretamente
  [ ] Barra de progresso aparece ao executar e some ao concluir

Qualidade:
  [ ] Nenhum path de máquina específico em código (mover para config.json)
  [ ] Mensagens de erro legíveis por não-técnicos
  [ ] Módulo invisível para papéis sem permissão
```

---

## 12. Mapa do projeto e decisões arquiteturais

### Estrutura de diretórios

```
N8N automacao/
│
├── dmf_engine/                    ← app desktop (PyWebView)
│   ├── main.py                    ← bootstrap: ~140 linhas, registra módulos e abre janela
│   ├── api.py                     ← bridge Python↔JS: dispatcher genérico
│   ├── auth.py                    ← autenticação: PBKDF2, machine binding, sessão
│   ├── core/
│   │   ├── event_bus.py           ← canal único Python→JS (window.__onEvent)
│   │   ├── thread_runner.py       ← execução assíncrona em daemon threads
│   │   └── config.py              ← leitura/escrita de config.json com defaults
│   ├── modules/
│   │   ├── base.py                ← BaseModule (ABC) + ModuleMeta (dataclass)
│   │   ├── registry.py            ← registro, dispatch e catálogo de módulos
│   │   ├── m_fiscal.py            ← horas fiscais via Domínio ODBC
│   │   ├── m_dp.py                ← folha Carol (DP)
│   │   ├── m_contabil.py          ← horas contábeis (2 fases)
│   │   └── m_buscador_xml.py      ← projeto externo buscador_xml (Padrão A)
│   └── ui/
│       ├── index.html             ← SPA completa: todo o frontend
│       └── logo.ico
│
├── modulos/                       ← regras de negócio PURAS (sem UI, sem threading)
│   ├── fiscal.py
│   ├── dp.py
│   ├── contabil_preenchedor.py
│   ├── contabil_integrador.py
│   └── excecoes.py
│
├── engine/                        ← infraestrutura compartilhada
│   ├── database.py                ← ODBC Sybase (32-bit obrigatório)
│   ├── master_writer.py           ← leitura/escrita do .xlsm sem quebrar fórmulas
│   ├── lock_master.py             ← lock cooperativo via .dmflock
│   ├── estado_compartilhado.py    ← JSON multi-usuário (supervisores.json)
│   ├── excel_parser.py
│   └── onedrive_helper.py
│
├── Specs_Definitivos/             ← fonte de verdade: queries SQL e regras de negócio
├── build.bat                      ← pipeline de build
├── run.bat                        ← executa com Python 32-bit
└── Instalar DMF Engine.bat        ← instalador para o usuário final
```

### Separação de responsabilidades

| Camada | Diretório | O que faz | Pode importar de |
|---|---|---|---|
| App / Bridge | `dmf_engine/` | UI, eventos, auth, dispatch | Todas as camadas |
| Adaptadores | `dmf_engine/modules/` | Conecta regras ao EventBus | `modulos/`, `engine/`, `core/` |
| Regras | `modulos/` | Lógica de negócio pura, sem UI | `engine/` apenas |
| Infraestrutura | `engine/` | Banco, arquivo, lock, estado | Ninguém — é a base |
| Plataforma | `dmf_engine/core/` | EventBus, threads, config | Sem lógica de negócio |

**Regra crítica:** `modulos/` nunca importa de `dmf_engine/`. As regras de negócio
devem funcionar sem subir a janela PyWebView.

### Decisões arquiteturais (por que é assim)

| Decisão | Por quê |
|---|---|
| **PyWebView** (não Electron, não Flet) | Flet travava com PyInstaller + Domínio; Electron = 150MB de overhead para app local sem internet |
| **Vanilla JS** (sem React/Vue) | PyInstaller empacota `index.html` estático; frameworks exigiriam `npm build` e `node_modules` a cada deploy |
| **Python 32-bit obrigatório** | Driver ODBC do SQL Anywhere (Domínio) não tem versão 64-bit. Python 64-bit lança `IM014` |
| **Plugin Module System** | `main.py` tinha 1771 linhas. Novo módulo = 1 arquivo + 1 linha de registro. `main.py` nunca mais é editado para adicionar funcionalidade |
| **Lock via `.dmflock`** | OneDrive sincroniza arquivos; SQLite seria mais um arquivo para conflito. `open(path, 'x')` é atômico no Windows |
| **config.json** (não banco) | Fácil de inspecionar, fácil de backup manual, sem dependência extra, volume pequeno de dados |

---

*Atualizar este documento sempre que um novo padrão de integração for estabelecido
ou uma decisão arquitetural relevante for tomada.*
