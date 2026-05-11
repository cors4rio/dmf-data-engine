import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        with open('ESTRUTURA/uuid_mapping_2.txt', 'w', encoding='utf-8') as f:
            
            f.write("\n--- Verificando Colunas GEEMPRE ---\n")
            try:
                cursor.execute("SELECT column_name FROM SYS.SYSCOLUMN WHERE table_id = (SELECT table_id FROM SYS.SYSTABLE WHERE table_name = 'geempre')")
                for row in cursor.fetchall():
                    f.write(f"{row[0]}, ")
            except Exception as e:
                f.write(f"GEEMPRE error: {e}\n")

            f.write("\n\n--- Verificando Colunas GECONTADOR ---\n")
            try:
                cursor.execute("SELECT column_name FROM SYS.SYSCOLUMN WHERE table_id = (SELECT table_id FROM SYS.SYSTABLE WHERE table_name = 'GeContador')")
                for row in cursor.fetchall():
                    f.write(f"{row[0]}, ")
            except Exception as e:
                f.write(f"GECONTADOR error: {e}\n")

            f.write("\n\n--- Verificando Colunas USCONFUSUARIO ---\n")
            try:
                cursor.execute("SELECT column_name FROM SYS.SYSCOLUMN WHERE table_id = (SELECT table_id FROM SYS.SYSTABLE WHERE table_name = 'usConfUsuario')")
                for row in cursor.fetchall():
                    f.write(f"{row[0]}, ")
            except Exception as e:
                pass
                
        print("Salvo em ESTRUTURA/uuid_mapping_2.txt")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
