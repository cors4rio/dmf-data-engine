import pyodbc
import sys
import json

def generate_report():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Testar se bethadba.geempresas existe de fato (nao tinha aparecido na query anterior mas vimos pelas FKs)
        print("--- Testando GEEMPRESAS ---")
        try:
            cursor.execute("SELECT TOP 5 codi_emp, nome_emp FROM bethadba.geempresas")
            for r in cursor.fetchall():
                print(r)
        except Exception as e:
            print(f"Erro GEEMPRESAS: {e}")
            
        print("\n--- Relatorio Preliminar: Contagem de Lançamentos 01/2026 ---")
        # Vamos assumir que 1 = Normal e 5 = Extrato (ou origem_reg = 2 / 3)
        # origin_reg = 2 costuma ser importados, 0 manual
        # Em ctlancto, orig_lan 1 = Normal, 5 = Extrato 
        
        query = """
            SELECT 
                l.codi_emp,
                -- e.nome_emp, -- Se conseguirmos join com geempresas
                SUM(CASE WHEN l.orig_lan IN (1) THEN 1 ELSE 0 END) as qtd_normal,
                SUM(CASE WHEN l.orig_lan IN (5) THEN 1 ELSE 0 END) as qtd_extrato,
                COUNT(*) as total_geral
            FROM 
                bethadba.ctlancto l
            WHERE 
                l.data_lan >= '2026-01-01' 
                AND l.data_lan <= '2026-01-31'
            GROUP BY 
                l.codi_emp
            ORDER BY 
                l.codi_emp
        """
        
        cursor.execute(query)
        res = cursor.fetchmany(10)
        
        print(f"{'Cod Cliente':<12} | {'Normal':<10} | {'Extrato Bancário':<18} | {'Total':<10}")
        print("-" * 60)
        for row in res:
            print(f"{row[0]:<12} | {row[1]:<10} | {row[2]:<18} | {row[3]:<10}")

    except Exception as e:
        print(f"Erro Fatal: {e}", file=sys.stderr)

if __name__ == '__main__':
    generate_report()
