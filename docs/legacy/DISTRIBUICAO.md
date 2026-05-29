# DMF Engine — Build e Distribuição

Guia operacional para quem mantém o sistema. Cobre como gerar nova versão, publicar na rede, atualizar as máquinas dos usuários e o roadmap de migração para um instalador profissional após o período de testes.

---

## 1. Visão geral do fluxo

```
[Sua máquina de dev]                [Rede / Servidor]                 [Máquina de cada usuário]
  build.bat            ─copy─►   \\servidor\dmf-engine\        ─click─►  %LOCALAPPDATA%\DMF Engine\
  (gera dist\)                     DMF Engine\                          DMF Engine.exe + atalho
                                   ├── DMF Engine.exe                   na Área de Trabalho
                                   ├── _internal\
                                   ├── config\nao_faz_setor\
                                   └── Instalar DMF Engine.bat
```

**Por que não rodar direto da rede:** latência (boot lento), SmartScreen/Defender bloqueia `.exe` em share, queda de rede crasha o app, conflito com OneDrive quando o `.exe` é atualizado em paralelo. Rodar local resolve tudo e o ciclo `instalar do .bat` é simples para usuário leigo.

---

## 2. Pré-requisitos da máquina de dev

| Item | Versão | Por quê |
|---|---|---|
| Python | **3.x 32-bit** (`py -3-32`) | Driver ODBC do Sybase é 32-bit. 64-bit dá erro `IM014`. |
| PyInstaller | qualquer recente | `py -3-32 -m pip install pyinstaller` |
| pythonnet | 3.1.0rc1+ | `py -3-32 -m pip install --pre pythonnet` (cp314 só tem em pré-release) |
| pywebview | qualquer recente | `py -3-32 -m pip install pywebview` |

Outras deps já estão no `requirements` informal do projeto (`openpyxl`, `pyodbc`, `pywebview`).

---

## 3. Como rebuildar

Na raiz do projeto:

```cmd
build.bat
```

O script faz, nesta ordem:

1. **Limpa** `build\` e `dist\` antigos.
2. **Empacota** com PyInstaller usando `dmf_engine.spec` (modo `onedir`, console oculto, ícone embarcado).
3. **Copia** os templates de exceção (`config\nao_faz_setor\*.txt`) para `dist\DMF Engine\config\nao_faz_setor\`.
4. **Copia** o `Instalar DMF Engine.bat` para dentro de `dist\DMF Engine\`.
5. **Remove** arquivos de estado de dev (`config.json`, `supervisores.json`, logs, `estado_compartilhado.json`) para nada vazar para a rede.

Resultado em `dist\DMF Engine\` — ~24 MB total, 4 itens:

```
DMF Engine.exe          (5.7 MB)
_internal\              (libs do Python)
config\nao_faz_setor\   (templates DP_NAO.txt, CONTABIL_NAO.txt, FISCAL_NAO.txt)
Instalar DMF Engine.bat (clicado pelo usuário)
```

Se algo falhar, o PyInstaller imprime o erro no console e o `pause` final segura a janela aberta.

---

## 4. Como publicar uma nova versão

1. Rode `build.bat` na sua máquina.
2. Teste o `.exe` gerado: clique duas vezes em `dist\DMF Engine\DMF Engine.exe`. Faça login, abra o dashboard, rode um módulo.
3. Copie a pasta `dist\DMF Engine\` **inteira** para a rede (`\\servidor\dmf-engine\DMF Engine\`), substituindo o conteúdo anterior.
4. Avise os usuários: *"Saiu versão nova. Cliquem duas vezes no `Instalar DMF Engine.bat` da rede."*

> **Importante:** nunca copie só o `.exe`. O `_internal\` também muda entre versões e dessincronizá-los gera erro de import na inicialização.

---

## 5. O que cada usuário faz (primeira vez e atualizações)

1. Abre a pasta da rede no Explorer.
2. Duplo clique em **Instalar DMF Engine.bat**.
3. O instalador:
   - Copia o app para `%LOCALAPPDATA%\DMF Engine\` (pasta do próprio usuário no PC).
   - Usa `robocopy /XO` — só sobrescreve arquivos mais antigos. **Preserva** `config.json`, `supervisores.json`, logs e estado local.
   - (Re)cria atalho **"DMF Engine"** na área de trabalho com `IconLocation` explícito (evita cache de ícone genérico do Windows).
   - Roda `ie4uinit -show` para forçar refresh do cache de ícones do Explorer.
   - Pergunta se quer abrir agora.

A partir daí, abrem pelo atalho. Não precisam mais navegar até a rede no dia a dia — só nas atualizações.

---

## 6. Arquivos importantes do build

| Arquivo | Função |
|---|---|
| `build.bat` | Script principal de build (raiz) |
| `dmf_engine.spec` | Spec do PyInstaller — `console=False`, `onedir`, ícone embarcado, hidden imports |
| `Instalar DMF Engine.bat` | Instalador que o usuário executa da rede |
| `dmf_engine/main.py` | Resolve `RESOURCES_DIR` via `sys._MEIPASS` em modo frozen |
| `dmf_engine/ui/logo.ico` | Ícone usado pelo `.exe`, pelo atalho e pela taskbar |
| `modulos/excecoes.py` | Resolve pasta de exceções dinamicamente (`_resolver_pasta`) |

Estado do usuário (não vai pra rede):

| Arquivo | O que é |
|---|---|
| `%LOCALAPPDATA%\DMF Engine\config.json` | Caminhos master/OneDrive, DSN, senha do banco |
| `%LOCALAPPDATA%\DMF Engine\supervisores.json` | 5 usuários + hash PBKDF2 das senhas + máquina autorizada |
| `%LOCALAPPDATA%\DMF Engine\dmf_engine.log` | Log geral |
| `%LOCALAPPDATA%\DMF Engine\dmf_engine_errors.log` | Só WARNING/ERROR/CRITICAL |

---

## 7. Diagnóstico rápido

| Sintoma | Causa provável | Solução |
|---|---|---|
| `IM014 [Microsoft][Driver Manager] data source name not found` | Python 64-bit tentando driver Sybase 32-bit | Sempre buildar com `py -3-32` |
| `404 NOT FOUND ... index.html` ao abrir o `.exe` | `BASE_DIR` apontando pro lugar errado em modo frozen | Já corrigido — `RESOURCES_DIR = sys._MEIPASS/dmf_engine` em [dmf_engine/main.py:26](dmf_engine/main.py#L26) |
| Atalho com ícone genérico do Python | Cache de ícone do Windows + `.lnk` antigo | Reinstalar (o `.bat` agora fixa `IconLocation` e chama `ie4uinit`) |
| `ModuleNotFoundError: clr` | Falta `pythonnet` | `py -3-32 -m pip install --pre pythonnet` |
| App não abre e nada acontece | Defender/SmartScreen | Botão direito no `.exe` → Propriedades → Desbloquear |

---

## 8. Roadmap pós-piloto (1 mês de uso real)

Após 1 mês com os 5 usuários reais (Carol, James, Nayane, Jailton, Adriele), avaliar a forma de distribuição. As duas opções no radar:

### Opção A — Inno Setup (instalador `.exe` único profissional)

- Empacota `dist\DMF Engine\` num único `Setup_DMF_Engine.exe`.
- Aparece em "Adicionar/Remover Programas" do Windows.
- Atalhos no Menu Iniciar + Área de Trabalho automáticos.
- Suporta uninstall limpo.
- Suporta versionamento (mostra "atualizando da v1.2 para v1.3").
- Permite assinar digitalmente para silenciar o SmartScreen.
- O usuário só baixa **um arquivo** e clica em "Next, Next, Finish".

Material já existente que cobre o miolo: `dmf_engine.spec`. O Inno Setup vira um wrapper externo, não substitui o PyInstaller.

### Opção B — Manter o `.bat` + automatizar mais

- Mais simples, sem nova dependência.
- Acrescentar verificação de versão dentro do `Instalar DMF Engine.bat` (lê um `VERSION` em `_internal\` e compara com o instalado).
- Notificar o usuário automaticamente quando subir versão nova na rede (popup ou link no dashboard).

### Decisão pendente

Vai depender do feedback do piloto: se os 5 usuários conseguirem rodar o `.bat` sem atrito, mantém B. Se houver fricção (gente que não acha o `.bat`, que não entende "instalar", etc.) ou se o sistema for ampliar para mais usuários, migra para A.

**Esta decisão está rastreada no [TASKBOARD.md](TASKBOARD.md), Epic "Pós-Piloto"**.
