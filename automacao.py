import os
import logging
from datetime import datetime

from engine.database import db
from engine.master_writer import MasterWriter
from modulos.fiscal import extrair_e_preencher_fiscal
from modulos.dp import extrair_e_preencher_dp
from modulos.contabil_integrador import extrair_e_preencher_contabil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def gerar_relatorio_md(status_fiscal, status_dp, status_contabil, status_salvamento):
    """Gera um log amigável em Markdown sobre o que rodou com sucesso."""
    md_content = f"# Relatório de Execução Local\n"
    md_content += f"**Data/Hora:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
    
    md_content += "## Status dos Módulos\n"
    md_content += f"- **Fiscal (Integração DB):** {'✅ Sucesso' if status_fiscal else '❌ Falha ou Sem Dados'}\n"
    md_content += f"- **Setor Pessoal/DP (DB + Excel):** {'✅ Sucesso' if status_dp else '❌ Falha ou Sem Dados'}\n"
    md_content += f"- **Contábil (Excel Integrador):** {'✅ Sucesso' if status_contabil else '❌ Falha ou Sem Dados'}\n"
    
    md_content += "\n## Status Final\n"
    md_content += f"**Escrita na Planilha Master:** {'✅ Salvo com sucesso' if status_salvamento else '❌ Erro crítico ao salvar'}\n\n"
    
    md_content += "---\n*Gerado automaticamente pelo Motor Local DMF.*"
    
    with open("log_execucao.md", "w", encoding="utf-8") as f:
        f.write(md_content)
    logging.info("Relatório de execução (log_execucao.md) gerado na raiz.")

def main():
    print("="*50)
    print(" MOTOR DE AUTOMAÇÃO DMF - MODO LOCAL E LINEAR")
    print("="*50)
    
    # Busca a Master (suporta .xlsx ou .xlsm)
    if os.path.exists("CONTROLE DE HORAS DMF.xlsm"):
        master_file = "CONTROLE DE HORAS DMF.xlsm"
    elif os.path.exists("CONTROLE DE HORAS DMF.xlsx"):
        master_file = "CONTROLE DE HORAS DMF.xlsx"
    else:
        logging.error("CRÍTICO: Planilha Master não encontrada no diretório raiz.")
        return
        
    writer = MasterWriter(master_file)
    if not writer.carregar():
        return
        
    # Variáveis de Período (Pode ser passado por argumento depois)
    # Por padrão, usa o mês atual para extração do banco, como teste.
    # Idealmente, solicitará ao usuário, ou definiremos fixo para teste:
    data_inicio = '2026-03-01'
    data_fim = '2026-03-31'
    
    logging.info(f"Período de Extração Banco: {data_inicio} até {data_fim}")
    
    # === EXECUÇÃO LINEAR E RESILIENTE ===
    
    status_fiscal = False
    try:
        status_fiscal = extrair_e_preencher_fiscal(writer, data_inicio, data_fim)
    except Exception as e:
        logging.error(f"Erro inesperado no módulo Fiscal: {e}")
        
    status_dp = False
    try:
        status_dp = extrair_e_preencher_dp(writer, data_inicio, data_fim)
    except Exception as e:
        logging.error(f"Erro inesperado no módulo DP: {e}")
        
    status_contabil = False
    try:
        status_contabil = extrair_e_preencher_contabil(writer)
    except Exception as e:
        logging.error(f"Erro inesperado no módulo Contábil: {e}")
        
    # Fim das extrações. Fechar banco.
    db.disconnect()
    
    # Recalcula as somas totais do Excel e salva
    writer.recalcular_totais()
    status_salvamento = writer.salvar()
    
    # Gera relatório MD
    gerar_relatorio_md(status_fiscal, status_dp, status_contabil, status_salvamento)
    
    print("\nExecução Concluída! Verifique o arquivo log_execucao.md.")

if __name__ == "__main__":
    main()
