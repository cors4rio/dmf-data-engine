import xlrd
import os

def buscar_1680_no_xls():
    file_path = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\ESTRUTURA\backup_rascunhos\Controle de Empregados 042226 (CAROL).xls"
    
    if not os.path.exists(file_path):
        print(f"ERRO: Arquivo não encontrado em {file_path}")
        return

    print(f"Abrindo arquivo: {file_path}")
    try:
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_index(0)
        
        print(f"Planilha lida. Total de linhas: {sheet.nrows}")
        
        encontrado = False
        for row_idx in range(sheet.nrows):
            row = sheet.row_values(row_idx)
            # Converte tudo para string para facilitar a busca
            row_str = [str(cell) for cell in row]
            
            # Procura por '1680' em qualquer célula da linha
            if any('1680' in s for s in row_str):
                print(f"\n[LINHA {row_idx}] Registro encontrado:")
                print(f"  Conteúdo: {row}")
                encontrado = True
        
        if not encontrado:
            print("\nCliente 1680 NÃO encontrado nesta planilha.")
            
    except Exception as e:
        print(f"Erro ao ler .xls: {e}")

if __name__ == "__main__":
    buscar_1680_no_xls()
