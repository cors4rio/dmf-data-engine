import pyodbc
import json
import sys

def get_relationships():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Obtendo lista de tabelas para extrair chaves e relacionamentos...")
        tables_names = []
        for row in cursor.tables():
            if row.table_type in ('TABLE', 'VIEW'):
                tables_names.append(row.table_name)
                
        relationships = {}
        
        # Como o banco tem quase 5000 tabelas, vamos tentar extrair chaves primarias
        # e chaves estrangeiras com cuidado
        print("Extraindo chaves primarias e estrangeiras. Isso vai demorar um pouco...")
        
        count = 0
        for table_name in tables_names:
            table_info = {'primary_keys': [], 'foreign_keys': []}
            
            # Chaves primárias
            try:
                for row in cursor.primaryKeys(table_name):
                    table_info['primary_keys'].append({
                        'column_name': getattr(row, 'column_name', None),
                        'pk_name': getattr(row, 'pk_name', None)
                    })
            except Exception:
                pass # Driver pode nao suportar
                
            # Chaves estrangeiras
            try:
                for row in cursor.foreignKeys(table=table_name):
                    table_info['foreign_keys'].append({
                        'pk_table_name': getattr(row, 'pktable_name', None),
                        'pk_column_name': getattr(row, 'pkcolumn_name', None),
                        'fk_table_name': getattr(row, 'fktable_name', None),
                        'fk_column_name': getattr(row, 'fkcolumn_name', None),
                        'fk_name': getattr(row, 'fk_name', None)
                    })
            except Exception:
                pass # Driver pode nao suportar

            if table_info['primary_keys'] or table_info['foreign_keys']:
                relationships[table_name] = table_info
                
            count += 1
            if count % 500 == 0:
                print(f"Processadas {count} de {len(tables_names)} tabelas...")
                
        # Salvar em JSON para facilitar a leitura
        with open('dominio_relationships.json', 'w', encoding='utf-8') as f:
            json.dump(relationships, f, indent=4)
            
        print(f"\nSucesso: Relacionamentos de {len(relationships)} tabelas processadas e salvas em dominio_relationships.json!")
    except Exception as e:
        print(f"Erro ao conectar ou buscar relacionamentos: {e}", file=sys.stderr)

if __name__ == '__main__':
    get_relationships()
