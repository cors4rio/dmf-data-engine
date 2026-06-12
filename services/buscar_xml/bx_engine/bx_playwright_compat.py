"""
bx_engine/bx_playwright_compat.py — Compatibilidade Playwright no exe (PyInstaller).

Dois problemas que só aparecem no .exe (não em dev) e quebram NF-e/NFCe/SPED:

1) NotImplementedError ao lançar o Chromium:
   O main.py da Central seta WindowsSelectorEventLoopPolicy globalmente (necessário
   para o pywebview/winforms). O Playwright cria subprocessos (node.exe) que o
   SelectorEventLoop NÃO suporta no Windows (_make_subprocess_transport →
   NotImplementedError). Só trocar a POLICY para Proactor resolve (set_event_loop
   manual não basta, pois sync_playwright lê a policy). Trocamos durante a operação
   e restauramos no fim. O pywebview usa message loop nativo (winforms), não asyncio,
   então não é afetado. Mesma correção já validada no TFF (tf_portal).

2) chromium.launch() trava / Executable doesn't exist:
   No exe o Chromium é empacotado em _internal/ms-playwright (ver dmf_engine.spec).
   Sem PLAYWRIGHT_BROWSERS_PATH apontando para lá, o Playwright procura num diretório
   vazio e trava. Apontamos para a pasta empacotada (ou ms-playwright do usuário em dev).

Uso:
    from bx_playwright_compat import configurar_browsers_path, policy_proactor

    configurar_browsers_path()
    with policy_proactor():
        with sync_playwright() as p:
            ...

    # async (sped):
    configurar_browsers_path()
    with policy_proactor():
        asyncio.run(minha_corrotina())
"""

import os
import sys
import logging
from contextlib import contextmanager

log = logging.getLogger("BuscarXML.PlaywrightCompat")

_subprocess_patched = False

# PIDs dos processos-filho que NÓS criamos (via subprocess). Usado pelo
# cancelamento para matar só a nossa árvore (Playwright→node→chrome, 7z),
# sem tocar em processos alheios (Chrome pessoal do usuário, etc.).
import threading as _threading
_pids_filhos = set()
_pids_lock = _threading.Lock()
# Popen original (sem o patch que registra PID) — usado pelo próprio taskkill do
# cancelamento, p/ não re-registrar a si mesmo no set.
_Popen_real = None


def matar_processos_filhos():
    """Mata imediatamente os processos-filho que criamos e suas árvores.

    Usado no cancelamento para encerrar NA HORA o navegador (chrome-headless-shell
    via node do Playwright) e o 7-Zip em andamento, em vez de esperar a operação
    longa terminar. Cirúrgico: só mata PIDs que registramos + descendentes (/T).
    """
    if sys.platform != "win32":
        return
    import subprocess
    with _pids_lock:
        pids = list(_pids_filhos)
        _pids_filhos.clear()
    Popen = _Popen_real or subprocess.Popen
    CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    for pid in pids:
        try:
            # /T mata a árvore (node → chrome); /F força. Usa o Popen original
            # para o taskkill não se registrar no set de PIDs.
            proc = Popen(["taskkill", "/F", "/T", "/PID", str(pid)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=CNW)
            proc.wait(timeout=10)
        except Exception as e:
            log.warning(f"Falha ao matar processo filho {pid}: {e}")
    if pids:
        log.info(f"Cancelamento: {len(pids)} processo(s) filho encerrado(s) imediatamente.")


def suprimir_janelas_subprocess():
    """Faz todo subprocess (7-Zip, unrar, patool, etc.) rodar SEM janela de console.

    No exe windowed (sem console), cada chamada do motor TOKAI ao 7z.exe via
    subprocess abre uma janela CMD preta na cara do usuário. Em vez de editar
    cada subprocess espalhado no motor externo (que vive em cada máquina), faz-se
    um patch GLOBAL e idempotente de subprocess.Popen: injeta CREATE_NO_WINDOW no
    creationflags de todo processo filho. Cobre o motor inteiro e qualquer
    subprocess futuro, de forma distribuível (a correção viaja no nosso exe).
    Só atua no Windows; no-op em outros SOs.
    """
    global _subprocess_patched, _Popen_real
    if _subprocess_patched or sys.platform != "win32":
        return
    import subprocess

    CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    _Popen_original = subprocess.Popen
    _Popen_real = _Popen_original

    class _PopenSemJanela(_Popen_original):
        def __init__(self, *args, **kwargs):
            flags = kwargs.get("creationflags", 0)
            kwargs["creationflags"] = flags | CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
            # Registra o PID para o cancelamento poder matar a nossa árvore.
            try:
                with _pids_lock:
                    _pids_filhos.add(self.pid)
            except Exception:
                pass

    subprocess.Popen = _PopenSemJanela  # subprocess.run/call usam Popen internamente
    _subprocess_patched = True
    log.info("subprocess.Popen patchado: filhos rodam sem janela de console (CREATE_NO_WINDOW).")


def configurar_browsers_path():
    """Aponta PLAYWRIGHT_BROWSERS_PATH para o Chromium correto (empacotado no exe
    ou ms-playwright do usuário em dev). Também ativa o patch de subprocess, que
    rastreia os PIDs dos filhos (p/ o cancelamento matar a árvore) e suprime
    janelas CMD. Chamado por todos os engines antes de abrir o Playwright."""
    # Garante o rastreamento de PIDs (cancelamento imediato) sempre que um engine
    # vai usar o navegador — sem precisar editar cada engine.
    suprimir_janelas_subprocess()
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return

    if getattr(sys, "frozen", False):
        bundled = os.path.join(sys._MEIPASS, "ms-playwright")
        if os.path.isdir(bundled):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bundled
            log.info(f"PLAYWRIGHT_BROWSERS_PATH (empacotado) = {bundled}")
            return
        log.warning(f"ms-playwright empacotado não encontrado em {bundled}")

    user_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if os.path.isdir(user_dir):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = user_dir
        log.info(f"PLAYWRIGHT_BROWSERS_PATH (usuário) = {user_dir}")


@contextmanager
def policy_proactor():
    """Context manager: troca a event loop policy para Proactor (necessária para
    o Playwright criar subprocessos no Windows) e restaura a anterior ao sair.
    No-op fora do Windows."""
    import asyncio
    policy_anterior = None
    if sys.platform == "win32":
        policy_anterior = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        yield
    finally:
        if policy_anterior is not None:
            asyncio.set_event_loop_policy(policy_anterior)
