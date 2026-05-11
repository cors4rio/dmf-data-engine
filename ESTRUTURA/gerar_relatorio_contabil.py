import pyodbc
import sys
import csv

def extract_accounting_entries_report():
    conn_str = 'DSN=Contabil;UID=<USER_NO_ENV>;PWD=<SENHA_NO_ENV>'
    try:
        print("Conectando ao banco de dados...")
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        query = """
            SELECT 
                l.codi_emp as Codigo_Cliente,
                SUM(CASE WHEN l.orig_lan = 1 THEN 1 ELSE 0 END) as Lancamentos_Normal,
                SUM(CASE WHEN l.orig_lan = 39 THEN 1 ELSE 0 END) as Lancamentos_Extrato_Bancario,
                COUNT(*) as Total_Lancamentos_Gerais
            FROM 
                bethadba.ctlancto l
            WHERE 
                l.data_lan >= '2025-12-01' 
                AND l.data_lan <= '2025-12-31'
            GROUP BY 
                l.codi_emp
            HAVING 
                SUM(CASE WHEN l.orig_lan IN (1, 39) THEN 1 ELSE 0 END) > 0
            ORDER BY 
                l.codi_emp
        """
        
        print("Executando consulta. Isso pode demorar um pouco...")
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("Nenhum dado encontrado para os filtros informados (12/2025).")
            return
            
        print(f"\nSucesso! {len(results)} empresas encontradas com lançamentos no período.")
        
        output_file = 'Relatorio_Lancamentos_Contabeis_12_2025.csv'
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(['Codigo_Cliente', 'Lancamentos_Normal', 'Lancamentos_Extrato_Bancario', 'Total_Lancamentos_Gerais'])
            
            for row in results:
                writer.writerow([row[0], row[1], row[2], row[3]])
                
        print(f"Relatório exportado com sucesso para: {output_file}")
        
    except Exception as e:
        print(f"Erro Fatal: {e}", file=sys.stderr)

if __name__ == '__main__':
    extract_accounting_entries_report()
