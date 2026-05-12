import pandas as pd
import xlrd
import sys

def inspect_xls(file_path):
    print(f"Inspecionando: {file_path}")
    xls = pd.ExcelFile(file_path, engine='xlrd')
    print(f"Abas encontradas: {xls.sheet_names}")
    
    for sheet_name in xls.sheet_names:
        print(f"\n--- Aba: {sheet_name} ---")
        df = pd.read_excel(xls, sheet_name=sheet_name, nrows=20)
        print("Primeiras 20 linhas:")
        print(df.to_string())
        
        # Verificar coluna Q (índice 16)
        if len(df.columns) > 16:
            print(f"\nColuna Q (índice 16): {df.columns[16]}")
        else:
            print("\nColuna Q não encontrada nesta aba.")

if __name__ == "__main__":
    path = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\CONTROLE_DE_HORAS_DMF.xls"
    try:
        inspect_xls(path)
    except Exception as e:
        print(f"Erro: {e}")
