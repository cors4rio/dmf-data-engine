import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Buscar todos os usuários para inspeção manual
        cursor.execute("SELECT user_id, NOME, SITUACAO FROM bethadba.usConfUsuario ORDER BY NOME")
        all_users = cursor.fetchall()
        
        with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\lista_completa_usuarios.txt', 'w', encoding='utf-8') as f:
            f.write(f"{'ID':<10} | {'SIT':<4} | {'NOME'}\n")
            f.write("-" * 60 + "\n")
            for u_id, u_nome, u_sit in all_users:
                f.write(f"{u_id:<10} | {u_sit:<4} | {u_nome}\n")

        print("Lista completa salva em ESTRUTURA/lista_completa_usuarios.txt")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
