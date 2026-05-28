"""
dmf_engine/modules/m_automacao_horas.py
Launcher da Automação de Horas para a Central DMF.

Ao ser executado, gera um token de sessão temporário (30s) e lança
services/automacao_horas/main.py como processo 32-bit separado.
O token passa a sessão do usuário logado na Central para a Automação (SSO).
"""
import os
import json
import secrets
import subprocess
import tempfile
from datetime import datetime, timedelta

from dmf_engine.modules.base import BaseModule, ModuleMeta


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
            papeis=["admin", "contabil", "fiscal", "dp"],
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

        # 2. Resolver caminhos
        python_32 = self.cfg("automacao_horas_python")
        app_path = os.path.normpath(os.path.join(
            os.path.dirname(__file__),          # dmf_engine/modules/
            "..", "..",                          # raiz do projeto
            "services", "automacao_horas", "main.py"
        ))

        if not os.path.exists(app_path):
            os.remove(caminho_token)
            return {"ok": False, "erro": f"Automação não encontrada: {app_path}"}
        if not python_32 or not os.path.exists(python_32):
            os.remove(caminho_token)
            return {
                "ok": False,
                "erro": "Python 32-bit não configurado. "
                        "Adicione 'automacao_horas_python' no config.json com o caminho completo.",
            }

        # 3. Lançar como processo separado (janela PyWebView própria)
        self.progress(10, "Abrindo Automação de Horas...")
        try:
            subprocess.Popen(
                [python_32, app_path, "--session-token", token],
                creationflags=(
                    subprocess.DETACHED_PROCESS
                    | subprocess.CREATE_NEW_PROCESS_GROUP
                ),
            )
            self.progress(100, "Automação de Horas aberta.")
            return {"ok": True, "msg": "Automação de Horas aberta com sessão ativa."}
        except Exception as e:
            if os.path.exists(caminho_token):
                os.remove(caminho_token)
            return {"ok": False, "erro": str(e)}
