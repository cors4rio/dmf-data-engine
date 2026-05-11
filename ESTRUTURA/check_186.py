import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            orig_lan,
            COUNT(*) as Qtd
        FROM bethadba.ctlancto
        WHERE data_lan >= '2025-01-01'
          AND data_lan <= '2025-01-31'
          AND codi_emp = 186
        GROUP BY orig_lan
        """
        
        print(f"Executando query COMPLETA para empresa 186 em 01.2025...")
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if rows:
            print("Origem | Quantidade")
            print("-------|-----------")
            for row in rows:
                print(f"{row.orig_lan:6} | {row.Qtd:10}")
        else:
            print("Nenhum lançamento encontrado para a empresa 186 em 01.2025.")
            
        conn.close()
    except Exception as e:
        print(f"Erro ao conectar ou executar query: {e}")

if __name__ == "__main__":
    main()
