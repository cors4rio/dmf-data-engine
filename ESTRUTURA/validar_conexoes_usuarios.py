import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Verificar amostra de geloguser para entender o formato de usua_log
        cursor.execute("SELECT TOP 5 usua_log FROM bethadba.geloguser WHERE sist_log = 5")
        log_sample = cursor.fetchall()
        print(f"Amostra usua_log (geloguser): {[r[0] for r in log_sample]}")
        
        # Verificar amostra de usConfUsuario
        cursor.execute("SELECT TOP 5 user_id FROM bethadba.usConfUsuario")
        conf_sample = cursor.fetchall()
        print(f"Amostra user_id (usConfUsuario): {[r[0] for r in conf_sample]}")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
