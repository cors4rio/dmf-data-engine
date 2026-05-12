import openpyxl

BASE_DIR = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA"
PLANILHA_MASTER = BASE_DIR + r"\CONTROLE DE HORAS DMF - CLIENTE.xlsm"

wb = openpyxl.load_workbook(PLANILHA_MASTER, keep_vba=True)
ws = wb['03.2026']

cell = ws.cell(row=94, column=17)
print(f"Cell value: {cell.value}")
print(f"Cell number_format: {cell.number_format}")

