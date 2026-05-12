from engine.database import db
import csv

def dump_833():
    print("=== DUMP COMPLETO EMPRESA 833 ===")
    
    query = """
        SELECT 
            f.i_empregados,
            f.nome,
            f.admissao,
            r.demissao,
            r.motivo
        FROM bethadba.foempregados f
        LEFT JOIN bethadba.forescisoes r ON f.codi_emp = r.codi_emp AND f.i_empregados = r.i_empregados
        WHERE f.codi_emp = 833
        ORDER BY f.i_empregados
    """
    
    dados = db.fetch_all(query)
    if dados:
        output_path = "scratch/dump_833_detalhado.csv"
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=dados[0].keys())
            writer.writeheader()
            writer.writerows(dados)
        print(f"Dump salvo em: {output_path}")
        
        # Imprimir alguns para análise
        print("\nAnálise rápida (ID, Nome, Adm, Dem):")
        for r in dados:
            status = "ATIVO" if not r['demissao'] else f"DEM ({r['demissao']})"
            print(f"  {r['i_empregados']:>3} | {r['nome'][:30]:<30} | {r['admissao']} | {status}")

if __name__ == "__main__":
    dump_833()
