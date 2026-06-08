"""
dmf_engine/modules/m_tff_salvador.py
Módulo TFF Salvador — Procuradoria (Padrão A) — adaptador BaseModule.

Download automático das 4 guias de Taxa de Fiscalização e Funcionamento
para lote de clientes no portal da prefeitura de Salvador.

Molde: m_sem_movimento_nfse.py
"""
import os
import sys
import logging

from dmf_engine.modules.base import BaseModule, ModuleMeta

log = logging.getLogger("TffSalvador")

_SVC_DIR    = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "services", "tff_salvador")
)
_ENGINE_DIR = os.path.join(_SVC_DIR, "tf_engine")


def _injetar_path():
    for p in (_ENGINE_DIR, _SVC_DIR):
        if p not in sys.path:
            sys.path.insert(0, p)


class TffSalvadorModule(BaseModule):

    _service_instance = None

    @property
    def meta(self) -> ModuleMeta:
        return ModuleMeta(
            id="tff_salvador",
            nome="TFF Salvador",
            desc="Download automático das 4 guias de TFF para lote de clientes.",
            setor="PROCURADORIA",
            icon="ti-file-download",
            color="#4A3080",
            papeis=["admin", "procuradoria"],
        )

    def _get_service(self):
        if TffSalvadorModule._service_instance is None:
            _injetar_path()
            from tf_service import TffSalvadorService  # noqa

            def _on_event(evento: str, dados: dict):
                self.emit(evento, dados)

            def _config_fn():
                return self._config.load()

            TffSalvadorModule._service_instance = TffSalvadorService(
                on_event_cb=_on_event,
                config_fn=_config_fn,
            )
        return TffSalvadorModule._service_instance

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
