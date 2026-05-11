import pyodbc

DB_DSN = "DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>"
DATA_INICIO = '2026-03-01'
DATA_FIM = '2026-03-31'

try:
    conn = pyodbc.connect(DB_DSN)
    cursor = conn.cursor()
    
    print("Contagem Total de Linhas (orig_lan 1 ou 5):")
    cursor.execute(f"SELECT COUNT(*) FROM bethadba.ctlancto WHERE codi_emp = 835 AND orig_lan IN (1,5) AND data_lan >= '{DATA_INICIO}' AND data_lan <= '{DATA_FIM}'")
    print(cursor.fetchone()[0])
    
    print("\nContagem de nume_lan distintos (orig_lan 1 ou 5):")
    cursor.execute(f"SELECT COUNT(DISTINCT nume_lan) FROM bethadba.ctlancto WHERE codi_emp = 835 AND orig_lan IN (1,5) AND data_lan >= '{DATA_INICIO}' AND data_lan <= '{DATA_FIM}'")
    print(cursor.fetchone()[0])
    
    print("\nContagem de lote_lan distintos (orig_lan 1 ou 5):")
    cursor.execute(f"SELECT COUNT(DISTINCT codi_lote) FROM bethadba.ctlancto WHERE codi_emp = 835 AND orig_lan IN (1,5) AND data_lan >= '{DATA_INICIO}' AND data_lan <= '{DATA_FIM}'")
    print(cursor.fetchone()[0])

    print("\nContagem agrupada por orig_lan:")
    cursor.execute(f"SELECT orig_lan, COUNT(*) as linhas, COUNT(DISTINCT nume_lan) as num_dist, COUNT(DISTINCT codi_lote) as lotes_dist FROM bethadba.ctlancto WHERE codi_emp = 835 AND data_lan >= '{DATA_INICIO}' AND data_lan <= '{DATA_FIM}' GROUP BY orig_lan")
    for r in cursor.fetchall():
        print(f"Origem: {r[0]}, Linhas: {r[1]}, Nume_lan Distintos: {r[2]}, Lotes Distintos: {r[3]}")

    conn.close()
except Exception as e:
    print(f"Erro: {e}")
