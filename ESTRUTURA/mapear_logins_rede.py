import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Vamos tentar cruzar auusuarios (login) com usConfUsuario (nome/ID)
        # Assumindo que auusuarios se relaciona com usConfUsuario via i_usuario ou similar
        # Mas vamos fazer um match manual de teste primeiro
        
        print("Buscando logins em auusuarios...")
        cursor.execute("SELECT usuario, i_usuario FROM bethadba.auusuarios")
        all_au = cursor.fetchall()
        
        print(f"Total auusuarios: {len(all_au)}")
        
        with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\mapeamento_final_logins.txt', 'w', encoding='utf-8') as f:
            f.write(f"{'LOGIN':<20} | {'I_USUARIO':<10}\n")
            f.write("-" * 40 + "\n")
            for login, i_usu in all_au:
                f.write(f"{str(login):<20} | {str(i_usu):<10}\n")

        print("Mapeamento final salvo em ESTRUTURA/mapeamento_final_logins.txt")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
