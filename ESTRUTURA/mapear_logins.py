import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # O usuário quer mapear nomes como "Aline", "Breno", etc.
        # Vamos buscar logins e nomes na tabela auusuarios
        cursor.execute("SELECT user_id, nome FROM bethadba.auusuarios")
        users = cursor.fetchall()
        
        print(f"Total de usuários encontrados: {len(users)}")
        with open('ESTRUTURA/mapeamento_usuarios_fiscal.txt', 'w', encoding='utf-8') as f:
            for u in users:
                f.write(f"LOGIN: {u[0]} | NOME: {u[1]}\n")
        
        print("Mapeamento salvo em ESTRUTURA/mapeamento_usuarios_fiscal.txt")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
