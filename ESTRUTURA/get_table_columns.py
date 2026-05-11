import json

def get_table_info(table_names_to_find):
    with open('dominio_columns.json', 'r', encoding='utf-8') as f:
        tables = json.load(f)
        
    for t in tables:
        name = t['name'].lower()
        if name in table_names_to_find:
            print(f"\n--- TABELA: {t['name']} ---")
            for col in t['columns']:
                print(f"  {col['name']} ({col['type']})")

if __name__ == '__main__':
    get_table_info(['ctlancto', 'geempresas', 'ctextrato_bancario_lancamento'])
