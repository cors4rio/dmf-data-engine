import sys

with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\calculos_encontrados_dp_032026.md', 'r', encoding='utf-8') as f:
    for line in f:
        if '1480' in line or '171' in line or 'RIGEL' in line:
            print("Found in calculos:", line.strip())

with open(r'c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\relatorio_dp_032026.md', 'r', encoding='utf-8') as f:
    for line in f:
        if '1480' in line or '171' in line or 'RIGEL' in line:
            print("Found in relatorio:", line.strip())

