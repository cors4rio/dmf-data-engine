import pyodbc

DB_CONN_STR = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
DATA_INICIO = '2026-02-01'
DATA_FIM = '2026-02-28'
CLIENTE = 1283

def diag():
    print(f"Buscando lançamentos para o cliente {CLIENTE}...")
    conn = pyodbc.connect(DB_CONN_STR)
    cursor = conn.cursor()
    
    query = f"""
        SELECT orig_lan, COUNT(*) as qtd
        FROM bethadba.ctlancto
        WHERE data_lan >= '{DATA_INICIO}' AND data_lan <= '{DATA_FIM}'
        AND codi_emp = {CLIENTE}
        GROUP BY orig_lan
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    if not rows:
        print("Nenhum lançamento encontrado para este cliente no período.")
    else:
        print(f"Origem | Quantidade")
        print("-" * 20)
        for row in rows:
            print(f"{row[0]:<6} | {row[1]}")
            
    conn.close()

if __name__ == "__main__":
    diag()
