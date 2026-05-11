import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Obter todos os logins
        cursor.execute("SELECT usuario FROM bethadba.auusuarios")
        logins = [r[0] for r in cursor.fetchall()]
        
        # Obter todos os nomes e IDs de usConfUsuario
        cursor.execute("SELECT i_usuario, NOME FROM bethadba.usConfUsuario")
        users = cursor.fetchall()
        
        with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\mapeamento_logins_vs_nomes.txt', 'w', encoding='utf-8') as f:
            f.write("--- LOGINS DISPONÍVEIS EM AUUSUARIOS ---\n")
            f.write(", ".join([str(l) for l in logins]) + "\n\n")
            
            f.write("--- USUÁRIOS EM USCONFUSUARIO ---\n")
            for i_usu, nome in users:
                f.write(f"ID: {i_usu} | NOME: {nome}\n")

        print("Mapeamento bruto salvo em ESTRUTURA/mapeamento_logins_vs_nomes.txt")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
