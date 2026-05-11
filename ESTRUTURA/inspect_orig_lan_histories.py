import pyodbc

DB_CONN_STR = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
DATA_INICIO = '2026-02-01'
DATA_FIM = '2026-02-28'
CLIENTE = 1283

def inspect_histories():
    print(f"Inspecionando histórias de lançamentos por origem para o cliente {CLIENTE}...")
    conn = pyodbc.connect(DB_CONN_STR)
    cursor = conn.cursor()
    
    # Pegar um sample de cada orig_lan
    # Chis_lan é o histórico
    query = f"""
        SELECT orig_lan, MIN(chis_lan) as exemplo_hist, COUNT(*) as qtd
        FROM bethadba.ctlancto
        WHERE data_lan >= '{DATA_INICIO}' AND data_lan <= '{DATA_FIM}'
        AND codi_emp = {CLIENTE}
        GROUP BY orig_lan
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    
    print(f"{'Orig':<4} | {'Qtd':<5} | {'Exemplo de Histórico'}")
    print("-" * 50)
    for row in rows:
        orig = row[0]
        qtd = row[1]
        hist = str(row[2])[:60].replace('\n', ' ')
        print(f"{orig:<4} | {qtd:<5} | {hist}")
            
    conn.close()

if __name__ == "__main__":
    inspect_histories()
