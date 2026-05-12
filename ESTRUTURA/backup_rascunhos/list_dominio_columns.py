import pyodbc
import json
import sys

def get_tables_and_columns():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Obter todas as tabelas e views
        tables = {}
        print("Obtendo lista de tabelas...")
        for row in cursor.tables():
            table_name = row.table_name
            table_type = row.table_type
            if table_type in ('TABLE', 'VIEW'):
                tables[table_name] = {'name': table_name, 'type': table_type, 'columns': []}
                
        # Obter todas as colunas
        print("Obtendo lista de colunas, isso pode demorar um pouco...")
        for row in cursor.columns():
            table_name = row.table_name
            if table_name in tables:
                col_info = {
                    'name': getattr(row, 'column_name', None),
                    'type': getattr(row, 'type_name', None),
                    'size': getattr(row, 'column_size', None)
                }
                tables[table_name]['columns'].append(col_info)
                
        # Converter dict para list
        tables_list = list(tables.values())
        
        # Salvar em JSON para facilitar a leitura
        with open('dominio_columns.json', 'w', encoding='utf-8') as f:
            json.dump(tables_list, f, indent=4)
            
        print(f"Sucesso: {len(tables_list)} tabelas/views processadas e salvas em dominio_columns.json!")
    except Exception as e:
        print(f"Erro ao conectar ou buscar tabelas/colunas: {e}", file=sys.stderr)

if __name__ == '__main__':
    get_tables_and_columns()
