import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("Obtendo colunas de auusuarios via cursor.columns()...")
        for row in cursor.columns(table='auusuarios'):
            print(f"Col: {row.column_name}")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
