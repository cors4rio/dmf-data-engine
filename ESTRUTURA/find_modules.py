import json

def find_module_tables():
    with open('dominio_columns.json', 'r', encoding='utf-8') as f:
        tables = json.load(f)
        
    print("--- Tabelas FISCAIS (EF) para REGIME ---")
    regime_tables = []
    for t in tables:
        name = t['name'].lower()
        if name in ['effederal', 'efempresas', 'efparametro', 'efparametros', 'bethadba.efempresas', 'bethadba.effederal']:
            print(f"Tabela: {t['name']}")
            for col in t['columns'][:10]: # Print limit to avoid flood
                if col['name']:
                    if 'regime' in col['name'].lower() or 'simples' in col['name'].lower() or 'lucro' in col['name'].lower() or 'apuracao' in col['name'].lower():
                        print(f"  Col: {col['name']} ({col['type']})")
            
    print("\n--- Tabelas FOLHA (FO) para TEM FOLHA? ---")
    for t in tables:
        name = t['name'].lower()
        if name in ['focalculo', 'bethadba.focalculo', 'fopagamento', 'bethadba.fopagamento']:
            print(f"Tabela: {t['name']}")
            for col in t['columns']:
                if col['name'] and ('comp' in col['name'].lower() or 'data' in col['name'].lower() or 'codi_emp' in col['name'].lower()):
                    print(f"  Col: {col['name']} ({col['type']})")
                    
    print("\n--- Tabelas FISCAIS (EF) para FATURAMENTO ---")
    for t in tables:
        name = t['name'].lower()
        if name in ['efacumuladores', 'efacumulador', 'bethadba.efacumuladores', 'efnotas_saidas', 'efsaidas', 'bethadba.efsaidas']:
            print(f"Tabela: {t['name']}")

if __name__ == '__main__':
    find_module_tables()
