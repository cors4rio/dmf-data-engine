import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        with open('ESTRUTURA/gestta_mapping.txt', 'w', encoding='utf-8') as f:
            
            f.write("--- Buscando GUIDs em GEEMP ---\n")
            try:
                cursor.execute("SELECT TOP 5 codigo, nome, guid FROM bethadba.geemp")  # Chutando o nome da coluna GUID
                for row in cursor.fetchall():
                    f.write(f"{row}\n")
            except Exception as e:
                f.write(f"GEEMP Error: {e}\n")
                
                # Vamos tentar ver as colunas de GEEMP
                try:
                    cursor.execute("SELECT column_name FROM SYS.SYSCOLUMN WHERE table_id = (SELECT table_id FROM SYS.SYSTABLE WHERE table_name = 'geemp')")
                    cols = [r[0] for r in cursor.fetchall()]
                    f.write(f"Colunas GEEMP: {', '.join(cols)}\n")
                except Exception as ex:
                    f.write(f"Erro ao listar colunas: {ex}\n")

            f.write("\n--- Buscando tabelas com USUARIO e GUID ---\n")
            try:
                # Qual tabela tem nome de usuario e GUID?
                cursor.execute("SELECT t.table_name FROM SYS.SYSTABLE t JOIN SYS.SYSCOLUMN c ON t.table_id = c.table_id WHERE t.creator = (SELECT user_id FROM SYS.SYSUSER WHERE user_name = 'bethadba') AND c.column_name LIKE '%GUID%'")
                tables = set([r[0] for r in cursor.fetchall()])
                f.write(f"Tabelas com GUID: {', '.join(tables)}\n")
            except Exception as e:
                f.write(f"Erro GUID: {e}\n")
                
        print("Salvo em ESTRUTURA/gestta_mapping.txt")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
