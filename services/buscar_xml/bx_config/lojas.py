"""
config/lojas.py
---------------
Fonte unica de verdade para mapeamento de lojas.

IMPORTANTE: NFCe usa sistema separado com IDs e ordem diferentes.
            NF-e Saida, SPED e NFe Entrada usam o mesmo sistema Bluesoft
            — logo os IDs e a ordem das lojas SAO OS MESMOS entre esses tres modulos.

Estrutura de cada loja:
    "codigo":   Codigo interno Agromix (chave do dicionario LOJAS_CADASTRO)
    "apelido":  Nome curto da loja
    "nome":     Razao social completa
    "cnpj":     CNPJ sem pontuacao (14 digitos) — usado pelo arquivos.py para roteamento de ZIPs
    "id_nfce":  ID da loja no sistema NFCe (None = loja nao existe no NFCe)
    "id_bluesoft": ID da loja no Bluesoft (None = loja nao existe no Bluesoft)
    
Derivados automaticos (gerados por get_pasta_loja):
    Pasta NFCe     = "<id_nfce>-<apelido>"     (ex: "7-AGROMIX FL 0006-24")
    Pasta Bluesoft = "<codigo>-<apelido>"       (ex: "833-AGROMIX FL 0006-24")
"""

# =============================================================================
# CADASTRO MESTRE DE LOJAS
# =============================================================================
# Chave = Codigo interno Agromix (str para consistencia)

LOJAS_CADASTRO = {
    "833": {
        "apelido":      "AGROMIX  FL 0006-24",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990000624",
        "id_nfce":      "7",
        "id_bluesoft":  "7",
    },
    "834": {
        "apelido":      "ATACADAO - MATRIZ",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000159",
        "id_nfce":      "4",
        "id_bluesoft":  "4",
    },
    "835": {
        "apelido":      "AGROMIX  FL 0001-10",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990000110",
        "id_nfce":      "2",
        "id_bluesoft":  "2",
    },
    "836": {
        "apelido":      "AGROMIX  FL 0004-62",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990000462",
        "id_nfce":      "3",
        "id_bluesoft":  "3",
    },
    "837": {
        "apelido":      "AGROMIX FL 0005-43",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990000543",
        "id_nfce":      None,       # NAO EXISTE no NFCe
        "id_bluesoft":  "1",
    },
    "838": {
        "apelido":      "VILLAS PET 0003-77",
        "nome":         "VILLAS PET LTDA",
        "cnpj":         "07345645000377",
        "id_nfce":      "6",
        "id_bluesoft":  "6",
    },
    "839": {
        "apelido":      "VILLAS PET 0001-05 M",
        "nome":         "VILLAS PET LTDA - EPP",
        "cnpj":         "07345645000105",
        "id_nfce":      None,       # NAO EXISTE no NFCe
        "id_bluesoft":  None,       # NAO EXISTE no Bluesoft
    },
    "840": {
        "apelido":      "AGROMIX  FL 0009-77",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990000977",
        "id_nfce":      "17",
        "id_bluesoft":  "17",
    },
    "841": {
        "apelido":      "ATACADAO FL 0002-30",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000230",
        "id_nfce":      "8",
        "id_bluesoft":  "8",
    },
    "842": {
        "apelido":      "ATACADAO FL 0003-10",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000310",
        "id_nfce":      "9",
        "id_bluesoft":  "9",
    },
    "843": {
        "apelido":      "AGROMIX  FL 0007-05",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990000705",
        "id_nfce":      "10",
        "id_bluesoft":  "10",
    },
    "844": {
        "apelido":      "ATACADAO FL 0004-00",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000400",
        "id_nfce":      None,       # NAO EXISTE no NFCe
        "id_bluesoft":  "12",
    },
    "845": {
        "apelido":      "ATACADAO FL 0005-82",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000582",
        "id_nfce":      "11",
        "id_bluesoft":  "11",
    },
    "846": {
        "apelido":      "ATACADAO FL 0006-63",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000663",
        "id_nfce":      "5",
        "id_bluesoft":  "5",
    },
    "847": {
        "apelido":      "AGROMIX  FL 0008-96",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990000896",
        "id_nfce":      "14",
        "id_bluesoft":  "14",
    },
    "848": {
        "apelido":      "ATACADAO FL 0007-44",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000744",
        "id_nfce":      "15",
        "id_bluesoft":  "15",
    },
    "849": {
        "apelido":      "ATACADAO FL 0008-25",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000825",
        "id_nfce":      "16",
        "id_bluesoft":  "16",
    },
    "850": {
        "apelido":      "AGROMIX  FL 0010-00",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990001000",
        "id_nfce":      "18",
        "id_bluesoft":  "18",
    },
    "852": {
        "apelido":      "AGROMIX  FL 0011-91",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990001191",
        "id_nfce":      "21",
        "id_bluesoft":  "21",
    },
    "853": {
        "apelido":      "AGROMIX  FL 0012-72",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990001272",
        "id_nfce":      "20",
        "id_bluesoft":  "20",
    },
    "854": {
        "apelido":      "ATACADAO FL 0009-06",
        "nome":         "ATACADAO PET PRODUTOS VETERINARIOS LTDA",
        "cnpj":         "11822488000906",
        "id_nfce":      "19",
        "id_bluesoft":  "19",
    },
    "855": {
        "apelido":      "AGROMIX  FL 0013-53",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990001353",
        "id_nfce":      "22",
        "id_bluesoft":  "22",
    },
    "856": {
        "apelido":      "AGROMIX FL 0014-34",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990001434",
        "id_nfce":      "23",
        "id_bluesoft":  "23",
    },
    "923": {
        "apelido":      "VILLAS PET 0002-96 F",
        "nome":         "VILLAS PET LTDA",
        "cnpj":         "07345645000296",
        "id_nfce":      None,       # NAO EXISTE no NFCe
        "id_bluesoft":  None,       # NAO EXISTE no Bluesoft
    },
    "1646": {
        "apelido":      "AGROMIX FL 0015-15",
        "nome":         "AGROMIX PET CENTER LTDA",
        "cnpj":         "06336990001515",
        "id_nfce":      "24",
        "id_bluesoft":  "24",
    },
}

# =============================================================================
# INDICES DERIVADOS (gerados automaticamente — nao editar manualmente)
# =============================================================================

# Indice: CNPJ -> codigo interno  (usado pelo arquivos.py para roteamento de ZIPs)
CNPJ_PARA_CODIGO = {
    loja["cnpj"]: codigo
    for codigo, loja in LOJAS_CADASTRO.items()
}

# Indice: id_bluesoft -> codigo interno  (usado pelo SPED, NFe Saida, NFe Entrada)
BLUESOFT_PARA_CODIGO = {
    loja["id_bluesoft"]: codigo
    for codigo, loja in LOJAS_CADASTRO.items()
    if loja["id_bluesoft"] is not None
}

# Indice: id_nfce -> codigo interno  (usado pelo NFCe)
NFCE_PARA_CODIGO = {
    loja["id_nfce"]: codigo
    for codigo, loja in LOJAS_CADASTRO.items()
    if loja["id_nfce"] is not None
}

# Mapa CNPJ -> nome padrao da pasta final (compatibilidade com arquivos.py)
MAPEAMENTO_CNPJ = {
    loja["cnpj"]: f"{codigo}-{loja['apelido']}"
    for codigo, loja in LOJAS_CADASTRO.items()
}

# =============================================================================
# LISTAS PRONTAS PARA CADA MODULO
# =============================================================================

def get_unidades_bluesoft():
    """
    Retorna dict {id_bluesoft: "CODIGO-APELIDO"} para NF-e Saida, SPED e NFe Entrada.
    Lojas sem id_bluesoft sao excluidas automaticamente.
    Ordenado pelo ID numerico do Bluesoft.
    """
    return dict(sorted(
        {
            loja["id_bluesoft"]: f"{codigo}-{loja['apelido']}"
            for codigo, loja in LOJAS_CADASTRO.items()
            if loja["id_bluesoft"] is not None
        }.items(),
        key=lambda x: int(x[0])
    ))


def get_unidades_nfce():
    """
    Retorna dict {id_nfce: "CODIGO-APELIDO"} para NFCe.
    Lojas sem id_nfce sao excluidas automaticamente.
    Ordenado pelo ID numerico do NFCe.
    """
    return dict(sorted(
        {
            loja["id_nfce"]: f"{codigo}-{loja['apelido']}"
            for codigo, loja in LOJAS_CADASTRO.items()
            if loja["id_nfce"] is not None
        }.items(),
        key=lambda x: int(x[0])
    ))


def get_pasta_por_cnpj(cnpj):
    """
    Dado um CNPJ (14 digitos), retorna o nome padrao da pasta final.
    Retorno: "CODIGO-APELIDO" ou None se nao mapeado.
    """
    codigo = CNPJ_PARA_CODIGO.get(cnpj)
    if not codigo:
        return None
    loja = LOJAS_CADASTRO[codigo]
    return f"{codigo}-{loja['apelido']}"


def get_pasta_bluesoft(id_bluesoft):
    """
    Dado um ID do Bluesoft, retorna o nome padrao da pasta final.
    """
    codigo = BLUESOFT_PARA_CODIGO.get(str(id_bluesoft))
    if not codigo:
        return f"LOJA_BLUESOFT_{id_bluesoft}_DESCONHECIDA"
    loja = LOJAS_CADASTRO[codigo]
    return f"{codigo}-{loja['apelido']}"


def get_pasta_nfce(id_nfce):
    """
    Dado um ID do NFCe, retorna o nome padrao da pasta final.
    """
    codigo = NFCE_PARA_CODIGO.get(str(id_nfce))
    if not codigo:
        return f"LOJA_NFCE_{id_nfce}_DESCONHECIDA"
    loja = LOJAS_CADASTRO[codigo]
    return f"{codigo}-{loja['apelido']}"
