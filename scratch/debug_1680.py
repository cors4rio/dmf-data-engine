import pandas as pd
import os

def analisar_carol_1680():
    # O arquivo é .xls, pandas com xlrd costuma ler
    file_path = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ENTRADAS_MANUAIS\Controle de Empregados (CAROL).xls"
    print(f"Lendo planilha: {file_path}")
    
    try:
        # Lendo sem header primeiro para ver a estrutura
        df = pd.read_excel(file_path, header=None)
        
        # Procurar 1680 em qualquer lugar do dataframe
        mask = df.apply(lambda row: row.astype(str).str.contains('1680').any(), axis=1)
        res = df[mask]
        
        if not res.empty:
            print("\nEncontrado registro(s) para 1680:")
            print(res)
        else:
            print("\nCliente 1680 NÃO encontrado na planilha Carol.")
            
    except Exception as e:
        print(f"Erro ao ler planilha: {e}")
        print("Tentando com motor alternativo...")
        try:
             # Às vezes o .xls da Domínio é na verdade um HTML/XML disfarçado
             import openpyxl
             # Se for .xlsx disfarçado de .xls
             df = pd.read_excel(file_path, engine='openpyxl')
             mask = df.apply(lambda row: row.astype(str).str.contains('1680').any(), axis=1)
             print(df[mask])
        except Exception as e2:
             print(f"Falha total na leitura: {e2}")

if __name__ == "__main__":
    analisar_carol_1680()
