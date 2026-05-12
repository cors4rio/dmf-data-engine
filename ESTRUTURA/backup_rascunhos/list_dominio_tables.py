import pyodbc
import json
import sys

def get_tables():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Obter todas as tabelas e views
        tables = []
        for row in cursor.tables():
            table_name = row.table_name
            table_type = row.table_type
            if table_type in ('TABLE', 'VIEW'):
                tables.append({'name': table_name, 'type': table_type})
                
        # Salvar em JSON para facilitar a leitura
        with open('dominio_tables.json', 'w', encoding='utf-8') as f:
            json.dump(tables, f, indent=4)
            
        print(f"Sucesso: {len(tables)} tabelas/views encontradas e salvas em dominio_tables.json")
    except Exception as e:
        print(f"Erro ao conectar ou buscar tabelas: {e}", file=sys.stderr)

if __name__ == '__main__':
    get_tables()
