import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Variantes de grafia para os nomes faltantes
        variantes = {
            "GIULIA": ["GIU", "JULIA"],
            "KEZIA": ["KES", "KEZ", "KEZIA", "RAFAELA"],
            "NATHALIA": ["NATALIA", "NATY", "NATH"]
        }
        
        cursor.execute("SELECT user_id, NOME, SITUACAO FROM bethadba.usConfUsuario")
        all_users = cursor.fetchall()
        
        with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\mapeamento_faltantes_fuzzy.txt', 'w', encoding='utf-8') as f:
            f.write("--- BUSCA FUZZY PARA COLABORADORES FALTANTES ---\n\n")
            for alvo, vars in variantes.items():
                f.write(f"BUSCA: {alvo} (Variantes: {vars})\n")
                found = False
                for v in vars:
                    for u_id, u_nome, u_sit in all_users:
                        u_nome_str = str(u_nome).upper()
                        if v in u_nome_str:
                            f.write(f"  -> MATCH [{v}]: {u_nome} (ID: {u_id}) [SIT: {u_sit}]\n")
                            found = True
                if not found:
                    f.write(f"  -> !!! NADA ENCONTRADO PARA {alvo} !!!\n")
                f.write("-" * 30 + "\n")
                
            f.write("\n\n--- USUÁRIOS ATIVOS RECENTEMENTE (Últimos 100) ---\n")
            # Vamos tentar inferir pela atividade recente se possível, mas aqui só temos os dados de cadastro.
            # Se SITUACAO for 'A' (Ativo), é um bom sinal.
            for u_id, u_nome, u_sit in all_users:
                if u_sit == 'A':
                    f.write(f"ID: {u_id} | NOME: {u_nome}\n")

        print("Busca fuzzy concluída em ESTRUTURA/mapeamento_faltantes_fuzzy.txt")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
