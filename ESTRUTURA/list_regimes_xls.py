import pyodbc

xls_path = r'C:\Users\DMF-AUTOMACAO\Downloads\Relação de Regime de Empresa 022026s.xls'

conn_str = r'DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};DBQ=' + xls_path + ';ReadOnly=1'
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()
tables = [t.table_name for t in cursor.tables()]
cursor.execute(f'SELECT * FROM [{tables[0]}]')

regimes_unicos = {}
for row in cursor.fetchall():
    try:
        # Tenta achar o regime em colunas 3, 4, 5
        for cell in [row[3], row[4], row[5]]:
            s_cell = str(cell).strip()
            if s_cell and not s_cell.isdigit() and len(s_cell) > 3:
                if s_cell not in regimes_unicos:
                    regimes_unicos[s_cell] = str(row[0]) # Salva um exemplo de Cod
                break
    except:
        continue

print("Regimes encontrados na planilha:")
for reg, cod in regimes_unicos.items():
    print(f"- {reg} (Ex: Cod {cod})")
