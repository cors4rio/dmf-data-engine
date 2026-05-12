import win32com.client as win32
from collections import defaultdict

def find_true_duplicates():
    xls_path = r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xls'
    
    excel = win32.Dispatch('Excel.Application')
    excel.Visible = False
    excel.DisplayAlerts = False
    
    try:
        wb = excel.Workbooks.Open(xls_path, ReadOnly=True)
        sheet_name = '12.2025'
        ws = wb.Sheets(sheet_name)
        
        last_row = ws.Cells(ws.Rows.Count, "J").End(-4162).Row # xlUp
        
        print(f"Lendo dados até a linha {last_row}...")
        # Lendo de H10 até K[last_row]
        # H=0, I=1, J=2 (CNPJ), K=3 (Nome)
        values = ws.Range(f"H10:K{last_row}").Value
        
        cnpj_dict = defaultdict(list)
        
        for i, row_data in enumerate((values or [])):
            row_num = i + 10
            
            codigo = row_data[0]
            cnpj = row_data[2] # Coluna J
            nome = row_data[3] # Coluna K
            
            if cnpj:
                cnpj_clean = str(cnpj).replace('.', '').replace('/', '').replace('-', '').strip()
                # Verificar se é numérico para afastar lixo ou letras
                if cnpj_clean.isdigit():
                    cnpj_dict[cnpj_clean].append((row_num, codigo, nome, cnpj))
                    
        print("\n--- CLIENTES COM CNPJ DUPLICADO ABA 12.2025 ---")
        has_dupes = False
        for cnpj_clean, ocorrencias in cnpj_dict.items():
            if len(ocorrencias) > 1:
                has_dupes = True
                print(f"\nCNPJ: {ocorrencias[0][3]}")
                for occ in ocorrencias:
                    row_idx, codigo, nome, cnpj_raw = occ
                    cod_str = str(int(codigo)) if codigo else "S/Cód"
                    print(f"  -> Linha {row_idx} | Cód: {cod_str} | Empresa: {nome}")
        
        if not has_dupes:
            print(">> NENHUM CNPJ DUPLICADO ENCONTRADO NA ABA 12.2025.")
            
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        try:
            wb.Close(False)
            excel.Quit()
        except:
            pass

if __name__ == "__main__":
    find_true_duplicates()
