from engine.master_writer import MasterWriter
import openpyxl
import logging

def lancar_1680_oficial():
    master_path = r"c:\Users\DMF-AUTOMACAO\Documents\PROJETOS\N8N automacao\CONTROLE DE HORAS DMF.xlsx"
    cliente_cod = "1680"
    ativos = 24
    
    # Cálculo conforme modulos/dp.py
    horas = (ativos * 0.33) + 1.5
    valor_excel = horas / 24.0
    
    print(f"Lançando Cliente {cliente_cod}: {ativos} ativos -> {horas:.2f} horas na Master Oficial.")
    
    writer = MasterWriter(master_path)
    if writer.carregar():
        # Listar abas para debug
        print(f"Abas encontradas: {writer.wb.sheetnames}")
        
        target_sheet = None
        for name in ["04.2026", "042026", "Abril 2026"]:
            if name in writer.wb.sheetnames:
                target_sheet = name
                break
        
        if target_sheet:
            writer.ws = writer.wb[target_sheet]
            writer._mapear_linhas()
            
            print(f"Aba '{target_sheet}' selecionada. Preenchendo...")
            writer.preencher_dp(cliente_cod, valor_excel)
            writer.recalcular_totais()
            
            if writer.salvar():
                print(f"SUCESSO: Cliente 1680 lançado na aba {target_sheet}!")
            else:
                print("ERRO: Falha ao salvar.")
        else:
            print("ERRO: Aba de Abril não encontrada.")

if __name__ == "__main__":
    lancar_1680_oficial()
