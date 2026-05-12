import win32com.client as win32

def check_headers():
    xls_path = r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xls'
    excel = win32.Dispatch('Excel.Application')
    excel.Visible = False
    excel.DisplayAlerts = False
    
    try:
        wb = excel.Workbooks.Open(xls_path, ReadOnly=True)
        sheet_name = '12.2025'
        ws = wb.Sheets(sheet_name)
        
        headers = ws.Range("A9:Z9").Value[0]
        for col_idx, header in enumerate(headers):
            col_letter = chr(65 + col_idx) if col_idx < 26 else 'Z' # simplification
            print(f"Coluna {col_letter} = {header}")
            
    finally:
        try:
            wb.Close(False)
            excel.Quit()
        except:
            pass

if __name__ == "__main__":
    check_headers()
