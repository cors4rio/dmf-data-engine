import pyodbc
import sys

def check_empresas_and_lanctos():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("--- Procurando tabelas de Empresa ---")
        # Listar as tabelas novamente para ver o dono (schema/owner)
        for row in cursor.tables():
            name = row.table_name.lower()
            if name == 'geempresas' or name == 'empescate': 
                print(f"Table: {row.table_name}, Owner: {row.table_owner}, Val: {row}")
                
        # Vamos tentar uma query em algumas variações de geempresas
        queries = [
            "SELECT COUNT(*) FROM geempresas",
            "SELECT COUNT(*) FROM bethadba.geempresas",
            "SELECT COUNT(*) FROM DBA.geempresas"
        ]
        
        for q in queries:
            try:
                cursor.execute(q)
                print(f"Sucesso: {q} -> {cursor.fetchone()[0]} registros")
            except Exception as e:
                pass
                
        print("\n--- Checando Lançamentos (Origens) ---")
        # Em vez de TOP/LIMIT que varia por banco, vamos agrupar
        cursor.execute("""
            SELECT orig_lan, origem_reg, COUNT(*) as qtd
            FROM ctlancto
            WHERE data_lan >= '2025-01-01'
            GROUP BY orig_lan, origem_reg
        """)
        results = cursor.fetchall()
        # Sort by count descending
        results.sort(key=lambda x: x[2], reverse=True)
        for r in results[:10]:
            print(f"Origem_LAN: {r[0]}, Origem_REG: {r[1]} -> Qtd: {r[2]}")
            
    except Exception as e:
        print(f"Erro Fatal: {e}", file=sys.stderr)

if __name__ == '__main__':
    check_empresas_and_lanctos()
