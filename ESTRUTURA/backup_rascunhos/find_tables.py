import json

def explore_tables():
    with open('dominio_columns.json', 'r', encoding='utf-8') as f:
        tables = json.load(f)
        
    print("--- Tabelas CT (Contabil) relacionadas a lancamentos ---")
    for t in tables:
        name = t['name'].lower()
        if name.startswith('ct') and 'lanc' in name:
            print(name)
            
    print("\n--- Outras tabelas CT importantes ---")
    for t in tables:
        name = t['name'].lower()
        if name in ('ctlancamentos', 'ctlancamento', 'ctpartidas', 'ctpartida', 'cthistoricos', 'ctempresas', 'geempresas', 'bethadba.geempresas', 'bethadba.ctlancamentos'):
            print(name)

if __name__ == '__main__':
    explore_tables()
