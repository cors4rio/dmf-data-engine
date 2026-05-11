import os

# Diretório Base do Projeto
BASE_DIR = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA"

# --- CAMINHOS DE ARQUIVOS ---

# Planilhas
SOURCE_CONTABIL = os.path.join(BASE_DIR, "HORAS CONTABEIS_V3_AeqwQXgR.xlsx")
TARGET_MASTER = os.path.join(BASE_DIR, "CONTROLE_DE_HORAS_DMF.xlsm")

# Filtros de Exceção
FILTER_DP_NAO = os.path.join(BASE_DIR, "nao_faz_setor", "DP NAO.txt")
FILTER_NAO_CONTABIL = os.path.join(BASE_DIR, "nao_faz_setor", "NAO FAZ CONTABIL.txt")

# Saídas Temporárias (para auditoria)
TEMP_OUTPUT = os.path.join(BASE_DIR, "CONTROLE_DE_HORAS_DMF_ATUALIZADO.xlsm")

# --- BANCO DE DADOS ---
DB_CONN_STR = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'

# --- MAPEAMENTO DA PLANILHA MASTER (Base 1-indexed) ---
COL_EXCECAO = 4    # D: Flag de exceção
COL_CODI_EMP = 8   # H: Código Domínio
COL_NOME_FANT = 9  # I: Nome Fantasia
COL_CNPJ = 10      # J: CNPJ
COL_RAZAO = 11     # K: Razão Social
COL_MES_ANT = 14   # N: Mês Anterior Fiscal
COL_FISCAL = 15    # O: Horário Fiscal
COL_CONTABIL = 16  # P: Horário Contábil
COL_DP = 17       # Q: Horário Pessoal (DP)
COL_TOTAL = 18     # R: Total (=O+P+Q)

# --- CONFIGURAÇÕES DO PROCESSO ---
START_ROW = 10              # Linha inicial dos dados
CURRENT_SHEET = "02.2026"   # Aba de trabalho do mês
ADICIONAL_FISCAL = 1.70     # Adicional de 70% no setor fiscal
