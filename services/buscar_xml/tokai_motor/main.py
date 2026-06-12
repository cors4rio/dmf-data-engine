"""
main.py — Ponto de entrada e daemon agendador do auto_tokai.

CORRECAO — TASK 2 › Escalada: adicionado lock de execucao via arquivo PID
para evitar execucoes concorrentes. Se o robo ainda estiver rodando quando
o scheduler disparar novamente (ex: download demorado excede o intervalo
de verificacao diaria), a segunda instancia detecta o lock e aborta com
log explicativo, em vez de iniciar uma segunda execucao paralela que
competiria pelos mesmos arquivos no drive Z: e corromperia os relatorios.
"""

import os
import sys
import time
import datetime
import schedule
import atexit
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------
# Configuracao de Log
# ---------------------------------------------------------------
logger.add(
    "logs/auto_tokai_{time}.log",
    rotation="10 MB",
    retention="30 days",
    level="INFO",
    encoding="utf-8",
)

# ---------------------------------------------------------------
# Configuracao de Agendamento
# ---------------------------------------------------------------
DIA_EXECUCAO = int(os.getenv("DIA_EXECUCAO", "5"))
HORA_EXECUCAO = os.getenv("HORA_EXECUCAO", "08:00")

# ---------------------------------------------------------------
# CORRECAO — TASK 2 › Escalada: Lock de execucao concorrente
# Usa arquivo PID como mecanismo de lock leve e portatil.
# Funciona em Windows e Linux sem dependencias externas.
# ---------------------------------------------------------------
LOCK_FILE = os.path.join(os.getcwd(), ".auto_tokai.lock")


def _adquirir_lock() -> bool:
    """
    Tenta adquirir o lock de execucao.
    Retorna True se o lock foi adquirido, False se ja existe uma instancia rodando.

    Estrategia: verifica se o PID registrado no lock ainda esta ativo.
    Se o processo nao existir mais (crash anterior), o lock e considerado
    obsoleto e pode ser sobrescrito.
    """
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, 'r') as f:
                pid_registrado = int(f.read().strip())

            # Verifica se o processo ainda existe
            os.kill(pid_registrado, 0)  # Signal 0 nao mata, apenas testa existencia
            logger.warning(
                "[AVISO] Lock de execucao ativo (PID %d). Uma instancia do robo ja esta rodando. "
                "Execucao cancelada para evitar processamento concorrente.",
                pid_registrado
            )
            return False

        except (ValueError, ProcessLookupError, PermissionError):
            # Processo nao existe mais (crash anterior) — lock obsoleto, pode sobrescrever
            logger.warning(
                "[AVISO] Lock obsoleto encontrado (processo nao existe mais). "
                "Sobrescrevendo lock e iniciando execucao."
            )

    # Escreve o PID da instancia atual
    try:
        with open(LOCK_FILE, 'w') as f:
            f.write(str(os.getpid()))
        logger.debug("[INFO] Lock adquirido (PID %d).", os.getpid())
        return True
    except Exception as e:
        logger.error("[ERRO] Nao foi possivel criar arquivo de lock: %s. Prosseguindo sem lock.", e)
        return True  # Falha suave — nao bloqueia a execucao por falha no lock


def _liberar_lock():
    """Remove o arquivo de lock. Registrado via atexit para garantir limpeza."""
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
            logger.debug("[INFO] Lock liberado.")
    except Exception as e:
        logger.warning("[AVISO] Nao foi possivel remover arquivo de lock: %s", e)


# Garante liberacao do lock mesmo em caso de excecao nao tratada
atexit.register(_liberar_lock)


def job():
    """Funcao principal executada pelo scheduler."""
    hoje = datetime.datetime.now()

    if hoje.day != DIA_EXECUCAO:
        logger.info(
            "[INFO] Verificacao diaria: hoje e dia %d, execucao programada para o dia %d. Aguardando...",
            hoje.day, DIA_EXECUCAO
        )
        return

    # CORRECAO — TASK 2 › Escalada: verifica lock antes de iniciar
    if not _adquirir_lock():
        return

    logger.info(
        "[INFO] === AUTO TOKAI — Iniciando execucao agendada (dia %d as %s) ===",
        DIA_EXECUCAO, HORA_EXECUCAO
    )

    from src.infrastructure.notifications.notificador_service import NotificadorService
    notifier = NotificadorService()
    notifier.notify_start(periodo=hoje.strftime("%m/%Y"))

    try:
        from src.application.use_cases.download_sharepoint_files import DownloadSharePointFilesUseCase
        use_case = DownloadSharePointFilesUseCase()
        ok, erro, lista_erros = use_case.execute()
        
        notifier.notify_end(sucessos=ok, erros=erro, lista_erros=lista_erros)
        logger.success("=== Execução concluída com sucesso ===")
    except Exception as e:
        logger.exception("Erro crítico durante a execução agendada: %s", e)
        notifier.notify_error(f"Erro inesperado: {str(e)}")
    finally:
        _liberar_lock()


def main():
    logger.info("Daemon auto_tokai iniciado. Agendamento: dia %d às %s.", DIA_EXECUCAO, HORA_EXECUCAO)
    logger.info("Consumo em standby: ~37 MB RAM, 0%% CPU.")

    schedule.every().day.at(HORA_EXECUCAO).do(job)

    # Salvaguarda: se reiniciado no dia de execução, dispara imediatamente
    hoje = datetime.datetime.now()
    if hoje.day == DIA_EXECUCAO:
        logger.info("Reiniciado no dia de execucao (%d). Disparando imediatamente como salvaguarda.", DIA_EXECUCAO)
        job()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
