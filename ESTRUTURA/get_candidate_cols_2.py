import pyodbc

def main():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        candidates = ['GEATENDIMENTOACOES', 'GEANALYTICS', 'GEATENDIMENTOLOG', 'GEATENDIMENTOWEBSOCKET_ONVIO_ROTA_LANCAMENTOS_CONTABEIS']
        
        with open('ESTRUTURA/candidate_columns_2.txt', 'w', encoding='utf-8') as f:
            for t in candidates:
                f.write(f"\n--- TABELA: {t} ---\n")
                try:
                    cursor.execute(f"SELECT column_name, domain_id FROM SYS.SYSCOLUMN WHERE table_id = (SELECT table_id FROM SYS.SYSTABLE WHERE table_name = '{t}' AND creator = (SELECT user_id FROM SYS.SYSUSER WHERE user_name = 'bethadba'))")
                    cols = cursor.fetchall()
                    if not cols:
                        f.write("  (Nenhuma coluna encontrada ou erro)\n")
                    for c in cols:
                        f.write(f"  {c[0]}\n")
                    
                    cursor.execute(f"SELECT TOP 3 * FROM bethadba.{t}")
                    sample_cols = [desc[0] for desc in cursor.description]
                    f.write(" | ".join(sample_cols) + "\n")
                    for row in cursor.fetchall():
                        f.write(" | ".join([str(x) for x in row]) + "\n")
                except Exception as ex:
                    f.write(f"  Erro: {ex}\n")
                    
        print("Salvo em ESTRUTURA/candidate_columns_2.txt")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
