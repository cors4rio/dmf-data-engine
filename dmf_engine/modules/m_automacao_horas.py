"""
dmf_engine/modules/m_automacao_horas.py
Adaptador da Automação de Horas para a Central DMF.

Abre a janela de Horas DENTRO do processo da Central (64-bit), sem subprocesso
e sem token SSO por arquivo. A sessão atual da Central é passada direto.
Ver docs/migracao-64bit.md (Passo 4) e memória migracao-horas-inline.

Antes da migração 64-bit, isto lançava um subprocesso Python 32-bit rodando
services/automacao_horas/main.py. Como o banco agora conecta via DSN-less em
64-bit, o subprocesso deixou de ser necessário — e com ele somem os bugs de
"main.py não encontrado" no exe frozen e a dependência de Python 32-bit.
"""
import os
import sys
import logging

from dmf_engine.modules.base import BaseModule, ModuleMeta

log = logging.getLogger("AutomacaoHoras")

# services/automacao_horas/ — onde vive o stack ah_*
_AH_DIR = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "services", "automacao_horas"
))


def _injetar_path():
    """Garante services/automacao_horas/ no sys.path para importar ah_launcher."""
    if _AH_DIR not in sys.path:
        sys.path.insert(0, _AH_DIR)


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
            execucao="sync",   # abre a janela e retorna sucesso/erro na hora
        )

    def execute(self, opcoes: dict) -> dict:
        sessao = self.sessao()
        if not sessao:
            return {"ok": False, "erro": "Sessão não autenticada."}

        if not os.path.isdir(_AH_DIR):
            return {"ok": False, "erro": f"Automação de Horas não encontrada em {_AH_DIR}."}

        _injetar_path()
        try:
            from ah_launcher import abrir_janela_horas
        except Exception as e:
            log.error("Falha ao importar ah_launcher: %s", e)
            return {"ok": False, "erro": f"Falha ao carregar a Automação de Horas: {e}"}

        try:
            return abrir_janela_horas(sessao=sessao)
        except Exception as e:
            log.error("Falha ao abrir a janela de Horas: %s", e)
            return {"ok": False, "erro": str(e)}
