import xlrd

def extract_data():
    files = {
        'fiscal': 'c:/Users/DMF-AUTOMACAO/Documents/PROJETOS/N8N automacao/ESTRUTURA/ClienteTempo Gasto022026.xls',
        'pessoal': 'c:/Users/DMF-AUTOMACAO/Documents/PROJETOS/N8N automacao/ESTRUTURA/Controle de Empregados (CAROL)022026.xls'
    }
    
    codes = [1195, 1283]
    results = {c: {'fiscal_sec': 0, 'pessoal_emp': 0} for c in codes}
    
    # 1. Fiscal
    print(f"--- FISCAL ({files['fiscal']}) ---")
    try:
        wb = xlrd.open_workbook(files['fiscal'])
        sh = wb.sheet_by_index(0)
        for i in range(sh.nrows):
            row = sh.row_values(i)
            try:
                c = int(float(row[0]))
                if c in codes:
                    results[c]['fiscal_sec'] = row[1]
                    print(f"Code {c}: {row[1]} seconds ({row[2]})")
            except: pass
    except Exception as e: print(f"Fiscal Error: {e}")

    # 2. Pessoal
    print(f"\n--- PESSOAL ({files['pessoal']}) ---")
    try:
        wb = xlrd.open_workbook(files['pessoal'])
        sh = wb.sheet_by_index(0)
        for i in range(sh.nrows):
            row = sh.row_values(i)
            try:
                c = int(float(row[0]))
                if c in codes:
                    results[c]['pessoal_emp'] = int(float(row[1]))
                    print(f"Code {c}: {results[c]['pessoal_emp']} employees")
            except: pass
    except Exception as e: print(f"Pessoal Error: {e}")

    return results

if __name__ == '__main__':
    extract_data()
