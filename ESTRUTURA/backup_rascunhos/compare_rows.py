import openpyxl

def compare():
    path = 'c:/Users/DMF-AUTOMACAO/Documents/PROJETOS/N8N automacao/ESTRUTURA/CONTROLE_DE_HORAS_DMF.xlsm'
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sh = wb['02.2026']
    
    for r in [88, 93, 761, 781]:
        row = sh[r]
        # Col indices (0-indexed): H=7, I=8, O=14, P=15, Q=16
        code = row[7].value
        name = row[8].value
        fiscal = row[14].value
        contabil = row[15].value
        pessoal = row[16].value
        
        print(f"Row {r} | Code: {code} | Fiscal: {fiscal} | Contabil: {contabil} | Pessoal: {pessoal} | Name: {name[:20]}")

if __name__ == '__main__':
    compare()
