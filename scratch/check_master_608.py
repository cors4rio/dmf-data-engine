import openpyxl

def check_608():
    file_path = "CONTROLE_DE_HORAS_DMF.xlsm"
    print(f"Lendo {file_path}...")
    try:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        ws = wb["04.2026"]
        for row in ws.iter_rows(min_row=10):
            # Coluna H (índice 7) é o código da empresa
            if row[7].value == 608:
                print(f"Empresa: {row[8].value}")
                # Coluna Q (índice 16) é o DP
                print(f"Valor atual DP (Coluna Q): {row[16].value}")
                return
        print("Empresa 608 não encontrada na planilha 04.2026.")
    except Exception as e:
        print(f"Erro ao ler planilha: {e}")

if __name__ == "__main__":
    check_608()
