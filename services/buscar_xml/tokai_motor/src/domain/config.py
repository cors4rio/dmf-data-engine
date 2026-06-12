from datetime import datetime
from dateutil.relativedelta import relativedelta

# Mapeamento do SharePoint para a Rede File System
CLIENT_MAPPING = {
    # 'NOME NO SHAREPOINT': 'NOME DA PASTA RAIZ NA REDE'
    'MISSKOH': '598-LAVDF COMERCIO FL 01',
    'RSBM': '568-RSBM_10645',
    'MISSKOH RIO MAR': '697-LAVDF COMERCIO FL 02',
    
    # Clientes onde o nome é idêntico ou contém apenas a sigla
    'FMM': '558-FMM_10642',
    'GAD': '560-GAD_COMERCIO 10649',
    'MAD': '559-MAD_10644',
    'EAC': '564-EAC_10636',
    'GFD': '575-GFD REST_10633',
    'RSC': '566-RSC_10641',
    'LSM': '553-LSM_10639',
    'LMS': '569-LMS RECIFE_10646',
    'LOTTI RIO MAR': '574-LOTTI RIO MAR',
    'ANND': '572-ANND_10659',
    'FMTB': '565-FMTB COMERCIO_10640',
    'LAVDF MTZ': '571-LAVDF MTZ',
    'LOTTI MATRIZ': '1644-LOTTI MATRIZ',
    'LOTTI FILIAL 01': '1645-LOTTI FILIAL 01',
    'RSTKI': '577-RSTKI_10648',
    
    # Consolidação de Duplicidades (SharePoint -> Z:)
    'LOTTI OSTERIA': '1644-LOTTI MATRIZ',   # pasta física: 1644-LOTTI MATRIZ
    'LOTTI CUCINA':  '1645-LOTTI FILIAL 01', # pasta física: 1645-LOTTI FILIAL 01
    'LAVDF': '571-LAVDF MTZ'
}

def get_target_month_sharepoint() -> str:
    """ Retorna o mês anterior formatado para busca no SharePoint (MM-YYYY) """
    last_month = datetime.now() - relativedelta(months=1)
    return last_month.strftime("%m-%Y")

def get_target_month_disk() -> str:
    """ Retorna o mês anterior formatado para criação de pastas no disco (MMAAAA) """
    last_month = datetime.now() - relativedelta(months=1)
    return last_month.strftime("%m%Y")
