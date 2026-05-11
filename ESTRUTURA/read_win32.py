import win32com.client as win32
import os

def check_formulas_win32():
    xls_path = r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xls'
    
    print(f"Iniciando Excel via COM...")
    excel = win32.Dispatch('Excel.Application')
    excel.Visible = False
    
    try:
        wb = excel.Workbooks.Open(xls_path)
        
        sheet_name = '12.2025'
        ws = wb.Sheets(sheet_name)
        
        cells_to_check = ['O7', 'P7', 'Q7', 'R7', 'O9', 'P9', 'Q9', 'R9']
        
        last_row = ws.Cells(ws.Rows.Count, "O").End(-4162).Row # xlUp
        print(f"Aba: {sheet_name} | Ultima linha com dados (col O): {last_row}")
        
        for cell_ref in cells_to_check:
            cell = ws.Range(cell_ref)
            formula = cell.FormulaLocal
            val = cell.Value
            print(f"[{cell_ref}] -> Valor: {val} | Formula: {formula}")
            
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        try:
            wb.Close(False)
        except:
            pass
        excel.Quit()

if __name__ == "__main__":
    check_formulas_win32()
