import json

def main():
    try:
        with open('c:/Users/DMF-AUTOMACAO/Documents/PROJETOS/N8N automacao/ESTRUTURA/dominio_columns.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        for table in data:
            if table['name'].lower() == 'usconfusuario':
                print(f"Tabela: {table['name']}")
                print(f"Colunas: {[col['name'] for col in table['columns']]}")
                break
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    main()
