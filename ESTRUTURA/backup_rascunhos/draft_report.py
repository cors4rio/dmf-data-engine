import pyodbc
import sys

def generate_report():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("\n--- Analisando origens de lancamentos (orig_lan) em 01/2026 ---")
        cursor.execute("""
            SELECT orig_lan, origem_reg, COUNT(*) as qtd
            FROM bethadba.ctlancto
            WHERE data_lan >= '2026-01-01' AND data_lan <= '2026-01-31'
            GROUP BY orig_lan, origem_reg
            ORDER BY 3 DESC
        """)
        results = cursor.fetchall()
        for r in results:
            print(f"Orig_lan: {r[0]}, Orig_reg: {r[1]} -> Qtd: {r[2]}")

        print("\n--- Verificando layout de Empresas Web ---")
        # Vamos verificar se GEEMPRESAS_MODULOWEB tem os dados do cliente
        cursor.execute("SELECT TOP 1 * FROM bethadba.GEEMPRESAS_MODULOWEB")
        cols = [column[0] for column in cursor.description]
        print(f"Colunas GEEMPRESAS_MODULOWEB: {cols}")
        
    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)

if __name__ == '__main__':
    generate_report()
