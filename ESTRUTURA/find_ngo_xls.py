import pyodbc

xls_path = r'C:\Users\DMF-AUTOMACAO\Downloads\Relação de Regime de Empresa 022026s.xls'

conn_str = r'DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};DBQ=' + xls_path + ';ReadOnly=1'
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()
tables = [t.table_name for t in cursor.tables()]
cursor.execute(f'SELECT * FROM [{tables[0]}]')

entities = []
keywords = ["ASSOC", "IGREJA", "FUNDACAO", "SINDICA", "CONSELHO", "CENTRO"]

for row in cursor.fetchall():
    name = str(row[1]).upper()
    if any(kw in name for kw in keywords):
        entities.append((row[0], row[1], row[3], row[4], row[5]))

print(f"Encontradas {len(entities)} entidades candidatas a Imune/Isenta:")
for ent in entities[:20]:
    print(ent)
