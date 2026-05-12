import openpyxl

file_path = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xlsm"
wb = openpyxl.load_workbook(file_path, data_only=False)
sh = wb['02.2026']

print("--- Fórmulas Finais (Aba 02.2026) ---")
print(f"O7: {sh['O7'].value}")
print(f"Q7: {sh['Q7'].value}")
print(f"R7: {sh['R7'].value}")
