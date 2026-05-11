import xlrd

PLANILHA_CAROL = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\Controle de Empregados (CAROL)032026.xls"

wb_carol = xlrd.open_workbook(PLANILHA_CAROL)
sh_carol = wb_carol.sheet_by_index(0)

count = 0
for i in range(1, sh_carol.nrows):
    row = sh_carol.row_values(i)
    if row[1] in [1152, 1152.0, "1152"]:
        count += 1
        print(f"Row {i} in Carol has code 1152")

print(f"Total occurrences of 1152 in Carol: {count}")
