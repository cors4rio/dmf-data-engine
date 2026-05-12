import json

def search_tables():
    with open('dominio_columns.json', 'r', encoding='utf-8') as f:
        tables = json.load(f)
        
    print("--- Procura Tabelas de Folha ---")
    folha_tables = []
    for t in tables:
        name = t['name'].lower()
        if name.startswith('fo') and ('calc' in name or 'pagto' in name or 'pagamento' in name or 'empregado' in name or 'resumo' in name):
            print(t['name'])
            folha_tables.append(t['name'])

    print(f"\nTotal Folha encontradas: {len(folha_tables)}")
    
    print("\n--- Procura Tabelas de Faturamento ---")
    fat_tables = []
    for t in tables:
        name = t['name'].lower()
        if 'faturam' in name or name.startswith('ef_') or name.startswith('effatur'):
            print(t['name'])
            fat_tables.append(t['name'])
            
    print(f"\nTotal Faturamento encontradas: {len(fat_tables)}")

if __name__ == '__main__':
    search_tables()
