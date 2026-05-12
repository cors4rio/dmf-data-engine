import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # Lista de nomes da imagem (normalizados para busca)
        nomes_alvo = [
            "ALINE", "BRENO", "CARINA", "CAMILE", "CLAUDINEIDE", "ERIKA", "ERON", 
            "ERVELE", "EZEQUIEL", "FERNANDA", "GEORGE", "GEOVANA", "GIULIA", 
            "KEZIA", "RAFAELA", "MARIA ANACISA", "MARTA", "NATHALIA", "GERENTE.FISCAL", 
            "COORDENADOR.DP", "SONILDES", "TAIS", "VITOR", "EDUARDO", "MARIANA"
        ]
        
        print(f"Buscando {len(nomes_alvo)} nomes na tabela usConfUsuario...")
        
        # Vamos buscar tudo e filtrar no Python para maior flexibilidade (fuzzy match)
        cursor.execute("SELECT user_id, NOME FROM bethadba.usConfUsuario")
        all_users = cursor.fetchall()
        
        mapeamento = {}
        for nome_busca in nomes_alvo:
            matches = []
            for u_id, u_nome in all_users:
                u_nome_str = str(u_nome).upper()
                if nome_busca in u_nome_str:
                    matches.append((u_id, u_nome))
            mapeamento[nome_busca] = matches
            
        with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\mapeamento_colaboradores_fiscal.txt', 'w', encoding='utf-8') as f:
            f.write("--- MAPEAMENTO DE COLABORADORES FISCAL ---\n\n")
            for nome, matches in mapeamento.items():
                if matches:
                    f.write(f"BUSCA: {nome}\n")
                    for mid, mnome in matches:
                        f.write(f"  -> MATCH: {mnome} (ID: {mid})\n")
                else:
                    f.write(f"BUSCA: {nome} -> !!! NÃO ENCONTRADO !!!\n")
                f.write("-" * 30 + "\n")
        
        print("Mapeamento concluído em ESTRUTURA/mapeamento_colaboradores_fiscal.txt")
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
