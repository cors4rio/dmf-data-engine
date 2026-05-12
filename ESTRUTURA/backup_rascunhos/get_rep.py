import sys

try:
    with open('analisys_txt.log', 'r', encoding='utf-16le') as f:
        lines = f.readlines()
        
    res = []
    
    # 3 lines of diagnostic
    diag_start = next((i for i, line in enumerate(lines) if 'DIAGNÓSTICO FINAL' in line), None)
    if diag_start is not None:
        res.append(lines[diag_start+1].strip())
        res.append(lines[diag_start+2].strip())
        res.append(lines[diag_start+3].strip())
    
    # divergentes
    div = next((i for i, line in enumerate(lines) if 'Lista de Divergentes' in line), None)
    if div is not None:
        res.append('\nAlguns Divergentes (Valor TXT vs Master):')
        for l in lines[div+1:div+8]:
            res.append(l.strip())
            
    # faltantes
    falt = next((i for i, line in enumerate(lines) if 'Top 20 Faltantes' in line), None)
    if falt is not None:
        res.append('\nTop 10 Faltantes (TXT tem, Master NÃO tem):')
        for l in lines[falt+1:falt+11]:
            res.append(l.strip())
            
    with open('rep.txt', 'w', encoding='utf-8') as out:
        out.write('\n'.join(res))
        
    print("report saved")
except Exception as e:
    print(f"Error: {e}")
