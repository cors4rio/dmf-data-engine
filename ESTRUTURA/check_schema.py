import pyodbc
import sys

def explore_db():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("--- Listando tabelas e seus donos (Schemas) ---")
        empresas_names = []
        ctlancto_names = []
        
        for row in cursor.tables():
            name = row.table_name.lower()
            if 'geempresa' in name or 'ctlancto' in name:
                print(f"Schema(Owner): {row.table_schem}, Tabela: {row.table_name}, Tipo: {row.table_type}")
                if 'geempresa' in name:
                    empresas_names.append(f"{row.table_schem}.{row.table_name}" if row.table_schem else row.table_name)
                if 'ctlancto' in name:
                    ctlancto_names.append(f"{row.table_schem}.{row.table_name}" if row.table_schem else row.table_name)
                    
        print(f"\nTabelas de empresas: {empresas_names}")
        print(f"Tabelas de ctlancto: {ctlancto_names}")
        
        # Tentar uma query com o nome exato descoberto
        for table in empresas_names:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                print(f"SUCESSO COUNT Empresas ({table}): {cursor.fetchone()[0]}")
            except Exception as e:
                pass
                
        for table in ctlancto_names:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                print(f"SUCESSO COUNT Lançamentos ({table}): {cursor.fetchone()[0]}")
                
                # Se for a principal, tenta agrupar as origens do mes 01/2026
                if 'ctlancto' in table.lower() and not '_' in table.lower().replace('ctlancto', ''):
                    print(f"Analisando dados da tabela principal {table}...")
                    cursor.execute(f"""
                        SELECT orig_lan, origem_reg, COUNT(*) as qtd
                        FROM {table}
                        WHERE data_lan >= '2026-01-01' AND data_lan <= '2026-01-31'
                        GROUP BY orig_lan, origem_reg
                    """)
                    for r in cursor.fetchall():
                        print(f"  Orig_lan: {r[0]}, Orig_reg: {r[1]} -> Qtd: {r[2]}")
            except Exception as e:
                pass

    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)

if __name__ == '__main__':
    explore_db()
