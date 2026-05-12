import re

def main():
    with open('ESTRUTURA/time_columns.txt', 'r', encoding='utf-8') as f:
        content = f.read()
        
    blocks = re.split(r'\n--- ', content)
    
    with open('ESTRUTURA/time_columns_filtered.txt', 'w', encoding='utf-8') as f:
        for b in blocks:
            if '(0 rows)' in b or '(Erro' in b:
                continue
            lines = b.split('\n')
            name_part = lines[0]
            if name_part.startswith('GE') or name_part.startswith('HR') or name_part.startswith('PC') or name_part.startswith('AD') or 'ATENDIMENTO' in name_part:
                f.write(f"--- {b}\n")
    print("Salvo em ESTRUTURA/time_columns_filtered.txt")

if __name__ == "__main__":
    main()
