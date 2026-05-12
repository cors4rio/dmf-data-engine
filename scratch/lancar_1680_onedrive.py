from engine.master_writer import MasterWriter
import openpyxl
import logging

def lancar_1680_onedrive():
    master_path = r"C:\Users\DMF-AUTOMACAO\OneDrive - DMF\DMF - Documentos\Administrativo\CONTROLE DE HORAS DMF.xlsx"
    cliente_cod = "1680"
    ativos = 24
    
    # Cálculo conforme modulos/dp.py
    horas = (ativos * 0.33) + 1.5
    valor_excel = horas / 24.0
    
    print(f"Lançando Cliente {cliente_cod} na Planilha do OneDrive: {master_path}")
    
    writer = MasterWriter(master_path)
    if writer.carregar():
        # Forçar a aba 04.2026
        target_sheet = "04.2026"
        if target_sheet in writer.wb.sheetnames:
            writer.ws = writer.wb[target_sheet]
            writer._mapear_linhas()
            
            print(f"Aba '{target_sheet}' selecionada. Preenchendo...")
            writer.preencher_dp(cliente_cod, valor_excel)
            writer.recalcular_totais()
            
            if writer.salvar():
                print(f"SUCESSO: Cliente 1680 lançado no arquivo do OneDrive!")
            else:
                print("ERRO: Falha ao salvar (pode estar aberto).")
        else:
            print(f"ERRO: Aba {target_sheet} não encontrada. Abas: {writer.wb.sheetnames}")

if __name__ == "__main__":
    lancar_1680_onedrive()
