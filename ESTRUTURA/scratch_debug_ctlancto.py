import pyodbc

DB_DSN = "DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>"

try:
    conn = pyodbc.connect(DB_DSN)
    cursor = conn.cursor()
    cursor.execute("SELECT TOP 1 * FROM bethadba.ctlancto")
    columns = [column[0] for column in cursor.description]
    print("Colunas em ctlancto:")
    print(columns)
    
    # Vamos ver como so os dados pro cliente 835
    cursor.execute("SELECT TOP 20 * FROM bethadba.ctlancto WHERE codi_emp = 835 AND orig_lan IN (1,5)")
    rows = cursor.fetchall()
    print("\nExemplo de linhas do cliente 835:")
    for row in rows:
        print(row)
        
    conn.close()
except Exception as e:
    print(f"Erro: {e}")
