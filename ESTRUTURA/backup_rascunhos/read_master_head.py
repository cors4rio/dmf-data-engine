import xlrd

def inspect_master(file_path):
    print(f"Lendo Master: {file_path}")
    wb = xlrd.open_workbook(file_path)
    print(f"Abas: {wb.sheet_names()}")
    
    # Inspeciona a primeira aba (geralmente onde estão os clientes)
    sh = wb.sheet_by_index(0)
    print(f"Aba 0: {sh.name}, Linhas: {sh.nrows}, Colunas: {sh.ncols}")
    
    # Mostra as primeiras 20 linhas para entender o mapeamento
    for r in range(min(25, sh.nrows)):
        row_values = sh.row_values(r)
        # Limita o número de colunas impressas para não poluir
        print(f"Linha {r}: {row_values[:20]}")

if __name__ == "__main__":
    path = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xls"
    inspect_master(path)
