import pyodbc
import os

xls_path = r'C:\Users\DMF-AUTOMACAO\Downloads\Relação de Regime de Empresa 022026s.xls'

# Tenta conectar usando o driver do Excel
conn_str = (
    r'DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};'
    f'DBQ={xls_path};'
    r'ReadOnly=1'
)

try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    
    # Lista as tabelas (planilhas)
    tables = [t.table_name for t in cursor.tables()]
    print("Planilhas encontradas:", tables)
    
    if tables:
        # Pega a primeira planilha
        sheet_name = tables[0]
        cursor.execute(f'SELECT TOP 20 * FROM [{sheet_name}]')
        for row in cursor.fetchall():
            print(row)
            
except Exception as e:
    print(f"Erro ao ler XLS via ODBC: {e}")
