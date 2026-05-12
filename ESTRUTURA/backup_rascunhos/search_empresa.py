import json

def search_empresas_table():
    with open('dominio_columns.json', 'r', encoding='utf-8') as f:
        tables = json.load(f)
        
    for t in tables:
        name = t['name'].lower()
        if 'empresa' in name and 'ge' in name:
            print(f"Encontrada: {t['name']}")
        if name == 'bethadba.geempresas' or name == 'geempresas':
            print(f"Encontrada exata: {t['name']}")

if __name__ == '__main__':
    search_empresas_table()
