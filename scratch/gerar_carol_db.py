from engine.database import db
import csv

def gerar_carol_db():
    print("=== GERANDO DADOS 'CAROL' VIA BANCO DE DADOS (CSV) ===")
    
    query = """
        SELECT 
            e.codi_emp,
            e.nome_emp,
            COUNT(f.i_empregados) as total
        FROM bethadba.geempre e
        JOIN bethadba.foempregados f ON e.codi_emp = f.i_empresas
        WHERE f.situacao = 1
        GROUP BY e.codi_emp, e.nome_emp
        ORDER BY e.codi_emp
    """
    
    try:
        dados = db.fetch_all(query)
        if dados:
            output_path = "scratch/relatorio_carol_db.csv"
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=dados[0].keys())
                writer.writeheader()
                writer.writerows(dados)
            
            print(f"Relatório gerado em: {output_path}")
            print("\nPrimeiros resultados:")
            for r in dados[:10]:
                print(f"Empresa {r['codi_emp']}: {r['total']} colaboradores ({r['nome_emp'][:30]})")
        else:
            print("Nenhum dado retornado.")
            
    except Exception as e:
        print(f"Erro: {e}")
        # Se falhar, vamos tentar ver se as tabelas existem mesmo
        try:
            db.fetch_all("SELECT FIRST 1 * FROM bethadba.foempregados")
            print("Tabela foempregados acessível.")
        except:
            print("Tabela foempregados NÃO acessível.")

if __name__ == "__main__":
    gerar_carol_db()
