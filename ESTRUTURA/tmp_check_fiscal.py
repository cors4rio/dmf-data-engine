import xlrd

def check():
    try:
        wb = xlrd.open_workbook('c:/Users/DMF-AUTOMACAO/Documents/PROJETOS/N8N automacao/ESTRUTURA/ClienteTempo Gasto022026.xls')
        sh = wb.sheet_by_index(0)
        print("CODE | SECONDS | FORMATTED")
        for i in range(sh.nrows):
            row = sh.row_values(i)
            try:
                # Assuming Code is in Col 0, Seconds in Col 1, Formatted in Col 2 (based on spec)
                code = int(float(row[0]))
                if code in [1195, 1283]:
                    print(f"{code} | {row[1]} | {row[2]}")
            except (ValueError, TypeError):
                pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    check()
