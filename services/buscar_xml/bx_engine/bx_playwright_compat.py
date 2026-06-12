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
    global _subprocess_patched
    if _subprocess_patched or sys.platform != "win32":
        return
    import subprocess

    CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    _Popen_original = subprocess.Popen

    class _PopenSemJanela(_Popen_original):
        def __init__(self, *args, **kwargs):
            flags = kwargs.get("creationflags", 0)
            kwargs["creationflags"] = flags | CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = _PopenSemJanela  # subprocess.run/call usam Popen internamente
    _subprocess_patched = True
    log.info("subprocess.Popen patchado: filhos rodam sem janela de console (CREATE_NO_WINDOW).")


def configurar_browsers_path():
    """Aponta PLAYWRIGHT_BROWSERS_PATH para o Chromium correto (empacotado no exe
    ou ms-playwright do usuário em dev). No-op se a env já estiver definida."""
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
