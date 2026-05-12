# DMF Automação — Controle de Horas

Projeto modular para preenchimento automático das planilhas de controle de horas da DMF Contabilidade.

## Estrutura

```
ESTRUTURA/
├── _ENGINE/             # Núcleo compartilhado
│   ├── config.py        # Configurações globais, caminhos, argparse
│   ├── database.py      # Conexão ODBC e execução SQL (Sybase/Domínio)
│   └── excel_utils.py   # Manipulação segura de planilhas (openpyxl)
├── 01_FISCAL/           # Produtividade Fiscal
│   ├── processar.py     # Extrai GELOGUSER sist_log=5 → col O Master
│   └── relatorios/
├── 02_CONTABIL/         # Módulo Contábil
│   ├── processar.py     # Extrai lançamentos + faturamento → cols F, O, I
│   └── relatorios/
├── 03_DP/               # Departamento Pessoal
│   ├── processar.py     # Extrai foempregados → col Q Master
│   └── relatorios/
├── 04_MASTER/           # Consolidação
│   ├── integrar.py      # Contábil → Master col P (Double Match)
│   ├── reparar.py       # Recalcula totais, subtotais, sanitiza ghosts
│   └── relatorios/
├── automacao.py         # Orquestrador (executa tudo ou módulo individual)
├── check_setup.py       # Verificação de ambiente antes de executar
├── requirements.txt
└── .env.example         # Copiar para .env e preencher senha
```

## Setup Inicial

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Criar arquivo de senhas
cp .env.example .env
# Editar .env e preencher ODBC_PASS

# 3. Verificar ambiente
python check_setup.py --mes 03 --ano 2026
```

## Uso

### Executar tudo (pipeline completo)
```bash
python automacao.py --mes 03 --ano 2026
```

### Módulo individual
```bash
python automacao.py --mes 03 --ano 2026 --setor fiscal
python automacao.py --mes 03 --ano 2026 --setor contabil
python automacao.py --mes 03 --ano 2026 --setor dp
python automacao.py --mes 03 --ano 2026 --setor integrar
python automacao.py --mes 03 --ano 2026 --setor reparar
```

### Dry Run (sem gravar, apenas log)
```bash
python automacao.py --mes 03 --ano 2026 --dry-run
```

### Com log detalhado
```bash
python automacao.py --mes 03 --ano 2026 --verbose
```

## Pipeline de Execução

| Ordem | Módulo | Script | Coluna preenchida |
|---|---|---|---|
| 1 | Fiscal | `01_FISCAL/processar.py` | Master col **O** |
| 2 | Contábil | `02_CONTABIL/processar.py` | HORAS CONTABEIS cols **F, O, I** |
| 3 | DP | `03_DP/processar.py` | Master col **Q** |
| 4 | Integrar | `04_MASTER/integrar.py` | Master col **P** |
| 5 | Reparar | `04_MASTER/reparar.py` | Master cols **R** + subtotais |

## Regras de Ouro (Implementadas)

- `keep_vba=True` somente para `.xlsm` (nunca para `.xlsx`)
- `data_only=True` para ler valores calculados (não fórmulas)
- Formato `[h]:mm:ss` em todas as células de tempo
- `timedelta` convertido para `float` (fração de dia) antes de gravar
- Código normalizado com `int(float(str(x)))` para tratar `1152.0`
- Zeros explícitos para eliminar "ghosts" de meses anteriores
- SUBTOTAL dinâmico usando `ws.max_row` (nunca range fixo)
- Lookup duplo: Código Domínio → CNPJ
- Dicionários com `list` de linhas (nunca sobrescrever duplicados)
- Senhas **nunca** no código — sempre via `.env`

## Relatórios

Cada execução gera um `.md` em `XX_SETOR/relatorios/` com:
- Resumo da execução (totais, aprovados, rejeitados)
- Anomalias detalhadas para revisão manual
- Timestamp da execução
