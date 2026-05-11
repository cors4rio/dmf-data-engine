import pyodbc
import sys
import csv

def check_dates():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        print("--- Amostra de datas na ctlancto onde data_lan é 01/2026 ---")
        
        # O banco Domínio geralmente tem data_lan (data do lançamento contábil)
        # origin_lan (origem) e as vezes dorig_lan (data original do documento)
        
        query = """
            SELECT TOP 10
                codi_emp,
                nume_lan,
                data_lan,
                dorig_lan,
                vlor_lan,
                orig_lan
            FROM 
                bethadba.ctlancto
            WHERE 
                data_lan >= '2026-01-01' 
                AND data_lan <= '2026-01-31'
                AND orig_lan IN (1, 5)
        """
        
        cursor.execute(query)
        res = cursor.fetchall()
        
        if not res:
            print("Nenhum registro encontrado na amostra.")
        else:
            print(f"{'Cod_Emp':<8} | {'Num_Lan':<8} | {'Data_Lan':<12} | {'Data_Orig':<12} | {'Valor':<10} | {'Orig_Lan':<8}")
            print("-" * 70)
            for r in res:
                dorig = r[3].strftime('%Y-%m-%d') if r[3] else 'NULL'
                dlan = r[2].strftime('%Y-%m-%d') if r[2] else 'NULL'
                print(f"{r[0]:<8} | {r[1]:<8} | {dlan:<12} | {dorig:<12} | {r[4]:<10} | {r[5]:<8}")

        print("\n--- Verificando layout da tabela CTEXTRATO_BANCARIO_LANCAMENTO ---")
        cursor.execute("SELECT TOP 1 * FROM bethadba.ctextrato_bancario_lancamento")
        cols = [column[0] for column in cursor.description]
        print(f"Colunas do Extrato: {cols}")
        
    except Exception as e:
        print(f"Erro Fatal: {e}", file=sys.stderr)

if __name__ == '__main__':
    check_dates()
