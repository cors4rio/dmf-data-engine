import pyodbc
import sys

def refine_queries():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        # 1. FOLHA: Procurando uma coluna de demissão ou status para saber se tem folha
        print("--- Colunas detalhadas FOEMPREGADOS ---")
        cursor.execute("SELECT TOP 1 * FROM bethadba.foempregados")
        cols = [col[0].lower() for col in cursor.description]
        demissao_cols = [c for c in cols if 'demi' in c or 'rescisao' in c or 'sit' in c or 'afast' in c]
        print(f"Colunas de rescisão/situacao: {demissao_cols}")
        
        # 2. FATURAMENTO: Validando EFNOTAS_SAIDAS ou EFFATURAMENTO se existirem
        print("\n--- Analisando Faturamento (efsaidas ou efnotas_saidas) ---")
        try:
            cursor.execute("SELECT TOP 1 * FROM bethadba.efsaidas")
            fat_cols = [col[0].lower() for col in cursor.description]
            vlr_cols = [c for c in fat_cols if 'vlor' in c or 'valor' in c or 'cont' in c]
            data_cols = [c for c in fat_cols if 'data' in c or 'emis' in c]
            print(f"EFSAIDAS - Colunas valor: {vlr_cols}")
            print(f"EFSAIDAS - Colunas data: {data_cols}")
        except Exception as e:
            print(f"Tabela efsaidas nao acessivel: {e}")
            
        # 3. REGIME: Validando EFPARAMETROS
        print("\n--- Analisando Regime (efparametro) ---")
        try:
            cursor.execute("SELECT TOP 1 * FROM bethadba.efparametro")
            reg_cols = [col[0].lower() for col in cursor.description]
            # Quais colunas indicam o regime?
            reg_keys = [c for c in reg_cols if 'simples' in c or 'lucro' in c or 'regime' in c or 'apuracao' in c]
            print(f"EFPARAMETRO - Colunas de Regime: {reg_keys}")
            
            # Puxar uma amostra para ver como é preenchido
            if reg_keys:
                query_reg = f"SELECT TOP 3 codi_emp, {', '.join(reg_keys[:3])} FROM bethadba.efparametro"
                cursor.execute(query_reg)
                print(f"Amostra Regime: {cursor.fetchall()}")
        except Exception as e:
            pass

    except Exception as e:
        print(f"Erro Fatal: {e}", file=sys.stderr)

if __name__ == '__main__':
    refine_queries()
