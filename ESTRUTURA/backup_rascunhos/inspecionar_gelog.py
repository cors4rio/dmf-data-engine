import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Inspecionar geloguser
        cursor.execute("SELECT TOP 1 * FROM bethadba.geloguser")
        columns = [column[0] for column in cursor.description]
        print(f"Colunas geloguser: {columns}")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
