# auto_tokai

RPA modular para coleta mensal automatizada de documentos fiscais (XML) a partir de repositório remoto em nuvem, com integração a API de e-mail para autenticação contínua e gerenciamento autônomo de sessão.

---

## Visao Geral

O sistema executa, sem intervencao humana, o ciclo completo de: autenticacao em repositorio protegido por MFA > navegacao deterministica por estrutura de pastas > download e verificacao de integridade de arquivos compactados > extracao robusta com suporte a multiplos formatos > organizacao dos documentos em estrutura de rede local definida por mapeamento de clientes.

A arquitetura prioriza resiliencia operacional: cada etapa possui mecanismos de retry, fallback e rastreamento de falhas individuais por entidade.

---

## Caracteristicas Tecnicas

### Autenticacao e Sessao

- Obtencao automatica de codigos OTP (8 digitos) diretamente via Gmail API (OAuth2), com filtro por timestamp para evitar reaproveitamento de codigos expirados.
- Persistencia de sessao via storage state do Playwright, reduzindo autenticacoes repetidas.
- Deteccao ativa de bloqueio MFA: ao identificar o desafio de verificacao, o sistema solicita o reenvio, aguarda o e-mail e preenche o campo automaticamente. Se o codigo nao for obtido em 2 minutos, a execucao e abortada com excecao explicita, evitando falhas em cascata nos clientes subsequentes.

### Navegacao

- Navegacao baseada em IDs de URL mapeados em arquivo JSON (`sharepoint_map_{ano}.json`), tornando o fluxo imune a alteracoes visuais na interface do repositorio.
- Deteccao de lista de arquivos por multiplos seletores CSS e fallback via traversal do DOM em JavaScript.
- Retries automaticos por operacao (configuravel via `MAX_RETRIES`).

### Download

- Download nativo via API do Playwright com fallback automatico para streaming via `requests`, reaproveitando os cookies da sessao ativa.
- Verificacao de existencia e tamanho do arquivo apos cada download antes de prosseguir para a extracao.

### Extracao de Arquivos (robust_extractor)

Modulo independente com as seguintes garantias:

| Camada | Comportamento |
| :--- | :--- |
| Validacao pre-extracao | Verificacao de integridade CRC (ZIP) e teste de arquivo (RAR/7z) sem extrair |
| Timeout dinamico | Calculado com base no tamanho real: `max(300s, min(3600s, tamanho_MB * 6s))` |
| Cascata de estrategias | 7-Zip > Python zipfile (por membro) > unrar > rarfile > patool |
| Monitor de progresso | Thread daemon que registra andamento a cada 30s durante subprocessos |
| Remocao segura | Arquivo compactado e removido SOMENTE apos verificacao de arquivos extraidos no destino |
| Relatorio de resultado | Retorna contagem de arquivos extraidos e XMLs encontrados |

### Mapeamento de Clientes (Sistema Dinamico)

A estrutura de clientes por regional e gerenciada via `config_clientes.json`, separando a configuracao da geracao do mapa operacional.

O script `scripts/generate_map.py` gera `sharepoint_map_{ano}.json` com todos os 12 meses do ano alvo, aplicando excecoes (overrides) definidas por mes:

```
config_clientes.json  ->  generate_map.py  ->  sharepoint_map_{ano}.json
```

Operacoes suportadas via overrides:
- Adicionar cliente a partir de um mes especifico
- Remover cliente em mes especifico (ex: empresa ausente em determinado periodo)
- Adicionar nova regional para um mes especifico

O sistema valida automaticamente se todos os clientes do mapa possuem mapeamento correspondente em `CLIENT_MAPPING` (domain/config.py) antes de finalizar a geracao.

### Scheduler (Daemon de Baixo Consumo)

- Executa verificacao diaria e dispara a rotina no dia e hora configurados.
- Consumo em standby: aproximadamente 37 MB de RAM, 0% de CPU.
- Ao ser reiniciado no dia de execucao, o job e disparado imediatamente como salvaguarda.

### Rastreamento de Erros

- Cada falha por entidade (cliente) e registrada com timestamp, tipo de erro, nome do arquivo e mensagem.
- Ao final da execucao, um relatorio consolidado e exibido no log e salvo em JSON no diretorio de destino.
- Tipos de erro rastreados: `NAVEGACAO_FALHOU`, `SEM_ARQUIVOS`, `DOWNLOAD_FALHOU`, `SAVE_FALHOU`, `EXTRACAO_FALHOU`, `ERRO_INESPERADO`.

### Logica de SKIP/Resume

Antes de processar cada entidade, o sistema verifica se a pasta de destino ja contem arquivos XML para o mes alvo. Se sim, a entidade e ignorada e marcada como concluida, permitindo retomada de execucoes interrumpidas sem reprocessamento.

---

## Stack Tecnologica

| Componente | Tecnologia |
| :--- | :--- |
| Linguagem | Python 3.10+ |
| Automacao de browser | Playwright (Chromium, modo headless configuravel) |
| Autenticacao de e-mail | Gmail API v1 via Google Cloud Console (OAuth2) |
| Extracao de arquivos | 7-Zip, Python zipfile, unrar, rarfile, patool |
| Agendamento | schedule |
| Logging | Loguru (rotacao por tamanho, retencao configuravel) |
| Containerizacao | Docker / Podman |
| Imagem base | `mcr.microsoft.com/playwright/python:v1.42.0-jammy` |

---

## Estrutura do Projeto

```
.
├── main.py                         # Ponto de entrada e agendador (daemon)
├── config_clientes.json            # Fonte da verdade: regionais e clientes
├── sharepoint_map_{ano}.json       # Mapa operacional gerado (12 meses)
├── scripts/
│   └── generate_map.py             # Gerador de mapa anual com suporte a overrides
├── src/
│   ├── application/
│   │   └── use_cases/
│   │       └── download_sharepoint_files.py  # Orquestrador principal
│   ├── domain/
│   │   └── config.py               # Mapeamento de entidades e funcoes de data
│   └── infrastructure/
│       ├── browser/
│       │   └── sharepoint_automation.py      # Automacao completa do repositorio
│       ├── email/
│       │   └── gmail_api_service.py          # Integracao Gmail API (link + OTP)
│       └── file_system/
│           └── robust_extractor.py           # Modulo de extracao resiliente
├── Dockerfile
├── docker-compose.yml
├── rebuild.ps1                     # Script de rebuild do container (Windows)
└── requirements.txt
```

---

## Instalacao e Configuracao

### Pre-requisitos

- Python 3.10+
- 7-Zip instalado e acessivel no PATH (ou nos caminhos padrao do Windows)
- Credenciais OAuth2 do Google Cloud Console (`credentials.json`) com escopo `gmail.readonly`

### Instalacao

```bash
pip install -r requirements.txt
playwright install chromium
```

### Variaveis de Ambiente

Crie um arquivo `.env` na raiz com as seguintes variaveis:

```env
# Conta de e-mail utilizada para autenticacao e captura de OTP
EMAIL_USER=conta@dominio.com

# URL base do repositorio remoto (obtida do e-mail de compartilhamento)
SHAREPOINT_BASE_URL=https://...

# Caminho de destino na rede local (drive mapeado)
NETWORK_DRIVE_Z=Z:\CAMINHO\DESTINO

# Etiqueta do Gmail que contem o e-mail com o link do repositorio
GMAIL_LABEL=NOME_DA_ETIQUETA

# Modo headless do browser (True para producao, False para debug visual)
HEADLESS_MODE=True

# Habilita capturas de tela por entidade (apenas para diagnostico)
DEBUG_SCREENSHOTS=False

# Caminho do storage state do Playwright
STORAGE_STATE_PATH=./playwright_storage.json
```

### Geracao do Mapa Anual

Antes da primeira execucao de um novo ano, gere o mapa operacional:

```bash
python scripts/generate_map.py --ano 2026
```

Para adicionar uma nova entidade, edite `config_clientes.json` e execute o script novamente.

---

## Execucao

### Direto (desenvolvimento/debug)

```bash
python main.py
```

### Via container

```bash
# Build e execucao (usando o script auxiliar no Windows)
.\rebuild.ps1

# Ou manualmente
docker-compose up --build -d
```

---

## Seguranca

Os seguintes arquivos sao excluidos do versionamento via `.gitignore`:

- `.env` — variaveis de ambiente e senhas
- `credentials.json` — chave OAuth2 do Google Cloud
- `token.json` — token de acesso OAuth2 persistido
- `storage_state.json` / `playwright_storage.json` — estado de sessao do browser
- `logs/` — arquivos de log locais
- `debug_*.png` / `debug_*.html` — artefatos de diagnostico

Os arquivos `config_clientes.json` e `sharepoint_map_{ano}.json` sao versionados, pois nao contem informacoes sensiveis.

---

## Agendamento

O daemon verifica diariamente o dia configurado (padrao: dia 05 de cada mes) e executa a rotina no horario definido (padrao: 08:00). Se reiniciado no dia de execucao, o job e disparado imediatamente.

Para alterar o dia ou horario, edite `main.py`:

```python
schedule.every().day.at("08:00").do(job)
# e a condicao: if hoje.day == 5:
```

---

## Manutencao Anual

1. Execute `python scripts/generate_map.py --ano {novo_ano}` para gerar o mapa do novo ano.
2. Verifique se o `CLIENT_MAPPING` em `src/domain/config.py` esta atualizado com eventuais novas entidades.
3. Se o token OAuth2 do Gmail expirar, delete `token.json` e execute `python main.py` localmente para reautenticar via browser.

---

**Status:** Producao / Autonomo
