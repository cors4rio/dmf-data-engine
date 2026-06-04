"""
dmf_engine/modules/m_sem_movimento_nfse.py
Módulo Sem Movimento NFS-e Salvador (Padrão A) — adaptador BaseModule.

Molde: m_buscar_xml.py
"""
import os
import sys
import logging

from dmf_engine.modules.base import BaseModule, ModuleMeta

log = logging.getLogger("SemMovimentoNfse")

_SVC_DIR    = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "sem_movimento_nfse")
)
_ENGINE_DIR = os.path.join(_SVC_DIR, "sm_engine")


def _injetar_path():
    for p in (_ENGINE_DIR, _SVC_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)


class SemMovimentoNfseModule(BaseModule):

    _service_instance = None

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="sem_movimento_nfse",
            nome="Sem Movimento NFS-e Salvador",
            desc="Emite comprovantes de ausência de movimento no portal NFS-e de Salvador.",
            setor="FISCAL",
            icon="ti-file-certificate",
            color="#B06A00",
            papeis=["admin", "fiscal"],
        )

    def _get_service(self):
        if SemMovimentoNfseModule._service_instance is None:
            _injetar_path()
            from sm_service import SemMovimentoService  # noqa

            def _on_event(evento: str, dados: dict):
                self.emit(evento, dados)

            def _config_fn():
                return self._config.load()

            SemMovimentoNfseModule._service_instance = SemMovimentoService(
                on_event_cb=_on_event,
                config_fn=_config_fn,
            )
        return SemMovimentoNfseModule._service_instance

    def execute(self, opcoes: dict) -> dict:
        import traceback
        try:
            acao = opcoes.get("acao", "status")
            svc  = self._get_service()

            if acao == "cancelar":
                return svc.cancelar()

            if acao == "status":
                return {"ok": True, **svc.get_status()}

            return {"ok": False, "erro": f"Ação desconhecida: {acao}"}

        except Exception as e:
            log.error(traceback.format_exc())
            return {"ok": False, "erro": str(e)}

    def get_status(self) -> dict:
        try:
            return self._get_service().get_status()
        except Exception:
            return {"status": "idle"}
