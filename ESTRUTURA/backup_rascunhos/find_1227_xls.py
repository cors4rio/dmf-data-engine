import pyodbc

xls_path = r'C:\Users\DMF-AUTOMACAO\Downloads\Relação de Regime de Empresa 022026s.xls'

conn_str = (
    r'DRIVER={Microsoft Excel Driver (*.xls, *.xlsx, *.xlsm, *.xlsb)};'
    f'DBQ={xls_path};'
    r'ReadOnly=1'
)

try:
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    tables = [t.table_name for t in cursor.tables()]
    sheet_name = tables[0]
    
    # Busca cabeçalhos e dados
    cursor.execute(f'SELECT * FROM [{sheet_name}]')
    
    # Os cabeçalhos podem estar na primeira linha se o driver não os detectou automaticamente
    rows = cursor.fetchmany(500) # Pega bastante pra garantir que acha a 1227
    
    found_1227 = None
    for row in rows:
        # Verifica se alguma coluna contém '1227'
        if any('1227' in str(cell) for cell in row):
            found_1227 = row
            break
            
    if found_1227:
        print("Dados da empresa 1227 na planilha:")
        print(found_1227)
    else:
        print("Empresa 1227 não encontrada nas 500 primeiras linhas.")
        # Se não achou, tenta procurar em tudo (pode ser lento)
        cursor.execute(f'SELECT * FROM [{sheet_name}]')
        for row in cursor.fetchall():
            if any('1227' in str(cell) for cell in row):
                print("Encontrada em busca total:", row)
                break

except Exception as e:
    print(f"Erro: {e}")
