import os
import sys
from loguru import logger
from dotenv import load_dotenv

# Adiciona a raiz do projeto ao path para permitir importacoes da src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.application.use_cases.download_sharepoint_files import DownloadSharePointFilesUseCase

def main():
    # Carrega configuracoes do .env
    load_dotenv()
    
    # Configura log para a execucao manual
    logger.add("logs/manual_exec_{time}.log", rotation="1 MB", retention="10 days", level="INFO")
    
    logger.info("=== INICIANDO EXECUCAO MANUAL FORCADA ===")
    logger.info("Ignorando agendamento e checagem de dia do mes.")
    
    try:
        use_case = DownloadSharePointFilesUseCase()
        use_case.execute()
        logger.success("=== EXECUCAO MANUAL CONCLUIDA COM SUCESSO ===")
    except Exception as e:
        logger.exception(f"Erro critico durante a execucao manual: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
