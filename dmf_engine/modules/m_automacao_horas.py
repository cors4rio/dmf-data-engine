"""
dmf_engine/modules/m_automacao_horas.py
Launcher da Automação de Horas para a Central DMF.

Ao ser executado, gera um token de sessão temporário (30s) e lança
services/automacao_horas/main.py como processo 32-bit separado.
O token passa a sessão do usuário logado na Central para a Automação (SSO).
"""
import os
import json
import logging
import secrets
import subprocess
import tempfile
from datetime import datetime, timedelta

from dmf_engine.modules.base import BaseModule, ModuleMeta

log = logging.getLogger("AutomacaoHoras")


def _eh_python_32bit(exe: str) -> bool:
    """True se o interpretador em `exe` é 32-bit (necessário p/ ODBC Sybase)."""
    try:
        out = subprocess.run(
            [exe, "-c", "import struct;print(struct.calcsize('P')*8)"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() == "32"
    except Exception:
        return False


def _resolver_python_32(override: str = "") -> str | None:
    """
    Resolve o caminho de um Python 32-bit, sem depender de config hardcoded.
    Ordem: override do config (se 32-bit válido) → py launcher (-3-32) →
    interpretador atual (se já for 32-bit). Retorna None se nada servir.
    """
    # 1. Override explícito do config — só vale se existir E for 32-bit
    if override and os.path.exists(override) and _eh_python_32bit(override):
        return override

    # 2. Windows py launcher: resolve o 32-bit instalado sem caminho fixo
    try:
        out = subprocess.run(
            ["py", "-3-32", "-c", "import sys;print(sys.executable)"],
            capture_output=True, text=True, timeout=10,
        )
        cand = out.stdout.strip()
        if cand and os.path.exists(cand) and _eh_python_32bit(cand):
            return cand
    except Exception:
        pass

    # 3. Último recurso: o próprio interpretador, se já for 32-bit
    import sys
    if not getattr(sys, "frozen", False) and _eh_python_32bit(sys.executable):
        return sys.executable

    return None


class AutomacaoHorasLauncher(BaseModule):

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="automacao_horas",
            nome="Automação de Horas",
            desc="Apuração e lançamento de horas via ERP Domínio — Fiscal, Contábil e DP.",
            setor="GESTAO",
            icon="ti-clock-play",
            color="#2B65B5",
            papeis=["admin", "contabil", "fiscal", "dp", "legalizacao"],
            execucao="sync",   # lança subprocesso e retorna sucesso/erro na hora
        )

    def execute(self, opcoes: dict) -> dict:
        sessao = self.sessao()
        if not sessao:
            return {"ok": False, "erro": "Sessão não autenticada."}

        # 1. Gerar token de sessão único (30 segundos de validade)
        token = secrets.token_hex(16)
        dados_sessao = {
            "usuario":   sessao["nome"],
            "label":     sessao.get("label", ""),
            "papel":     sessao["papel"],
            "maquina":   sessao.get("maquina", ""),
            "expira_em": (datetime.now() + timedelta(seconds=30)).isoformat(),
        }
        caminho_token = os.path.join(tempfile.gettempdir(), f"dmf_session_{token}.json")
        try:
            with open(caminho_token, "w", encoding="utf-8") as f:
                json.dump(dados_sessao, f)
        except Exception as e:
            return {"ok": False, "erro": f"Falha ao criar token de sessão: {e}"}

        # 2. Resolver caminhos — interpretador 32-bit descoberto automaticamente.
        #    O config é apenas override opcional; em dev não é necessário.
        python_32 = _resolver_python_32(self.cfg("automacao_horas_python") or "")
        app_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__),          # dmf_engine/modules/
            "..", "..",                          # raiz do projeto
            "services", "automacao_horas", "main.py"
        ))

        if not os.path.exists(app_path):
            os.remove(caminho_token)
            return {"ok": False, "erro": f"Automação não encontrada: {app_path}"}
        if not python_32:
            os.remove(caminho_token)
            return {
                "ok": False,
                "erro": "Python 32-bit não encontrado. Instale um Python 32-bit "
                        "(py -3-32) ou defina 'automacao_horas_python' no config.json "
                        "apontando para um python.exe 32-bit.",
            }

        # 3. Lançar como processo separado (janela PyWebView própria).
        #    stderr → log de erros do automacao_horas, para que uma falha de boot
        #    do subprocesso (import quebrado, dep faltando) não desapareça.
        log_err = os.path.join(os.path.dirname(app_path), "automacao_horas_errors.log")
        try:
            err_fp = open(log_err, "a", encoding="utf-8")
        except Exception:
            err_fp = subprocess.DEVNULL

        try:
            proc = subprocess.Popen(
                [python_32, app_path, "--session-token", token],
                stdout=subprocess.DEVNULL,
                stderr=err_fp,
                creationflags=(
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                ),
            )
        except Exception as e:
            if err_fp not in (subprocess.DEVNULL, None):
                err_fp.close()
            if os.path.exists(caminho_token):
                os.remove(caminho_token)
            return {"ok": False, "erro": str(e)}

        # Verificação rápida: se o subprocesso morre no boot (ex: erro de import),
        # detecta e reporta em vez de mostrar "aberto" para uma janela que não veio.
        try:
            codigo = proc.wait(timeout=1.2)
        except subprocess.TimeoutExpired:
            codigo = None  # ainda vivo → boot OK, janela abrindo

        if err_fp not in (subprocess.DEVNULL, None):
            err_fp.close()

        if codigo is not None and codigo != 0:
            log.error(f"Subprocesso encerrou no boot (código {codigo}). Veja {log_err}.")
            if os.path.exists(caminho_token):
                os.remove(caminho_token)
            return {
                "ok": False,
                "erro": f"A Automação de Horas fechou ao iniciar (código {codigo}). "
                        f"Detalhes em automacao_horas_errors.log.",
            }

        return {"ok": True, "msg": "Automação de Horas aberta com sessão ativa."}
