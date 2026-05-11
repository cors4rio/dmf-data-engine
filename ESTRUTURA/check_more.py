import win32com.client as win32
import os

def check_more_formulas():
    xls_path = r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xls'
    
    print(f"Iniciando Excel via COM...")
    excel = win32.Dispatch('Excel.Application')
    excel.Visible = False
    
    try:
        wb = excel.Workbooks.Open(xls_path)
        sheet_name = '12.2025'
        ws = wb.Sheets(sheet_name)
        
        last_row = ws.Cells(ws.Rows.Count, "O").End(-4162).Row # xlUp
        print(f"Ultima linha com dados na coluna O: {last_row}")
        print(f"Ultima linha com dados na coluna P: {ws.Cells(ws.Rows.Count, 'P').End(-4162).Row}")
        print(f"Ultima linha com dados na coluna A: {ws.Cells(ws.Rows.Count, 'A').End(-4162).Row}")
        
        # Testar a formula em O7, P7, Q7, R7
        for c in ['O7', 'P7', 'Q7', 'R7', 'O8', 'P8', 'Q8', 'R8', 'O9', 'P9', 'Q9', 'R9']:
            cell = ws.Range(c)
            print(f"[{c}] -> Valor: {cell.Value} | Formula: {cell.FormulaLocal}")
            
        # Pegar algumas formulas da coluna R para ver como calcula o total por linha
        for r in range(10, 15):
            cell = ws.Range(f"R{r}")
            print(f"[R{r}] -> Valor: {cell.Value} | Formula: {cell.FormulaLocal}")
            
    finally:
        try:
            wb.Close(False)
            excel.Quit()
        except:
            pass

if __name__ == "__main__":
    check_more_formulas()
