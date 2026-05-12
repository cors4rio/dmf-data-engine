import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        with open('ESTRUTURA/uuid_mapping.txt', 'w', encoding='utf-8') as f:
            
            f.write("--- GEEMPRE ---\n")
            try:
                cursor.execute("SELECT TOP 5 codigo, nome, guid_empresa FROM bethadba.geempre") # Tentando de novo
                for row in cursor.fetchall():
                    f.write(f"{row}\n")
            except Exception as e:
                try:
                    cursor.execute("SELECT TOP 5 codigo, nome, ID_ONVIO FROM bethadba.geempre")
                    for row in cursor.fetchall():
                        f.write(f"{row}\n")
                except Exception as e:
                    f.write(f"GEEMPRE error: {e}\n")
                    
            f.write("\n--- AUUSUARIOS ---\n")
            try:
                cursor.execute("SELECT TOP 5 nome_usuario, guid FROM bethadba.auusuarios")
                for row in cursor.fetchall():
                    f.write(f"{row}\n")
            except Exception as e:
                f.write(f"AUUSUARIOS erro: {e}\n")

            f.write("\n--- GEUSUARIOS ---\n")
            try:
                cursor.execute("SELECT TOP 5 nome_usuario, guid FROM bethadba.geusuarios")
                for row in cursor.fetchall():
                    f.write(f"{row}\n")
            except Exception as e:
                f.write(f"GEUSUARIOS erro: {e}\n")

            f.write("\n--- Buscar TODAS Colunas com GUID ---\n")
            try:
                cursor.execute("SELECT t.table_name, c.column_name FROM SYS.SYSTABLE t JOIN SYS.SYSCOLUMN c ON t.table_id = c.table_id WHERE c.column_name LIKE '%GUID%' AND t.table_name IN ('geempre', 'auusuarios', 'geusuarios', 'GeContador', 'usConfUsuario')")
                for row in cursor.fetchall():
                    f.write(f"{row[0]}.{row[1]}\n")
            except Exception as e:
                f.write(f"Erro cols: {e}\n")
                
        print("Salvo em ESTRUTURA/uuid_mapping.txt")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
